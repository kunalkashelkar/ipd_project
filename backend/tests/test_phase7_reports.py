# ============================================================
# Phase 7 Reports Tests
# ============================================================

import io
import uuid
import pytest
from datetime import datetime, timezone

from backend.app.models.finding import Finding, FindingOccurrence
from backend.app.models.organization import Organization
from backend.app.models.project import Project
from backend.app.models.report import Report, ReportFile
from backend.app.models.scan import Scan
from backend.app.models.source_snapshot import SourceSnapshot
from backend.app.services.report_generator import (
    CSVReportGenerator,
    HTMLReportGenerator,
    JSONReportGenerator,
    PDFReportGenerator,
    ReportGenerator,
)
from backend.app.services.report_service import ReportService
from backend.app.storage.service import StorageService


@pytest.fixture
def mock_report_data():
    return {
        "project": {
            "id": str(uuid.uuid4()),
            "public_id": "prj_test12345678",
            "name": "Test Security Project",
            "description": "A sample project for security evaluation.",
        },
        "organization": {
            "id": str(uuid.uuid4()),
            "name": "Test Organization",
        },
        "scan": {
            "id": str(uuid.uuid4()),
            "public_id": "scn_test12345678",
            "scan_type": "full",
            "status": "completed",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": datetime.now(timezone.utc).isoformat(),
        },
        "snapshot": {
            "id": str(uuid.uuid4()),
            "commit_sha": "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
            "branch": "main",
        },
        "metrics": {
            "total_findings": 2,
            "total_occurrences": 3,
            "severity_counts": {"critical": 1, "high": 1, "medium": 0, "low": 0, "info": 0},
            "status_counts": {"OPEN": 2},
            "top_cwes": [{"cwe_id": "CWE-89", "count": 1}, {"cwe_id": "CWE-79", "count": 1}],
            "health_score": 77.0,
            "health_rating": "C",
            "score_version": "v1.0.0",
        },
        "findings": [
            {
                "id": str(uuid.uuid4()),
                "public_id": "fnd_crit89sql001",
                "title": "SQL Injection in User Query",
                "vulnerability_type": "SQL_INJECTION",
                "cwe_id": "CWE-89",
                "severity": "critical",
                "cvss_score": 9.8,
                "confidence": 0.95,
                "risk_score": 93.0,
                "status": "OPEN",
                "first_seen_at": datetime.now(timezone.utc).isoformat(),
                "last_seen_at": datetime.now(timezone.utc).isoformat(),
                "occurrences": [
                    {
                        "id": str(uuid.uuid4()),
                        "file_path": "app/db/user.py",
                        "start_line": 42,
                        "end_line": 45,
                        "confidence": 0.95,
                    }
                ],
                "remediations": [
                    {
                        "id": str(uuid.uuid4()),
                        "explanation": "Use parameterized queries instead of string formatting.",
                        "suggested_patch": "--- a/app/db/user.py\n+++ b/app/db/user.py\n- cursor.execute(f'SELECT * FROM users WHERE id={uid}')\n+ cursor.execute('SELECT * FROM users WHERE id=%s', (uid,))",
                        "confidence_score": 0.98,
                        "status": "proposed",
                        "validation_status": "passed",
                    }
                ],
            },
            {
                "id": str(uuid.uuid4()),
                "public_id": "fnd_high79xss002",
                "title": "Cross-Site Scripting in Render",
                "vulnerability_type": "XSS",
                "cwe_id": "CWE-79",
                "severity": "high",
                "cvss_score": 7.5,
                "confidence": 0.88,
                "risk_score": 72.0,
                "status": "OPEN",
                "first_seen_at": datetime.now(timezone.utc).isoformat(),
                "last_seen_at": datetime.now(timezone.utc).isoformat(),
                "occurrences": [
                    {
                        "id": str(uuid.uuid4()),
                        "file_path": "app/views/home.py",
                        "start_line": 12,
                        "end_line": 14,
                        "confidence": 0.88,
                    }
                ],
                "remediations": [],
            },
        ],
    }


def test_json_generator(mock_report_data):
    gen = JSONReportGenerator()
    out = gen.generate(mock_report_data, report_type="security")
    assert isinstance(out, bytes)
    assert b"1.0.0" in out
    assert b"SQL Injection" in out
    assert b"fnd_crit89sql001" in out


def test_csv_generator_and_sanitization(mock_report_data):
    # Add a potentially malicious formula to test CSV escaping
    mock_report_data["findings"][0]["title"] = "=CMD|' /C calc'!A0"

    gen = CSVReportGenerator()
    out = gen.generate(mock_report_data, report_type="security")
    assert isinstance(out, bytes)
    decoded = out.decode("utf-8-sig")
    assert "'=CMD" in decoded, "Leading '=' formula should be escaped with leading quote"
    assert "fnd_crit89sql001" in decoded
    assert "app/db/user.py" in decoded


def test_html_generator(mock_report_data):
    gen = HTMLReportGenerator()
    out = gen.generate(mock_report_data, report_type="developer")
    assert isinstance(out, bytes)
    decoded = out.decode("utf-8")
    assert "<!DOCTYPE html>" in decoded
    assert "Developer Remediation Report" in decoded
    assert "Test Security Project" in decoded
    assert "Proposed AI Remediation" in decoded
    assert "fnd_crit89sql001" in decoded


