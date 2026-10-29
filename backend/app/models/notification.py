"""Notification model."""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.db.session import Base


class NotificationPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    notification_type = Column(String(100), nullable=True)  # overdue, new_relationship, transfer, etc.
    priority = Column(SAEnum(NotificationPriority), default=NotificationPriority.MEDIUM)
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime(timezone=True), nullable=True)
    link_url = Column(String(500), nullable=True)
    related_case_id = Column(Integer, ForeignKey("cases.id"), nullable=True)
    related_coordination_id = Column(Integer, ForeignKey("coordination_items.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="notifications")
