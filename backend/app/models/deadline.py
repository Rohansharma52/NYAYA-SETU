"""Deadline and escalation models."""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Enum as SAEnum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base


class DeadlineRule(Base):
    __tablename__ = "deadline_rules"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    applies_to = Column(String(100), nullable=False)  # case_category, coordination, bureau
    applies_to_value = Column(String(200), nullable=True)
    days_to_resolve = Column(Integer, nullable=False, default=30)
    escalation_after_days = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class CaseDeadline(Base):
    __tablename__ = "case_deadlines"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    deadline_rule_id = Column(Integer, ForeignKey("deadline_rules.id"), nullable=True)
    due_date = Column(DateTime(timezone=True), nullable=False)
    is_overdue = Column(Boolean, default=False)
    is_extended = Column(Boolean, default=False)
    extension_reason = Column(Text, nullable=True)
    extended_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    extended_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
