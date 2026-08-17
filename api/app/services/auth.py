import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta

import httpx
from fastapi import Depends, Header, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.entities import Household, HouseholdMember, User, UserSession


WECHAT_CODE2SESSION_URL = "https://api.weixin.qq.com/sns/jscode2session"


def sha256_token(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def exchange_wechat_code(code: str) -> dict:
    if not settings.wechat_app_id or not settings.wechat_app_secret:
        raise HTTPException(status_code=503, detail="服务端尚未配置微信登录")
    try:
        response = httpx.get(
            WECHAT_CODE2SESSION_URL,
            params={
                "appid": settings.wechat_app_id,
                "secret": settings.wechat_app_secret,
                "js_code": code,
                "grant_type": "authorization_code",
            },
            timeout=10.0,
        )
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(status_code=502, detail="微信登录服务暂时不可用") from exc
    if payload.get("errcode"):
        raise HTTPException(status_code=401, detail="微信登录凭证无效或已过期")
    if not payload.get("openid"):
        raise HTTPException(status_code=502, detail="微信登录响应缺少用户标识")
    return payload


def get_or_create_user(
    db: Session,
    *,
    openid: str,
    unionid: str | None = None,
    nickname: str | None = None,
    legal_version: str,
) -> User:
    user = db.scalar(select(User).where(User.openid == openid))
    now = datetime.now()
    if not user:
        user = User(
            openid=openid,
            unionid=unionid,
            nickname=nickname or "微信用户",
            last_login_at=now,
        )
        db.add(user)
        db.flush()
    else:
        if user.status != "active":
            raise HTTPException(status_code=403, detail="账号已停用")
        user.last_login_at = now
        if unionid and not user.unionid:
            user.unionid = unionid
        if nickname:
            user.nickname = nickname
    user.legal_version = legal_version
    user.legal_accepted_at = now
    ensure_personal_household(db, user)
    return user


def ensure_personal_household(db: Session, user: User) -> None:
    membership = db.scalar(select(HouseholdMember).where(HouseholdMember.user_id == user.id))
    if membership:
        return
    household = Household(name="我的家庭", owner_id=user.id)
    db.add(household)
    db.flush()
    db.add(HouseholdMember(household_id=household.id, user_id=user.id, role="owner"))


def create_session(db: Session, user: User) -> tuple[str, UserSession]:
    raw_token = secrets.token_urlsafe(32)
    expires_at = datetime.now() + timedelta(days=settings.session_ttl_days)
    session = UserSession(
        user_id=user.id,
        token_hash=sha256_token(raw_token),
        expires_at=expires_at,
    )
    db.add(session)
    db.commit()
    db.refresh(user)
    db.refresh(session)
    return raw_token, session


def check_dev_key(value: str) -> bool:
    return bool(
        settings.allow_dev_login
        and settings.dev_login_secret
        and hmac.compare_digest(value, settings.dev_login_secret)
    )


def list_households(db: Session, user_id: int) -> list[dict]:
    rows = db.execute(
        select(Household, HouseholdMember.role)
        .join(HouseholdMember, HouseholdMember.household_id == Household.id)
        .where(HouseholdMember.user_id == user_id)
        .order_by(Household.created_at, Household.id)
    ).all()
    result = []
    for household, role in rows:
        member_count = db.scalar(
            select(func.count()).select_from(HouseholdMember).where(
                HouseholdMember.household_id == household.id
            )
        ) or 0
        result.append(
            {"id": household.id, "name": household.name, "role": role, "member_count": member_count}
        )
    return result


def _bearer_token(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="请先登录")
    token = authorization[7:].strip()
    if not token:
        raise HTTPException(status_code=401, detail="登录凭证无效")
    return token


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    token = _bearer_token(authorization)
    now = datetime.now()
    session = db.scalar(
        select(UserSession).where(
            UserSession.token_hash == sha256_token(token),
            UserSession.revoked_at.is_(None),
            UserSession.expires_at > now,
        )
    )
    if not session:
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")
    user = db.get(User, session.user_id)
    if not user or user.status != "active":
        raise HTTPException(status_code=401, detail="账号不可用")
    if user.legal_version != settings.legal_version:
        session.revoked_at = now
        db.commit()
        raise HTTPException(status_code=401, detail="用户协议或隐私政策已更新，请重新阅读并登录")
    session.last_seen_at = now
    return user


@dataclass
class HouseholdContext:
    user: User
    household: Household
    role: str


def get_household_context(
    x_household_id: int | None = Header(default=None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> HouseholdContext:
    memberships = db.scalars(select(HouseholdMember).where(HouseholdMember.user_id == user.id)).all()
    if not memberships:
        raise HTTPException(status_code=403, detail="当前账号未加入家庭")
    if x_household_id is None:
        if len(memberships) != 1:
            raise HTTPException(status_code=400, detail="请选择当前家庭")
        membership = memberships[0]
    else:
        membership = next((item for item in memberships if item.household_id == x_household_id), None)
        if not membership:
            raise HTTPException(status_code=403, detail="无权访问该家庭")
    household = db.get(Household, membership.household_id)
    if not household:
        raise HTTPException(status_code=404, detail="家庭不存在")
    return HouseholdContext(user=user, household=household, role=membership.role)


def require_owner(context: HouseholdContext = Depends(get_household_context)) -> HouseholdContext:
    if context.role != "owner":
        raise HTTPException(status_code=403, detail="只有家庭所有者可以执行此操作")
    return context
