# ============================================================
# Phase 3 Automated Test Suite — Source Ingestion & Preprocessing
# ============================================================

import io
import json
import zipfile
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.security import create_token_pair, hash_password
from backend.app.models.organization import Organization, OrganizationMember
from backend.app.models.project import Project
from backend.app.models.rbac import Role
from backend.app.models.source_snapshot import Function, SourceFile, SourceSnapshot
from backend.app.models.user import User
from backend.app.services.code_parser.duplicate_detector import detect_duplicate_functions
from backend.app.services.code_parser.extractor import extract_functions
from backend.app.services.code_parser.language_detector import detect_language
from backend.app.services.code_parser.normalizer import normalize_identifiers
from backend.app.services.code_parser.source_validator import validate_archive_entry, validate_source_file
from backend.app.services.code_parser.tokenizer import tokenize_source


# ── Helper to Create User with Specific Role in Org ───────────
async def create_org_member_user(
    db: AsyncSession, org: Organization, email: str, role_name: str
) -> tuple[User, dict[str, str]]:
    user = User(
        name=f"User {role_name}",
        email=email,
        password_hash=hash_password("password123"),
        role=role_name,
        status="active",
        is_verified=True,
    )
    db.add(user)
    await db.flush()

    role_res = await db.execute(select(Role).where(Role.name == role_name))
    role = role_res.scalar_one()

    member = OrganizationMember(
        organization_id=org.id,
        user_id=user.id,
        role_id=role.id,
        status="active",
    )
    db.add(member)
    await db.commit()

    tokens = create_token_pair(str(user.id), user.email)
    headers = {
        "Authorization": f"Bearer {tokens['access_token']}",
        "X-Organization-ID": str(org.id),
    }
    return user, headers


# ── Helper to Create In-Memory ZIP Archive ─────────────────────
def create_test_zip(files: dict[str, str]) -> io.BytesIO:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for path, content in files.items():
            zf.writestr(path, content.encode("utf-8"))
    buf.seek(0)
    return buf


# ==============================================================
# 1. PREPROCESSING & PARSING UNIT TESTS
# ==============================================================

def test_language_detection():
    assert detect_language("app/main.py", b"import os") == "python"
    assert detect_language("src/vuln.c", b"#include <stdio.h>") == "c"
    assert detect_language("include/header.h", b"class Node {};") == "cpp"
    assert detect_language("Server.java", b"public class Server {}") == "java"
    assert detect_language("index.js", b"function calculate() {}") == "javascript"
    assert detect_language("App.tsx", b"export const App = () => {}") == "typescript"
    assert detect_language("main.go", b"package main") == "go"
    assert detect_language("lib.rs", b"pub fn run() {}") == "rust"
    assert detect_language("README.md", b"# Title") is None


def test_tokenization_deterministic():
    code = "def calculate_tax(amount, rate):\n    return amount * rate\n"
    res1 = tokenize_source(code, "python")
    res2 = tokenize_source(code, "python")
    assert res1.token_count == res2.token_count
    assert [t["value"] for t in res1.tokens] == [t["value"] for t in res2.tokens]
    assert any(t["type"] == "KEYWORD" and t["value"] == "def" for t in res1.tokens)


def test_identifier_normalization_preserves_semantics():
    code = "def calculateUserBalance(user_id, balance):\n    current_balance = balance + 10\n    return current_balance\n"
    normalized, norm_hash = normalize_identifiers(code, "python", remove_comments=True)
    assert "calculateUserBalance" not in normalized or "VAR_" in normalized
    assert "def " in normalized
    assert "return " in normalized
    assert norm_hash is not None


def test_comment_removal_optional():
    code = "# This is a secret comment\ndef hello():\n    # Inner comment\n    return 42\n"
    norm_no_comm, _ = normalize_identifiers(code, "python", remove_comments=True)
    assert "secret comment" not in norm_no_comm
    assert "Inner comment" not in norm_no_comm

    norm_with_comm, _ = normalize_identifiers(code, "python", remove_comments=False)
    assert "secret comment" in norm_with_comm


