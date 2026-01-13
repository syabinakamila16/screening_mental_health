from typing import Dict, Tuple
import logging
from decimal import Decimal, getcontext
import time

logger = logging.getLogger(__name__)
getcontext().prec = 10  # presisi cukup untuk CF


class ScreeningService:
    SEVERITY_MAPPING = {
        "TS": Decimal('0.2'),
        "AS": Decimal('0.4'),
        "S": Decimal('0.6'),
        "SS": Decimal('0.8')
    }

    def __init__(self, knowledge_provider):
        self._kr = knowledge_provider
        self._processing_times = []
        self._request_count = 0

    def process_screening(self, jawaban: Dict[str, str]) -> Tuple[Dict[str, Dict[str, str]], Dict[str, float]]:
        start_time = time.time()
        self._request_count += 1
        try:
            self._validate_input(jawaban)
            cf_user_input = self._map_severity_values(jawaban)
            hasil_cf = self._calculate_cf_total(cf_user_input)  # persentase float
            results = self._format_results(hasil_cf)            # untuk klien
            processing_time = time.time() - start_time
            self._processing_times.append(processing_time)
            logger.info(
                f"Screening processed - Symptoms: {len(jawaban)}, "
                f"Time: {processing_time:.3f}s, Total: {self._request_count}"
            )
            return results, hasil_cf
        except ValueError as e:
            logger.warning(f"Input validation failed: {str(e)}")
            raise e
        except Exception as e:
            logger.error(
                f"Screening processing error: {str(e)}",
                exc_info=True,
                extra={"symptoms_count": len(jawaban) if isinstance(jawaban, dict) else 0,
                       "processing_time": time.time() - start_time}
            )
            raise Exception(f"Terjadi kesalahan sistem dalam memproses screening: {str(e)}")

    def _validate_input(self, jawaban: Dict[str, str]) -> None:
        if not jawaban:
            raise ValueError("Data jawaban tidak boleh kosong")

        valid_symptoms = set(self._kr.list_all_symptoms())
        if len(jawaban) > len(valid_symptoms):
            raise ValueError(f"Jumlah gejala melebihi batas maksimal {len(valid_symptoms)}")

        invalid_codes, invalid_values = [], []
        for kode, nilai in jawaban.items():
            if kode not in valid_symptoms:
                invalid_codes.append(kode)
            if nilai not in set(self.SEVERITY_MAPPING.keys()):
                invalid_values.append(f"{kode}: {nilai}")

        errors = []
        if invalid_codes:
            errors.append(f"Kode gejala tidak valid: {', '.join(invalid_codes)}")
        if invalid_values:
            errors.append(f"Nilai severity tidak valid: {', '.join(invalid_values)}")
        if errors:
            raise ValueError("; ".join(errors))

    def _map_severity_values(self, jawaban: Dict[str, str]) -> Dict[str, Decimal]:
        return {kode: self.SEVERITY_MAPPING[nilai] for kode, nilai in jawaban.items()}

    def combine_two_cf(self, cf_current: Decimal, cf_new: Decimal) -> Decimal:
        cf_current = Decimal(cf_current)
        cf_new = Decimal(cf_new)

        if cf_current >= 0 and cf_new >= 0:
            return cf_current + cf_new * (Decimal('1.0') - cf_current)
        if cf_current <= 0 and cf_new <= 0:
            return cf_current + cf_new * (Decimal('1.0') + cf_current)

        abs_current = abs(cf_current)
        abs_new = abs(cf_new)
        denom = Decimal('1.0') - min(abs_current, abs_new)
        if denom == Decimal('0'):
            return Decimal('0.0')
        return (cf_current + cf_new) / denom

    def _calculate_cf_total(self, cf_user_input: Dict[str, Decimal]) -> Dict[str, float]:
        hasil = {}
        for penyakit in ["Depresi", "Kecemasan", "Stres"]:
            gejala_list = self._kr.get_symptoms_for_disease(penyakit)
            cf_combined = []
            for gejala in gejala_list:
                if gejala in cf_user_input:
                    cf_user = cf_user_input[gejala]
                    cf_pakar = self._kr.get_cf_pakar(gejala)
                    if not (Decimal('-1') <= cf_pakar <= Decimal('1')):
                        logger.warning(f"CF pakar {gejala} di luar [-1,1]: {cf_pakar}")
                    if not (Decimal('-1') <= cf_user <= Decimal('1')):
                        logger.warning(f"CF user {gejala} di luar [-1,1]: {cf_user}")
                    cf_gejala = cf_user * cf_pakar
                    cf_combined.append(cf_gejala)

            if not cf_combined:
                hasil[penyakit] = 0.0
            else:
                cf_total = cf_combined[0]
                for cf_val in cf_combined[1:]:
                    cf_total = self.combine_two_cf(cf_total, cf_val)
                percentage = cf_total * Decimal('100')
                try:
                    pct_float = float(percentage)
                except Exception:
                    pct_float = 0.0
                hasil[penyakit] = round(pct_float, 2)
        return hasil

    def _format_results(self, hasil_cf: Dict[str, float]) -> Dict[str, Dict[str, str]]:
        output = {}
        for penyakit, persentase in hasil_cf.items():
            kategori, gejala_desc, rekomendasi = self._determine_category(penyakit, persentase)
            output[penyakit] = {
                "Kategori": kategori,
                "Gejala": gejala_desc,
                "Rekomendasi": rekomendasi,
            }
        return output

    def _determine_category(self, penyakit: str, persentase: float) -> Tuple[str, str, str]:
        if penyakit == "Depresi":
            return self._kategori_depresi(persentase)
        elif penyakit == "Kecemasan":
            return self._kategori_kecemasan(persentase)
        elif penyakit == "Stres":
            return self._kategori_stres(persentase)
        # fallback defensif
        return ("Tidak Diketahui",
                "Konsultasi dengan profesional kesehatan",
                "Hubungi tenaga kesehatan untuk evaluasi lebih lanjut")

    # --- kategori helpers (selalu return 3 nilai) ---
    def _kategori_depresi(self, persentase: float) -> Tuple[str, str, str]:
        if persentase >= 97:
            return ("Sangat Berat",
                    "Pikiran bunuh diri, putus asa",
                    "Segera hubungi psikiater/layanan darurat; pendampingan keluarga.")
        elif persentase >= 88:
            return ("Berat",
                    "Sedih mendalam, menarik diri",
                    "Konsultasi psikiater/psikolog; rencana keselamatan; dukungan sosial intensif.")
        elif persentase >= 80:
            return ("Sedang",
                    "Sedih terus-menerus, motivasi turun",
                    "Konseling psikolog; aktivitas terstruktur; sleep hygiene.")
        elif persentase >= 40:
            return ("Ringan",
                    "Mood menurun sesekali",
                    "Olahraga ringan; jadwal tidur teratur; journaling.")
        else:
            return ("Normal",
                    "Tidak menunjukkan gangguan signifikan",
                    "Pertahankan gaya hidup sehat; monitoring jika ada stresor baru.")

    def _kategori_kecemasan(self, persentase: float) -> Tuple[str, str, str]:
        if persentase >= 97:
            return ("Sangat Berat",
                    "Serangan panik / takut intens",
                    "Psikiater/psikolog segera; teknik grounding; evaluasi obat.")
        elif persentase >= 88:
            return ("Berat",
                    "Gelisah kuat, sulit bernapas",
                    "Terapi kognitif-perilaku; latihan pernapasan; konsultasi dokter.")
        elif persentase >= 80:
            return ("Sedang",
                    "Gemetar, tegang, waspada",
                    "Relaksasi terjadwal; CBT; batasi kafein/gadget malam.")
        elif persentase >= 40:
            return ("Ringan",
                    "Gugup, waspada berlebihan",
                    "Relaksasi, aktivitas fisik ringan, sleep hygiene.")
        else:
            return ("Normal",
                    "Tidak menunjukkan gangguan signifikan",
                    "Lanjutkan pola hidup sehat; kontrol jika keluhan muncul.")

    def _kategori_stres(self, persentase: float) -> Tuple[str, str, str]:
        if persentase >= 97:
            return ("Sangat Berat",
                    "Burnout/gangguan fungsi",
                    "Pertimbangkan cuti; dukungan profesional; atur beban kerja.")
        elif persentase >= 88:
            return ("Berat",
                    "Tekanan tinggi, sulit rileks",
                    "Konseling; manajemen waktu; latihan relaksasi intensif.")
        elif persentase >= 80:
            return ("Sedang",
                    "Cemas soal tugas, ketegangan otot",
                    "Prioritaskan tugas; peregangan; micro-break terjadwal.")
        elif persentase >= 40:
            return ("Ringan",
                    "Mudah lelah, tegang ringan",
                    "Mindfulness; olahraga ringan; batasi lembur/gadget malam.")
        else:
            return ("Normal",
                    "Tidak menunjukkan gangguan signifikan",
                    "Jaga keseimbangan kerja-istirahat; tidur cukup.")