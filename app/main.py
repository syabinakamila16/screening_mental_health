from fastapi import FastAPI, Request
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
import uvicorn
import logging
from contextlib import asynccontextmanager
from typing import List

# Security and application configuration
class Settings:
    def __init__(self):
        # Application settings
        self.app_name = os.getenv("APP_NAME", "Mental Health Screening API - SECURE")
        self.app_version = os.getenv("APP_VERSION", "1.0.0")
        self.api_prefix = os.getenv("API_PREFIX", "/api")
        self.host = os.getenv("HOST", "0.0.0.0")
        self.port = int(os.getenv("PORT", "8443"))  # Default HTTPS port
        self.debug = os.getenv("DEBUG", "False").lower() == "true"
        
        # Security settings
        self.require_https = os.getenv("REQUIRE_HTTPS", "True").lower() == "true"
        self.allowed_hosts = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1,::1").split(",")
        self.allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")
        self.ssl_keyfile = os.getenv("SSL_KEYFILE", "./ssl/key.pem")
        self.ssl_certfile = os.getenv("SSL_CERTFILE", "./ssl/cert.pem")
        
        # Validate critical security settings in production
        if not self.debug and self.require_https:
            if not os.path.exists(self.ssl_keyfile) or not os.path.exists(self.ssl_certfile):
                raise RuntimeError("SSL certificates not found for production!")

settings = Settings()

# Enhanced logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan manager for startup and shutdown events"""
    # Startup
    logger.info("Starting Mental Health Screening API")
    logger.info(f" App: {settings.app_name} v{settings.app_version}")
    logger.info(f" Environment: {'Development' if settings.debug else 'Production'}")
    
    # Security configuration logging
    if settings.require_https:
        logger.info(" HTTPS Enforcement: ENABLED")
        if os.path.exists(settings.ssl_certfile) and os.path.exists(settings.ssl_keyfile):
            logger.info(" SSL Certificates: LOADED")
        else:
            logger.warning("SSL Certificates: NOT FOUND - HTTPS may not work")
    else:
        logger.warning(" HTTPS Enforcement: DISABLED - Not recommended for production")
    
    logger.info(f"Allowed Hosts: {settings.allowed_hosts}")
    logger.info(f"Server: {settings.host}:{settings.port}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Mental Health Screening API")

# FastAPI app instance
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="""
    SECURE API untuk Screening Kesehatan Mental menggunakan Certainty Factor.
    
    ## Fitur Keamanan:
    - Enkripsi HTTPS wajib untuk data sensitif
    -  CORS protection dengan origin validation
    -  Trusted host middleware
    -  Security headers lengkap
    -  Input validation dan sanitization
    
    ## Data Sensitivity:
    - TINGGI - Data kesehatan mental
    - ENKRIPSI - TLS 1.2+ required
    - PEMROSESAN - Ephemeral (tidak disimpan)
    
    **PERINGATAN:** API ini memproses data kesehatan mental yang sangat sensitif.
    """,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# ===== SECURITY MIDDLEWARES =====

# Force HTTPS in production (disabled in debug mode)
if settings.require_https and not settings.debug:
    app.add_middleware(HTTPSRedirectMiddleware)
    logger.info(" HTTPS Redirect middleware: ENABLED")

# Trusted hosts middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.allowed_hosts
)

# CORS middleware - security enhanced
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=[
        "Content-Type",
        "Authorization", 
        "Accept",
        "X-Requested-With"
    ],
    expose_headers=["Content-Length", "X-Total-Count"],
    max_age=600  # 10 minutes
)

# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add comprehensive security headers to all responses"""
    response = await call_next(request)
    
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
    
    # Add all security headers
    for header, value in security_headers.items():
        response.headers[header] = value
        
    return response

# Import routers
from app.api.endpoints.screening import router as screening_router

# Include routers
app.include_router(
    screening_router,
    prefix=settings.api_prefix,
    tags=["screening"]
)

# ===== APPLICATION ENDPOINTS =====

@app.get("/")
async def root():
    """Root endpoint dengan informasi keamanan"""
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
    """Comprehensive health check dengan status keamanan"""
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
    """Detailed security information endpoint"""
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
        "data_protection": {
            "sensitivity_level": "HIGH - Mental Health Information",
            "encryption": "TLS 1.2+ Required",
            "data_persistence": "Ephemeral - No storage",
            "compliance": "Health Data Protection Standards"
        },
        "security_headers": {
            "hsts": "enabled",
            "x_frame_options": "DENY",
            "content_security_policy": "enabled",
            "x_content_type_options": "nosniff"
        }
    }

# ===== APPLICATION STARTUP =====

def create_ssl_config() -> dict:
    """Create SSL configuration dictionary"""
    if (os.path.exists(settings.ssl_keyfile) and 
        os.path.exists(settings.ssl_certfile) and
        settings.require_https):
        return {
            "ssl_keyfile": settings.ssl_keyfile,
            "ssl_certfile": settings.ssl_certfile
        }
    return {}

if __name__ == "__main__":
    ssl_config = create_ssl_config()
    
    # Log startup configuration
    if ssl_config:
        logger.info(" Starting with HTTPS configuration")
        logger.info(f"   Keyfile: {ssl_config['ssl_keyfile']}")
        logger.info(f"   Certfile: {ssl_config['ssl_certfile']}")
    else:
        if settings.require_https:
            logger.warning(" HTTPS required but SSL certificates not found!")
        else:
            logger.info("Starting without HTTPS (development mode)")
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        **ssl_config,
        reload=settings.debug,
        log_level="debug" if settings.debug else "info",
        access_log=True
    )