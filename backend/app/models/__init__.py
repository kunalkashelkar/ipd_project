# ============================================================
# Models Package — import all models so SQLAlchemy registers them
# ============================================================

from backend.app.models.user import User
from backend.app.models.project import Project
from backend.app.models.repository import Repository
from backend.app.models.upload import Upload
from backend.app.models.scan import Scan
from backend.app.models.scan_log import ScanLog
from backend.app.models.scan_result import ScanResult
from backend.app.models.vulnerability import Vulnerability
from backend.app.models.report import Report
from backend.app.models.notification import Notification
from backend.app.models.feedback import Feedback
from backend.app.models.audit_log import AuditLog

__all__ = [
    "User",
    "Project",
    "Repository",
    "Upload",
    "Scan",
    "ScanLog",
    "ScanResult",
    "Vulnerability",
    "Report",
    "Notification",
    "Feedback",
    "AuditLog",
]
