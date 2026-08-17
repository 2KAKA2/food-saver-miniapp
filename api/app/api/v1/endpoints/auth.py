from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.entities import User, UserSession
from app.schemas.auth import DevLoginRequest, LoginOut, MeOut, ProfileUpdate, UserOut, WechatLoginRequest
from app.services.auth import (
    check_dev_key,
    create_session,
    exchange_wechat_code,
    get_current_user,
    get_or_create_user,
    list_households,
    sha256_token,
)


router = APIRouter()


def user_out(user: User) -> UserOut:
    return UserOut(id=user.id, nickname=user.nickname, avatar_url=user.avatar_url)


def login_out(db: Session, user: User, token: str, session: UserSession) -> LoginOut:
    return LoginOut(
        access_token=token,
        expires_at=session.expires_at,
        user=user_out(user),
        households=list_households(db, user.id),
    )


@router.post("/wechat", response_model=LoginOut)
def wechat_login(payload: WechatLoginRequest, db: Session = Depends(get_db)):
    identity = exchange_wechat_code(payload.code)
    user = get_or_create_user(
        db,
        openid=identity["openid"],
        unionid=identity.get("unionid"),
        nickname=payload.nickname,
        avatar_url=str(payload.avatar_url) if payload.avatar_url else None,
    )
    token, session = create_session(db, user)
    return login_out(db, user, token, session)


@router.post("/dev", response_model=LoginOut)
def dev_login(payload: DevLoginRequest, db: Session = Depends(get_db)):
    if not check_dev_key(payload.dev_key):
        raise HTTPException(status_code=404, detail="接口不存在")
    user = get_or_create_user(db, openid=f"dev:{payload.openid}", nickname=payload.nickname)
    token, session = create_session(db, user)
    return login_out(db, user, token, session)


@router.get("/me", response_model=MeOut)
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return MeOut(user=user_out(user), households=list_households(db, user.id))


@router.put("/profile", response_model=UserOut)
def update_profile(
    payload: ProfileUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user.nickname = payload.nickname.strip()
    user.avatar_url = str(payload.avatar_url) if payload.avatar_url else ""
    db.commit()
    db.refresh(user)
    return user_out(user)


@router.post("/logout", status_code=204)
def logout(
    authorization: str | None = Header(default=None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    del user
    token = (authorization or "")[7:].strip()
    session = db.scalar(select(UserSession).where(UserSession.token_hash == sha256_token(token)))
    if session:
        session.revoked_at = datetime.now()
        db.commit()
    return Response(status_code=204)

