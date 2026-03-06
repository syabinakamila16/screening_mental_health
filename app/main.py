import os
import uvicorn
import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI

from app.api.endpoints import screening as screening_module
from app.models.schemas import InMemoryKnowledgeProvider
from app.services.screening_service import ScreeningService
from app.repositories.storage import FileStorageRepository


# ==============================
# CONFIGURATION
# ==============================
class Settings:
    def __init__(self):
        self.app_name = os.getenv("APP_NAME", "RESTful API Screening Kesehatan Mental")
        self.app_version = os.getenv("APP_VERSION", "1.0.0")
        self.api_prefix = os.getenv("API_PREFIX", "/api")
        self.host = os.getenv("HOST", "0.0.0.0")
        self.port = int(os.getenv("PORT", "8000"))
        self.debug = os.getenv("DEBUG", "True").lower() == "true"


settings = Settings()

# ==============================
# LOGGING
# ==============================
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


# ==============================
# LIFESPAN
# ==============================
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Mental Health Screening API")
    logger.info(f"App: {settings.app_name} v{settings.app_version}")
    logger.info(f"Environment: {'Development' if settings.debug else 'Production'}")
    yield
    logger.info("Shutting down API")


# ==============================
# FASTAPI INSTANCE
# ==============================
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="""
    Produk      : S1T25B1K05
    Modul       : Screening Kesehatan Mental menggunakan Certainty Factor
    Instrumen   : DASS-21
    PERINGATAN  : API ini memproses data kesehatan mental yang sensitif
    """,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)


# ==============================
# DEPENDENCY INJECTION
# ==============================
knowledge_provider = InMemoryKnowledgeProvider()
screening_service = ScreeningService(knowledge_provider)
storage_repo = FileStorageRepository(path="data/screening_results.jsonl")

screening_module.knowledge_provider = knowledge_provider
screening_module.screening_service = screening_service
screening_module.storage_repo = storage_repo


# ==============================
# ROUTES DASAR
# ==============================
@app.get("/")
async def root():
    return {
        "message": "Mental Health Screening API",
        "version": settings.app_version,
        "status": "operational",
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "screening": f"{settings.api_prefix}/screening",
        },
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": settings.app_version,
        "service": settings.app_name,
        "timestamp": datetime.utcnow().isoformat()
    }


# ==============================
# ROUTER SCREENING
# ==============================
app.include_router(screening_module.router, prefix=settings.api_prefix, tags=["screening"])


# ==============================
# RUN SERVER (DEV)
# ==============================
if __name__ == "__main__":
    logger.info("Running in DEVELOPMENT mode")
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
        log_level="info",
    )