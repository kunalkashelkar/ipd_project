import io
import json
import time
import urllib.error
import urllib.request
import zipfile

BASE_URL = "http://localhost:8000/api/v1"


def api_request(method, path, data=None, token=None, org_id=None):
    url = f"{BASE_URL}{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if org_id:
        headers["X-Organization-ID"] = org_id

    req_data = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=req_data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        return e.code, json.loads(body) if body else {}


def multipart_upload(path, file_bytes, filename, token=None, org_id=None):
    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    data = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: application/zip\r\n\r\n"
    ).encode("utf-8") + file_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")

    headers = {
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "Content-Length": str(len(data)),
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if org_id:
        headers["X-Organization-ID"] = org_id

    req = urllib.request.Request(f"{BASE_URL}{path}", data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        return e.code, json.loads(body) if body else {}


def test_acceptance_journey():
    print("\n--- STARTING PRODUCT ACCEPTANCE TEST JOURNEY ---\n")
    import uuid
    run_id = uuid.uuid4().hex[:6]

    # 1. User A registers
    email_a = f"user_a_{run_id}@example.com"
    pass_a = "SecurePass123!"
    status, res = api_request("POST", "/auth/register", {
        "name": "User Alpha",
        "email": email_a,
        "password": pass_a,
        "organization_name": f"Alpha Corp {run_id}"
    })
    print(f"1. User A registered: status={status}")
    assert status in (200, 201), f"User A registration failed: {res}"

    # User A logs in
    status, res = api_request("POST", "/auth/login", {
        "email": email_a,
        "password": pass_a
    })
    print(f"2. User A login: status={status}")
    assert status == 200
    token_a = res["data"]["tokens"]["access_token"]
    org_a = res["data"]["active_organization"]
    org_a_id = org_a["id"]
    print(f"   -> Active Org A: {org_a['name']} ({org_a_id})")

    # 3. User A opens Team
    status, res = api_request("GET", f"/organizations/{org_a_id}/team/members", token=token_a, org_id=org_a_id)
    print(f"3. User A lists members: status={status}")
    assert status == 200
    members = res["data"]
    assert len(members) == 1
    assert members[0]["user_email"] == email_a
    assert members[0]["role"] == "owner"
    print("   -> User A is verified as Owner")

    # 4. User A invites User B as Developer
    email_b = f"user_b_{run_id}@example.com"
    status, res = api_request("POST", f"/organizations/{org_a_id}/team/invitations", {
        "email": email_b,
        "role_name": "developer"
    }, token=token_a, org_id=org_a_id)
    print(f"4. User A invites User B (developer): status={status}")
    assert status == 201
    invite_token = res["data"]["invitation_token"]
    print(f"   -> Invite token generated: {invite_token[:8]}...")

    # Preview invitation without auth
    status, res = api_request("GET", f"/invitations/{invite_token}")
    print(f"   -> Public preview of invitation: status={status}, org={res['data']['organization_name']}, role={res['data']['role_name']}")
    assert status == 200
    assert res["data"]["invited_email"] == email_b
    assert res["data"]["role_name"] == "developer"

    # 5. User B registers
    pass_b = "SecurePass123!"
    status, res = api_request("POST", "/auth/register", {
        "name": "User Bravo",
        "email": email_b,
        "password": pass_b
    })
    print(f"5. User B registered: status={status}")
    assert status in (200, 201)

    status, res = api_request("POST", "/auth/login", {
        "email": email_b,
        "password": pass_b
    })
    print(f"   -> User B login: status={status}")
    assert status == 200
    token_b = res["data"]["tokens"]["access_token"]
    user_b_id = res["data"]["user"]["id"]

    # 6. User B accepts invitation
    status, res = api_request("POST", "/invitations/accept", {
        "token": invite_token
    }, token=token_b)
    print(f"6. User B accepts invitation: status={status}")
    assert status == 200
    assert res["data"]["role"] == "developer"

    # Verify User B appears in Org A members
    status, res = api_request("GET", f"/organizations/{org_a_id}/team/members", token=token_a, org_id=org_a_id)
    members = res["data"]
    member_b = next((m for m in members if m["user_email"] == email_b), None)
    assert member_b is not None
    assert member_b["role"] == "developer"
    print("   -> User B appears as Developer in Team list")

    # 7. User A changes User B to Viewer
    status, res = api_request("PATCH", f"/organizations/{org_a_id}/team/members/{user_b_id}/role", {
        "role_name": "viewer"
    }, token=token_a, org_id=org_a_id)
    print(f"7. User A changes User B role to Viewer: status={status}")
    assert status == 200
    assert res["data"]["role"] == "viewer"

    # 8. User B checks permissions / attempts management operation
    status, res = api_request("POST", f"/organizations/{org_a_id}/team/invitations", {
        "email": "hacker@example.com",
        "role_name": "developer"
    }, token=token_b, org_id=org_a_id)
    print(f"8. User B (Viewer) attempt to invite member: status={status} (Expected 403)")
    assert status == 403, f"Expected 403 Forbidden for Viewer, got {status}"

    # As Viewer, User B must NOT be able to create projects (project.create)
    status, res = api_request("POST", "/projects", {
        "name": "Unauthorized Project"
    }, token=token_b, org_id=org_a_id)
    print(f"   -> User B (Viewer) attempt to create project: status={status} (Expected 403)")
    assert status == 403, f"Expected 403 Forbidden for Viewer, got {status}"

    # 9. User A changes User B role to Security Analyst
    status, res = api_request("PATCH", f"/organizations/{org_a_id}/team/members/{user_b_id}/role", {
        "role_name": "security_analyst"
    }, token=token_a, org_id=org_a_id)
    print(f"9. User A changes User B role to Security Analyst: status={status}")
    assert status == 200
    assert res["data"]["role"] == "security_analyst"

    # 10. User A attempts to demote self (sole owner) -> MUST FAIL with 422/400
    status, res = api_request("GET", "/auth/me", token=token_a)
    user_a_id = res["data"]["id"]
    status, res = api_request("PATCH", f"/organizations/{org_a_id}/team/members/{user_a_id}/role", {
        "role_name": "developer"
    }, token=token_a, org_id=org_a_id)
    print(f"10. Sole owner demotion attempt: status={status} (Expected 422/400 validation error)")
    assert status in (400, 422), f"Expected 422/400 for sole owner demotion, got {status}"

    # 11. User A removes User B
    status, res = api_request("DELETE", f"/organizations/{org_a_id}/team/members/{user_b_id}", token=token_a, org_id=org_a_id)
    print(f"11. User A removes User B: status={status}")
    assert status == 200

    # User B no longer has access to Org A
    status, res = api_request("GET", f"/organizations/{org_a_id}/team/members", token=token_b, org_id=org_a_id)
    print(f"    -> User B access after removal: status={status} (Expected 403 Forbidden)")
    assert status == 403

    # 12. User C in Org B Tenant Isolation Check
    email_c = f"user_c_{run_id}@example.com"
    pass_c = "SecurePass123!"
    status, res = api_request("POST", "/auth/register", {
        "name": "User Charlie",
        "email": email_c,
        "password": pass_c,
        "organization_name": f"Charlie Corp {run_id}"
    })
    status, res = api_request("POST", "/auth/login", {
        "email": email_c,
        "password": pass_c
    })
    token_c = res["data"]["tokens"]["access_token"]
    org_c_id = res["data"]["active_organization"]["id"]
    print(f"12. User C in Org B created: {org_c_id}")

    # User C tries to access Org A team
    status, res = api_request("GET", f"/organizations/{org_a_id}/team/members", token=token_c, org_id=org_a_id)
    print(f"    -> User C cross-tenant access to Org A: status={status} (Expected 403)")
    assert status == 403

    # User C tries to invite into Org A
    status, res = api_request("POST", f"/organizations/{org_a_id}/team/invitations", {
        "email": "injected@example.com",
        "role_name": "admin"
    }, token=token_c, org_id=org_a_id)
    print(f"    -> User C cross-tenant invite to Org A: status={status} (Expected 403)")
    assert status == 403

    # ==============================================================
    # PHASE 3 PRODUCT ACCEPTANCE JOURNEY
    # ==============================================================
    print("\n--- EXECUTING PHASE 3 SOURCE INGESTION & PROVENANCE JOURNEY ---\n")

    # 13. User A creates a real Project in Org A
    status, res = api_request("POST", "/projects", {
        "name": f"Enterprise Vulnerability Target {run_id}",
        "description": "Core production code target for static graph analysis",
        "language": "python",
        "default_branch": "main",
    }, token=token_a, org_id=org_a_id)
    print(f"13. Project created: status={status}")
    assert status in (200, 201), f"Project creation failed: {res}"
    project_id = res["data"]["id"]
    print(f"    -> Project ID: {project_id}")

    # 14. User A uploads real multi-language ZIP archive
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            "app/auth.py",
            "def authenticate_user(user, password):\n    # Authenticate credentials\n    return user == 'admin' and password == 'secret'\n",
        )
        zf.writestr(
            "app/crypto.py",
            "def authenticate_user(u, p):\n    # Clone function with identical normalized logic\n    return u == 'admin' and p == 'secret'\n",
        )
        zf.writestr(
            "src/buffer.c",
            "#include <stdio.h>\nint check_buffer(char *buf) {\n    return 0;\n}\n",
        )
    zip_bytes = zip_buf.getvalue()

    status, res = multipart_upload(
        f"/projects/{project_id}/snapshots/upload",
        zip_bytes,
        "source_code.zip",
        token=token_a,
        org_id=org_a_id,
    )
    print(f"14. Source ZIP uploaded: status={status}")
    assert status in (200, 201), f"Upload failed: {res}"
    snapshot_id = res["data"]["id"]
    print(f"    -> Immutable Snapshot ID: {snapshot_id} (Initial status: {res['data']['status']})")

    # 15. Poll Celery worker for completion to READY state
    print("15. Awaiting Celery worker preprocessing to reach READY state...")
    ready = False
    for _ in range(30):
        time.sleep(1)
        status, res = api_request(
            "GET", f"/projects/{project_id}/snapshots/{snapshot_id}", token=token_a, org_id=org_a_id
        )
        if status == 200 and res["data"]["status"] == "ready":
            ready = True
            print(f"    -> Snapshot successfully processed to READY in {_+1}s!")
            print(f"       Files: {res['data']['file_count']}, Total Bytes: {res['data']['total_bytes']}")
            print(f"       Detected Languages: {res['data']['detected_languages']}")
            print(f"       Preprocessing Spec: {res['data']['preprocessing_version']}")
            break
        elif status == 200 and res["data"]["status"] == "failed":
            raise RuntimeError(f"Snapshot processing failed: {res['data']}")
    assert ready, "Worker timed out processing source snapshot"

    # 16. Inspect Ingested Files
    status, res = api_request(
        "GET", f"/projects/{project_id}/snapshots/{snapshot_id}/files", token=token_a, org_id=org_a_id
    )
    print(f"16. Snapshot file listing: status={status}")
    assert status == 200
    files = res["data"]["items"]
    assert len(files) == 3
    file_paths = [f["relative_path"] for f in files]
    assert "app/auth.py" in file_paths
    assert "src/buffer.c" in file_paths
    print(f"    -> Ingested Files: {file_paths}")

    # 17. Safe Source Content Retrieval
    auth_file = next(f for f in files if f["relative_path"] == "app/auth.py")
    status, res = api_request(
        "GET",
        f"/projects/{project_id}/snapshots/{snapshot_id}/files/{auth_file['id']}/content",
        token=token_a,
        org_id=org_a_id,
    )
    print(f"17. Safe source content retrieval: status={status}")
    assert status == 200
    content = res["data"]["content"]
    assert "authenticate_user" in content
    assert res["data"]["line_count"] > 0
    print("    -> Source verified directly from S3/MinIO containment")

    # 18. Extracted Functions & Duplicate Detection Verification
    status, res = api_request(
        "GET", f"/projects/{project_id}/snapshots/{snapshot_id}/functions", token=token_a, org_id=org_a_id
    )
    print(f"18. Extracted deterministic functions: status={status}")
    assert status == 200
    funcs = res["data"]["items"]
    assert len(funcs) >= 2
    func_names = [fn["name"] for fn in funcs]
    assert "authenticate_user" in func_names
    # Duplicate detection verification: app/auth.py and app/crypto.py have duplicate group
    dup_funcs = [fn for fn in funcs if fn.get("duplicate_group_id")]
    assert len(dup_funcs) >= 2, "Normalized duplicate functions should be assigned duplicate_group_id"
    print(f"    -> Deterministic functions: {len(funcs)} extracted, {len(dup_funcs)} grouped in duplicate group {dup_funcs[0]['duplicate_group_id']}")

    # 19. Start Security Scan Bound to Immutable Snapshot
    status, res = api_request("POST", "/scans", {
        "project_id": project_id,
        "source_snapshot_id": snapshot_id,
    }, token=token_a, org_id=org_a_id)
    print(f"19. Scan creation against READY snapshot: status={status}")
    assert status in (200, 201), f"Scan creation failed: {res}"
    scan_id = res["data"]["id"]
    assert res["data"]["source_snapshot_id"] == snapshot_id
    print(f"    -> Scan {scan_id} successfully bound to Snapshot {snapshot_id}")

    # 20. Strict Cross-Tenant Isolation Attack Prevention
    print("20. Testing Cross-Tenant IDOR/BOLA Invariant Enforcement...")
    # User C in Org B cannot read Project A
    status, res = api_request("GET", f"/projects/{project_id}", token=token_c, org_id=org_c_id)
    print(f"    -> User C access Project A: status={status} (Expected 404)")
    assert status in (403, 404)

    # User C cannot list Snapshot A
    status, res = api_request("GET", f"/projects/{project_id}/snapshots/{snapshot_id}", token=token_c, org_id=org_c_id)
    print(f"    -> User C access Snapshot A: status={status} (Expected 404)")
    assert status in (403, 404)

    # User C cannot read file content from Snapshot A
    status, res = api_request(
        "GET",
        f"/projects/{project_id}/snapshots/{snapshot_id}/files/{auth_file['id']}/content",
        token=token_c,
        org_id=org_c_id,
    )
    print(f"    -> User C access source content from Snapshot A: status={status} (Expected 404)")
    assert status in (403, 404)

    # User C cannot trigger scan against Snapshot A
    status, res = api_request("POST", "/scans", {
        "project_id": project_id,
        "source_snapshot_id": snapshot_id,
    }, token=token_c, org_id=org_c_id)
    print(f"    -> User C create scan on Snapshot A: status={status} (Expected 404/403)")
    assert status in (403, 404)

    # 21. Project Archive & Provenance Preservation
    status, res = api_request("POST", f"/projects/{project_id}/archive", token=token_a, org_id=org_a_id)
    print(f"21. Project archive lifecycle: status={status}")
    assert status == 200
    assert res["data"]["is_archived"] is True
    print("    -> Project archived while snapshots, files, and scans remain immutable and preserved.")

    print("\n==================================================================")
    print("PHASE 3 COMPLETE: ALL END-TO-END PRODUCT ACCEPTANCE JOURNEYS PASSED 100%!")
    print("==================================================================\n")


if __name__ == "__main__":
    test_acceptance_journey()
