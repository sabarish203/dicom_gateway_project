import datetime
from fastapi import FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
import logging
from .settings import settings
from .metrics import setup_metrics

# Initialize logger
logger = logging.getLogger(__name__)

app = FastAPI(
    title="DICOM Gateway API",
    description="Gateway service for DICOM image processing",
    version="1.0.0"
)

# Setup CORS (adjust as needed for your environment)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize metrics
setup_metrics(app)

@app.get("/", include_in_schema=False)
async def root():
    """Hidden root endpoint that redirects to docs"""
    return Response(
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
        headers={"Location": "/docs"}
    )

@app.get("/health")
async def health_check():
    """
    Health check endpoint
    
    Returns:
        dict: Service status with timestamp
    """
    logger.info("Health check requested")
    return {
        "status": "ok",
        "version": app.version,
        "timestamp": datetime.datetime.utcnow().isoformat()
    }

@app.get("/metrics")
async def get_metrics():
    """
    Prometheus metrics endpoint
    
    Returns:
        Response: Metrics data in Prometheus format
    """
    logger.debug("Metrics endpoint accessed")
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )

# Example of how to add additional routers
# from .routes import dicom_router
# app.include_router(dicom_router, prefix="/dicom", tags=["DICOM"])