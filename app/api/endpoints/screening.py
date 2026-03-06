from app.models.schemas import ScreeningRequest, ScreeningResponse, knowledge_provider
import time
import logging

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