from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.schemas.auth import HouseholdSummary, UserOut


class HouseholdCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("家庭名称不能为空")
        return cleaned


class HouseholdUpdate(HouseholdCreate):
    pass


class HouseholdMemberOut(BaseModel):
    user: UserOut
    role: str
    joined_at: datetime


class HouseholdDetail(HouseholdSummary):
    members: list[HouseholdMemberOut]


class InviteCreate(BaseModel):
    expires_in_hours: int = Field(default=24, ge=1, le=168)
    max_uses: int = Field(default=1, ge=1, le=20)


class InviteOut(BaseModel):
    invite_id: int
    invite_code: str
    expires_at: datetime
    max_uses: int


class InviteAccept(BaseModel):
    invite_code: str = Field(min_length=8, max_length=200)


class TransferOwnerRequest(BaseModel):
    new_owner_user_id: int
