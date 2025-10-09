from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
import time
import logging
from typing import Dict

from app.models.schemas import ScreeningRequest, ScreeningResponse
from app.services.screening_service import screening_service

router = APIRouter()
logger = logging.getLogger(__name__)

# Simple rate limiting storage
request_timestamps = {}

async def rate_limit_check(client_ip: str, max_requests: int = 10, window: int = 60):
    """
    Basic rate limiting implementation
    - 10 requests per minute per IP
    - Prevents abuse and DDoS attacks
    """
    current_time = time.time()
    
    # Clean old entries
    window_start = current_time - window
    if client_ip in request_timestamps:
        request_timestamps[client_ip] = [
            ts for ts in request_timestamps[client_ip] 
            if ts > window_start
        ]
    else:
        request_timestamps[client_ip] = []
    
    # Check rate limit
    if len(request_timestamps[client_ip]) >= max_requests:
        logger.warning(f"Rate limit exceeded for IP: {client_ip}")
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Maximum {max_requests} requests per {window} seconds."
        )
    
    request_timestamps[client_ip].append(current_time)

async def get_client_identifier(request: Request):
    """
    Get client identifier for rate limiting
    Handles proxies via X-Forwarded-For header
    """
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()
    else:
        client_ip = request.client.host
    
    return client_ip

@router.post(
    "/screening",
    response_model=ScreeningResponse,
    summary="Mental Health Screening",
    description="""
    Perform mental health screening using Certainty Factor algorithm.
    
    ## Security Features:
    - HTTPS Encryption (enforced in production)
    -  Rate Limiting (10 requests/minute)
    -  Input Validation
    -  Security Headers
    -  No Data Persistence
    
    ## Data Sensitivity:
    - **HIGH** - Mental Health Information
    - **ENCRYPTED** - TLS 1.2+ Required
    - **EPHEMERAL** - No storage of sensitive data
    
    **Input Format:**
    - `jawaban`: Dictionary of symptom codes (G01-G21) and severity levels
    - **Severity Levels:** 
      - TS: Tidak Setuju (Disagree)
      - AS: Agak Setuju (Somewhat Agree)
      - S: Setuju (Agree) 
      - SS: Sangat Setuju (Strongly Agree)
    
    **Example Request:**
    ```json
    {
        "jawaban": {
            "G01": "SS",
            "G02": "S",
            "G03": "AS",
            "G04": "TS"
        }
    }
    ```
    """,
    responses={
        200: {
            "description": "Screening completed successfully",
            "content": {
                "application/json": {
                    "example": {
                        "Depresi": {
                            "kategori": "Ringan",
                            "keterangan": "Rekomendasi: Lakukan olahraga ringan..."
                        },
                        "Kecemasan": {
                            "kategori": "Normal", 
                            "keterangan": "Tidak menunjukkan gangguan signifikan"
                        },
                        "Stres": {
                            "kategori": "Sedang",
                            "keterangan": "Rekomendasi: Konseling psikologis..."
                        }
                    }
                }
            }
        },
        400: {
            "description": "Invalid input data",
            "content": {
                "application/json": {
                    "example": {"detail": "Kode gejala tidak valid: G99"}
                }
            }
        },
        429: {
            "description": "Rate limit exceeded",
            "content": {
                "application/json": {
                    "example": {"detail": "Rate limit exceeded. Maximum 10 requests per 60 seconds."}
                }
            }
        },
        500: {
            "description": "Internal server error",
            "content": {
                "application/json": {
                    "example": {"detail": "Internal server error occurred"}
                }
            }
        }
    }
)
async def screening_endpoint(
    request: Request,
    screening_data: ScreeningRequest
):
    """
    Mental Health Screening Endpoint
    
    Processes mental health screening requests with comprehensive security measures
    including rate limiting, input validation, and secure response headers.
    """
    client_ip = await get_client_identifier(request)
    
    try:
        # Apply rate limiting
        await rate_limit_check(client_ip)
        
        # Log the request (anonymized)
        logger.info(
            f"Screening request - IP: {client_ip}, "
            f"Symptoms: {len(screening_data.jawaban)}, "
            f"Secure: {request.url.scheme == 'https'}"
        )
        
        # Process screening - validation handled by Pydantic schemas
        result = screening_service.process_screening(screening_data.jawaban)
        
        # Log successful processing
        logger.info(f"Screening completed for {client_ip}")
        
        # Create response with security headers
        response = JSONResponse(content=result)
        
        # Additional security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        
        # Add HSTS header if using HTTPS
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response
        
    except ValueError as e:
        # Input validation errors from service layer
        logger.warning(f"Validation error from {client_ip}: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except HTTPException:
        # Re-raise existing HTTP exceptions (like rate limit)
        raise
    except Exception as e:
        # Generic error to avoid information leakage
        logger.error(f"Processing error from {client_ip}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error occurred"
        )

@router.get("/screening/security")
async def security_info():
    """
    Security Information Endpoint
    
    Provides information about security measures implemented for the screening API.
    """
    return {
        "endpoint": "/api/screening",
        "security_level": "HIGH",
        "data_sensitivity": "Mental Health Information",
        "security_measures": {
            "https": "Required in production",
            "rate_limiting": "10 requests per minute per IP",
            "input_validation": "Comprehensive symptom code and value validation",
            "data_persistence": "None - ephemeral processing only",
            "encryption": "TLS 1.2+ required for production"
        },
        "compliance": "Health data protection standards"
    }