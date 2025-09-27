from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.core.config import settings
from app.api.v1.routes.sms import router as sms_router
from app.api.v1.routes.email import router as email_router
from app.core.tasks import cleanup_logs_task
from app.services.otp.otp_consumer import otp_consumer_service
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info("FastAPI server started - scheduler available via manual triggers")
    
    # Start OTP consumer service
    try:
        logger.info("Starting OTP consumer service...")
        otp_consumer_service.start_consuming()
        logger.info("OTP consumer service started successfully")
    except Exception as e:
        logger.error(f"Failed to start OTP consumer service: {e}")
        logger.warning("Application will continue without OTP consumer functionality")
    
    yield
    
    # Shutdown
    logger.info(f"Shutting down {settings.app_name}")
    try:
        otp_consumer_service.stop_consuming()
        logger.info("OTP consumer service stopped")
    except Exception as e:
        logger.error(f"Error stopping OTP consumer service: {e}")

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(",") if hasattr(settings, 'cors_origins') and settings.cors_origins else ["http://localhost:3000", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Include routers
app.include_router(sms_router)
app.include_router(email_router)


@app.get("/")
async def root():
    """
    Root endpoint
    """
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": settings.app_version,
        "docs": "/docs",
        "redoc": "/redoc"
    }


@app.get("/health")
async def health_check():
    """
    Health check endpoint
    """
    otp_consumer_healthy = otp_consumer_service.is_healthy()
    
    return {
        "status": "healthy" if otp_consumer_healthy else "degraded",
        "service": settings.app_name,
        "version": settings.app_version,
        "otp_consumer": "healthy" if otp_consumer_healthy else "unhealthy"
    }


@app.post("/maintenance/cleanup-logs")
async def manual_cleanup_logs(background_tasks: BackgroundTasks):
    """
    Manually trigger log cleanup
    """
    try:
        # Run cleanup in background
        cleanup_logs_task.delay()

        return {
            "message": "Log cleanup task has been queued",
            "status": "accepted"
        }
    except Exception as e:
        return {
            "error": f"Failed to queue cleanup task: {str(e)}",
            "status": "failed"
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )
