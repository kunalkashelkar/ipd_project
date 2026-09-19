# ============================================================
# HTML Report Generator (Phase 7)
# ============================================================

from __future__ import annotations

import html
from datetime import datetime, timezone
from typing import Any


class HTMLReportGenerator:
    """Generates standalone, beautifully formatted, self-contained HTML security reports."""

    def generate(self, data: dict[str, Any], report_type: str = "security") -> bytes:
        """Produce HTML bytes with embedded CSS and proper escaping."""
        project = data.get("project", {})
        org = data.get("organization", {})
        scan = data.get("scan", {})
        snapshot = data.get("snapshot", {})
        metrics = data.get("metrics", {})
        findings = data.get("findings", [])

        proj_name = html.escape(project.get("name", "Project"))
        org_name = html.escape(org.get("name", "Organization"))
        scan_id = html.escape(scan.get("public_id", "N/A"))
        commit_sha = html.escape(str(snapshot.get("commit_sha", "HEAD"))[:10])
        branch = html.escape(snapshot.get("branch", "main"))
        health_score = metrics.get("health_score", 100.0)
        health_rating = metrics.get("health_rating", "A")
        gen_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        sev_counts = metrics.get("severity_counts", {})
        crit = sev_counts.get("critical", 0)
        high = sev_counts.get("high", 0)
        med = sev_counts.get("medium", 0)
        low = sev_counts.get("low", 0)

        type_title = {
            "developer": "Developer Remediation Report",
            "security": "Security Assessment Report",
            "executive": "Executive Security Posture Report",
        }.get(report_type, "Security Report")

        # HTML Head and Styles
        html_out = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{html.escape(type_title)} - {proj_name}</title>
  <style>
    :root {{
      --bg: #0f172a;
      --card-bg: #1e293b;
      --card-border: #334155;
      --text: #f8fafc;
      --text-muted: #94a3b8;
      --crit: #ef4444;
      --high: #f97316;
      --med: #eab308;
      --low: #3b82f6;
      --success: #10b981;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.5;
      padding: 32px 20px;
    }}
    .container {{ max-width: 1100px; margin: 0 auto; }}
    .header {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      border-bottom: 1px solid var(--card-border);
      padding-bottom: 24px;
      margin-bottom: 32px;
    }}
    .header h1 {{ font-size: 26px; font-weight: 700; color: #fff; margin-bottom: 6px; }}
    .header p {{ color: var(--text-muted); font-size: 14px; }}
    .badge-score {{
      display: inline-flex;
      flex-direction: column;
      align-items: center;
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 12px 20px;
      text-align: center;
    }}
    .badge-score .score {{ font-size: 28px; font-weight: 800; color: #38bdf8; }}
    .badge-score .rating {{ font-size: 12px; font-weight: 600; color: var(--text-muted); text-transform: uppercase; }}
    .grid-kpi {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 16px;
      margin-bottom: 32px;
    }}
    .kpi-card {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 10px;
      padding: 18px;
    }}
    .kpi-title {{ font-size: 13px; font-weight: 500; color: var(--text-muted); margin-bottom: 4px; }}
    .kpi-value {{ font-size: 24px; font-weight: 700; }}
    .crit {{ color: var(--crit); }}
    .high {{ color: var(--high); }}
    .med {{ color: var(--med); }}
    .low {{ color: var(--low); }}
    .card {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 10px;
      padding: 24px;
      margin-bottom: 24px;
    }}
    .card h2 {{ font-size: 18px; font-weight: 600; margin-bottom: 16px; border-bottom: 1px solid var(--card-border); padding-bottom: 10px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 14px; text-align: left; }}
    th, td {{ padding: 10px 12px; border-bottom: 1px solid var(--card-border); }}
    th {{ color: var(--text-muted); font-weight: 600; text-transform: uppercase; font-size: 12px; }}
    .tag {{
      display: inline-block;
      padding: 2px 8px;
      border-radius: 4px;
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
    }}
    .tag-crit {{ background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.4); }}
    .tag-high {{ background: rgba(249, 115, 22, 0.2); color: #fb923c; border: 1px solid rgba(249, 115, 22, 0.4); }}
    .tag-med {{ background: rgba(234, 179, 8, 0.2); color: #facc15; border: 1px solid rgba(234, 179, 8, 0.4); }}
    .tag-low {{ background: rgba(59, 130, 246, 0.2); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.4); }}
    .code-block {{
      background: #090d16;
      border: 1px solid #1e293b;
      border-radius: 6px;
      padding: 12px;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 12px;
      color: #e2e8f0;
      overflow-x: auto;
      white-space: pre;
      margin-top: 8px;
    }}
    .finding-item {{
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 16px;
      margin-bottom: 16px;
      background: rgba(15, 23, 42, 0.5);
    }}
    .footer {{
      text-align: center;
      color: var(--text-muted);
      font-size: 12px;
      margin-top: 40px;
      border-top: 1px solid var(--card-border);
      padding-top: 20px;
    }}
    @media print {{
      body {{ background: #fff; color: #000; padding: 0; }}
      .card, .finding-item, .kpi-card {{ border: 1px solid #ccc; background: #fff; color: #000; }}
      .code-block {{ background: #f4f4f4; color: #000; border: 1px solid #ccc; }}
    }}
  </style>
</head>
<body>
<div class="container">

  <div class="header">
    <div>
      <h1>{html.escape(type_title)}</h1>
      <p>Project: <strong>{proj_name}</strong> | Org: <strong>{org_name}</strong></p>
      <p>Scan: <code>{scan_id}</code> | Branch: <code>{branch}</code> ({commit_sha})</p>
    </div>
    <div class="badge-score">
      <div class="score">{health_score}</div>
      <div class="rating">Grade {health_rating} (Score {metrics.get("score_version", "v1.0.0")})</div>
    </div>
  </div>

  <div class="grid-kpi">
    <div class="kpi-card">
      <div class="kpi-title">Total Persistent Findings</div>
      <div class="kpi-value">{len(findings)}</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-title">Critical Severity</div>
      <div class="kpi-value crit">{crit}</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-title">High Severity</div>
      <div class="kpi-value high">{high}</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-title">Medium & Low</div>
      <div class="kpi-value med">{med + low}</div>
    </div>
  </div>
"""

        # Section: Executive Summary (Included for Executive and Security reports)
        if report_type in ("executive", "security"):
            html_out += f"""
  <div class="card">
    <h2>Executive Posture Summary</h2>
    <p style="color: var(--text-muted); margin-bottom: 14px;">
      This project demonstrates an overall Security Health Score of <strong>{health_score}/100 (Grade {health_rating})</strong>.
      {'Immediate remediation is required due to active Critical/High risk findings.' if (crit + high) > 0 else 'No critical vulnerabilities were observed during this analysis cycle.'}
    </p>
    <table>
      <thead>
        <tr>
          <th>Severity</th>
          <th>Finding Count</th>
          <th>Risk Weight</th>
          <th>Posture Impact</th>
        </tr>
      </thead>
      <tbody>
        <tr><td><span class="tag tag-crit">Critical</span></td><td>{crit}</td><td>-15.0 pts each</td><td>{'High Priority Block' if crit > 0 else 'Clear'}</td></tr>
        <tr><td><span class="tag tag-high">High</span></td><td>{high}</td><td>-8.0 pts each</td><td>{'Review Suggested' if high > 0 else 'Clear'}</td></tr>
        <tr><td><span class="tag tag-med">Medium</span></td><td>{med}</td><td>-3.0 pts each</td><td>Standard Triage</td></tr>
        <tr><td><span class="tag tag-low">Low</span></td><td>{low}</td><td>-1.0 pts each</td><td>Backlog / Informational</td></tr>
      </tbody>
    </table>
  </div>
"""

        # Section: Findings / Remediation
        if report_type == "executive":
            html_out += """
  <div class="card">
    <h2>Findings Inventory (Summary)</h2>
    <table>
      <thead>
        <tr>
          <th>ID</th>
          <th>Title</th>
          <th>Severity</th>
          <th>CWE</th>
          <th>Status</th>
          <th>Risk Score</th>
        </tr>
      </thead>
      <tbody>
"""
            for f in findings:
                sev_cls = f"tag-{f.get('severity', 'low')}"
                html_out += f"""
        <tr>
          <td><code>{html.escape(f.get('public_id', ''))}</code></td>
          <td><strong>{html.escape(f.get('title', ''))}</strong></td>
          <td><span class="tag {sev_cls}">{html.escape(f.get('severity', '').upper())}</span></td>
          <td>{html.escape(f.get('cwe_id', 'N/A'))}</td>
          <td>{html.escape(f.get('status', 'OPEN'))}</td>
          <td>{f.get('risk_score', 0.0)}</td>
        </tr>
"""
            html_out += """
      </tbody>
    </table>
  </div>
"""
        else:
            # Detailed Developer or Security Report
            html_out += f"""
  <div class="card">
    <h2>Detailed Findings & Occurrences ({len(findings)})</h2>
"""
            if not findings:
                html_out += "<p style='color: var(--text-muted);'>No findings observed in this evaluation scope.</p>"

            for f in findings:
                sev = f.get("severity", "low")
                sev_cls = f"tag-{sev}"
                rems = f.get("remediations", [])
                occs = f.get("occurrences", [])

                html_out += f"""
    <div class="finding-item">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
        <div>
          <span class="tag {sev_cls}">{html.escape(sev.upper())}</span>
          <span style="font-size: 15px; font-weight: 700; margin-left: 8px;">{html.escape(f.get('title', ''))}</span>
        </div>
        <span style="font-size: 12px; color: var(--text-muted);">CWE: {html.escape(f.get('cwe_id', 'N/A'))} | Score: {f.get('risk_score', 0.0)}</span>
      </div>
      <p style="font-size: 13px; color: var(--text-muted); margin-bottom: 8px;">
        Finding ID: <code>{html.escape(f.get('public_id', ''))}</code> | Finding Type: <strong>Vulnerability</strong> | Status: <strong>{html.escape(f.get('status', 'OPEN'))}</strong>
      </p>
"""
                # Occurrences
                if occs:
                    html_out += "<div style='font-size: 13px; margin-top: 8px;'><strong>Affected Locations:</strong><ul style='margin-left: 20px;'>"
                    for occ in occs:
                        loc = f"{html.escape(occ.get('file_path', ''))}:{occ.get('start_line') or 1}"
                        html_out += f"<li><code>{loc}</code> (Confidence: {occ.get('confidence', 0.0)})</li>"
                    html_out += "</ul></div>"

                # If developer report, include patch and remediation
                if report_type == "developer" and rems:
                    rem = rems[0]
                    html_out += f"""
      <div style="margin-top: 12px; background: rgba(30, 41, 59, 0.8); border: 1px solid var(--card-border); border-radius: 6px; padding: 12px;">
        <div style="font-size: 13px; font-weight: 600; color: #38bdf8; margin-bottom: 4px;">Proposed AI Remediation (Validation: {html.escape(rem.get('validation_status', 'unvalidated'))}):</div>
        <p style="font-size: 13px; color: var(--text-muted); margin-bottom: 8px;">{html.escape(rem.get('explanation', ''))}</p>
"""
                    if rem.get("suggested_patch"):
                        html_out += f"""
        <div class="code-block">{html.escape(rem.get('suggested_patch', ''))}</div>
"""
                    html_out += "</div>"

                html_out += "</div>"

            html_out += "</div>"

        # Footer
        html_out += f"""
  <div class="footer">
    Generated on {gen_time} by VulnScan Platform &bull; Authoritative Persistent Security State
  </div>

</div>
</body>
</html>
"""
        return html_out.encode("utf-8")
