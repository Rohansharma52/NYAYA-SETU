"""Authentication endpoints for NYAYA SETU."""
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    get_current_active_user,
    get_password_hash,
    verify_password,
)
from app.db.session import get_db
from app.models.user import AccountStatus, User, UserRole

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])

# ─── Schemas ──────────────────────────────────────────────────────────────────


class Token(BaseModel):
    access_token: str
    token_type: str
    user_id: int
    email: str
    full_name: str
    role: str
    bureau_id: Optional[int] = None


class SignupRequest(BaseModel):
    email: EmailStr
    full_name: str
    password: str
    designation: Optional[str] = None

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v

    @field_validator("full_name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("full_name cannot be empty")
        return v.strip()


class UserProfileResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    account_status: str
    bureau_id: Optional[int] = None
    region: Optional[str] = None
    designation: Optional[str] = None
    is_active: bool
    last_login: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UpdateProfileRequest(BaseModel):
    full_name: Optional[str] = None
    designation: Optional[str] = None


# ─── Endpoints ────────────────────────────────────────────────────────────────


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Authenticate user and return JWT access token.

    Rate limiting should be applied at the API gateway/reverse proxy level.
    This endpoint intentionally returns a generic error to prevent user enumeration.
    """
    user: Optional[User] = db.query(User).filter(User.email == form_data.username).first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is not active. Please contact the administrator.",
        )

    if user.account_status == AccountStatus.SUSPENDED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account has been suspended.",
        )

    if user.account_status == AccountStatus.REJECTED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account registration was rejected.",
        )

    # Update last login
    try:
        user.last_login = datetime.now(timezone.utc)
        db.commit()
        db.refresh(user)
    except Exception as exc:
        logger.warning("Could not update last_login: %s", exc)
        db.rollback()

    access_token = create_access_token(data={"sub": str(user.id)})

    return Token(
        access_token=access_token,
        token_type="bearer",
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role.value,
        bureau_id=user.bureau_id,
    )


@router.post("/signup", status_code=status.HTTP_201_CREATED)
async def signup(
    payload: SignupRequest,
    db: Session = Depends(get_db),
):
    """Public self-registration endpoint.

    Creates a bureau_officer account with pending status.
    Account requires admin approval before it becomes active.

    SECURITY: This endpoint can never set privileged roles (admin/senior management).
    """
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists.",
        )

    try:
        user = User(
            email=payload.email,
            full_name=payload.full_name,
            hashed_password=get_password_hash(payload.password),
            designation=payload.designation,
            # ALWAYS force safe defaults — never trust client for role/status
            role=UserRole.BUREAU_OFFICER,
            account_status=AccountStatus.PENDING,
            is_active=False,
            is_superuser=False,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed. Please try again later.",
        )

    return {
        "message": "Registration successful. Your account is pending administrator approval.",
        "user_id": user.id,
    }


@router.get("/me", response_model=UserProfileResponse)
async def get_me(current_user: User = Depends(get_current_active_user)):
    """Return the currently authenticated user's profile."""
    return current_user


@router.put("/me", response_model=UserProfileResponse)
async def update_me(
    payload: UpdateProfileRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update own profile. Only full_name and designation can be changed."""
    try:
        if payload.full_name is not None:
            current_user.full_name = payload.full_name.strip()
        if payload.designation is not None:
            current_user.designation = payload.designation.strip()
        db.commit()
        db.refresh(current_user)
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update profile.")
    return current_user


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_active_user)):
    """Logout endpoint. Token invalidation is handled client-side.

    In a production system with token blacklisting, the token would be
    added to a Redis blocklist here.
    """
    return {"message": "Logged out successfully."}
