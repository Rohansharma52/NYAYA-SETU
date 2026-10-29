"""Institution models with multi-source identifier support."""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.db.session import Base


class InstitutionStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    UNDER_REVIEW = "under_review"
    MERGED = "merged"


class Institution(Base):
    __tablename__ = "institutions"

    id = Column(Integer, primary_key=True, index=True)
    canonical_name = Column(String(500), nullable=False, index=True)
    short_name = Column(String(100), nullable=True)
    institution_type = Column(String(100), nullable=True)  # university, college, deemed, etc.
    status = Column(SAEnum(InstitutionStatus), default=InstitutionStatus.ACTIVE)
    state = Column(String(100), nullable=True, index=True)
    district = Column(String(100), nullable=True)
    city = Column(String(100), nullable=True)
    region = Column(String(100), nullable=True, index=True)
    address = Column(Text, nullable=True)
    pincode = Column(String(10), nullable=True)
    phone = Column(String(20), nullable=True)
    email = Column(String(255), nullable=True)
    website = Column(String(500), nullable=True)
    # Data provenance
    data_source = Column(String(100), nullable=True)
    source_last_synced = Column(DateTime(timezone=True), nullable=True)
    import_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Relationships
    identifiers = relationship("InstitutionIdentifier", back_populates="institution", cascade="all, delete-orphan")
    cases = relationship("Case", back_populates="institution", lazy="dynamic")


class InstitutionIdentifier(Base):
    __tablename__ = "institution_identifiers"

    id = Column(Integer, primary_key=True, index=True)
    institution_id = Column(Integer, ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False)
    id_type = Column(String(50), nullable=False)  # aicte_permanent_id, aishe_id, nic_id, etc.
    id_value = Column(String(255), nullable=False)
    source_system = Column(String(100), nullable=True)
    is_primary = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False)
    verified_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    institution = relationship("Institution", back_populates="identifiers")
