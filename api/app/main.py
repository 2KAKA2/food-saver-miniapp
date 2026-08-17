from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.db.session import SessionLocal
from app.seed import seed_demo_data


def create_app(seed_demo: bool | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(_: FastAPI):
        should_seed = settings.seed_demo_data if seed_demo is None else seed_demo
        if should_seed:
            with SessionLocal() as db:
                seed_demo_data(db)
        yield

    application = FastAPI(
        title=settings.app_name,
        description="家庭食材库存、临期提醒与 AI 菜谱生成接口",
        version="0.1.0",
        docs_url="/docs",
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(api_router, prefix=settings.api_v1_prefix)

    @application.get("/health", tags=["系统"])
    def health():
        return {"status": "ok", "name": settings.app_name}

    return application


app = create_app()
