"""Coordination Closure Protocol (CCP) models."""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Enum as SAEnum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.db.session import Base


class CoordinationStatus(str, enum.Enum):
    DETECTED = "detected"
    UNDER_REVIEW = "under_review"
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    FOLLOW_UP = "follow_up"
    CLOSURE_REVIEW = "closure_review"
    CLOSED = "closed"
    DISMISSED = "dismissed"
    ESCALATED = "escalated"


class CoordinationDecision(str, enum.Enum):
    COORDINATE = "coordinate"
    LINK_RELATED = "link_related"
    KEEP_SEPARATE = "keep_separate"
    DISMISS = "dismiss"
    ESCALATE = "escalate"


class CoordinationItem(Base):
    """Main coordination record — one per cross-bureau coordination initiative."""
    __tablename__ = "coordination_items"

    id = Column(Integer, primary_key=True, index=True)
    reference_number = Column(String(50), unique=True, nullable=False, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)

    # Source relationship
    source_relationship_id = Column(Integer, ForeignKey("case_relationships.id"), nullable=True)

    # "One Institution, One Voice" — institution-level coordination with a lead bureau
    institution_id = Column(Integer, ForeignKey("institutions.id"), nullable=True, index=True)
    lead_bureau_id = Column(Integer, ForeignKey("bureaus.id"), nullable=True)

    # Owner and status
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    status = Column(SAEnum(CoordinationStatus), default=CoordinationStatus.DETECTED, index=True)
    decision = Column(SAEnum(CoordinationDecision), nullable=True)
    decision_rationale = Column(Text, nullable=True)
    decision_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    decision_at = Column(DateTime(timezone=True), nullable=True)

    # Deadlines
    acknowledge_by = Column(DateTime(timezone=True), nullable=True)
    action_due_date = Column(DateTime(timezone=True), nullable=True)

    # Closure
    closure_notes = Column(Text, nullable=True)
    closed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)
    is_exception_closure = Column(Boolean, default=False)
    exception_reason = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Relationships
    participants = relationship("CoordinationParticipant", back_populates="coordination_item", cascade="all, delete-orphan")
    tasks = relationship("CoordinationTask", back_populates="coordination_item", cascade="all, delete-orphan")
    owner = relationship("User", foreign_keys=[owner_id])
    institution = relationship("Institution")
    lead_bureau = relationship("Bureau", foreign_keys=[lead_bureau_id])
    decision_by = relationship("User", foreign_keys=[decision_by_id])
    closed_by = relationship("User", foreign_keys=[closed_by_id])
    created_by = relationship("User", foreign_keys=[created_by_id])


class CoordinationParticipant(Base):
    __tablename__ = "coordination_participants"

    id = Column(Integer, primary_key=True, index=True)
    coordination_item_id = Column(Integer, ForeignKey("coordination_items.id", ondelete="CASCADE"), nullable=False)
    bureau_id = Column(Integer, ForeignKey("bureaus.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    role_in_coordination = Column(String(100), nullable=True)  # lead, reviewer, observer
    acknowledged = Column(Boolean, default=False)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    added_at = Column(DateTime(timezone=True), server_default=func.now())

    coordination_item = relationship("CoordinationItem", back_populates="participants")
    bureau = relationship("Bureau")
    user = relationship("User")


class CoordinationTask(Base):
    """Follow-up tasks within a coordination item."""
    __tablename__ = "coordination_tasks"

    id = Column(Integer, primary_key=True, index=True)
    coordination_item_id = Column(Integer, ForeignKey("coordination_items.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    assigned_to_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    due_date = Column(DateTime(timezone=True), nullable=True)
    is_completed = Column(Boolean, default=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    completed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    completion_notes = Column(Text, nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    coordination_item = relationship("CoordinationItem", back_populates="tasks")
    assigned_to = relationship("User", foreign_keys=[assigned_to_id])
    completed_by = relationship("User", foreign_keys=[completed_by_id])
    created_by = relationship("User", foreign_keys=[created_by_id])
