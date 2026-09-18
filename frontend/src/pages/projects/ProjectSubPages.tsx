import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Activity, ShieldAlert, FileText, Settings as SettingsIcon, Plus } from 'lucide-react';
import { PageHeader, Breadcrumbs, EmptyState, Button, Card, CardContent, Spinner, ErrorState, Badge } from '../../components/ui';
import { projectService } from '../../services/projectService';
import { findingService } from '../../services/findingService';
import { Project, FindingListItem } from '../../types';

import { useLocation } from 'react-router-dom';
import { getProjectUrl, getScanConfigUrl, getResultsUrl } from '../../utils/routes';

function useCurrentProject(projectId?: string) {
  const [project, setProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    if (!projectId) return;
    setLoading(true);
    setError(null);
    projectService
      .getProject(projectId)
      .then((data) => {
        setProject(data);
        if (data.public_id && projectId === data.id && projectId !== data.public_id) {
          const canonicalPath = location.pathname.replace(`/projects/${projectId}`, `/projects/${data.public_id}`);
          navigate(`${canonicalPath}${location.search}${location.hash}`, { replace: true });
        }
      })
      .catch((err) => {
        setError(err.response?.data?.message || 'Failed to load project');
      })
      .finally(() => setLoading(false));
  }, [projectId, navigate, location.pathname, location.search, location.hash]);

  return { project, loading, error };
}

export function ProjectScans() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const { project, loading, error } = useCurrentProject(projectId);

  if (loading) return <div className="p-12"><Spinner size="lg" /></div>;
  if (error || !project) return <ErrorState message={error || 'Project not found'} onRetry={() => window.location.reload()} />;

  const projectUrl = getProjectUrl(project);
  const scanConfigUrl = getScanConfigUrl(project);

  return (
    <div className="space-y-6 pb-12">
      <PageHeader
        breadcrumbs={
          <Breadcrumbs
            items={[
              { label: 'Projects', to: '/projects' },
              { label: project.name, to: projectUrl },
              { label: 'Scans' },
            ]}
          />
        }
        title={`${project.name} — Scans`}
        description="Historical and running vulnerability analysis scans for this project."
        action={
          <Button size="sm" onClick={() => navigate(scanConfigUrl)}>
            <Plus className="w-4 h-4 mr-1.5" />
            New Scan
          </Button>
        }
      />
      <EmptyState
        icon={<Activity className="w-8 h-8 text-muted-foreground/60" />}
        title="No Scans Recorded"
        description="Run your first scan configuration to initialize preprocessing and security analysis."
        action={
          <Button onClick={() => navigate(scanConfigUrl)}>
            Configure Scan
          </Button>
        }
      />
    </div>
  );
}

