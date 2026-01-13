from app.models.schemas import ScreeningRequest, ScreeningResponse, knowledge_provider
import time
import logging
import uuid

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from app.services.screening_service import ScreeningService
from app.repositories.storage import FileStorageRepository
from app.services.screening_service import ScreeningService  
from app.repositories.storage import FileStorageRepository


router = APIRouter()
logger = logging.getLogger(__name__)

# Akan dioverride dari main.py (module assignment). Diset None untuk menghindari warning.
screening_service: ScreeningService | None = None
storage_repo: FileStorageRepository | None = None
knowledge_provider = None  # optional, jika ingin diakses

# Rate limiting storage (in-memory)
request_timestamps = {}

async def rate_limit_check(client_ip: str, max_requests: int = 10, window: int = 60):
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
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host

@router.post(
    "/screening",
    response_model=ScreeningResponse,
    summary="Mental Health Screening",
    description="""
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
    global screening_service, storage_repo
    # Fallback default jika main tidak meng-assign
    if screening_service is None:
        from app.models.schemas import knowledge_provider as kp_default
        screening_service = ScreeningService(kp_default)
    if storage_repo is None:
        storage_repo = FileStorageRepository(path="data/screening_results.jsonl")

    client_ip = await get_client_identifier(request)

    try:
        await rate_limit_check(client_ip)
        # Log the request (anonymized)
        logger.info(
            f"Screening request - IP: {client_ip}, "
            f"Symptoms: {len(screening_data.jawaban)}, "
            f"Secure: {request.url.scheme == 'https'}"
        )

        presentation_results, percentages = screening_service.process_screening(screening_data.jawaban)

        # Persist percentages (tidak mengganggu response jika gagal)
        try:
            record = {
                "id": str(uuid.uuid4()),
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "client_ip": client_ip,  # pertimbangkan hashing/anonim sesuai kebijakan
                "percentages": percentages,
                "meta": {
                    "symptoms_count": len(screening_data.jawaban),
                    "schema_version": 1
                }
            }
            storage_repo.save_percentages(record)
        except Exception:
            logger.error("Failed to persist percentages", exc_info=True)

        response = JSONResponse(content=presentation_results)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    except ValueError as e:
        logger.warning(f"Validation error from {client_ip}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Processing error from {client_ip}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error occurred")