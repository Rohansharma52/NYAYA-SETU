"""Deadline extension request model."""
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.db.session import Base


class ExtensionStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class DeadlineExtensionRequest(Base):
    __tablename__ = "deadline_extension_requests"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    requested_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    original_due_date = Column(DateTime(timezone=True), nullable=True)
    requested_due_date = Column(DateTime(timezone=True), nullable=False)
    reason = Column(Text, nullable=False)
    status = Column(SAEnum(ExtensionStatus), default=ExtensionStatus.PENDING, nullable=False)
    reviewed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    review_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    case = relationship("Case", foreign_keys=[case_id])
    requested_by = relationship("User", foreign_keys=[requested_by_id])
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_id])
