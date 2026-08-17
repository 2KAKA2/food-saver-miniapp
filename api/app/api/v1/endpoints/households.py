import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.v1.endpoints.auth import user_out
from app.db.session import get_db
from app.models.entities import Household, HouseholdInvite, HouseholdMember, User
from app.schemas.auth import HouseholdSummary
from app.schemas.household import (
    HouseholdCreate,
    HouseholdDetail,
    HouseholdMemberOut,
    HouseholdUpdate,
    InviteAccept,
    InviteCreate,
    InviteOut,
    TransferOwnerRequest,
)
from app.services.auth import (
    HouseholdContext,
    get_current_user,
    get_household_context,
    list_households,
    require_owner,
    sha256_token,
)


router = APIRouter()


def household_detail(db: Session, household: Household, role: str) -> HouseholdDetail:
    rows = db.execute(
        select(HouseholdMember, User)
        .join(User, User.id == HouseholdMember.user_id)
        .where(HouseholdMember.household_id == household.id)
        .order_by(HouseholdMember.joined_at, HouseholdMember.id)
    ).all()
    return HouseholdDetail(
        id=household.id,
        name=household.name,
        role=role,
        member_count=len(rows),
        members=[
            HouseholdMemberOut(user=user_out(user), role=member.role, joined_at=member.joined_at)
            for member, user in rows
        ],
    )


@router.get("", response_model=list[HouseholdSummary])
def households(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return list_households(db, user.id)


@router.post("", response_model=HouseholdSummary, status_code=status.HTTP_201_CREATED)
def create_household(
    payload: HouseholdCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    household = Household(name=payload.name.strip(), owner_id=user.id)
    db.add(household)
    db.flush()
    db.add(HouseholdMember(household_id=household.id, user_id=user.id, role="owner"))
    db.commit()
    return HouseholdSummary(id=household.id, name=household.name, role="owner", member_count=1)


@router.get("/current", response_model=HouseholdDetail)
def current_household(
    context: HouseholdContext = Depends(get_household_context),
    db: Session = Depends(get_db),
):
    return household_detail(db, context.household, context.role)


@router.put("/current", response_model=HouseholdDetail)
def update_household(
    payload: HouseholdUpdate,
    context: HouseholdContext = Depends(require_owner),
    db: Session = Depends(get_db),
):
    context.household.name = payload.name.strip()
    db.commit()
    db.refresh(context.household)
    return household_detail(db, context.household, context.role)


@router.post("/current/invites", response_model=InviteOut, status_code=status.HTTP_201_CREATED)
def create_invite(
    payload: InviteCreate,
    context: HouseholdContext = Depends(require_owner),
    db: Session = Depends(get_db),
):
    raw_code = secrets.token_urlsafe(12)
    invite = HouseholdInvite(
        household_id=context.household.id,
        creator_id=context.user.id,
        code_hash=sha256_token(raw_code),
        expires_at=datetime.now() + timedelta(hours=payload.expires_in_hours),
        max_uses=payload.max_uses,
    )
    db.add(invite)
    db.commit()
    db.refresh(invite)
    return InviteOut(
        invite_id=invite.id,
        invite_code=raw_code,
        expires_at=invite.expires_at,
        max_uses=invite.max_uses,
    )


@router.delete("/current/invites/{invite_id}", status_code=204)
def revoke_invite(
    invite_id: int,
    context: HouseholdContext = Depends(require_owner),
    db: Session = Depends(get_db),
):
    invite = db.get(HouseholdInvite, invite_id)
    if not invite or invite.household_id != context.household.id:
        raise HTTPException(status_code=404, detail="邀请不存在")
    invite.revoked_at = datetime.now()
    db.commit()
    return Response(status_code=204)


@router.post("/join", response_model=HouseholdSummary)
def join_household(
    payload: InviteAccept,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    now = datetime.now()
    invite = db.scalar(
        select(HouseholdInvite)
        .where(
            HouseholdInvite.code_hash == sha256_token(payload.invite_code.strip()),
            HouseholdInvite.revoked_at.is_(None),
            HouseholdInvite.expires_at > now,
            HouseholdInvite.used_count < HouseholdInvite.max_uses,
        )
        .with_for_update()
    )
    if not invite:
        raise HTTPException(status_code=404, detail="邀请无效、已过期或已用完")
    existing = db.scalar(
        select(HouseholdMember).where(
            HouseholdMember.household_id == invite.household_id,
            HouseholdMember.user_id == user.id,
        )
    )
    if existing:
        raise HTTPException(status_code=409, detail="你已经是该家庭成员")
    db.add(HouseholdMember(household_id=invite.household_id, user_id=user.id, role="member"))
    invite.used_count += 1
    db.commit()
    household = db.get(Household, invite.household_id)
    member_count = db.scalar(
        select(func.count()).select_from(HouseholdMember).where(
            HouseholdMember.household_id == invite.household_id
        )
    ) or 0
    return HouseholdSummary(id=household.id, name=household.name, role="member", member_count=member_count)


@router.delete("/current/members/{user_id}", status_code=204)
def remove_member(
    user_id: int,
    context: HouseholdContext = Depends(require_owner),
    db: Session = Depends(get_db),
):
    if user_id == context.user.id:
        raise HTTPException(status_code=409, detail="所有者不能移除自己，请先转让家庭")
    membership = db.scalar(
        select(HouseholdMember).where(
            HouseholdMember.household_id == context.household.id,
            HouseholdMember.user_id == user_id,
        )
    )
    if not membership:
        raise HTTPException(status_code=404, detail="家庭成员不存在")
    db.delete(membership)
    db.commit()
    return Response(status_code=204)


@router.post("/current/transfer", response_model=HouseholdDetail)
def transfer_owner(
    payload: TransferOwnerRequest,
    context: HouseholdContext = Depends(require_owner),
    db: Session = Depends(get_db),
):
    target = db.scalar(
        select(HouseholdMember).where(
            HouseholdMember.household_id == context.household.id,
            HouseholdMember.user_id == payload.new_owner_user_id,
        )
    )
    current = db.scalar(
        select(HouseholdMember).where(
            HouseholdMember.household_id == context.household.id,
            HouseholdMember.user_id == context.user.id,
        )
    )
    if not target or target.user_id == context.user.id:
        raise HTTPException(status_code=422, detail="请选择其他家庭成员")
    target.role = "owner"
    current.role = "member"
    context.household.owner_id = target.user_id
    db.commit()
    return household_detail(db, context.household, "member")


@router.post("/current/leave", status_code=204)
def leave_household(
    context: HouseholdContext = Depends(get_household_context),
    db: Session = Depends(get_db),
):
    if context.role == "owner":
        raise HTTPException(status_code=409, detail="家庭所有者需先转让家庭后才能退出")
    membership = db.scalar(
        select(HouseholdMember).where(
            HouseholdMember.household_id == context.household.id,
            HouseholdMember.user_id == context.user.id,
        )
    )
    db.delete(membership)
    db.commit()
    return Response(status_code=204)

