"""Supporting documents attached to a case / action (PS 26264 §5: remarks and supporting documents)."""
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base


class CaseAttachment(Base):
    __tablename__ = "case_attachments"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    action_id = Column(Integer, ForeignKey("case_actions.id", ondelete="SET NULL"), nullable=True)
    filename = Column(String(255), nullable=False)
    content_type = Column(String(120), nullable=True)
    size_bytes = Column(Integer, nullable=False, default=0)
    sha256 = Column(String(64), nullable=False)
    storage_path = Column(String(500), nullable=False)
    remarks = Column(Text, nullable=True)
    uploaded_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    uploaded_by = relationship("User")
