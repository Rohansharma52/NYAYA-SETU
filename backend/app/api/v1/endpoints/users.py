"""User management endpoints (admin only) for NYAYA SETU."""
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy.orm import Session

from app.core.security import get_current_active_user, get_password_hash, require_roles
from app.db.session import get_db
from app.models.user import AccountStatus, User, UserRole
from app.services.audit import log_audit
from app.services.notification import create_notification

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/users", tags=["users"])

ADMIN_ROLES = (UserRole.SYSTEM_ADMIN.value,)

# ─── Schemas ──────────────────────────────────────────────────────────────────


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    account_status: str
    bureau_id: Optional[int] = None
    region: Optional[str] = None
    designation: Optional[str] = None
    is_active: bool
    is_superuser: bool

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    items: List[UserResponse]
    total: int
    skip: int
    limit: int


class CreateUserRequest(BaseModel):
    email: EmailStr
    full_name: str
    password: str
    role: UserRole
    bureau_id: Optional[int] = None
    region: Optional[str] = None
    designation: Optional[str] = None


class UpdateUserRequest(BaseModel):
    full_name: Optional[str] = None
    role: Optional[UserRole] = None
    account_status: Optional[AccountStatus] = None
    bureau_id: Optional[int] = None
    region: Optional[str] = None
    designation: Optional[str] = None
    is_active: Optional[bool] = None


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _get_user_or_404(user_id: int, db: Session) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return user


# ─── Endpoints ────────────────────────────────────────────────────────────────


@router.get("/", response_model=UserListResponse)
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    role: Optional[str] = None,
    account_status: Optional[str] = None,
    _: User = Depends(require_roles(UserRole.SYSTEM_ADMIN.value)),
    db: Session = Depends(get_db),
):
    """List all users with optional filters. Admin only."""
    try:
        q = db.query(User)
        if role:
            q = q.filter(User.role == role)
        if account_status:
            q = q.filter(User.account_status == account_status)
        total = q.count()
        users = q.offset(skip).limit(limit).all()
        return UserListResponse(items=users, total=total, skip=skip, limit=limit)
    except Exception as exc:
        logger.error("list_users error: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to fetch users.")


@router.get("/directory")
async def officer_directory(
    bureau_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Minimal officer directory (name, designation, bureau) for assignment pickers."""
    q = db.query(User).filter(User.is_active == True)  # noqa: E712
    if bureau_id:
        q = q.filter(User.bureau_id == bureau_id)
    return [
        {"id": u.id, "full_name": u.full_name, "designation": u.designation,
         "bureau_id": u.bureau_id, "role": u.role.value if hasattr(u.role, "value") else u.role}
        for u in q.order_by(User.full_name).all()
    ]


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: CreateUserRequest,
    admin: User = Depends(require_roles(UserRole.SYSTEM_ADMIN.value)),
    db: Session = Depends(get_db),
):
    """Admin creates a user directly with any role."""
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered.")
    try:
        user = User(
            email=payload.email,
            full_name=payload.full_name,
            hashed_password=get_password_hash(payload.password),
            role=payload.role,
            account_status=AccountStatus.ACTIVE,
            is_active=True,
            bureau_id=payload.bureau_id,
            region=payload.region,
            designation=payload.designation,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        log_audit(db, admin.id, "create_user", "user", user.id, f"Admin created user {user.email}")
        return user
    except Exception as exc:
        db.rollback()
        logger.error("create_user error: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to create user.")


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    _: User = Depends(require_roles(UserRole.SYSTEM_ADMIN.value)),
    db: Session = Depends(get_db),
):
    """Get a single user's details. Admin only."""
    return _get_user_or_404(user_id, db)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    payload: UpdateUserRequest,
    admin: User = Depends(require_roles(UserRole.SYSTEM_ADMIN.value)),
    db: Session = Depends(get_db),
):
    """Update user role, status, bureau, etc. Admin only."""
    user = _get_user_or_404(user_id, db)
    old = {"role": user.role, "account_status": user.account_status, "bureau_id": user.bureau_id}
    try:
        if payload.full_name is not None:
            user.full_name = payload.full_name
        if payload.role is not None:
            user.role = payload.role
        if payload.account_status is not None:
            user.account_status = payload.account_status
        if payload.bureau_id is not None:
            user.bureau_id = payload.bureau_id
        if payload.region is not None:
            user.region = payload.region
        if payload.designation is not None:
            user.designation = payload.designation
        if payload.is_active is not None:
            user.is_active = payload.is_active
        db.commit()
        db.refresh(user)
        log_audit(db, admin.id, "update_user", "user", user.id, "User updated", old_data=old)
        return user
    except Exception as exc:
        db.rollback()
        logger.error("update_user error: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to update user.")


