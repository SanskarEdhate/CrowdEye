from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config.settings import settings
from app.routes.health import router as health_router
from app.routes.crowd import router as crowd_router
from app.routes.detection import router as detection_router
from app.routes.tracking import router as tracking_router
from app.routes.density import router as density_router
from app.websocket.tracking_socket import router as websocket_router

# Initialize FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="CrowdEye AI - Real-time Crowd Safety and Monitoring Platform",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure Cross-Origin Resource Sharing (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Route Modules
app.include_router(health_router)
app.include_router(crowd_router)
app.include_router(detection_router)
app.include_router(detection_router, prefix="/api/v1")
app.include_router(tracking_router)
app.include_router(tracking_router, prefix="/api/v1")
app.include_router(density_router)
app.include_router(density_router, prefix="/api/v1")
app.include_router(websocket_router)



@app.get("/")
def read_root():
    """
    Root status endpoint.
    Verifies that the CrowdEye AI backend service is running.
    """
    return {
        "project": "CrowdEye AI",
        "status": "Backend running"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
