"""Case models with lifecycle management."""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Enum as SAEnum, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.db.session import Base


class CaseStatus(str, enum.Enum):
    RECEIVED = "received"
    TRIAGED = "triaged"
    ASSIGNED = "assigned"
    UNDER_PROCESS = "under_process"
    AWAITING_INFORMATION = "awaiting_information"
    DECISION_REVIEW = "decision_review"
    DISPOSED = "disposed"
    TRANSFER_REQUESTED = "transfer_requested"
    TRANSFERRED = "transferred"
    ESCALATED = "escalated"
    REOPENED = "reopened"
    CLOSED = "closed"


class CasePriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class Case(Base):
    __tablename__ = "cases"

    id = Column(Integer, primary_key=True, index=True)
    case_number = Column(String(50), unique=True, nullable=False, index=True)
    source_case_id = Column(String(255), nullable=True, index=True)
    source_system = Column(String(100), nullable=True)

    institution_id = Column(Integer, ForeignKey("institutions.id"), nullable=False, index=True)
    bureau_id = Column(Integer, ForeignKey("bureaus.id"), nullable=True, index=True)
    assigned_officer_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    title = Column(String(500), nullable=False)
    summary = Column(Text, nullable=True)
    category = Column(String(200), nullable=False, index=True)
    sub_category = Column(String(200), nullable=True)

    status = Column(SAEnum(CaseStatus), nullable=False, default=CaseStatus.RECEIVED, index=True)
    priority = Column(SAEnum(CasePriority), nullable=False, default=CasePriority.MEDIUM)

    complainant_name = Column(String(255), nullable=True)
    complainant_email = Column(String(255), nullable=True)
    complainant_phone = Column(String(20), nullable=True)

    # Dates
    received_date = Column(DateTime(timezone=True), nullable=True)
    due_date = Column(DateTime(timezone=True), nullable=True)
    disposed_date = Column(DateTime(timezone=True), nullable=True)
    last_action_date = Column(DateTime(timezone=True), nullable=True)

    # Next action
    next_action = Column(Text, nullable=True)
    next_action_owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Data provenance
    source_last_synced = Column(DateTime(timezone=True), nullable=True)
    import_job_id = Column(Integer, ForeignKey("import_jobs.id"), nullable=True)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Relationships
    institution = relationship("Institution", back_populates="cases")
    bureau = relationship("Bureau", back_populates="cases")
    assigned_officer = relationship("User", foreign_keys=[assigned_officer_id])
    next_action_owner = relationship("User", foreign_keys=[next_action_owner_id])
    created_by = relationship("User", foreign_keys=[created_by_id])
    actions = relationship("CaseAction", back_populates="case", order_by="CaseAction.created_at", cascade="all, delete-orphan")
    assignments = relationship("CaseAssignment", back_populates="case", cascade="all, delete-orphan")
    relationships_as_case_a = relationship("CaseRelationship", foreign_keys="CaseRelationship.case_a_id", back_populates="case_a", cascade="all, delete-orphan")
    relationships_as_case_b = relationship("CaseRelationship", foreign_keys="CaseRelationship.case_b_id", back_populates="case_b")
    transfer_requests = relationship("TransferRequest", foreign_keys="TransferRequest.case_id", back_populates="case")


class CaseAction(Base):
    __tablename__ = "case_actions"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    action_type = Column(String(100), nullable=False)  # status_change, note, assignment, etc.
    description = Column(Text, nullable=False)
    old_status = Column(SAEnum(CaseStatus), nullable=True)
    new_status = Column(SAEnum(CaseStatus), nullable=True)
    performed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    case = relationship("Case", back_populates="actions")
    performed_by = relationship("User")


class CaseAssignment(Base):
    __tablename__ = "case_assignments"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    assigned_to_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    assigned_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    bureau_id = Column(Integer, ForeignKey("bureaus.id"), nullable=True)
    notes = Column(Text, nullable=True)
    is_current = Column(Boolean, default=True)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())
    ended_at = Column(DateTime(timezone=True), nullable=True)

    case = relationship("Case", back_populates="assignments")
    assigned_to = relationship("User", foreign_keys=[assigned_to_id])
    assigned_by = relationship("User", foreign_keys=[assigned_by_id])
