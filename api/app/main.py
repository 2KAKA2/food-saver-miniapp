from contextlib import asynccontextmanager
import logging
import time
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.db.session import SessionLocal
from app.seed import seed_demo_data
from app.services.rate_limit import limiter


def create_app(seed_demo: bool | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(_: FastAPI):
        settings.validate_for_startup()
        should_seed = settings.seed_demo_data if seed_demo is None else seed_demo
        if should_seed:
            with SessionLocal() as db:
                seed_demo_data(db)
        yield

    production = settings.environment == "production"
    application = FastAPI(
        title=settings.app_name,
        description="家庭食材库存、临期提醒与 AI 菜谱生成接口",
        version="0.1.0",
        docs_url=None if production else "/docs",
        redoc_url=None if production else "/redoc",
        openapi_url=None if production else "/openapi.json",
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts)
    application.include_router(api_router, prefix=settings.api_v1_prefix)

    access_logger = logging.getLogger("food_saver.access")

    @application.middleware("http")
    async def request_context(request, call_next):
        request_id = request.headers.get("X-Request-ID", "")
        if not request_id or len(request_id) > 80:
            request_id = uuid.uuid4().hex
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            access_logger.exception(
                "request_failed method=%s path=%s duration_ms=%s request_id=%s",
                request.method,
                request.url.path,
                duration_ms,
                request_id,
            )
            raise
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        access_logger.info(
            "request method=%s path=%s status=%s duration_ms=%s request_id=%s",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            request_id,
        )
        return response

    @application.get("/health", tags=["系统"])
    def health():
        return {"status": "ok", "name": settings.app_name}

    @application.get("/health/live", include_in_schema=False)
    def liveness():
        return {"status": "ok"}

    @application.get("/health/ready", include_in_schema=False)
    def readiness():
        checks = {"database": "ok"}
        try:
            with SessionLocal() as db:
                db.execute(text("SELECT 1"))
        except Exception as exc:
            raise HTTPException(status_code=503, detail="数据库暂不可用") from exc
        redis_ready, redis_status = limiter.health_status()
        checks["redis"] = redis_status
        if not redis_ready:
            raise HTTPException(status_code=503, detail="缓存与请求保护服务暂不可用")
        return {"status": "ready", "checks": checks}

    return application


app = create_app()
