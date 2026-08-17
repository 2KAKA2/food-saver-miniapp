from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.schemas.api import RecognitionOut
from app.services.ai import recognize_ingredients
from app.services.auth import HouseholdContext, get_household_context
from app.services.rate_limit import ai_rate_limit


router = APIRouter()
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_IMAGE_SIZE = 5 * 1024 * 1024


def detect_image_type(content: bytes) -> str | None:
    if content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "image/webp"
    return None


@router.post(
    "/recognize-ingredients",
    response_model=RecognitionOut,
    dependencies=[Depends(ai_rate_limit)],
)
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
    detected_type = detect_image_type(content)
    if detected_type is None:
        raise HTTPException(status_code=400, detail="图片内容无效，请重新选择图片")
    if detected_type != content_type:
        raise HTTPException(status_code=415, detail="图片格式与文件类型不一致")
    return recognize_ingredients(content, content_type)
