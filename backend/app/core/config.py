from pydantic_settings import BaseSettings
from pydantic import field_validator
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
    RATE_LIMIT_AUTH: str = "20/hour"
    RATE_LIMIT_COPY: str = "30/hour"

    QUESTIONS_CONFIG_PATH: str = "/app/config/questions.yaml"
    QUESTIONS_WATCH_ENABLED: bool = True

    # VK ID
    VK_CLIENT_ID: str = ""
    # "Сервисный ключ доступа" (service_token) — им подписывается серверный обмен кода на токен.
    # Обязателен для конфиденциальных приложений.
    VK_SERVICE_TOKEN: str = ""
    # "Защищённый ключ" (client_secret). В серверном обмене кода VK ID не участвует.
    VK_CLIENT_SECRET: str = ""
    VK_REDIRECT_URI: str = "https://quest.leonet.site/api/auth/vk/callback"
    VK_AUTH_URL: str = "https://id.vk.com/authorize"
    VK_TOKEN_URL: str = "https://id.vk.com/oauth2/auth"
    VK_USERINFO_URL: str = "https://id.vk.com/oauth2/user_info"

    # Sessions
    SESSION_COOKIE_NAME: str = "quest_session"
    SESSION_TTL_HOURS: int = 24 * 7

    @field_validator("QUESTIONS_CONFIG_PATH")
    @classmethod
    def _default_questions_path(cls, value: str) -> str:
        return value or "/app/config/questions.yaml"

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
