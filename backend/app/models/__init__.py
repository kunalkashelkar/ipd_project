# ============================================================
# Models Package — Re-export all SQLAlchemy models
# ============================================================

from backend.app.models.analysis_artifact import AnalysisArtifact
from backend.app.models.api_key import ApiKey
from backend.app.models.audit_log import AuditLog
from backend.app.models.feedback import Feedback
from backend.app.models.git_meta import RepositoryBranch, RepositoryCommit
from backend.app.models.notification import Notification
from backend.app.models.organization import (
    Organization,
    OrganizationInvitation,
    OrganizationMember,
)
from backend.app.models.project import Project
from backend.app.models.rbac import Permission, Role, RolePermission
from backend.app.models.report import Report
from backend.app.models.repository import Repository
from backend.app.models.scan import Scan, ScanEvent, ScanStageRun
from backend.app.models.scan_log import ScanLog
from backend.app.models.scan_result import ScanResult
from backend.app.models.session import UserSession, VerificationToken
from backend.app.models.source_snapshot import Function, SourceFile, SourceSnapshot
from backend.app.models.ai_prediction import AIPrediction
from backend.app.models.finding import (
    Finding,
    FindingAssignment,
    FindingComment,
    FindingOccurrence,
    FindingStatusHistory,
    FindingSuppression,
)
from backend.app.models.upload import Upload
from backend.app.models.user import User
from backend.app.models.vulnerability import Vulnerability
from backend.app.models.model_registry import ModelVersion
from backend.app.models.explanation import AIExplanation
from backend.app.models.remediation import Remediation, RemediationValidation

__all__ = [
    "AIExplanation",
    "AIPrediction",
    "AnalysisArtifact",
    "ApiKey",
    "AuditLog",
    "Feedback",
    "Finding",
    "FindingAssignment",
    "FindingComment",
    "FindingOccurrence",
    "FindingStatusHistory",
    "FindingSuppression",
    "Function",
    "ModelVersion",
    "Notification",
    "Organization",
    "OrganizationInvitation",
    "OrganizationMember",
    "Permission",
    "Project",
    "Remediation",
    "RemediationValidation",
    "Report",
    "Repository",
    "RepositoryBranch",
    "RepositoryCommit",
    "Role",
    "RolePermission",
    "Scan",
    "ScanEvent",
    "ScanLog",
    "ScanResult",
    "ScanStageRun",
    "SourceFile",
    "SourceSnapshot",
    "Upload",
    "User",
    "UserSession",
    "VerificationToken",
    "Vulnerability",
]
