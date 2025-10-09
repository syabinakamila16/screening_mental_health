from typing import Dict, Tuple
import logging
from decimal import Decimal, ROUND_HALF_UP
import time

logger = logging.getLogger(__name__)

class ScreeningService:
    """
    Service class for mental health screening using Certainty Factor algorithm.
    
    Features:
    - Input validation and sanitization
    - Certainty Factor calculation
    - Category determination with medical recommendations
    - Comprehensive logging and error handling
    - Thread-safe operations
    """
    
    # ===== CONSTANTS =====
    SEVERITY_MAPPING = {
        "TS": Decimal('0.2'),  # Tidak Setuju
        "AS": Decimal('0.4'),  # Agak Setuju
        "S": Decimal('0.6'),   # Setuju
        "SS": Decimal('0.8')   # Sangat Setuju
    }
    
    CF_PAKAR = {f"G{i:02}": Decimal('0.9') for i in range(1, 22)}
    
    DISEASE_SYMPTOMS = {
        "Depresi": ["G04", "G05", "G10", "G13", "G16", "G17", "G21"],
        "Kecemasan": ["G02", "G03", "G07", "G09", "G15", "G19", "G20"], 
        "Stres": ["G01", "G06", "G08", "G11", "G12", "G14", "G18"]
    }
    
    VALID_SYMPTOM_CODES = set(f"G{i:02}" for i in range(1, 22))
    VALID_SEVERITY_VALUES = set(SEVERITY_MAPPING.keys())

    def __init__(self):
        """Initialize screening service with configuration"""
        self._processing_times = []
        self._request_count = 0

    def process_screening(self, jawaban: Dict[str, str]) -> Dict[str, Dict[str, str]]:
        """
        Process mental health screening with comprehensive validation and logging
        
        Args:
            jawaban: Dictionary of symptom codes and severity values
            
        Returns:
            Dictionary containing screening results for all diseases
            
        Raises:
            ValueError: For invalid input data
            Exception: For processing errors with proper logging
        """
        start_time = time.time()
        self._request_count += 1
        
        try:
            # Input validation
            self._validate_input(jawaban)
            
            # Convert to numerical values
            cf_user_input = self._map_severity_values(jawaban)
            
            # Calculate Certainty Factor
            hasil_cf = self._calculate_cf_total(cf_user_input)
            
            # Format results
            results = self._format_results(hasil_cf)
            
            # Log successful processing
            processing_time = time.time() - start_time
            self._processing_times.append(processing_time)
            
            logger.info(
                f"Screening processed successfully - "
                f"Symptoms: {len(jawaban)}, "
                f"Time: {processing_time:.3f}s, "
                f"Total requests: {self._request_count}"
            )
            
            return results
            
        except ValueError as e:
            logger.warning(f"Input validation failed: {str(e)}")
            raise e
        except Exception as e:
            logger.error(
                f"Screening processing error: {str(e)}", 
                exc_info=True,
                extra={
                    "symptoms_count": len(jawaban),
                    "processing_time": time.time() - start_time
                }
            )
            raise Exception(f"Terjadi kesalahan sistem dalam memproses screening: {str(e)}")

    def _validate_input(self, jawaban: Dict[str, str]) -> None:
        """
        Validate input data with comprehensive checks
        
        Raises:
            ValueError: If any validation check fails
        """
        if not jawaban:
            raise ValueError("Data jawaban tidak boleh kosong")
        
        if len(jawaban) > len(self.VALID_SYMPTOM_CODES):
            raise ValueError(f"Jumlah gejala melebihi batas maksimal {len(self.VALID_SYMPTOM_CODES)}")
        
        invalid_codes = []
        invalid_values = []
        
        for kode, nilai in jawaban.items():
            # Validate symptom code
            if kode not in self.VALID_SYMPTOM_CODES:
                invalid_codes.append(kode)
            
            # Validate severity value
            if nilai not in self.VALID_SEVERITY_VALUES:
                invalid_values.append(f"{kode}: {nilai}")
        
        # Collect all validation errors
        errors = []
        if invalid_codes:
            errors.append(f"Kode gejala tidak valid: {', '.join(invalid_codes)}")
        if invalid_values:
            errors.append(f"Nilai severity tidak valid: {', '.join(invalid_values)}")
        
        if errors:
            raise ValueError("; ".join(errors))

    def _map_severity_values(self, jawaban: Dict[str, str]) -> Dict[str, Decimal]:
        """Convert severity labels to numerical values using Decimal for precision"""
        return {
            kode: self.SEVERITY_MAPPING[nilai]
            for kode, nilai in jawaban.items()
        }

    def _calculate_cf_total(self, cf_user_input: Dict[str, Decimal]) -> Dict[str, float]:
        """
        Calculate total Certainty Factor for each disease using Decimal arithmetic
        
        Returns:
            Dictionary with disease names as keys and percentage scores as values
        """
        hasil = {}
        
        for penyakit, gejala_list in self.DISEASE_SYMPTOMS.items():
            cf_combined = []
            
            for gejala in gejala_list:
                if gejala in cf_user_input:
                    cf_user = cf_user_input[gejala]
                    cf_pakar = self.CF_PAKAR[gejala]
                    
                    # CF_combine = CF_user * CF_pakar
                    cf_gejala = cf_user * cf_pakar
                    cf_combined.append(cf_gejala)
            
            if not cf_combined:
                # No symptoms provided for this disease
                hasil[penyakit] = 0.0
            else:
                # Combine CF: CF1 + CF2*(1 - CF1)
                cf_total = cf_combined[0]
                for cf in cf_combined[1:]:
                    cf_total = cf_total + cf * (Decimal('1.0') - cf_total)
                
                # Convert to percentage and round
                percentage = float(cf_total * Decimal('100'))
                hasil[penyakit] = round(percentage, 2)
        
        return hasil

    def _format_results(self, hasil_cf: Dict[str, float]) -> Dict[str, Dict[str, str]]:
        """
        Format screening results with categories and medical recommendations
        
        Returns:
            Formatted results ready for API response
        """
        output = {}
        
        for penyakit, persentase in hasil_cf.items():
            kategori, keterangan = self._determine_category(penyakit, persentase)
            
            output[penyakit] = {
                "kategori": kategori,
                "keterangan": keterangan
                # Note: persentase dihilangkan sesuai requirement sebelumnya
            }
        
        return output

    def _determine_category(self, penyakit: str, persentase: float) -> Tuple[str, str]:
        """
        Determine disease category based on percentage score
        
        Returns:
            Tuple of (category, recommendation)
        """
        if penyakit == "Depresi":
            return self._kategori_depresi(persentase)
        elif penyakit == "Kecemasan":
            return self._kategori_kecemasan(persentase)
        elif penyakit == "Stres":
            return self._kategori_stres(persentase)
        else:
            return "Tidak Diketahui", "Konsultasi dengan profesional kesehatan"

    def _kategori_depresi(self, persentase: float) -> Tuple[str, str]:
        """Determine depression category"""
        if persentase >= 97:
            return ("Sangat Berat", 
                   "Pikiran untuk bunuh diri, rasa hampa total, tidak mampu melakukan aktivitas dasar. Rekomendasi: Harus segera diperiksakan ke psikiater. Kemungkinan besar membutuhkan obat antidepresan, dan dalam kasus tertentu, harus rawat inap. Hindari akses ke alat yang berbahaya. Tidak boleh dibiarkan sendiri. Diskusikan dengan psikiater kemungkinan mendapatkan psikoterapi dari psikolog")
        elif persentase >= 88:
            return ("Berat", 
                   "Putus asa, tidak berharga, gangguan tidur berat, nafsu makan turun/naik drastis. Rekomendasi: Segera hubungi psikiater untuk pemeriksaan dan kemungkinan pengobatan farmakologis (antidepresan). Keluarga atau teman dekat perlu waspada terhadap tanda bunuh diri atau self-harm. Pertimbangkan break/cuti kuliah bila perlu. Psikoterapi dengan psikolog minimal 1x/minggu")
        elif persentase >= 80:
            return ("Sedang", 
                   "Sedih terus-menerus, gangguan tidur, harga diri rendah, kesulitan berkonsentrasi. Rekomendasi: Identifikasi stresor (akademik, pekerjaan, hubungan) dan cari solusi bersama psikolog. Tidur teratur (6-8 jam), hindari alkohol/narkoba, konsumsi makanan bergizi. Bergabung dengan kelompok dukungan sebaya (peer support) untuk mengurangi rasa kesepian")
        elif persentase >= 40:
            return ("Ringan", 
                   "Perasaan sedih sesekali, kehilangan minat ringan, mudah lelah, kurang semangat. Rekomendasi: Pahami bahwa perasaan sedih adalah bagian dari pengalaman manusia. Lakukan olahraga ringan minimal 3-5 kali/minggu. Buat jadwal harian dan tetapkan target kecil. Bicarakan perasaan dengan teman, keluarga, atau konselor kampus. Latihan pernapasan, meditasi, atau jurnal harian")
        else:
            return ("Normal", "Tidak menunjukkan gangguan signifikan")

    def _kategori_kecemasan(self, persentase: float) -> Tuple[str, str]:
        """Determine anxiety category"""
        if persentase >= 97:
            return ("Sangat Berat", 
                   "Serangan panik, menghindari situasi sosial. Rekomendasi: Periksa ke psikiater. Kemungkinan perlu kombinasi obat dan terapi psikologis intensif. Perlu dukungan sosial terlatih. Kemungkinan ada serangan panik yang menyebabkan emergency, perlu kunjungan ke IGD")
        elif persentase >= 88:
            return ("Berat", 
                   "Sulit bernapas, takut kehilangan kendali. Rekomendasi: Perlu periksa ke psikiater apakah diperlukan obat anti kecemasan. Psikoterapi dengan psikolog untuk menentukan sumber pemicu kecemasan dan bagaimana mengatasinya")
        elif persentase >= 80:
            return ("Sedang", 
                   "Gemetar, berkeringat, takut akan bahaya. Rekomendasi: Konseling psikologis dengan psikolog. Identifikasi pemicu dan kelola kecemasan. Gunakan teknik grounding. Bentuk support system yang baik. Hindari konsumsi stimulan (kopi, dll)")
        elif persentase >= 40:
            return ("Ringan", 
                   "Gugup, waspada berlebihan. Rekomendasi: Relaksasi, Butterfly hug, Aktivitas fisik (olahraga ringan)")
        else:
            return ("Normal", "Tidak menunjukkan gangguan signifikan")

    def _kategori_stres(self, persentase: float) -> Tuple[str, str]:
        """Determine stress category"""
        if persentase >= 97:
            return ("Sangat Berat", 
                   "Gejala somatik, burnout, gangguan fungsi sehari-hari. Rekomendasi: Ikuti saran dari psikolog (dan psikiater) untuk pemulihan. Pertimbangkan cuti kuliah (jika perlu). Libatkan orang lain sebagai sumber dukungan. Batasi penggunaan gadget/medsos. Jaga kesehatan fisik dengan memperhatikan asupan makan dan pola tidur sehat")
        elif persentase >= 88:
            return ("Berat", 
                   "Tertekan, sulit berkonsentrasi, mudah lelah. Rekomendasi: Segera konsultasi ke psikolog. Diskusikan dengan psikolog kemungkinan perlunya periksa ke psikiater. Lakukan praktik regulasi emosi. Lakukan penyesuaian waktu dan beban tugas. Batasi penggunaan gadget/medsos")
        elif persentase >= 80:
            return ("Sedang", 
                   "Sulit rileks, mudah marah, mudah kaget. Rekomendasi: Konseling psikologis dengan psikolog. Belajar mengatakan 'tidak' dan tentukan prioritas. Bentuk kelompok dukungan teman sebaya")
        elif persentase >= 40:
            return ("Ringan", 
                   "Kelola tugas dan waktu. Break sejenak dari rutinitas harian. Mindfulness sederhana. Batasi penggunaan gadget dan medsos")
        else:
            return ("Normal", "Tidak menunjukkan gangguan signifikan")

    def get_service_metrics(self) -> Dict[str, any]:
        """Get service performance metrics"""
        avg_time = sum(self._processing_times) / len(self._processing_times) if self._processing_times else 0
        return {
            "total_requests": self._request_count,
            "average_processing_time": round(avg_time, 3),
            "recent_processing_times": self._processing_times[-10:]  # Last 10 requests
        }


# Service instance (singleton pattern)
screening_service = ScreeningService()