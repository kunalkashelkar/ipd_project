#!/usr/bin/env python3
"""
VulnScan CLI — Lightweight CI/CD Interface (Phase 7)
Standalone command-line client for automated scans and security gate verification.
Requires Python 3.8+ with standard library only.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request


class SecurityCLI:
    """Lightweight client interfacing with platform CI/CD endpoints."""

    def __init__(self, api_url: str, api_key: str):
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key

    def _request(self, method: str, path: str, payload: dict | None = None) -> dict:
        url = f"{self.api_url}{path}"
        headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
            "User-Agent": "VulnScan-CLI/1.0",
        }
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        req = urllib.request.Request(url, data=data, headers=headers, method=method)

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = resp.read().decode("utf-8")
                return json.loads(body)
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            try:
                parsed = json.loads(err_body)
                msg = parsed.get("detail") or parsed.get("message") or err_body
            except Exception:
                msg = err_body
            raise RuntimeError(f"HTTP {e.code}: {msg}")
        except urllib.error.URLError as e:
            raise RuntimeError(f"Network error: {e.reason}")

    def trigger_scan(self, project_id: str, branch: str, commit_sha: str) -> dict:
        return self._request(
            "POST",
            "/api/v1/ci/scans",
            {
                "project_id": project_id,
                "branch": branch,
                "commit_sha": commit_sha,
            },
        )

    def get_status(self, scan_id: str) -> dict:
        return self._request("GET", f"/api/v1/ci/scans/{scan_id}")

    def get_gate(self, scan_id: str) -> dict:
        return self._request("GET", f"/api/v1/ci/scans/{scan_id}/gate")


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="vulnscan",
        description="VulnScan CLI tool for automated CI security scans and gate checks.",
    )
    parser.add_argument(
        "--api-url",
        default=os.environ.get("VULNSCAN_API_URL", os.environ.get("SECURITY_API_URL", "http://localhost:8000")),
        help="Base platform API URL (default: $VULNSCAN_API_URL or http://localhost:8000)",
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("VULNSCAN_API_KEY", os.environ.get("SECURITY_API_KEY", "")),
        help="API Key for CI authentication (default: $VULNSCAN_API_KEY)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON to stdout",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # Subcommand: scan
    scan_p = subparsers.add_parser("scan", help="Trigger a security scan")
    scan_p.add_argument("--project", required=True, help="Target project public ID")
    scan_p.add_argument("--branch", default="main", help="Target branch name")
    scan_p.add_argument("--commit", default="HEAD", help="Commit SHA to analyze")
    scan_p.add_argument("--wait", action="store_true", help="Poll until scan and gate complete")
    scan_p.add_argument("--timeout", type=int, default=300, help="Wait timeout in seconds")

    # Subcommand: status
    status_p = subparsers.add_parser("status", help="Get scan status")
    status_p.add_argument("scan_id", help="Scan public ID")

    # Subcommand: gate / check-gate
    gate_p = subparsers.add_parser("gate", aliases=["check-gate"], help="Evaluate security gate for scan")
    gate_p.add_argument("scan_id", help="Scan public ID")

    args = parser.parse_args()

    if not args.api_key:
        sys.stderr.write("Error: --api-key or SECURITY_API_KEY environment variable is required.\n")
        return 2

    cli = SecurityCLI(api_url=args.api_url, api_key=args.api_key)

    try:
        if args.command == "scan":
            resp = cli.trigger_scan(args.project, args.branch, args.commit)
            scan_id = resp.get("data", {}).get("scan_id")

            if not args.wait:
                if args.json:
                    print(json.dumps(resp, indent=2))
                else:
                    print(f"Scan enqueued successfully: {scan_id}")
                return 0

            # Polling loop
            if not args.json:
                print(f"Polling scan {scan_id} for completion...")

            start_time = time.time()
            while time.time() - start_time < args.timeout:
                status_resp = cli.get_status(scan_id)
                curr_status = status_resp.get("data", {}).get("status")

                if curr_status in ("completed", "failed"):
                    break
                time.sleep(3)
            else:
                sys.stderr.write(f"Error: Scan timed out after {args.timeout}s.\n")
                return 2

            # Evaluate Gate
            gate_resp = cli.get_gate(scan_id)
            gate_data = gate_resp.get("data", {})
            exit_code = gate_data.get("exit_code", 0)

            if args.json:
                print(json.dumps(gate_resp, indent=2))
            else:
                verdict = gate_data.get("gate_result", "UNKNOWN")
                print(f"Security Gate Verdict: {verdict}")
                print(f"Summary: {gate_data.get('summary', '')}")
                if gate_data.get("violations"):
                    print("Violations:")
                    for v in gate_data["violations"]:
                        print(f"  - [{v.get('rule')}] {v.get('title')}")

            return exit_code

        elif args.command == "status":
            resp = cli.get_status(args.scan_id)
            if args.json:
                print(json.dumps(resp, indent=2))
            else:
                data = resp.get("data", {})
                print(f"Scan: {data.get('scan_id')} | Status: {data.get('status')}")
            return 0

        elif args.command in ("gate", "check-gate"):
            resp = cli.get_gate(args.scan_id)
            gate_data = resp.get("data", {})
            exit_code = gate_data.get("exit_code", 0)

            if args.json:
                print(json.dumps(resp, indent=2))
            else:
                verdict = gate_data.get("gate_result", "UNKNOWN")
                print(f"Security Gate Verdict: {verdict}")
                print(f"Summary: {gate_data.get('summary', '')}")
                if gate_data.get("violations"):
                    print("Violations:")
                    for v in gate_data["violations"]:
                        print(f"  - [{v.get('rule')}] {v.get('title')}")

            return exit_code

    except Exception as exc:
        sys.stderr.write(f"Error: {exc}\n")
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
