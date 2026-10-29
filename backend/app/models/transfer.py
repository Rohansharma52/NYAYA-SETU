"""Transfer request model."""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.db.session import Base


class TransferStatus(str, enum.Enum):
    REQUESTED = "requested"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class TransferRequest(Base):
    __tablename__ = "transfer_requests"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False, index=True)
    from_bureau_id = Column(Integer, ForeignKey("bureaus.id"), nullable=True)
    to_bureau_id = Column(Integer, ForeignKey("bureaus.id"), nullable=True)
    from_officer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    to_officer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reason = Column(Text, nullable=False)
    status = Column(SAEnum(TransferStatus), default=TransferStatus.REQUESTED)
    response_notes = Column(Text, nullable=True)
    requested_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    responded_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    requested_at = Column(DateTime(timezone=True), server_default=func.now())
    responded_at = Column(DateTime(timezone=True), nullable=True)

    case = relationship("Case", back_populates="transfer_requests", foreign_keys=[case_id])
    from_bureau = relationship("Bureau", foreign_keys=[from_bureau_id])
    to_bureau = relationship("Bureau", foreign_keys=[to_bureau_id])
    requested_by = relationship("User", foreign_keys=[requested_by_id])
    responded_by = relationship("User", foreign_keys=[responded_by_id])
