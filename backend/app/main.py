import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config.settings import settings
from app.config.rate_limiter import limiter
from app.config.logger import api_logger
from app.routes.health import router as health_router
from app.routes.crowd import router as crowd_router
from app.routes.detection import router as detection_router
from app.routes.tracking import router as tracking_router
from app.routes.density import router as density_router
from app.routes.risk import router as risk_router
from app.routes.dashboard import router as dashboard_router
from app.routes.cameras import router as cameras_router
from app.routes.alerts import router as alerts_router
from app.routes.analytics import router as analytics_router
from app.routes.demo import router as demo_router
from app.websocket.tracking_socket import router as websocket_router

# Initialize FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="CrowdEye AI - Real-time Crowd Safety and Monitoring Platform",
    docs_url="/docs",
    redoc_url="/redoc"
)

# TASK 8: SlowAPI Rate Limiter State & Exception Handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# TASK 14: API Request & Latency Logging Middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration_ms = round((time.time() - start_time) * 1000.0, 2)
    api_logger.info(
        f"{request.method} {request.url.path} - Status: {response.status_code} - {duration_ms}ms"
    )
    return response

# Configure Cross-Origin Resource Sharing (CORS) - TASK 7 Hardening
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Startup event: Pre-warm & load model once (TASK 2)
@app.on_event("startup")
def startup_event():
    try:
        from ai.detection.yolo_detector import YOLODetector
        YOLODetector.load_model_once()
    except Exception:
        pass

# Include Route Modules
app.include_router(health_router)
app.include_router(crowd_router)
app.include_router(detection_router)
app.include_router(detection_router, prefix="/api/v1")
app.include_router(tracking_router)
app.include_router(tracking_router, prefix="/api/v1")
app.include_router(density_router)
app.include_router(density_router, prefix="/api/v1")
app.include_router(risk_router)
app.include_router(risk_router, prefix="/api/v1")
app.include_router(dashboard_router)
app.include_router(cameras_router)
app.include_router(alerts_router)
app.include_router(analytics_router)
app.include_router(demo_router)
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
