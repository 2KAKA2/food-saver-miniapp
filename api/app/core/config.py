from datetime import date
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "食尽其用 API"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./data/food_inventory.db"
    redis_url: str = ""
    environment: str = "development"
    wechat_app_id: str = ""
    wechat_app_secret: str = ""
    session_ttl_days: int = 30
    legal_version: str = "2026-08-17"
    allow_dev_login: bool = False
    dev_login_secret: str = ""
    zhipu_api_key: str = ""
    zhipu_chat_model: str = "glm-4.7-flash"
    zhipu_vision_model: str = "glm-4.6v-flash"
    seed_demo_data: bool = False
    allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    allowed_hosts: str = "127.0.0.1,localhost"
    login_rate_limit: int = 10
    ai_rate_limit: int = 20

    @property
    def cors_origins(self) -> list[str]:
        return [item.strip() for item in self.allowed_origins.split(",") if item.strip()]

    @property
    def trusted_hosts(self) -> list[str]:
        return [item.strip() for item in self.allowed_hosts.split(",") if item.strip()]

    def validate_for_startup(self) -> None:
        if self.environment != "production":
            return
        problems = []
        if self.database_url.startswith("sqlite"):
            problems.append("生产环境不能使用 SQLite")
        if not self.wechat_app_id or not self.wechat_app_secret:
            problems.append("缺少微信 AppID 或 AppSecret")
        if not self.zhipu_api_key:
            problems.append("缺少 AI 服务 API Key")
        if not self.redis_url:
            problems.append("缺少 Redis 连接配置")
        if self.allow_dev_login:
            problems.append("生产环境必须关闭开发登录")
        if self.seed_demo_data:
            problems.append("生产环境必须关闭演示数据")
        if not self.trusted_hosts or "*" in self.trusted_hosts:
            problems.append("生产环境必须配置明确的 ALLOWED_HOSTS")
        try:
            date.fromisoformat(self.legal_version)
        except ValueError:
            problems.append("用户协议与隐私政策版本必须是有效日期")
        if problems:
            raise RuntimeError("生产配置校验失败：" + "；".join(problems))

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
