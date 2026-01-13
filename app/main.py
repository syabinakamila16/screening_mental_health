import os
import uvicorn
import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.cors import CORSMiddleware

from app.api.endpoints import screening as screening_module
from app.models.schemas import InMemoryKnowledgeProvider
from app.services.screening_service import ScreeningService
from app.repositories.storage import FileStorageRepository


# ==============================
# 🔧 CONFIGURATION CLASS
# ==============================
class Settings:
    def __init__(self):
        self.app_name = os.getenv("APP_NAME", "RESTful API Screening Kesehatan Mental")
        self.app_version = os.getenv("APP_VERSION", "1.0.0")
        self.api_prefix = os.getenv("API_PREFIX", "/api")
        self.host = os.getenv("HOST", "0.0.0.0")
        self.port = int(os.getenv("PORT", "8000"))
        self.debug = os.getenv("DEBUG", "True").lower() == "true"

        # Security
        self.require_https = os.getenv("REQUIRE_HTTPS", "False").lower() == "true"
        self.allowed_hosts = os.getenv("ALLOWED_HOSTS", "*").split(",")
        self.allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")
        self.ssl_keyfile = os.getenv("SSL_KEYFILE", "./ssl/key.pem")
        self.ssl_certfile = os.getenv("SSL_CERTFILE", "./ssl/cert.pem")


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
    logger.info(f"HTTPS required: {settings.require_https}")
    logger.info(f"Allowed hosts: {settings.allowed_hosts}")
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
# Dependency (bisa diganti ke DB nanti)
# ==============================
knowledge_provider = InMemoryKnowledgeProvider()
screening_service = ScreeningService(knowledge_provider)
storage_repo = FileStorageRepository(path="data/screening_results.jsonl")

# Inject ke modul endpoint
screening_module.knowledge_provider = knowledge_provider  # optional
screening_module.screening_service = screening_service
screening_module.storage_repo = storage_repo

# ==============================
# MIDDLEWARE KEAMANAN (opsional, aktifkan bila siap)
# ==============================
# if settings.require_https and not settings.debug:
#     app.add_middleware(HTTPSRedirectMiddleware)
# app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=settings.allowed_origins,
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# ==============================
# ROUTES DASAR
# ==============================
@app.get("/")
async def root():
    return {
        "message": "Secure Mental Health Screening API",
        "version": settings.app_version,
        "status": "operational",
        "security": {
            "https_required": settings.require_https,
            "data_sensitivity": "HIGH - Mental Health Data",
            "encryption": "TLS 1.2+ Required",
        },
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "security": "/security",
            "screening": f"{settings.api_prefix}/screening",
        },
    }

@app.get("/health")
async def health_check():
    ssl_configured = all([
        os.path.exists(settings.ssl_certfile),
        os.path.exists(settings.ssl_keyfile)
    ])
    return {
        "status": "healthy",
        "version": settings.app_version,
        "service": settings.app_name,
        "security": {
            "https_enforced": settings.require_https and not settings.debug,
            "ssl_configured": ssl_configured,
            "trusted_hosts": len(settings.allowed_hosts),
            "cors_enabled": len(settings.allowed_origins) > 0
        },
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/security")
async def security_info():
    return {
        "status": "secure",
        "application": {
            "name": settings.app_name,
            "version": settings.app_version,
            "environment": "development" if settings.debug else "production"
        },
        "https_configuration": {
            "required": settings.require_https,
            "enforced": settings.require_https and not settings.debug,
            "ssl_certificates": {
                "key_file": settings.ssl_keyfile,
                "cert_file": settings.ssl_certfile,
                "exists": all([
                    os.path.exists(settings.ssl_certfile),
                    os.path.exists(settings.ssl_keyfile)
                ])
            }
        },
        "access_control": {
            "allowed_hosts": settings.allowed_hosts,
            "allowed_origins": settings.allowed_origins,
            "api_prefix": settings.api_prefix
        },
    }

# ==============================
# ROUTER SCREENING
# ==============================
app.include_router(screening_module.router, prefix=settings.api_prefix, tags=["screening"])

# ==============================
# STARTUP / SHUTDOWN (opsional untuk DB/cache nanti)
# ==============================
@app.on_event("startup")
async def on_startup():
    pass

@app.on_event("shutdown")
async def on_shutdown():
    pass

# ==============================
# RUN SERVER (DEV)
# ==============================
if __name__ == "__main__":
    logger.info("🚀 Running in DEVELOPMENT mode")
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
        log_level="info",
    )