def test_python_ast_function_extraction():
    code = """
class Calculator:
    def add(self, a, b):
        return a + b

    def subtract(self, a, b):
        return a - b

def standalone(x):
    return x * 2
"""
    funcs = extract_functions(code, "python", "snap-123", "calc.py")
    assert len(funcs) == 3
    names = [f["name"] for f in funcs]
    assert "add" in names
    assert "subtract" in names
    assert "standalone" in names
    # Deterministic function_id checks
    for f in funcs:
        assert f["function_id"] is not None
        assert len(f["function_id"]) == 32
        assert f["start_line"] > 0
        assert f["end_line"] >= f["start_line"]


def test_c_style_function_extraction():
    c_code = """
#include <stdio.h>

int calculate_sum(int a, int b) {
    int sum = a + b;
    return sum;
}

void process_data(char *data) {
    printf("%s\\n", data);
}
"""
    funcs = extract_functions(c_code, "c", "snap-c-test", "main.c")
    assert len(funcs) == 2
    assert funcs[0]["name"] == "calculate_sum"
    assert funcs[1]["name"] == "process_data"
    assert funcs[0]["language"] == "c"


def test_duplicate_function_detection():
    code1 = "def auth(u, p):\n    return u == 'admin' and p == 'pass'\n"
    code2 = "def check_creds(user, pwd):\n    return user == 'admin' and pwd == 'pass'\n"

    funcs1 = extract_functions(code1, "python", "snap-dup", "a.py")
    funcs2 = extract_functions(code2, "python", "snap-dup", "b.py")

    all_funcs = funcs1 + funcs2
    dup_map = detect_duplicate_functions(all_funcs)
    # Since identifiers are normalized to VAR_1, VAR_2, both bodies have identical normalized hashes
    assert all_funcs[0]["function_id"] in dup_map
    assert all_funcs[1]["function_id"] in dup_map
    assert dup_map[all_funcs[0]["function_id"]] == dup_map[all_funcs[1]["function_id"]]


# ==============================================================
# 2. SOURCE SECURITY & VALIDATION TESTS
# ==============================================================

def test_zip_slip_rejection():
    res, is_safe, reason = validate_archive_entry("../../etc/passwd")
    assert not is_safe
    assert "traversal" in reason.lower()

    res2, is_safe2, _ = validate_archive_entry("/etc/shadow")
    assert not is_safe2

    res3, is_safe3, _ = validate_archive_entry("C:\\Windows\\System32\\cmd.exe")
    assert not is_safe3

    res4, is_safe4, _ = validate_archive_entry("src/app/main.py")
    assert is_safe4
    assert res4 == "src/app/main.py"


def test_binary_file_detection():
    binary_bytes = b"\x7fELF\x02\x01\x01\x00" + b"\x00" * 20
    is_valid, classification, is_bin = validate_source_file("bin/app", binary_bytes)
    assert is_bin
    assert classification == "binary"

    text_bytes = b"def run():\n    pass\n"
    is_valid2, class2, is_bin2 = validate_source_file("app.py", text_bytes)
    assert not is_bin2
    assert class2 == "source"


# ==============================================================
# 3. END-TO-END SNAPSHOT & REPOSITORY API TESTS
# ==============================================================

