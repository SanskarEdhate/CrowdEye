import os
from pathlib import Path
from typing import List, Union
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Resolve paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BASE_DIR / ".env"

if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)
else:
    load_dotenv()


class Settings(BaseSettings):
    PROJECT_NAME: str = "CrowdEye AI"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")

    # Host & Port
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    # Supabase Credentials
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_SERVICE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY", "")

    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000,http://localhost:5500,http://127.0.0.1:5500,http://localhost:8000,https://crowdeye-ai.vercel.app")
    CORS_ORIGINS_RAW: str = os.getenv("CORS_ORIGINS", "")

    @property
    def cors_origins(self) -> List[str]:
        """
        TASK 7: Strict CORS hardening.
        Prohibits wildcard '*' in production environments.
        """
        raw = self.CORS_ORIGINS_RAW or self.FRONTEND_URL
        origins = [o.strip() for o in raw.split(",") if o.strip() and o.strip() != "*"]
        if not origins:
            return ["http://localhost:3000", "http://localhost:5500", "http://127.0.0.1:5500", "https://crowdeye-ai.vercel.app"]
        return origins

    @property
    def is_supabase_configured(self) -> bool:
        return bool(
            self.SUPABASE_URL
            and self.SUPABASE_SERVICE_KEY
            and self.SUPABASE_URL.startswith("http")
        )

    class Config:
        env_file = str(ENV_PATH)
        extra = "ignore"


settings = Settings()
