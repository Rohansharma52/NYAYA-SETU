"""Import job models."""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Enum as SAEnum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.db.session import Base


class ImportStatus(str, enum.Enum):
    PENDING = "pending"
    VALIDATING = "validating"
    PREVIEW = "preview"
    IMPORTING = "importing"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class ImportJob(Base):
    __tablename__ = "import_jobs"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(500), nullable=False)
    import_type = Column(String(100), nullable=False)  # institutions, cases
    status = Column(SAEnum(ImportStatus), default=ImportStatus.PENDING)
    total_rows = Column(Integer, default=0)
    valid_rows = Column(Integer, default=0)
    error_rows = Column(Integer, default=0)
    skipped_rows = Column(Integer, default=0)
    imported_rows = Column(Integer, default=0)
    error_summary = Column(JSON, nullable=True)
    notes = Column(Text, nullable=True)
    imported_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    rows = relationship("ImportRow", back_populates="job", cascade="all, delete-orphan")
    imported_by = relationship("User")


class ImportRow(Base):
    __tablename__ = "import_rows"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("import_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    row_number = Column(Integer, nullable=False)
    raw_data = Column(JSON, nullable=True)
    status = Column(String(50), nullable=False, default="pending")  # valid, error, skipped, imported
    errors = Column(JSON, nullable=True)
    warnings = Column(JSON, nullable=True)
    created_resource_id = Column(Integer, nullable=True)

    job = relationship("ImportJob", back_populates="rows")
