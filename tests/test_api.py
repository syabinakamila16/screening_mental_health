from fastapi.testclient import TestClient
from app.main import app
client = TestClient(app)
def test_root():
    response = client.get("/")
    assert response.status_code == 200
    print("✅ Root endpoint working!")
def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    print("✅ Health check working!")
if __name__ == "__main__":
    test_root()
    test_health()
    print("🎉 All tests passed!")

# test_installation.py
try:
    from fastapi import FastAPI
    from pydantic import BaseModel
    from jose import JWTError, jwt
    from passlib.context import CryptContext
    import uvicorn
    import bcrypt
    
    print("✅ Semua modul berhasil diimport!")
    print("🔒 HTTPS siap diimplementasikan!")
    
except ImportError as e:
    print(f"❌ Error: {e}")
    print("📦 Jalankan: pip install -r requirements.txt")