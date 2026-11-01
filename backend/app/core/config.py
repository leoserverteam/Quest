from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List


class Settings(BaseSettings):
    APP_NAME: str = "Quest"
    APP_ENV: str = "production"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    SECRET_KEY: str = "change_me"

    DATABASE_URL: str = "postgresql+psycopg2://quest:quest@db:5432/quest"

    CORS_ORIGINS: str = "https://quest.leonet.site,http://localhost:5173"

    UPLOAD_DIR: str = "/app/data/uploads"
    MAX_UPLOAD_SIZE_MB: int = 5
    ALLOWED_IMAGE_MIMES: str = "image/jpeg,image/png,image/webp,image/gif"

    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_CREATE_PROFILE: str = "10/hour"
    RATE_LIMIT_UPLOAD: str = "20/hour"
    RATE_LIMIT_EDIT: str = "60/hour"

    QUESTIONS_CONFIG_PATH: str = "/app/config/questions.yaml"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def allowed_mimes_list(self) -> List[str]:
        return [m.strip() for m in self.ALLOWED_IMAGE_MIMES.split(",") if m.strip()]


settings = Settings()
