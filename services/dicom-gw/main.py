import os
import threading
import logging
from pathlib import Path
from fastapi import FastAPI
from pynetdicom import AE, evt
from pynetdicom.sop_class import Verification, CTImageStorage
import uvicorn

# ===== Configuration =====
class Config:
    DICOM_PORT = int(os.getenv("DICOM_PORT", 11112))
    HTTP_PORT = int(os.getenv("HTTP_PORT", 8000))
    STORAGE_PATH = Path(os.getenv("STORAGE_PATH", "./buffer"))
    AE_TITLE = os.getenv("AE_TITLE", "DICOM_GATEWAY")
    MAX_PDU = 16382

# ===== Logging Setup =====
def configure_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    # Reduce verbose logging from dependencies
    for logger_name in ['pynetdicom', 'uvicorn', 'asyncio']:
        logging.getLogger(logger_name).setLevel(logging.WARNING)

# ===== FastAPI App =====
app = FastAPI(title="DICOM Gateway")

# ===== DICOM Handlers =====
def handle_store(event):
    """Handle incoming DICOM C-STORE requests with validation"""
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
        
        logging.info(f"Stored DICOM: {filepath}")
        return 0x0000  # Success
        
    except Exception as e:
        logging.error(f"Storage failed: {e}", exc_info=True)
        return 0xC001  # Processing failure

# ===== DICOM Service =====
class DICOMService:
    def __init__(self):
        self.ae = None
        self.server_thread = None

    def start(self):
        """Start DICOM SCP in background thread"""
        try:
            self.ae = AE(ae_title=Config.AE_TITLE)
            self.ae.add_supported_context(Verification)
            self.ae.add_supported_context(CTImageStorage)
            
            self.server_thread = threading.Thread(
                target=self._run_server,
                daemon=True,
                name="DICOM-SCP"
            )
            self.server_thread.start()
            
        except Exception as e:
            logging.critical(f"Failed to start DICOM service: {e}")
            raise

    def _run_server(self):
        """Main server loop"""
        logging.info(f"Starting DICOM listener on port {Config.DICOM_PORT}")
        try:
            self.ae.start_server(
                ('0.0.0.0', Config.DICOM_PORT),
                evt_handlers=[(evt.EVT_C_STORE, handle_store)],
                block=True
            )
        except Exception as e:
            logging.critical(f"DICOM listener crashed: {e}")

# ===== API Endpoints =====
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "services": {
            "dicom": "running",
            "http": "running"
        }
    }

@app.get("/dicom-echo")
async def perform_echo_test():
    """DICOM Verification Service (C-ECHO)"""
    try:
        ae = AE(ae_title=f"{Config.AE_TITLE}_SCU")
        ae.add_requested_context(Verification)
        
        logging.info("Initiating DICOM echo test")
        with ae.associate(
            'localhost', 
            Config.DICOM_PORT, 
            ae_title=Config.AE_TITLE,
            max_pdu=Config.MAX_PDU
        ) as assoc:
            if assoc.is_established:
                status = assoc.send_c_echo()
                if status.Status == 0x0000:
                    logging.info("Echo test succeeded")
                    return {"status": "success"}
                
                logging.error(f"Echo failed with status: {status.Status:04X}")
                return {"status": "error", "code": status.Status}
            
            logging.error("Association rejected")
            return {"status": "error", "reason": "Association rejected"}
            
    except Exception as e:
        logging.error(f"Echo test failed: {e}")
        return {"status": "error", "reason": str(e)}

# ===== Startup =====
def initialize_services():
    """Initialize all application services"""
    configure_logging()
    
    # Ensure storage directory exists
    Config.STORAGE_PATH.mkdir(parents=True, exist_ok=True)
    
    # Start DICOM service
    dicom_service = DICOMService()
    dicom_service.start()
    
    logging.info(f"HTTP server starting on port {Config.HTTP_PORT}")
    return dicom_service

# ===== Main Application =====
if __name__ == "__main__":
    initialize_services()
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=Config.HTTP_PORT,
        log_config=None,  # Use our logging config
        access_log=False
    )