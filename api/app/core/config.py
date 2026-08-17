from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "食尽其用 API"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./data/food_inventory.db"
    environment: str = "development"
    wechat_app_id: str = ""
    wechat_app_secret: str = ""
    session_ttl_days: int = 30
    allow_dev_login: bool = False
    dev_login_secret: str = ""
    zhipu_api_key: str = ""
    zhipu_chat_model: str = "glm-4.7-flash"
    zhipu_vision_model: str = "glm-4.6v-flash"
    seed_demo_data: bool = False
    allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def cors_origins(self) -> list[str]:
        return [item.strip() for item in self.allowed_origins.split(",") if item.strip()]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
