from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Response
import secrets

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.entities import (
    Household,
    HouseholdInvite,
    HouseholdMember,
    InventoryBatch,
    Recipe,
    StockChange,
    User,
    UserSession,
)
from app.schemas.auth import (
    AccountDeleteRequest,
    DevLoginRequest,
    LoginOut,
    MeOut,
    ProfileUpdate,
    UserOut,
    WechatLoginRequest,
)
from app.services.auth import (
    check_dev_key,
    create_session,
    exchange_wechat_code,
    get_current_user,
    get_or_create_user,
    list_households,
    sha256_token,
)
from app.services.rate_limit import login_rate_limit


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


@router.post("/wechat", response_model=LoginOut, dependencies=[Depends(login_rate_limit)])
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


@router.post("/dev", response_model=LoginOut, dependencies=[Depends(login_rate_limit)])
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


@router.delete("/account", status_code=204)
def delete_account(
    payload: AccountDeleteRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.confirmation != "注销账号":
        raise HTTPException(status_code=422, detail="请输入“注销账号”确认操作")

    owned_households = db.scalars(select(Household).where(Household.owner_id == user.id)).all()
    for household in owned_households:
        member_count = db.scalar(
            select(func.count()).select_from(HouseholdMember).where(
                HouseholdMember.household_id == household.id
            )
        ) or 0
        if member_count > 1:
            raise HTTPException(
                status_code=409,
                detail=f"请先转让“{household.name}”的所有者后再注销账号",
            )

    owned_ids = [item.id for item in owned_households]
    if owned_ids:
        recipe_ids = db.scalars(select(Recipe.id).where(Recipe.household_id.in_(owned_ids))).all()
        db.execute(delete(StockChange).where(StockChange.household_id.in_(owned_ids)))
        if recipe_ids:
            db.execute(delete(Recipe).where(Recipe.id.in_(recipe_ids)))
        db.execute(delete(InventoryBatch).where(InventoryBatch.household_id.in_(owned_ids)))
        db.execute(delete(HouseholdInvite).where(HouseholdInvite.household_id.in_(owned_ids)))
        db.execute(delete(HouseholdMember).where(HouseholdMember.household_id.in_(owned_ids)))
        db.execute(delete(Household).where(Household.id.in_(owned_ids)))

    db.execute(delete(HouseholdMember).where(HouseholdMember.user_id == user.id))
    now = datetime.now()
    db.execute(
        UserSession.__table__.update().where(UserSession.user_id == user.id).values(revoked_at=now)
    )
    user.openid = f"deleted:{user.id}:{secrets.token_hex(12)}"
    user.unionid = None
    user.nickname = "已注销用户"
    user.avatar_url = ""
    user.status = "deleted"
    user.updated_at = now
    db.commit()
    return Response(status_code=204)
