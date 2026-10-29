"""Case relationship models for AI-assisted matching."""
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, Enum as SAEnum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.db.session import Base


class RelationshipType(str, enum.Enum):
    POSSIBLE_DUPLICATE = "possible_duplicate"
    RELATED_COMPLAINT = "related_complaint"
    SAME_INSTITUTION_UNRELATED = "same_institution_unrelated"
    ACTION_CONFLICT = "action_conflict"


class ReviewStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    CORRECTED = "corrected"
    ESCALATED = "escalated"


class CaseRelationship(Base):
    __tablename__ = "case_relationships"

    id = Column(Integer, primary_key=True, index=True)
    case_a_id = Column(Integer, ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    case_b_id = Column(Integer, ForeignKey("cases.id"), nullable=False, index=True)

    relationship_type = Column(SAEnum(RelationshipType), nullable=False)
    score = Column(Float, nullable=True)
    reasons = Column(JSON, nullable=True)
    matching_evidence = Column(JSON, nullable=True)
    algorithm_version = Column(String(50), default="v1.0")

    review_status = Column(SAEnum(ReviewStatus), default=ReviewStatus.PENDING, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    case_a = relationship("Case", foreign_keys=[case_a_id], back_populates="relationships_as_case_a")
    case_b = relationship("Case", foreign_keys=[case_b_id], back_populates="relationships_as_case_b")
    reviews = relationship("RelationshipReview", back_populates="source_relationship", cascade="all, delete-orphan")


class RelationshipReview(Base):
    __tablename__ = "relationship_reviews"

    id = Column(Integer, primary_key=True, index=True)
    relationship_id = Column(Integer, ForeignKey("case_relationships.id", ondelete="CASCADE"), nullable=False, index=True)
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    decision = Column(SAEnum(ReviewStatus), nullable=False)
    corrected_type = Column(SAEnum(RelationshipType), nullable=True)
    rationale = Column(Text, nullable=True)
    reviewed_at = Column(DateTime(timezone=True), server_default=func.now())

    source_relationship = relationship("CaseRelationship", back_populates="reviews")
    reviewer = relationship("User")
