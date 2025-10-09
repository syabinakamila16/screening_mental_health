from pydantic import BaseModel, Field, validator
from typing import Dict, Literal

# ===== VALIDATION CONSTANTS =====
VALID_SYMPTOM_CODES = {f"G{i:02}" for i in range(1, 22)}
VALID_SEVERITY_VALUES = {"TS", "AS", "S", "SS"}

# ===== REQUEST SCHEMAS =====
class ScreeningRequest(BaseModel):
    """
    Request model for mental health screening
    
    Attributes:
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
            "**Example:**\n"
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
        """Validate all symptom codes are within G01-G21"""
        invalid_codes = []
        for code in v.keys():
            if code not in VALID_SYMPTOM_CODES:
                invalid_codes.append(code)
        
        if invalid_codes:
            raise ValueError(f"Kode gejala tidak valid: {', '.join(invalid_codes)}. Harus G01-G21")
        return v
    
    @validator('jawaban')
    def validate_severity_values(cls, v):
        """Validate all severity values are valid"""
        invalid_values = []
        for code, value in v.items():
            if value not in VALID_SEVERITY_VALUES:
                invalid_values.append(f"{code}: {value}")
        
        if invalid_values:
            raise ValueError(f"Nilai severity tidak valid: {', '.join(invalid_values)}. Harus TS, AS, S, atau SS")
        return v
    
    @validator('jawaban')
    def validate_minimum_symptoms(cls, v):
        """Ensure at least one symptom is provided"""
        if len(v) == 0:
            raise ValueError("Minimal harus ada 1 gejala yang diisi")
        return v

# ===== RESPONSE SCHEMAS =====
class DiseaseResult(BaseModel):
    """
    Individual disease screening result
    """
    kategori: str = Field(
        ...,
        description="Tingkat keparahan hasil screening",
        examples=["Normal", "Ringan", "Sedang", "Berat", "Sangat Berat"]
    )
    
    keterangan: str = Field(
        ...,
        description="Penjelasan detail dan rekomendasi penanganan",
        examples=[
            "Tidak menunjukkan gangguan signifikan",
            "Rekomendasi: Lakukan olahraga ringan minimal 3-5 kali/minggu"
        ]
    )

class ScreeningResponse(BaseModel):
    """
    Complete screening response for all mental health aspects
    """
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