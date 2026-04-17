"""
PCB Builder - API Gateway
Main FastAPI application that mounts all service routers.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from shared.config import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup/shutdown lifecycle."""
    # Startup
    print(f"🚀 PCB Builder API starting in {settings.app_env} mode")
    yield
    # Shutdown
    print("👋 PCB Builder API shutting down")


app = FastAPI(
    title=settings.app_title,
    version=settings.app_version,
    description="World-Class Autonomous PCB Builder API",
    default_response_class=ORJSONResponse,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Mount Service Routers ────────────────────────────────────

from services.user_service.routes import router as user_router
from services.project_service.routes import router as project_router
from services.ai_service.routes import router as ai_router
from services.eda_service.routes import router as eda_router
from services.fab_service.routes import router as fab_router

app.include_router(user_router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(project_router, prefix="/api/v1/projects", tags=["Projects & Designs"])
app.include_router(ai_router, prefix="/api/v1/ai", tags=["AI Services"])
app.include_router(eda_router, prefix="/api/v1/eda", tags=["EDA Services"])
app.include_router(fab_router, prefix="/api/v1/fab", tags=["Fabrication"])


@app.get("/", tags=["Health"])
async def root():
    return {
        "service": "PCB Builder API",
        "version": settings.app_version,
        "status": "operational",
    }


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy", "environment": settings.app_env}
