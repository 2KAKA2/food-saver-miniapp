from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.schemas.api import RecognitionOut
from app.services.ai import recognize_ingredients
from app.services.auth import HouseholdContext, get_household_context


router = APIRouter()
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_IMAGE_SIZE = 5 * 1024 * 1024


@router.post("/recognize-ingredients", response_model=RecognitionOut)
async def recognize(
    file: UploadFile = File(...),
    context: HouseholdContext = Depends(get_household_context),
):
    del context
    content_type = file.content_type or ""
    if content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=415, detail="仅支持 JPG、PNG 或 WebP 图片")
    content = await file.read(MAX_IMAGE_SIZE + 1)
    if not content:
        raise HTTPException(status_code=400, detail="图片内容为空")
    if len(content) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=413, detail="图片不能超过 5MB")
    return recognize_ingredients(content, content_type)
