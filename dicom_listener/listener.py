import os
import logging
import pika
import json
import pydicom
from pathlib import Path
from pynetdicom import AE, evt
from pynetdicom.sop_class import Verification, CTImageStorage
import ssl
from typing import Optional


class Config:
    STORAGE_PATH = Path("./buffer")
    LISTEN_PORT = 11112
    AE_TITLE = "DICOM_GATEWAY"
    CERT_DIR = Path("certs")
    SERVER_CRT = CERT_DIR / "server.crt"
    SERVER_KEY = CERT_DIR / "server.key"
    TLS_ENABLED = os.getenv('TLS_ENABLED', 'false').lower() == 'true'
    RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'rabbitmq')
    RABBITMQ_QUEUE = 'new_study'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class RabbitMQPublisher:
    def __init__(self):
        self.connection = None
        self.channel = None
        
    def connect(self) -> bool:
        try:
            self.connection = pika.BlockingConnection(
                pika.ConnectionParameters(Config.RABBITMQ_HOST)
            )
            self.channel = self.connection.channel()
            self.channel.queue_declare(queue=Config.RABBITMQ_QUEUE)
            return True
        except Exception as e:
            logger.error(f"RabbitMQ connection failed: {e}")
            return False
            
    def publish_study(self, study_metadata: dict) -> bool:
        try:
            if not self.channel or self.connection.is_closed:
                if not self.connect():
                    return False
                    
            self.channel.basic_publish(
                exchange='',
                routing_key=Config.RABBITMQ_QUEUE,
                body=json.dumps(study_metadata),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # make message persistent
                ))
            logger.info(f"Published study to RabbitMQ: {study_metadata['study_uid']}")
            return True
        except Exception as e:
            logger.error(f"Failed to publish study: {e}")
            return False
            
    def close(self):
        if self.connection and not self.connection.is_closed:
            self.connection.close()

publisher = RabbitMQPublisher()

def handle_echo(event):
    """Handle C-ECHO request (verification)"""
    requester = event.assoc.requestor.ae_title or "Unknown"
    logger.info(f"Received C-ECHO from {requester}")
    return 0x0000
def is_study_complete(study_path: Path) -> bool:
    """Check if all DICOM slices arrived using headers"""
    dcm_files = list(study_path.glob("**/*.dcm"))
    if not dcm_files:
        return False
    
    try:
        ds = pydicom.dcmread(dcm_files[0])
        expected = getattr(ds, "NumberOfSeriesRelatedInstances", len(dcm_files))
        return len(dcm_files) >= expected
    except Exception as e:
        logger.error(f"Study completion check failed: {e}")
        return False
def handle_store(event):
    """Handle C-STORE request (DICOM file storage)"""
    try:
        ds = event.dataset
        ds.file_meta = event.file_meta
        
        storage_path = (
            Config.STORAGE_PATH / 
            ds.StudyInstanceUID / 
            ds.SeriesInstanceUID
        )
        storage_path.mkdir(parents=True, exist_ok=True)
        
        filepath = storage_path / f"{ds.SOPInstanceUID}.dcm"
        ds.save_as(filepath, write_like_original=False)
        
        logger.info(f"Stored: {filepath}")
        
        # Check if study is complete
        study_path = Config.STORAGE_PATH / ds.StudyInstanceUID
        if is_study_complete(study_path):
            study_metadata = {
                "study_uid": ds.StudyInstanceUID,
                "patient_id": ds.PatientID,
                "modality": ds.Modality,
                "slice_count": len(list(study_path.glob("**/*.dcm"))),
                "storage_path": str(study_path)
            }
            publisher.publish_study(study_metadata)
            
        return 0x0000
        
    except Exception as e:
        logger.error(f"Storage failed: {e}", exc_info=True)
        return 0xC001

def configure_tls() -> Optional[ssl.SSLContext]:
    """Configure TLS for secure DICOM communication"""
    if not Config.TLS_ENABLED:
        return None
        
    if not (Config.SERVER_CRT.exists() and Config.SERVER_KEY.exists()):
        logger.error("TLS enabled but missing certificate files")
        return None

    try:
        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        context.load_cert_chain(
            certfile=str(Config.SERVER_CRT),
            keyfile=str(Config.SERVER_KEY)
        )
        context.set_ciphers('ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384')
        return context
    except ssl.SSLError as e:
        logger.error(f"TLS config failed: {e}")
        return None

def start_server():
    """Start the DICOM SCP server"""
    ae = AE(ae_title=Config.AE_TITLE)
    ae.add_supported_context(Verification)
    ae.add_supported_context(CTImageStorage)

    # Ensure directories exist
    Config.STORAGE_PATH.mkdir(exist_ok=True)
    Config.CERT_DIR.mkdir(exist_ok=True)

    ssl_context = configure_tls()
    
    logger.info(f"Starting DICOM SCP on port {Config.LISTEN_PORT} (TLS: {'Enabled' if ssl_context else 'Disabled'})")
    logger.info(f"RabbitMQ configured for host: {Config.RABBITMQ_HOST}")

    try:
        # Initialize RabbitMQ connection
        if not publisher.connect():
            logger.warning("Initial RabbitMQ connection failed. Will retry during publishing.")
        
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
        logger.info("Server stopped by user")
    except Exception as e:
        logger.critical(f"Server failed: {e}", exc_info=True)
    finally:
        publisher.close()

if __name__ == "__main__":
    start_server()