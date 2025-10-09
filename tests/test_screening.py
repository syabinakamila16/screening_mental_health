import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_screening_success():
    """Test screening dengan data valid"""
    test_data = {
        "jawaban": {
            "G01": "SS", "G02": "S", "G03": "AS", "G04": "TS",
            "G05": "SS", "G06": "S", "G07": "AS", "G08": "TS",
            "G09": "SS", "G10": "S", "G11": "AS", "G12": "TS",
            "G13": "SS", "G14": "S", "G15": "AS", "G16": "TS",
            "G17": "SS", "G18": "S", "G19": "AS", "G20": "TS",
            "G21": "SS"
        }
    }
    
    response = client.post("/api/screening", json=test_data)
    assert response.status_code == 200
    
    data = response.json()
    assert "Depresi" in data
    assert "Kecemasan" in data
    assert "Stres" in data
    
    # Check structure for each disease
    for disease in ["Depresi", "Kecemasan", "Stres"]:
        assert "persentase" in data[disease]
        assert "kategori" in data[disease]
        assert "keterangan" in data[disease]
        assert isinstance(data[disease]["persentase"], float)
        assert isinstance(data[disease]["kategori"], str)

def test_screening_invalid_code():
    """Test dengan kode gejala tidak valid"""
    test_data = {
        "jawaban": {
            "G99": "SS"  # Kode tidak valid
        }
    }
    
    response = client.post("/api/screening", json=test_data)
    assert response.status_code == 400
    assert "Kode gejala tidak valid" in response.json()["detail"]

def test_screening_invalid_value():
    """Test dengan nilai tidak valid"""
    test_data = {
        "jawaban": {
            "G01": "INVALID"  # Nilai tidak valid
        }
    }
    
    response = client.post("/api/screening", json=test_data)
    assert response.status_code == 400
    assert "Nilai tidak dikenali" in response.json()["detail"]

def test_screening_partial_data():
    """Test dengan data parsial"""
    test_data = {
        "jawaban": {
            "G01": "SS",
            "G02": "S"
        }
    }
    
    response = client.post("/api/screening", json=test_data)
    assert response.status_code == 200
    
    data = response.json()
    # Should still return all three diseases
    assert "Depresi" in data
    assert "Kecemasan" in data
    assert "Stres" in data

def test_screening_empty_data():
    """Test dengan data kosong"""
    test_data = {
        "jawaban": {}
    }
    
    response = client.post("/api/screening", json=test_data)
    assert response.status_code == 200
    
    data = response.json()
    # Should return all diseases with 0 percentage
    for disease in ["Depresi", "Kecemasan", "Stres"]:
        assert data[disease]["persentase"] == 0.0