@pytest_asyncio.fixture
async def sample_project(db_session: AsyncSession, test_user: User) -> Project:
    stmt = (
        select(Organization)
        .join(OrganizationMember, OrganizationMember.organization_id == Organization.id)
        .where(OrganizationMember.user_id == test_user.id)
    )
    res = await db_session.execute(stmt)
    org = res.scalar_one()

    project = Project(
        organization_id=org.id,
        name="Security Core",
        description="Core security scanning target",
        language="python",
        default_branch="main",
        owner_id=test_user.id,
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


@pytest.mark.asyncio
async def test_zip_snapshot_upload_and_read(
    client: AsyncClient,
    auth_headers: dict[str, str],
    sample_project: Project,
    db_session: AsyncSession,
):
    zip_bytes = create_test_zip({
        "main.py": "def root():\n    return 'OK'\n",
        "utils/helpers.py": "def format_name(n):\n    return n.strip().lower()\n",
    })

    files = {"file": ("repo.zip", zip_bytes.getvalue(), "application/zip")}
    res = await client.post(
        f"/api/v1/projects/{sample_project.id}/snapshots/upload",
        headers=auth_headers,
        files=files,
    )
    assert res.status_code == 201
    data = res.json()["data"]
    snapshot_id = data["id"]
    assert data["source_type"] == "upload"
    assert data["status"] == "pending"
    assert data["file_count"] == 0

    # Verify snapshot can be listed
    list_res = await client.get(
        f"/api/v1/projects/{sample_project.id}/snapshots",
        headers=auth_headers,
    )
    assert list_res.status_code == 200
    items = list_res.json()["data"]["items"]
    assert any(s["id"] == snapshot_id for s in items)

    # Verify detail
    detail_res = await client.get(
        f"/api/v1/projects/{sample_project.id}/snapshots/{snapshot_id}",
        headers=auth_headers,
    )
    assert detail_res.status_code == 200
    assert detail_res.json()["data"]["id"] == snapshot_id


@pytest.mark.asyncio
async def test_individual_files_upload(
    client: AsyncClient,
    auth_headers: dict[str, str],
    sample_project: Project,
):
    files = [
        ("files", ("main.py", b"def index(): pass\n", "text/x-python")),
        ("files", ("config.py", b"DEBUG = True\n", "text/x-python")),
    ]
    res = await client.post(
        f"/api/v1/projects/{sample_project.id}/snapshots/files",
        headers=auth_headers,
        files=files,
    )
    assert res.status_code == 201
    data = res.json()["data"]
    assert data["source_type"] == "upload"
    assert data["status"] == "pending"


@pytest.mark.asyncio
async def test_repository_connect_and_branch_select(
    client: AsyncClient,
    auth_headers: dict[str, str],
    sample_project: Project,
):
    from unittest.mock import patch

    payload = {
        "provider": "local_git",
        "repo_url": "https://github.com/example/sec-lib.git",
        "display_name": "Security Library",
        "default_branch": "main",
    }
    with patch("backend.app.services.vcs.git_provider.GitProvider.validate_connection", return_value=True):
        res = await client.post(
            f"/api/v1/projects/{sample_project.id}/repositories",
            headers=auth_headers,
            json=payload,
        )
        assert res.status_code == 201
        repo = res.json()["data"]
        repo_id = repo["id"]
        assert repo["provider"] == "git"
        assert repo["selected_branch"] == "main"
        assert repo["status"] == "connected"

    # Duplicate connection prevention to same project & URL
    dup_res = await client.post(
        f"/api/v1/projects/{sample_project.id}/repositories",
        headers=auth_headers,
        json=payload,
    )
    assert dup_res.status_code == 409

    # Select branch
    branch_res = await client.post(
        f"/api/v1/repositories/{repo_id}/branches/select",
        headers=auth_headers,
        json={"branch_name": "develop"},
    )
    assert branch_res.status_code == 200
    assert branch_res.json()["data"]["selected_branch"] == "develop"

    # Sync
    sync_res = await client.post(
        f"/api/v1/projects/{sample_project.id}/repositories/{repo_id}/sync",
        headers=auth_headers,
    )
    assert sync_res.status_code == 202

    # Disconnect
    disc_res = await client.post(
        f"/api/v1/projects/{sample_project.id}/repositories/{repo_id}/disconnect",
        headers=auth_headers,
    )
    assert disc_res.status_code == 200
    assert disc_res.json()["data"]["status"] == "disconnected"


@pytest.mark.asyncio
async def test_tenant_isolation_idor_prevention(
    client: AsyncClient,
    auth_headers: dict[str, str],
    sample_project: Project,
    db_session: AsyncSession,
):
    # Create Organization B and User B
    org_b = Organization(name="Competitor Org", slug="competitor-org")
    db_session.add(org_b)
    await db_session.commit()

    user_b, headers_b = await create_org_member_user(
        db_session, org_b, "competitor@example.com", "owner"
    )

    # 1. User B cannot list or get Organization A's project
    res1 = await client.get(f"/api/v1/projects/{sample_project.id}", headers=headers_b)
    assert res1.status_code in (403, 404)

    # 2. User B cannot upload to Organization A's project
    zip_bytes = create_test_zip({"hack.py": "print('malicious')"})
    res2 = await client.post(
        f"/api/v1/projects/{sample_project.id}/snapshots/upload",
        headers=headers_b,
        files={"file": ("hack.zip", zip_bytes.getvalue(), "application/zip")},
    )
    assert res2.status_code in (403, 404)

    # 3. User B cannot list Organization A's snapshots
    res3 = await client.get(
        f"/api/v1/projects/{sample_project.id}/snapshots",
        headers=headers_b,
    )
    assert res3.status_code in (403, 404)


@pytest.mark.asyncio
async def test_scan_requires_ready_snapshot(
    client: AsyncClient,
    auth_headers: dict[str, str],
    sample_project: Project,
    db_session: AsyncSession,
):
    # Create a pending snapshot directly in db
    pending_snap = SourceSnapshot(
        project_id=sample_project.id,
        source_type="upload",
        status="pending",
        content_hash="abc" * 21 + "a",
        artifact_uri="s3://test/snap.zip",
        preprocessing_version="v1.0.0",
        created_by=sample_project.owner_id,
    )
    db_session.add(pending_snap)
    await db_session.commit()

    # Attempting to scan a pending snapshot must be rejected (400 Bad Request)
    scan_res = await client.post(
        "/api/v1/scans",
        headers=auth_headers,
        json={
            "project_id": str(sample_project.id),
            "source_snapshot_id": str(pending_snap.id),
        },
    )
    assert scan_res.status_code in (400, 422)
    assert "ready" in scan_res.json()["message"].lower() or "ready" in str(scan_res.json()).lower()

    # Mark snapshot READY
    pending_snap.status = "ready"
    await db_session.commit()

    # Now scan creation must succeed
    scan_res2 = await client.post(
        "/api/v1/scans",
        headers=auth_headers,
        json={
            "project_id": str(sample_project.id),
            "source_snapshot_id": str(pending_snap.id),
        },
    )
    assert scan_res2.status_code in (200, 201)
    scan_data = scan_res2.json()["data"]
    assert scan_data["source_snapshot_id"] == str(pending_snap.id)


@pytest.mark.asyncio
async def test_project_archive_unarchive(
    client: AsyncClient,
    auth_headers: dict[str, str],
    sample_project: Project,
):
    # Archive
    res = await client.post(
        f"/api/v1/projects/{sample_project.id}/archive",
        headers=auth_headers,
    )
    assert res.status_code == 200
    assert res.json()["data"]["is_archived"] is True

    # Unarchive
    res2 = await client.post(
        f"/api/v1/projects/{sample_project.id}/archive",
        headers=auth_headers,
    )
    assert res2.status_code == 200
    assert res2.json()["data"]["is_archived"] is False


# ==============================================================
# 5. PHASE 3 REPAIR FOCUSED TESTS
# ==============================================================

def test_python_function_extraction_syntax_error_fallback():
    """Verify that Python 2 syntax (e.g. print statement) does not fail extraction."""
    code = """#!/usr/bin/python
import sys

if len(sys.argv) != 3:
    print "Usage: %s <LHOST> <LPORT>" % (sys.argv[0])
    sys.exit(0)

def charencode(string):
    '''String.CharCode'''
    encoded = ''
    for char in string:
        encoded = encoded + "," + str(ord(char))
    return encoded[1:]

def helper():
    return 42
"""
    funcs = extract_functions(code, "python", "snap_test", "nodejsshell.py")
    assert len(funcs) == 2
    names = [f["name"] for f in funcs]
    assert "charencode" in names
    assert "helper" in names
    charencode_fn = next(f for f in funcs if f["name"] == "charencode")
    assert charencode_fn["start_line"] == 8
    assert charencode_fn["language"] == "python"
    assert "def charencode(string):" in charencode_fn["signature"]


def test_javascript_function_extraction_allman_and_callbacks():
    """Verify JS extractor finds Allman brace functions, callbacks, and arrow functions."""
    code = """var http = require("http");
var app = require("express")();

// Allman style brace on next line
http.createServer(function(request, response)
{
  response.end("OK");
}).listen(8888);

// Express callback
app.get('/api', function(req, res) {
  res.send('ok');
});

// Arrow function
const handlePing = (host) => {
  return host;
};

// Standard function
function regularFunc(x, y) {
  return x + y;
}
"""
    funcs = extract_functions(code, "javascript", "snap_test", "server.js")
    assert len(funcs) == 4
    names = [f["name"] for f in funcs]
    assert "regularFunc" in names
    assert "handlePing" in names
    # Verify anonymous callback was extracted
    assert any("callback" in n or "anonymous" in n for n in names)
    for fn in funcs:
        assert fn["start_line"] > 0
        assert fn["end_line"] >= fn["start_line"]
        assert fn["language"] == "javascript"
        assert len(fn["function_id"]) == 32


def test_github_url_normalization():
    """Verify GitHub coordinates normalization across various formats."""
    from backend.app.services.vcs.github_provider import GitHubProvider
    p = GitHubProvider()

    assert p._normalize_repo_coords("https://github.com/ajinabraham/Node.Js-Security-Course") == ("ajinabraham", "Node.Js-Security-Course")
    assert p._normalize_repo_coords("https://github.com/ajinabraham/Node.Js-Security-Course.git") == ("ajinabraham", "Node.Js-Security-Course")
    assert p._normalize_repo_coords("ajinabraham/Node.Js-Security-Course") == ("ajinabraham", "Node.Js-Security-Course")
    assert p._normalize_repo_coords("git@github.com:ajinabraham/Node.Js-Security-Course.git") == ("ajinabraham", "Node.Js-Security-Course")
    assert p._normalize_repo_coords("git@github.com:ajinabraham/Node.Js-Security-Course") == ("ajinabraham", "Node.Js-Security-Course")

    with pytest.raises(ValueError, match="Invalid GitHub repository identifier"):
        p._normalize_repo_coords("just-a-string")


@pytest.mark.asyncio
async def test_multi_tenant_project_access_for_org_member(
    db_session: AsyncSession,
    sample_project: Project,
):
    """Verify that an active organization member (non-owner) has access via require_project_access."""
    from backend.app.core.permissions import require_project_access
    from backend.app.core.exceptions import AuthorizationError

    org = (await db_session.execute(select(Organization).where(Organization.id == sample_project.organization_id))).scalar_one()

    # Create developer user in sample_organization
    member_user, _ = await create_org_member_user(
        db_session, org, "developer@example.com", "developer"
    )

    # Member should succeed even though member_user.id != sample_project.owner_id
    accessed_user = await require_project_access(sample_project.id, member_user, db_session)
    assert accessed_user.id == member_user.id

    # Create outside user in a different org
    outside_user = User(
        name="Outside User",
        email="outside@example.com",
        password_hash=hash_password("password123"),
        role="user",
        status="active",
        is_verified=True,
    )
    db_session.add(outside_user)
    await db_session.commit()

    # Outside user should be rejected with AuthorizationError
    with pytest.raises(AuthorizationError, match="You do not have access to this project"):
        await require_project_access(sample_project.id, outside_user, db_session)


@pytest.mark.asyncio
async def test_repository_model_direct_insert_without_repo_url(
    db_session: AsyncSession,
    sample_project: Project,
):
    """Verify that Repository model can be inserted using only canonical repository_url without legacy repo_url."""
    from backend.app.models.repository import Repository
    import uuid

    repo = Repository(
        id=uuid.uuid4(),
        project_id=sample_project.id,
        provider="github",
        repository_url="https://github.com/ajinabraham/Node.Js-Security-Course",
        branch="master",
        auth_method="none",
        status="connected",
    )
    db_session.add(repo)
    await db_session.commit()
    await db_session.refresh(repo)

    assert repo.id is not None
    assert repo.repository_url == "https://github.com/ajinabraham/Node.Js-Security-Course"
    assert repo.branch == "master"
    assert repo.status == "connected"


@pytest.mark.asyncio
async def test_github_repository_connect_api_with_auto_detect_branch(
    client: AsyncClient,
    auth_headers: dict[str, str],
    sample_project: Project,
):
    """Verify connecting a GitHub repo via API with blank branch auto-detects default branch."""
    from unittest.mock import patch, AsyncMock

    payload = {
        "provider": "github",
        "repository_url": "https://github.com/ajinabraham/Node.Js-Security-Course",
        "branch": "",
    }

    with patch("backend.app.services.vcs.github_provider.GitHubProvider.validate_connection", return_value=True), \
         patch("backend.app.services.vcs.github_provider.GitHubProvider.get_default_branch", return_value="master"), \
         patch("backend.app.workers.repository_tasks.sync_repository_task.delay") as mock_sync:

        res = await client.post(
            f"/api/v1/projects/{sample_project.id}/repositories",
            headers=auth_headers,
            json=payload,
        )
        assert res.status_code == 201
        data = res.json()["data"]
        assert data["provider"] == "github"
        assert data["repository_url"] == "https://github.com/ajinabraham/Node.Js-Security-Course"
        assert data["branch"] == "master"
        mock_sync.assert_called_once()

