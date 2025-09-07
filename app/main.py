from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.config import settings
from app.api.v1.routes.sms import router as sms_router
from app.api.v1.routes.email import router as email_router
from app.core.tasks import cleanup_logs_task
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print(f"Starting {settings.app_name} v{settings.app_version}")
    print("FastAPI server started - scheduler available via manual triggers")
    yield
    # Shutdown
    print(f"Shutting down {settings.app_name}")

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
    allow_origins=["*"],  # Configure this for production
    allow_credentials=True,
    allow_methods=["*"],
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
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version
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
