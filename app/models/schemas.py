from __future__ import annotations
from pydantic import BaseModel, Field, validator
from typing import Dict, Literal, List
from decimal import Decimal
import os


# ===== VALIDATION CONSTANTS =====
VALID_SYMPTOM_CODES = {f"G{i:02}" for i in range(1, 22)}
VALID_SEVERITY_VALUES = {"TS", "AS", "S", "SS"}

# ===== REQUEST SCHEMAS =====
class ScreeningRequest(BaseModel):
    """
        jawaban: Dictionary of symptom codes (G01-G21) and severity levels
                TS: Tidak Setuju (0.2)
                AS: Agak Setuju (0.4) 
                S: Setuju (0.6)
                SS: Sangat Setuju (0.8)
    """
    
    jawaban: Dict[str, Literal["TS", "AS", "S", "SS"]] = Field(
        ...,
        description=(
            "Dictionary of symptom codes and severity levels\n\n"
            "**Valid Symptom Codes:** G01-G21\n"
            "**Valid Severity Values:** TS, AS, S, SS\n\n"
            "Example:\n"
            "```json\n"
            "{\n"
            '  "G01": "SS",\n'
            '  "G02": "S",\n' 
            '  "G03": "AS",\n'
            '  "G04": "TS"\n'
            "}\n"
            "```"
        ),
        example={
            "G01": "SS",
            "G02": "S", 
            "G03": "AS",
            "G04": "TS"
        }
    )
    
    @validator('jawaban')
    def validate_symptom_codes(cls, v):
        "Validate all symptom codes are within G01-G21"
        if not v:
            raise ValueError("Minimal harus ada 1 gejala yang diisi")
        invalid_codes = [c for c in v.keys() if c not in VALID_SYMPTOM_CODES]
        if invalid_codes:
            raise ValueError(f"Kode gejala tidak valid: {', '.join(invalid_codes)}. Harus G01-G21")
        return v
    
# ===== RESPONSE SCHEMAS =====
class DiseaseResult(BaseModel):
    kategori: str = Field(...)
    gejala: str = Field(...)
    rekomendasi: str = Field(...)

class ScreeningResponse(BaseModel):
    Depresi: DiseaseResult = Field(
        ...,
        description="Hasil screening untuk depresi"
    )
    Kecemasan: DiseaseResult = Field(
        ...,
        description="Hasil screening untuk kecemasan"
    )
    Stres: DiseaseResult = Field(
        ...,
        description="Hasil screening untuk stres"
    )

# ===== Knowledge Provider (Data Layer) =====
class KnowledgeProvider:
    """Interface for knowledge access (can be replaced by DB-backed impl)"""
    def get_cf_pakar(self, symptom_code: str) -> Decimal:
        raise NotImplementedError
    def get_symptoms_for_disease(self, disease_name: str) -> List[str]:
        raise NotImplementedError
    def list_all_symptoms(self) -> List[str]:
        raise NotImplementedError

class InMemoryKnowledgeProvider(KnowledgeProvider):
    def __init__(self):
        self.cf_pakar = {f"G{i:02}": Decimal('0.9') for i in range(1, 22)}
        self.disease_symptoms = {
            "Depresi": ["G04", "G05", "G10", "G13", "G16", "G17", "G21"],
            "Kecemasan": ["G02", "G03", "G07", "G09", "G15", "G19", "G20"],
            "Stres": ["G01", "G06", "G08", "G11", "G12", "G14", "G18"]
        }

    def get_cf_pakar(self, symptom_code: str) -> Decimal:
        return self.cf_pakar.get(symptom_code, Decimal('0.0'))
    def get_symptoms_for_disease(self, disease_name: str) -> List[str]:
        return self.disease_symptoms.get(disease_name, [])
    def list_all_symptoms(self) -> List[str]:
        return list(self.cf_pakar.keys())

# Default provider instance (used by endpoints/service unless swapped)
knowledge_provider = InMemoryKnowledgeProvider()