@router.post("/{user_id}/approve", response_model=UserResponse)
async def approve_user(
    user_id: int,
    admin: User = Depends(require_roles(UserRole.SYSTEM_ADMIN.value)),
    db: Session = Depends(get_db),
):
    """Approve a pending user registration."""
    user = _get_user_or_404(user_id, db)
    if user.account_status != AccountStatus.PENDING:
        raise HTTPException(status_code=400, detail="User is not in pending status.")
    if user.role == UserRole.BUREAU_OFFICER and not user.bureau_id:
        raise HTTPException(status_code=422, detail="Assign the officer's Bureau / Cell before approving.")
    try:
        user.account_status = AccountStatus.ACTIVE
        user.is_active = True
        db.commit()
        db.refresh(user)
        log_audit(db, admin.id, "approve_user", "user", user.id, f"Approved user {user.email}")
        create_notification(
            db, user.id,
            "Account Approved",
            "Your NYAYA SETU account has been approved. You can now log in.",
            notification_type="account_approved",
        )
        return user
    except Exception as exc:
        db.rollback()
        logger.error("approve_user error: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to approve user.")


@router.post("/{user_id}/reject", response_model=UserResponse)
async def reject_user(
    user_id: int,
    admin: User = Depends(require_roles(UserRole.SYSTEM_ADMIN.value)),
    db: Session = Depends(get_db),
):
    """Reject a pending user registration."""
    user = _get_user_or_404(user_id, db)
    try:
        user.account_status = AccountStatus.REJECTED
        user.is_active = False
        db.commit()
        db.refresh(user)
        log_audit(db, admin.id, "reject_user", "user", user.id, f"Rejected user {user.email}")
        return user
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to reject user.")


@router.post("/{user_id}/suspend", response_model=UserResponse)
async def suspend_user(
    user_id: int,
    admin: User = Depends(require_roles(UserRole.SYSTEM_ADMIN.value)),
    db: Session = Depends(get_db),
):
    """Suspend an active user."""
    user = _get_user_or_404(user_id, db)
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot suspend yourself.")
    try:
        user.account_status = AccountStatus.SUSPENDED
        user.is_active = False
        db.commit()
        db.refresh(user)
        log_audit(db, admin.id, "suspend_user", "user", user.id, f"Suspended user {user.email}")
        return user
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to suspend user.")


@router.post("/{user_id}/reactivate", response_model=UserResponse)
async def reactivate_user(
    user_id: int,
    admin: User = Depends(require_roles(UserRole.SYSTEM_ADMIN.value)),
    db: Session = Depends(get_db),
):
    """Restore access for a suspended or rejected account."""
    user = _get_user_or_404(user_id, db)
    if user.account_status not in (AccountStatus.SUSPENDED, AccountStatus.REJECTED):
        raise HTTPException(status_code=400, detail="Only suspended or rejected accounts can be reactivated.")
    try:
        user.account_status = AccountStatus.ACTIVE
        user.is_active = True
        db.commit()
        db.refresh(user)
        log_audit(db, admin.id, "reactivate_user", "user", user.id, f"Reactivated user {user.email}")
        return user
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to reactivate user.")
