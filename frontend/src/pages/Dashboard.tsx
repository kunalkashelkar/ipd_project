import React, { useEffect, useState } from 'react';
import {
  ShieldCheck,
  Activity,
  FolderOpen,
  AlertTriangle,
  ArrowRight,
  Loader2,
  Plus,
  Play,
  Clock,
  CheckCircle2,
  XCircle,
  ExternalLink,
  ShieldAlert,
  FileCode2,
  Terminal,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Link, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store';
import { analyticsService } from '../services/analyticsService';
import { projectService } from '../services/projectService';
import { scanService } from '../services/scanService';
import { findingService } from '../services/findingService';
import { Project, DashboardMetrics, Scan, FindingListItem } from '../types';
import { getProjectUrl, getResultsUrl, getScanProgressUrl } from '../utils/routes';
import { VulnScanLogo } from '../components/VulnScanLogo';

export default function Dashboard() {
  const navigate = useNavigate();
  const { activeOrganization } = useAuthStore();
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [recentScans, setRecentScans] = useState<Scan[]>([]);
  const [topFindings, setTopFindings] = useState<FindingListItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadDashboard() {
      setLoading(true);
      try {
        const [metricsData, projectsData] = await Promise.allSettled([
          analyticsService.getDashboardMetrics(),
          projectService.listProjects({ page: 1, page_size: 5 }),
        ]);

        if (metricsData.status === 'fulfilled') {
          setMetrics(metricsData.value);
          setRecentScans(metricsData.value.recent_scans || []);
        }
        if (projectsData.status === 'fulfilled') {
          setProjects(projectsData.value.items || []);
        }
      } catch {
        // Handled by API interceptor
      } finally {
        setLoading(false);
      }
    }
    loadDashboard();
  }, [activeOrganization?.id]);

  const healthScoreObj =
    typeof metrics?.health_score === 'object' && metrics?.health_score !== null
      ? metrics.health_score
      : null;
  const rawScore = healthScoreObj
    ? healthScoreObj.score
    : typeof metrics?.health_score === 'number'
    ? metrics.health_score
    : null;
  const rawRating = healthScoreObj
    ? healthScoreObj.rating
    : metrics?.health_rating ?? null;
  const rawStatus = healthScoreObj
    ? healthScoreObj.status
    : metrics?.health_status ?? (rawScore === null ? 'NO_DATA' : 'SCORED');

  const isNoData = rawStatus === 'NO_DATA' || rawScore === null || rawScore === undefined;

  const criticalCount = metrics?.severity_breakdown?.critical ?? metrics?.severity_breakdown?.CRITICAL ?? 0;
  const highCount = metrics?.severity_breakdown?.high ?? metrics?.severity_breakdown?.HIGH ?? 0;
  const mediumCount = metrics?.severity_breakdown?.medium ?? metrics?.severity_breakdown?.MEDIUM ?? 0;
  const lowCount = metrics?.severity_breakdown?.low ?? metrics?.severity_breakdown?.LOW ?? 0;

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-16">
      {/* Platform Header with Breadcrumb and Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-border">
        <div className="flex items-center gap-3">
          <VulnScanLogo variant="icon" size="sm" />
          <div>
            <h1 className="text-xl font-bold tracking-tight text-foreground font-display">
              Workspace Security Overview
            </h1>
            <p className="text-xs text-muted-foreground mt-0.5">
              Authoritative security posture, provenance tracking, and vulnerability triage for{' '}
              <span className="font-semibold text-foreground">
                {activeOrganization?.name || 'Active Workspace'}
              </span>
              .
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2.5">
          <Link to="/projects/create">
            <Button size="sm" className="btn-primary">
              <Plus className="w-3.5 h-3.5" />
              <span>New Project</span>
            </Button>
          </Link>
        </div>
      </div>

      {/* Primary Security Posture & Triage Block */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Security Health Score Posture Card */}
        <div className="lg:col-span-4 bg-card border border-border rounded-card p-5 shadow-soft flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Security Health Score
              </span>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-primary/10 text-primary border border-primary/20">
                Authoritative
              </span>
            </div>

            <div className="mt-4">
              {loading ? (
                <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
              ) : isNoData ? (
                <div>
                  <div className="text-2xl font-bold text-muted-foreground tracking-tight font-display">
                    No data
                  </div>
                  <span className="text-[11px] text-muted-foreground block mt-0.5">
                    Unscored — scan required
                  </span>
                </div>
              ) : (
                <div>
                  <div className="flex items-baseline gap-2">
                    <span className="text-4xl font-extrabold text-foreground font-display tracking-tight">
                      {Math.round(rawScore!)}
                    </span>
                    <span className="text-xs font-medium text-muted-foreground">/ 100</span>
                    <span
                      className={`ml-auto px-2 py-0.5 rounded text-xs font-bold font-mono border ${
                        rawScore! >= 80
                          ? 'bg-severity-success/10 text-severity-success border-severity-success/30'
                          : rawScore! >= 60
                          ? 'bg-severity-medium/10 text-severity-medium border-severity-medium/30'
                          : 'bg-destructive/10 text-destructive border-destructive/30'
                      }`}
                    >
                      Grade {rawRating || (rawScore! >= 80 ? 'A' : rawScore! >= 60 ? 'B' : 'C')}
                    </span>
                  </div>
                  <span className="text-[11px] text-muted-foreground block mt-1">
                    Authoritative workspace posture
                  </span>
                </div>
              )}
            </div>

            {!isNoData && !loading && (
              <div className="mt-4">
                <div className="w-full h-1.5 bg-sidebar rounded-full overflow-hidden border border-border/60">
                  <div
                    className="h-full bg-gradient-to-r from-brand-orange via-brand-amber to-primary rounded-full transition-all duration-500"
                    style={{ width: `${Math.min(100, Math.max(0, rawScore || 0))}%` }}
                  />
                </div>
              </div>
            )}
          </div>

          <div className="pt-4 mt-4 border-t border-border/60 flex items-center justify-between text-xs">
            <div>
              <span className="font-semibold text-foreground block">Total Projects</span>
              <span className="text-[11px] text-muted-foreground">Non-archived projects in this workspace</span>
            </div>
            <span className="text-xl font-bold font-mono text-foreground">{metrics?.total_projects ?? 0}</span>
          </div>
        </div>

        {/* Severity Triage Matrix */}
        <div className="lg:col-span-8 grid grid-cols-2 sm:grid-cols-4 gap-3">
          {/* Critical */}
          <Link
            to="/findings"
            className="bg-card border border-border rounded-card p-4 hover:border-destructive/60 transition-all shadow-soft flex flex-col justify-between group"
          >
            <div>
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Critical</span>
                <span className="w-2 h-2 rounded-full bg-destructive animate-pulse" />
              </div>
              <div className="text-3xl font-extrabold text-destructive font-display mt-3 tabular-nums">
                {loading ? '—' : criticalCount}
              </div>
            </div>
            <span className="text-[11px] text-muted-foreground group-hover:text-foreground transition-colors mt-2 flex items-center gap-1">
              Immediate triage <ArrowRight className="w-3 h-3 group-hover:translate-x-0.5 transition-transform" />
            </span>
          </Link>

          {/* High */}
          <Link
            to="/findings"
            className="bg-card border border-border rounded-card p-4 hover:border-brand-orange/60 transition-all shadow-soft flex flex-col justify-between group"
          >
            <div>
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">High</span>
                <span className="w-2 h-2 rounded-full bg-brand-orange" />
              </div>
              <div className="text-3xl font-extrabold text-brand-orange font-display mt-3 tabular-nums">
                {loading ? '—' : highCount}
              </div>
            </div>
            <span className="text-[11px] text-muted-foreground group-hover:text-foreground transition-colors mt-2 flex items-center gap-1">
              Priority review <ArrowRight className="w-3 h-3 group-hover:translate-x-0.5 transition-transform" />
            </span>
          </Link>

          {/* Medium */}
          <Link
            to="/findings"
            className="bg-card border border-border rounded-card p-4 hover:border-brand-amber/60 transition-all shadow-soft flex flex-col justify-between group"
          >
            <div>
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Medium</span>
                <span className="w-2 h-2 rounded-full bg-brand-amber" />
              </div>
              <div className="text-3xl font-extrabold text-brand-amber font-display mt-3 tabular-nums">
                {loading ? '—' : mediumCount}
              </div>
            </div>
            <span className="text-[11px] text-muted-foreground group-hover:text-foreground transition-colors mt-2 flex items-center gap-1">
              Scheduled fix <ArrowRight className="w-3 h-3 group-hover:translate-x-0.5 transition-transform" />
            </span>
          </Link>

          {/* Low / Informational */}
          <Link
            to="/findings"
            className="bg-card border border-border rounded-card p-4 hover:border-primary/60 transition-all shadow-soft flex flex-col justify-between group"
          >
            <div>
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Low / Info</span>
                <span className="w-2 h-2 rounded-full bg-primary" />
              </div>
              <div className="text-3xl font-extrabold text-primary font-display mt-3 tabular-nums">
                {loading ? '—' : lowCount}
              </div>
            </div>
            <span className="text-[11px] text-muted-foreground group-hover:text-foreground transition-colors mt-2 flex items-center gap-1">
              Code hygiene <ArrowRight className="w-3 h-3 group-hover:translate-x-0.5 transition-transform" />
            </span>
          </Link>
        </div>
      </div>

      {/* Analytics & Vulnerability Intelligence: Top CWEs & Historical Risk */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top Common Weaknesses (CWE) */}
        <div className="bg-card border border-border rounded-card shadow-soft p-5">
          <div className="flex items-center justify-between pb-3 border-b border-border/60 mb-4">
            <h2 className="text-xs font-bold uppercase tracking-wider text-foreground font-display">
              Top Common Weaknesses (CWE)
            </h2>
            <span className="text-[11px] text-muted-foreground">Most prevalent vulnerability patterns</span>
          </div>
          {metrics?.vulnerabilities_by_cwe && metrics.vulnerabilities_by_cwe.length > 0 ? (
            <div className="space-y-2.5">
              {metrics.vulnerabilities_by_cwe.map((cwe) => (
                <div key={cwe.cwe_id} className="flex items-center justify-between p-2.5 rounded-md bg-sidebar border border-border/60 text-xs">
                  <span className="font-mono font-semibold text-foreground">{cwe.cwe_id}</span>
                  <span className="text-muted-foreground font-mono text-[11px]">{cwe.count} findings</span>
                </div>
              ))}
            </div>
          ) : (
            <div className="py-8 text-center text-muted-foreground">
              <ShieldAlert className="w-8 h-8 mx-auto mb-2 opacity-30" />
              <p className="text-xs font-semibold text-foreground">No CWE Attributions</p>
              <p className="text-[11px] text-muted-foreground mt-0.5">
                No Common Weakness Enumerations mapped to active findings.
              </p>
            </div>
          )}
        </div>

        {/* Risk Timeline */}
        <div className="bg-card border border-border rounded-card shadow-soft p-5">
          <div className="flex items-center justify-between pb-3 border-b border-border/60 mb-4">
            <h2 className="text-xs font-bold uppercase tracking-wider text-foreground font-display">
              Risk Timeline
            </h2>
            <span className="text-[11px] text-muted-foreground">Workspace posture progression</span>
          </div>
          <div className="py-8 text-center text-muted-foreground flex flex-col items-center justify-center">
            <Clock className="w-8 h-8 mx-auto mb-2 opacity-30" />
            <p className="text-xs font-semibold text-foreground">No Historical Risk Trend</p>
            <p className="text-[11px] text-muted-foreground mt-0.5">
              Historical risk trend is not available for this workspace yet.
            </p>
          </div>
        </div>
      </div>

      {/* Two-Pane Workstation: Recent Pipeline Scans & Top Active Findings */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Scans Workstation */}
        <div className="bg-card border border-border rounded-card shadow-soft overflow-hidden flex flex-col">
          <div className="px-5 py-3.5 bg-sidebar border-b border-border flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4 text-primary" />
              <h2 className="text-xs font-bold uppercase tracking-wider text-foreground font-display">
                Recent Pipeline Scans
              </h2>
            </div>
            <Link to="/scans" className="text-xs text-primary hover:underline flex items-center gap-1">
              View all <ArrowRight className="w-3 h-3" />
            </Link>
          </div>

          <div className="p-0 flex-1">
            {loading ? (
              <div className="py-12 flex items-center justify-center">
                <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
              </div>
            ) : recentScans.length === 0 ? (
              <div className="py-12 px-4 text-center text-muted-foreground">
                <Clock className="w-8 h-8 mx-auto mb-2 opacity-30" />
                <p className="text-xs font-medium text-foreground">No analysis pipeline executions yet</p>
                <p className="text-[11px] mt-1 text-muted-foreground">
                  Select a project and launch a scan against an immutable snapshot.
                </p>
                <Link to="/projects">
                  <Button size="sm" variant="outline" className="mt-3 text-xs">
                    Browse Projects
                  </Button>
                </Link>
              </div>
            ) : (
              <table className="w-full text-xs text-left">
                <thead className="text-[10px] font-semibold uppercase text-muted-foreground bg-sidebar/50 border-b border-border">
                  <tr>
                    <th className="px-4 py-2.5">Scan Identifier</th>
                    <th className="px-4 py-2.5">Status</th>
                    <th className="px-4 py-2.5">Stage</th>
                    <th className="px-4 py-2.5 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/60">
                  {recentScans.map((scan) => {
                    const isCompleted = scan.status === 'completed';
                    const isRunning = scan.status === 'running' || scan.status === 'queued' || scan.status === 'preparing';
                    const isFailed = scan.status === 'failed' || scan.status === 'cancelled';
                    return (
                      <tr key={scan.id} className="hover:bg-hover transition-colors">
                        <td className="px-4 py-3">
                          <div className="font-mono font-medium text-foreground">
                            {scan.public_id || scan.id.slice(0, 12)}
                          </div>
                          <div className="text-[11px] text-muted-foreground truncate max-w-[180px]">
                            {scan.project_name || 'Project'}
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          <span
                            className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-mono font-medium uppercase ${
                              isCompleted
                                ? 'bg-severity-success/10 text-severity-success border border-severity-success/30'
                                : isRunning
                                ? 'bg-primary/10 text-primary border border-primary/30 animate-pulse'
                                : 'bg-destructive/10 text-destructive border border-destructive/30'
                            }`}
                          >
                            {isCompleted && <CheckCircle2 className="w-3 h-3" />}
                            {isRunning && <Loader2 className="w-3 h-3 animate-spin" />}
                            {isFailed && <XCircle className="w-3 h-3" />}
                            <span>{scan.status}</span>
                          </span>
                        </td>
                        <td className="px-4 py-3 text-muted-foreground font-mono text-[11px]">
                          {scan.current_stage || '—'}
                        </td>
                        <td className="px-4 py-3 text-right">
                          <Link to={getResultsUrl(scan.project_public_id || scan.project_id, scan)}>
                            <Button variant="ghost" size="sm" className="h-7 text-xs gap-1">
                              <span>Results</span>
                              <ArrowRight className="w-3 h-3" />
                            </Button>
                          </Link>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {/* Top Active Security Findings */}
        <div className="bg-card border border-border rounded-card shadow-soft overflow-hidden flex flex-col">
          <div className="px-5 py-3.5 bg-sidebar border-b border-border flex items-center justify-between">
            <div className="flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-brand-orange" />
              <h2 className="text-xs font-bold uppercase tracking-wider text-foreground font-display">
                Top Active Findings
              </h2>
            </div>
            <Link to="/findings" className="text-xs text-primary hover:underline flex items-center gap-1">
              View all <ArrowRight className="w-3 h-3" />
            </Link>
          </div>

          <div className="p-0 flex-1">
            {loading ? (
              <div className="py-12 flex items-center justify-center">
                <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
              </div>
            ) : topFindings.length === 0 ? (
              <div className="py-12 px-4 text-center text-muted-foreground">
                <CheckCircle2 className="w-8 h-8 mx-auto mb-2 text-severity-success/60" />
                <p className="text-xs font-medium text-foreground">Zero active security findings</p>
                <p className="text-[11px] mt-1 text-muted-foreground">
                  All triaged vulnerabilities are resolved, verified, or unscanned.
                </p>
              </div>
            ) : (
              <div className="divide-y divide-border/60">
                {topFindings.map((finding) => {
                  const sev = (finding.severity || 'medium').toLowerCase();
                  return (
                    <div
                      key={finding.id}
                      onClick={() => navigate(getResultsUrl(
                        finding.project_public_id || finding.project_id,
                        finding.latest_scan_public_id || finding.latest_scan_id || finding.scan_public_id || '',
                        finding.public_id || finding.id
                      ))}
                      className="px-4 py-3 hover:bg-hover transition-colors cursor-pointer flex items-center justify-between gap-3 group"
                    >
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <span
                            className={`px-1.5 py-0.2 rounded text-[10px] font-mono font-bold uppercase ${
                              sev === 'critical'
                                ? 'bg-destructive/15 text-destructive border border-destructive/30'
                                : sev === 'high'
                                ? 'bg-brand-orange/15 text-brand-orange border border-brand-orange/30'
                                : 'bg-brand-amber/15 text-brand-amber border border-brand-amber/30'
                            }`}
                          >
                            {sev}
                          </span>
                          {finding.cwe_id && (
                            <span className="font-mono text-[10px] text-muted-foreground bg-sidebar px-1.5 py-0.2 rounded border border-border">
                              {finding.cwe_id}
                            </span>
                          )}
                          <span className="font-mono text-[10px] text-muted-foreground truncate">
                            {finding.public_id || finding.id.slice(0, 10)}
                          </span>
                        </div>
                        <div className="text-xs font-medium text-foreground truncate group-hover:text-primary transition-colors">
                          {finding.title}
                        </div>
                        {finding.latest_file_path && (
                          <div className="text-[11px] font-mono text-muted-foreground truncate mt-0.5">
                            {finding.latest_file_path}:{finding.latest_line_number || 1}
                          </div>
                        )}
                      </div>
                      <Button variant="ghost" size="sm" className="h-7 w-7 p-0 shrink-0 text-muted-foreground group-hover:text-foreground">
                        <ArrowRight className="w-3.5 h-3.5" />
                      </Button>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Managed Projects Inventory Table */}
      <div className="bg-card border border-border rounded-card shadow-soft overflow-hidden">
        <div className="px-5 py-3.5 bg-sidebar border-b border-border flex items-center justify-between">
          <div>
            <h2 className="text-xs font-bold uppercase tracking-wider text-foreground font-display">
              Managed Codebases & Targets
            </h2>
            <p className="text-[11px] text-muted-foreground mt-0.5">
              Active projects scoped to this organization with source repository connectivity.
            </p>
          </div>
          <Link to="/projects" className="text-xs text-primary hover:underline flex items-center gap-1">
            Browse all ({metrics?.total_projects ?? projects.length}) <ArrowRight className="w-3 h-3" />
          </Link>
        </div>

        <div className="p-0">
          {loading ? (
            <div className="py-12 flex items-center justify-center">
              <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
            </div>
          ) : projects.length === 0 ? (
            <div className="py-12 px-4 text-center text-muted-foreground">
              <FolderOpen className="w-8 h-8 mx-auto mb-2 opacity-30" />
              <p className="text-xs font-medium text-foreground">No projects created yet</p>
              <p className="text-[11px] mt-1 text-muted-foreground max-w-sm mx-auto">
                Create your first project and attach repository source code to begin automated security audits.
              </p>
              <Link to="/projects/create">
                <Button className="mt-3 text-xs gap-1.5 btn-primary" size="sm">
                  <Plus className="w-3.5 h-3.5" />
                  <span>Create First Project</span>
                </Button>
              </Link>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="text-[10px] font-semibold text-muted-foreground uppercase bg-sidebar/50 border-b border-border">
                  <tr>
                    <th className="px-5 py-3">Project Target</th>
                    <th className="px-5 py-3">Primary Language</th>
                    <th className="px-5 py-3">Public Identifier</th>
                    <th className="px-5 py-3">Created</th>
                    <th className="px-5 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/60">
                  {projects.map((project) => (
                    <tr key={project.id} className="hover:bg-hover transition-colors">
                      <td className="px-5 py-3">
                        <Link
                          to={getProjectUrl(project)}
                          className="font-medium text-foreground hover:text-primary transition-colors flex items-center gap-2"
                        >
                          <FileCode2 className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
                          <span>{project.name}</span>
                        </Link>
                      </td>
                      <td className="px-5 py-3 text-muted-foreground">
                        <span className="font-mono text-[11px] bg-sidebar px-2 py-0.5 rounded border border-border/60">
                          {project.language || 'Multi-language'}
                        </span>
                      </td>
                      <td className="px-5 py-3 text-muted-foreground font-mono text-[11px]">
                        {project.public_id || project.id.slice(0, 12)}
                      </td>
                      <td className="px-5 py-3 text-muted-foreground font-mono text-[11px]">
                        {new Date(project.created_at).toLocaleDateString()}
                      </td>
                      <td className="px-5 py-3 text-right space-x-1">
                        <Link to={`${getProjectUrl(project)}/scan-config`}>
                          <Button variant="outline" size="sm" className="h-7 text-xs gap-1 border-border/80">
                            <Play className="w-3 h-3 text-primary" />
                            <span>Scan</span>
                          </Button>
                        </Link>
                        <Link to={getProjectUrl(project)}>
                          <Button variant="ghost" size="sm" className="h-7 text-xs gap-1">
                            <span>Open</span>
                            <ArrowRight className="w-3 h-3" />
                          </Button>
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
