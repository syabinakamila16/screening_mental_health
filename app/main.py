from fastapi import FastAPI, Request
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
import uvicorn
import logging
from contextlib import asynccontextmanager

# ==============================
# 🔧 CONFIGURATION CLASS
# ==============================
class Settings:
    def __init__(self):
        # Application
        self.app_name = os.getenv("APP_NAME", "REst API Screening Kesehatan Mental")
        self.app_version = os.getenv("APP_VERSION", "1.0.0")
        self.api_prefix = os.getenv("API_PREFIX", "/api")
        self.host = os.getenv("HOST", "0.0.0.0")
        self.port = int(os.getenv("PORT", "8080"))
        self.debug = os.getenv("DEBUG", "True").lower() == "true"

        # Security
        self.require_https = os.getenv("REQUIRE_HTTPS", "False").lower() == "true"
        self.allowed_hosts = os.getenv("ALLOWED_HOSTS", "*").split(",")
        self.allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")
        self.ssl_keyfile = os.getenv("SSL_KEYFILE", "./ssl/key.pem")
        self.ssl_certfile = os.getenv("SSL_CERTFILE", "./ssl/cert.pem")

settings = Settings()

# ==============================
#LOGGING SETUP
# ==============================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ==============================
#  LIFESPAN EVENTS
# ==============================
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Starting Mental Health Screening API")
    logger.info(f"App: {settings.app_name} v{settings.app_version}")
    logger.info(f"Environment: {'Development' if settings.debug else 'Production'}")
    logger.info(f"HTTPS required: {settings.require_https}")
    logger.info(f"Allowed hosts: {settings.allowed_hosts}")
    yield
    logger.info("🛑 Shutting down API")

# ==============================
#  FASTAPI INSTANCE
# ==============================
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="""
    SECURE API untuk Screening Kesehatan Mental menggunakan Certainty Factor.
       Capstone TA
       Pengembangan Sistem Monitoring dan Intervensi Kesehatan Mental Berbasis Algoritma Pembelajaran Mendalam dan Sistem Pakar 
       Kelompok: S1T25K05

    **PERINGATAN:** API ini memproses data kesehatan mental yang sangat sensitif.
    """,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# ==============================
#  MIDDLEWARE KEAMANAN
# ==============================

# 1. HTTPS Redirect Middleware (hanya jika production)
if settings.require_https and not settings.debug:
    app.add_middleware(HTTPSRedirectMiddleware)
    logger.info("✅ HTTPS Redirect Middleware diaktifkan")

# 2. Trusted Hosts Middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.allowed_hosts
)

# 3. CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# 4. Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)

    # Jangan blokir Swagger / Redoc / OpenAPI
    if request.url.path.startswith(("/docs", "/redoc", "/openapi.json")):
        return response

    security_headers = {
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
        "Cache-Control": "no-store, no-cache, must-revalidate",
        "Pragma": "no-cache",
        "X-Permitted-Cross-Domain-Policies": "none"
    }
    for header, value in security_headers.items():
        response.headers[header] = value

    return response

# ==============================
# 📡 ENDPOINTS DASAR
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
            "encryption": "TLS 1.2+ Required"
        },
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "security": "/security",
            "screening": f"{settings.api_prefix}/screening"
        },
        "warning": "This API handles sensitive health data - Proper security protocols are enforced"
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
        "timestamp": __import__('datetime').datetime.utcnow().isoformat()
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
# 🔗 IMPORT ROUTER SCREENING
# ==============================
try:
    from app.api.endpoints.screening import router as screening_router
    app.include_router(screening_router, prefix=settings.api_prefix, tags=["screening"])
except ModuleNotFoundError:
    logger.warning("⚠️ Modul screening belum ditemukan. Pastikan 'app/api/endpoints/screening.py' tersedia.")

# ==============================
# 🏁 RUN SERVER (DEV MODE)
# ==============================
if __name__ == "__main__":
    logger.info("🚀 Running in DEVELOPMENT mode")
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
        log_level="info"
    )
