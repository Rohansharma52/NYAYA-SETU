"""User model with role-based access control."""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.db.session import Base


class UserRole(str, enum.Enum):
    SYSTEM_ADMIN = "system_admin"
    SENIOR_MANAGEMENT = "senior_management"
    BUREAU_OFFICER = "bureau_officer"
    REGIONAL_OFFICER = "regional_officer"
    DATA_ADMIN = "data_admin"
    COORDINATION_REVIEWER = "coordination_reviewer"


class AccountStatus(str, enum.Enum):
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    REJECTED = "rejected"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(SAEnum(UserRole), nullable=False, default=UserRole.BUREAU_OFFICER)
    account_status = Column(SAEnum(AccountStatus), nullable=False, default=AccountStatus.PENDING)
    bureau_id = Column(Integer, nullable=True)
    region = Column(String(100), nullable=True)
    designation = Column(String(200), nullable=True)
    is_active = Column(Boolean, default=False)
    is_superuser = Column(Boolean, default=False)
    last_login = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    notifications = relationship("Notification", back_populates="user", lazy="dynamic")
    audit_events = relationship("AuditEvent", back_populates="user", lazy="dynamic")