export function ProjectFindings() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const { project, loading: projectLoading, error: projectError } = useCurrentProject(projectId);
  const [findings, setFindings] = useState<FindingListItem[]>([]);
  const [loadingFindings, setLoadingFindings] = useState(true);

  useEffect(() => {
    if (!projectId) return;
    setLoadingFindings(true);
    findingService
      .getProjectFindings(projectId)
      .then((data) => setFindings(data.items || []))
      .catch(() => setFindings([]))
      .finally(() => setLoadingFindings(false));
  }, [projectId]);

  if (projectLoading || loadingFindings) return <div className="p-12"><Spinner size="lg" /></div>;
  if (projectError || !project) return <ErrorState message={projectError || 'Project not found'} onRetry={() => window.location.reload()} />;

  const projectUrl = getProjectUrl(project);
  const scanConfigUrl = getScanConfigUrl(project);

  return (
    <div className="space-y-6 pb-12">
      <PageHeader
        breadcrumbs={
          <Breadcrumbs
            items={[
              { label: 'Projects', to: '/projects' },
              { label: project.name, to: projectUrl },
              { label: 'Findings' },
            ]}
          />
        }
        title={`${project.name} — Findings`}
        description="Persistent vulnerability findings and security classifications across project scans."
        action={
          <Button size="sm" onClick={() => navigate(scanConfigUrl)}>
            <Plus className="w-4 h-4 mr-1.5" />
            New Scan
          </Button>
        }
      />

      {findings.length === 0 ? (
        <EmptyState
          icon={<ShieldAlert className="w-8 h-8 text-muted-foreground/60" />}
          title="No Vulnerabilities Detected Yet"
          description="Findings will appear here once an automated vulnerability scan runs against an immutable snapshot."
          action={
            <Button onClick={() => navigate(scanConfigUrl)}>
              Start Scan
            </Button>
          }
        />
      ) : (
        <div className="space-y-3">
          {findings.map((f) => {
            const sev = f.severity.toLowerCase();
            const findingDisplayId = f.public_id || f.id;
            const findingResultsUrl = getResultsUrl(project, f.latest_scan_public_id || f.latest_scan_id, f.public_id || f.id);
            return (
              <Card
                key={f.id}
                className="p-4 hover:border-primary/50 transition-colors cursor-pointer"
                onClick={() => navigate(findingResultsUrl)}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="space-y-1.5">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span
                        className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded ${
                          sev === 'critical'
                            ? 'bg-red-500/20 text-red-400 border border-red-500/30'
                            : sev === 'high'
                            ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                            : sev === 'medium'
                            ? 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30'
                            : 'bg-blue-500/20 text-blue-400 border border-blue-500/30'
                        }`}
                      >
                        {f.severity}
                      </span>
                      <span className="text-xs font-mono text-muted-foreground bg-muted/40 px-1.5 py-0.5 rounded">
                        {findingDisplayId}
                      </span>
                      {f.cwe_id && (
                        <span className="text-xs font-mono text-muted-foreground bg-muted/40 px-1.5 py-0.5 rounded">
                          {f.cwe_id}
                        </span>
                      )}
                      <span className="text-xs font-mono px-2 py-0.5 rounded bg-muted/50 text-foreground">
                        {f.status}
                      </span>
                    </div>
                    <h4 className="text-sm font-semibold text-foreground">{f.title}</h4>
                    <p className="text-xs font-mono text-muted-foreground">
                      {f.latest_file_path || 'unknown file'}
                      {f.latest_line_number ? `:${f.latest_line_number}` : ''}
                    </p>
                  </div>
                  <div className="text-right shrink-0">
                    <span className="text-xs font-mono font-bold text-amber-400 block">
                      Risk {f.risk_score.toFixed(1)}
                    </span>
                    <span className="text-[11px] text-muted-foreground block">
                      Conf {Math.round(f.confidence * 100)}%
                    </span>
                    <span className="text-[10px] text-muted-foreground">
                      {f.occurrence_count} {f.occurrence_count === 1 ? 'scan' : 'scans'}
                    </span>
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}

export function ProjectReports() {
  const { projectId } = useParams<{ projectId: string }>();
  const { project, loading, error } = useCurrentProject(projectId);

  if (loading) return <div className="p-12"><Spinner size="lg" /></div>;
  if (error || !project) return <ErrorState message={error || 'Project not found'} onRetry={() => window.location.reload()} />;

  const projectUrl = getProjectUrl(project);

  return (
    <div className="space-y-6 pb-12">
      <PageHeader
        breadcrumbs={
          <Breadcrumbs
            items={[
              { label: 'Projects', to: '/projects' },
              { label: project.name, to: projectUrl },
              { label: 'Reports' },
            ]}
          />
        }
        title={`${project.name} — Security Reports`}
        description="Generated compliance and vulnerability assessment reports (PDF/JSON/CSV)."
      />
      <EmptyState
        icon={<FileText className="w-8 h-8 text-muted-foreground/60" />}
        title="No Reports Generated"
        description="Comprehensive reports can be exported once a vulnerability scan is completed."
      />
    </div>
  );
}

export function ProjectSettings() {
  const { projectId } = useParams<{ projectId: string }>();
  const { project, loading, error } = useCurrentProject(projectId);

  if (loading) return <div className="p-12"><Spinner size="lg" /></div>;
  if (error || !project) return <ErrorState message={error || 'Project not found'} onRetry={() => window.location.reload()} />;

  const projectUrl = getProjectUrl(project);

  return (
    <div className="max-w-4xl space-y-6 pb-12">
      <PageHeader
        breadcrumbs={
          <Breadcrumbs
            items={[
              { label: 'Projects', to: '/projects' },
              { label: project.name, to: projectUrl },
              { label: 'Settings' },
            ]}
          />
        }
        title={`${project.name} — Settings`}
        description="Manage project metadata, branch targets, and access permissions."
      />
      <Card>
        <CardContent className="p-6 space-y-4">
          <div className="space-y-1">
            <h4 className="text-sm font-semibold text-foreground">Project Name</h4>
            <p className="text-xs text-muted-foreground">{project.name}</p>
          </div>
          <div className="space-y-1 border-t border-border pt-3">
            <h4 className="text-sm font-semibold text-foreground">Default Branch</h4>
            <p className="text-xs text-muted-foreground">{project.default_branch || 'main'}</p>
          </div>
          <div className="space-y-1 border-t border-border pt-3">
            <h4 className="text-sm font-semibold text-foreground">Status</h4>
            <p className="text-xs text-muted-foreground">{project.is_archived ? 'Archived' : 'Active'}</p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
