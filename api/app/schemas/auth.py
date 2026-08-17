from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class WechatLoginRequest(BaseModel):
    code: str = Field(min_length=1, max_length=200)
    legal_version: str = Field(min_length=1, max_length=20)


class DevLoginRequest(BaseModel):
    openid: str = Field(default="local-user", min_length=1, max_length=80)
    nickname: str = Field(default="本地体验用户", min_length=1, max_length=80)
    dev_key: str = Field(min_length=1, max_length=200)
    legal_version: str = Field(min_length=1, max_length=20)


class UserOut(BaseModel):
    id: int
    nickname: str


class HouseholdSummary(BaseModel):
    id: int
    name: str
    role: str
    member_count: int


class LoginOut(BaseModel):
    access_token: str
    expires_at: datetime
    user: UserOut
    households: list[HouseholdSummary]


class MeOut(BaseModel):
    user: UserOut
    households: list[HouseholdSummary]


class ProfileUpdate(BaseModel):
    nickname: str = Field(min_length=1, max_length=80)

    @field_validator("nickname")
    @classmethod
    def validate_nickname(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("昵称不能为空")
        return cleaned


class AccountDeleteRequest(BaseModel):
    confirmation: str = Field(min_length=1, max_length=20)
