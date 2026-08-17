from fastapi import APIRouter

from app.api.v1.endpoints import ai, dashboard, inventory, recipes


api_router = APIRouter()
api_router.include_router(dashboard.router, tags=["首页"])
api_router.include_router(inventory.router, prefix="/inventory", tags=["库存"])
api_router.include_router(ai.router, prefix="/ai", tags=["AI识别"])
api_router.include_router(recipes.router, prefix="/recipes", tags=["菜谱"])