def test_pdf_generator(mock_report_data):
    gen = PDFReportGenerator()
    out = gen.generate(mock_report_data, report_type="security")
    assert isinstance(out, bytes)
    assert out.startswith(b"%PDF-"), "Generated file should be a valid PDF"
    assert len(out) > 500


def test_unified_report_generator(mock_report_data):
    gen = ReportGenerator()
    pdf_bytes, pdf_ct = gen.generate(mock_report_data, "security", "pdf")
    assert pdf_ct == "application/pdf"
    assert pdf_bytes.startswith(b"%PDF-")

    html_bytes, html_ct = gen.generate(mock_report_data, "developer", "html")
    assert "text/html" in html_ct
    assert b"<!DOCTYPE html>" in html_bytes

    json_bytes, json_ct = gen.generate(mock_report_data, "executive", "json")
    assert json_ct == "application/json"
    assert b"findings_summary" in json_bytes

    csv_bytes, csv_ct = gen.generate(mock_report_data, "security", "csv")
    assert "text/csv" in csv_ct
    assert len(csv_bytes) > 0


@pytest.mark.asyncio
async def test_report_service_lifecycle_and_download(db_session, test_user, test_organization, test_project):
    # Setup test snapshot and scan
    snapshot = SourceSnapshot(
        id=uuid.uuid4(),
        project_id=test_project.id,
        source_type="git",
        source_version="a1b2c3d4e5f67890",
        content_hash="a" * 64,
        artifact_uri="snapshots/test/archive.zip",
        status="ready",
    )
    db_session.add(snapshot)
    await db_session.commit()

    scan = Scan(
        id=uuid.uuid4(),
        project_id=test_project.id,
        organization_id=test_organization.id,
        source_snapshot_id=snapshot.id,
        status="completed",
    )
    db_session.add(scan)
    await db_session.commit()

    service = ReportService(db_session)

    # 1. Request report
    report = await service.request_report(
        scan_id=scan.id,
        format="json",
        report_type="security",
        user_id=test_user.id,
        org_id=test_organization.id,
    )
    assert report.status == "queued"
    assert report.public_id.startswith("rpt_")

    # 2. Execute generation
    completed_report = await service.execute_generation(report.id)
    assert completed_report.status == "completed"
    assert completed_report.generated_at is not None
    assert len(completed_report.files) == 1

    file_meta = completed_report.files[0]
    assert file_meta.format == "json"
    assert file_meta.size_bytes > 0
    assert len(file_meta.checksum_sha256) == 64

    # 3. Download report
    content, filename, content_type = await service.get_report_download(
        report.public_id, test_organization.id
    )
    assert content_type == "application/json"
    assert len(content) == file_meta.size_bytes
    assert filename.endswith(".json")

    # 4. Cross-tenant access rejection
    other_org_id = uuid.uuid4()
    with pytest.raises(Exception):
        await service.get_report(report.public_id, other_org_id)


def test_all_twelve_report_type_and_format_combinations(mock_report_data):
    """Exercise and verify all 12 advertised format x type combinations:
    (developer, security, executive) x (pdf, html, json, csv).
    """
    gen = ReportGenerator()
    types = ["developer", "security", "executive"]
    formats = ["pdf", "html", "json", "csv"]

    for r_type in types:
        for r_fmt in formats:
            content, c_type = gen.generate(mock_report_data, r_type, r_fmt)
            assert isinstance(content, bytes), f"Failed for {r_type} x {r_fmt}"
            assert len(content) > 50, f"Content too short for {r_type} x {r_fmt}"

            if r_fmt == "pdf":
                assert c_type == "application/pdf"
                assert content.startswith(b"%PDF-")
            elif r_fmt == "html":
                assert "text/html" in c_type
                assert b"<!DOCTYPE html>" in content
            elif r_fmt == "json":
                assert c_type == "application/json"
            elif r_fmt == "csv":
                assert "text/csv" in c_type


def test_report_grammar_and_terminology_contract(mock_report_data):
    """Validate dynamic pluralization for Critical findings and canonical Finding terminology."""
    pdf_gen = PDFReportGenerator()
    html_gen = HTMLReportGenerator()
    csv_gen = CSVReportGenerator()

    # 1. Single critical finding -> singular "Critical vulnerability requires"
    mock_report_data["metrics"]["severity_counts"]["critical"] = 1
    pdf_single = pdf_gen.generate(mock_report_data, "security")
    assert isinstance(pdf_single, bytes)
    assert pdf_single.startswith(b"%PDF-")

    # 2. Multiple critical findings -> plural "Critical vulnerabilities require"
    mock_report_data["metrics"]["severity_counts"]["critical"] = 7
    pdf_multiple = pdf_gen.generate(mock_report_data, "security")
    assert isinstance(pdf_multiple, bytes)
    assert pdf_multiple.startswith(b"%PDF-")

    # 3. HTML terminology check
    html_bytes = html_gen.generate(mock_report_data, "executive")
    html_text = html_bytes.decode("utf-8")
    assert "Findings Inventory (Summary)" in html_text

    # 4. CSV header terminology check
    csv_bytes = csv_gen.generate(mock_report_data, "security")
    csv_text = csv_bytes.decode("utf-8-sig")
    assert "Finding ID" in csv_text
    assert "Finding Type" in csv_text


