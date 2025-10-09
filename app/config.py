import os
from typing import List

class Settings:
    def __init__(self):
        self.app_name = os.getenv("APP_NAME", "Mental Health Screening API")
        self.app_version = os.getenv("APP_VERSION", "1.0.0")
        self.api_prefix = os.getenv("API_PREFIX", "/api")
        self.host = os.getenv("HOST", "0.0.0.0")
        self.port = int(os.getenv("PORT", 8000))
        self.debug = os.getenv("DEBUG", "False").lower() == "true"
        self.allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")
        
        # Security settings
        self.enable_rate_limit = os.getenv("ENABLE_RATE_LIMIT", "True").lower() == "true"

settings = Settings()