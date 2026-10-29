from app.db.session import Base  # noqa — import all models so Alembic can see them
from app.models.user import User  # noqa
from app.models.bureau import Bureau  # noqa
from app.models.institution import Institution, InstitutionIdentifier  # noqa
from app.models.case import Case, CaseAction, CaseAssignment  # noqa
from app.models.relationship import CaseRelationship, RelationshipReview  # noqa
from app.models.coordination import CoordinationItem, CoordinationParticipant, CoordinationTask  # noqa
from app.models.notification import Notification  # noqa
from app.models.audit import AuditEvent  # noqa
from app.models.import_job import ImportJob, ImportRow  # noqa
from app.models.transfer import TransferRequest  # noqa
from app.models.deadline import DeadlineRule, CaseDeadline  # noqa
from app.models.deadline_extension import DeadlineExtensionRequest  # noqa
from app.models.attachment import CaseAttachment  # noqa
