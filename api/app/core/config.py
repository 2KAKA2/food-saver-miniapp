from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "食尽其用 API"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./data/food_inventory.db"
    zhipu_api_key: str = ""
    zhipu_chat_model: str = "glm-4.7-flash"
    zhipu_vision_model: str = "glm-4.6v-flash"
    seed_demo_data: bool = True

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

