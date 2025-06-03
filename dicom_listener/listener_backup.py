import os
import logging
from pathlib import Path
from pynetdicom import AE, evt
from pynetdicom.sop_class import Verification, CTImageStorage
import ssl

# ===== Configuration =====
class Config:
    STORAGE_PATH = Path("./buffer")
    LISTEN_PORT = 11112
    AE_TITLE = "DICOM_GATEWAY"
    CERT_DIR = Path("certs")
    SERVER_CRT = CERT_DIR / "server.crt"
    SERVER_KEY = CERT_DIR / "server.key"
    TLS_ENABLED = os.getenv('TLS_ENABLED', 'false').lower() == 'true'

# ===== Logging =====
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# ===== Handlers =====
def handle_echo(event):
    """Handle C-ECHO requests with validation."""
    requester = event.assoc.requestor.ae_title or "Unknown"
    logger.info(f"Received C-ECHO from {requester}")
    return 0x0000  # Success

def handle_store(event):
    """Handle C-STORE requests with proper error handling."""
    try:
        ds = event.dataset
        ds.file_meta = event.file_meta  # Preserve metadata
        
        # Create directory structure
        storage_path = (
            Config.STORAGE_PATH / 
            ds.StudyInstanceUID / 
            ds.SeriesInstanceUID
        )
        storage_path.mkdir(parents=True, exist_ok=True)
        
        # Save file with validation
        filepath = storage_path / f"{ds.SOPInstanceUID}.dcm"
        ds.save_as(filepath, write_like_original=False)
        
        logger.info(f"Successfully stored: {filepath}")
        return 0x0000  # Success
        
    except Exception as e:
        logger.error(f"Storage failed: {str(e)}", exc_info=True)
        return 0xC001  # Processing failure

# ===== Server Setup =====
def configure_tls():
    """Configure TLS with proper validation."""
    if not Config.TLS_ENABLED:
        return None
        
    if not (Config.SERVER_CRT.exists() and Config.SERVER_KEY.exists()):
        logger.error("TLS enabled but certificate files missing!")
        return None

    try:
        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        context.load_cert_chain(
            certfile=str(Config.SERVER_CRT),
            keyfile=str(Config.SERVER_KEY)
        )
        context.set_ciphers('ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384')
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        return context
    except ssl.SSLError as e:
        logger.error(f"TLS configuration failed: {e}")
        return None

def start_server():
    """Start DICOM SCP server with proper cleanup."""
    ae = AE(ae_title=Config.AE_TITLE)
    ae.add_supported_context(Verification)
    ae.add_supported_context(CTImageStorage)

    # Ensure directories exist
    Config.STORAGE_PATH.mkdir(exist_ok=True)
    Config.CERT_DIR.mkdir(exist_ok=True)

    ssl_context = configure_tls() if Config.TLS_ENABLED else None
    
    logger.info(
        f"Starting DICOM SCP on port {Config.LISTEN_PORT} "
        f"(TLS: {'Enabled' if ssl_context else 'Disabled'})"
    )

    try:
        ae.start_server(
            ('0.0.0.0', Config.LISTEN_PORT),
            evt_handlers=[
                (evt.EVT_C_ECHO, handle_echo),
                (evt.EVT_C_STORE, handle_store)
            ],
            ssl_context=ssl_context,
            block=True
        )
    except KeyboardInterrupt:
        logger.info("Server shutdown requested")
    except Exception as e:
        logger.critical(f"Server failed: {e}", exc_info=True)
    finally:
        logger.info("Server stopped")

if __name__ == "__main__":
    start_server()