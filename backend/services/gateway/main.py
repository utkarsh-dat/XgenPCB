"""
PCB Builder - API Gateway
Main FastAPI application that mounts all service routers.
Production-grade with middleware, health probes, and structured errors.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.exceptions import HTTPException as StarletteHTTPException

from shared.config import get_settings
from shared.logging_config import logger
from shared.middleware.correlation import CorrelationIdMiddleware
from shared.middleware.error_handler import (
    APIError,
    generic_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from shared.middleware.idempotency import IdempotencyMiddleware
from shared.middleware.rate_limit import limiter
from shared.schemas import HealthResponse

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup/shutdown lifecycle."""
    logger.info(
        "API starting",
        environment=settings.app_env,
        version=settings.app_version,
    )
    yield
    logger.info("API shutting down")


app = FastAPI(
    title=settings.app_title,
    version=settings.app_version,
    description="Production-Grade Autonomous PCB Builder API",
    default_response_class=ORJSONResponse,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── Middleware (order matters: innermost first) ───────────────

# 1. Correlation ID (first to capture)
app.add_middleware(CorrelationIdMiddleware)

# 2. Idempotency
app.add_middleware(IdempotencyMiddleware)

# 3. CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 4. Rate limiting (stateless)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── Exception Handlers ────────────────────────────────────────

app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(APIError, generic_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# ── Mount Service Routers ─────────────────────────────────────

from services.user_service.routes import router as user_router
from services.project_service.routes import router as project_router
from services.ai_service.routes import router as ai_router
from services.eda_service.routes import router as eda_router
from services.fab_service.routes import router as fab_router
from services.component_service.routes import router as component_router
from services.analytics_service.routes import router as analytics_router

app.include_router(user_router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(project_router, prefix="/api/v1/projects", tags=["Projects & Designs"])
app.include_router(ai_router, prefix="/api/v1/ai", tags=["AI Services"])
app.include_router(eda_router, prefix="/api/v1/eda", tags=["EDA Services"])
app.include_router(fab_router, prefix="/api/v1/fab", tags=["Fabrication"])
app.include_router(component_router, prefix="/api/v1/components", tags=["Components"])
app.include_router(analytics_router, prefix="/api/v1/analytics", tags=["Analytics"])


@app.get("/", tags=["Health"])
async def root():
    return {
        "service": settings.app_title,
        "version": settings.app_version,
        "status": "operational",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy", "environment": settings.app_env}


@app.get("/health/live", tags=["Health"])
async def liveness_probe():
    """Liveness probe - is the service running?"""
    return {"status": "alive"}


@app.get("/health/ready", tags=["Health"])
async def readiness_probe():
    """Readiness probe - can it accept traffic?"""
    try:
        # Quick DB check
        from shared.database import engine
        from sqlalchemy import text
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "ready", "database": "connected"}
    except Exception as e:
        logger.warning("Readiness probe failed", error=str(e))
        return ORJSONResponse(
            status_code=503,
            content={"status": "not_ready", "database": "unavailable", "error": str(e)},
        )


@app.get("/health/deep", tags=["Health"], response_model=HealthResponse)
async def deep_health_check():
    """Deep health check - tests all dependencies."""
    from datetime import datetime, timezone

    checks = {
        "api": "healthy",
        "database": "unknown",
        "redis": "unknown",
        "celery": "unknown",
    }
    healthy = True

    # Database check
    try:
        from shared.database import engine
        from sqlalchemy import text
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["database"] = "healthy"
    except Exception as e:
        checks["database"] = f"unhealthy: {str(e)}"
        healthy = False

    # Redis check
    try:
        import redis.asyncio as redis
        r = redis.from_url(settings.redis_url)
        await r.ping()
        await r.close()
        checks["redis"] = "healthy"
    except Exception as e:
        checks["redis"] = f"unhealthy: {str(e)}"
        healthy = False

    # Celery check
    try:
        from shared.celery_app import celery_app
        inspector = celery_app.control.inspect()
        active = inspector.active()
        checks["celery"] = "healthy" if active is not None else "no_workers"
    except Exception as e:
        checks["celery"] = f"unhealthy: {str(e)}"
        healthy = False

    status_code = 200 if healthy else 503
    response = {
        "status": "healthy" if healthy else "degraded",
        "version": settings.app_version,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
    }

    return ORJSONResponse(status_code=status_code, content=response)
