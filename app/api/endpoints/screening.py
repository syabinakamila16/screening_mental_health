import logging

from fastapi import APIRouter, HTTPException, Request
from app.models.schemas import ScreeningRequest, ScreeningResponse
from app.services.screening_service import ScreeningService
from app.repositories.storage import FileStorageRepository

router = APIRouter()
logger = logging.getLogger(__name__)

# Dioverride dari main.py via module assignment
screening_service: ScreeningService | None = None
storage_repo: FileStorageRepository | None = None
knowledge_provider = None

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

    Semua 21 gejala (G01-G21) wajib diisi.
    """,
    responses={
 
    }
)
async def screening_endpoint(
    request: Request,
    screening_data: ScreeningRequest
):
    global screening_service, storage_repo

    try:
        # Jalankan proses screening
        results, hasil_cf = screening_service.process_screening(screening_data.jawaban)

        if storage_repo: storage_repo.save_percentages({
        "timestamp": __import__('datetime').datetime.utcnow().isoformat(),
        "percentages": hasil_cf
    })

        def to_disease_result(d):
            return {"kategori": d["Kategori"], "gejala": d["Gejala"], "rekomendasi": d["Rekomendasi"]}

        return ScreeningResponse(
        Depresi=to_disease_result(results["Depresi"]),
        Kecemasan=to_disease_result(results["Kecemasan"]),
        Stres=to_disease_result(results["Stres"])
)

    except ValueError as e:
        logger.warning(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        logger.error(f"Screening error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error occurred")