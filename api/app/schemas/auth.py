from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl


class WechatLoginRequest(BaseModel):
    code: str = Field(min_length=1, max_length=200)
    nickname: str | None = Field(default=None, max_length=80)
    avatar_url: HttpUrl | None = None


class DevLoginRequest(BaseModel):
    openid: str = Field(default="local-user", min_length=1, max_length=80)
    nickname: str = Field(default="本地体验用户", min_length=1, max_length=80)
    dev_key: str = Field(min_length=1, max_length=200)


class UserOut(BaseModel):
    id: int
    nickname: str
    avatar_url: str


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
    avatar_url: HttpUrl | None = None


class AccountDeleteRequest(BaseModel):
    confirmation: str = Field(min_length=1, max_length=20)
