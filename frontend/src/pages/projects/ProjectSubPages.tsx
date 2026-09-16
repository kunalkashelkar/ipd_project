import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Activity, ShieldAlert, FileText, Settings as SettingsIcon, Plus } from 'lucide-react';
import { PageHeader, Breadcrumbs, EmptyState, Button, Card, CardContent, Spinner, ErrorState } from '../../components/ui';
import { projectService } from '../../services/projectService';
import { Project } from '../../types';

function useCurrentProject(projectId?: string) {
  const [project, setProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!projectId) return;
    setLoading(true);
    setError(null);
    projectService
      .getProject(projectId)
      .then(setProject)
      .catch((err) => {
        setError(err.response?.data?.message || 'Failed to load project');
      })
      .finally(() => setLoading(false));
  }, [projectId]);

  return { project, loading, error };
}

export function ProjectScans() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const { project, loading, error } = useCurrentProject(projectId);

  if (loading) return <div className="p-12"><Spinner size="lg" /></div>;
  if (error || !project) return <ErrorState message={error || 'Project not found'} onRetry={() => window.location.reload()} />;

  return (
    <div className="space-y-6 pb-12">
      <PageHeader
        breadcrumbs={
          <Breadcrumbs
            items={[
              { label: 'Projects', to: '/projects' },
              { label: project.name, to: `/projects/${project.id}` },
              { label: 'Scans' },
            ]}
          />
        }
        title={`${project.name} — Scans`}
        description="Historical and running vulnerability analysis scans for this project."
        action={
          <Button size="sm" onClick={() => navigate(`/projects/${project.id}/scan-config`)}>
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
          <Button onClick={() => navigate(`/projects/${project.id}/scan-config`)}>
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
  const { project, loading, error } = useCurrentProject(projectId);

  if (loading) return <div className="p-12"><Spinner size="lg" /></div>;
  if (error || !project) return <ErrorState message={error || 'Project not found'} onRetry={() => window.location.reload()} />;

  return (
    <div className="space-y-6 pb-12">
      <PageHeader
        breadcrumbs={
          <Breadcrumbs
            items={[
              { label: 'Projects', to: '/projects' },
              { label: project.name, to: `/projects/${project.id}` },
              { label: 'Findings' },
            ]}
          />
        }
        title={`${project.name} — Findings`}
        description="Detailed vulnerability findings, CWE attributions, and remediation patches."
      />
      <EmptyState
        icon={<ShieldAlert className="w-8 h-8 text-muted-foreground/60" />}
        title="No Vulnerabilities Detected Yet"
        description="Findings will appear here after automated graph extraction and ML classification in Phases 4 & 5."
        action={
          <Button onClick={() => navigate(`/projects/${project.id}/scan-config`)}>
            Start Scan
          </Button>
        }
      />
    </div>
  );
}

export function ProjectReports() {
  const { projectId } = useParams<{ projectId: string }>();
  const { project, loading, error } = useCurrentProject(projectId);

  if (loading) return <div className="p-12"><Spinner size="lg" /></div>;
  if (error || !project) return <ErrorState message={error || 'Project not found'} onRetry={() => window.location.reload()} />;

  return (
    <div className="space-y-6 pb-12">
      <PageHeader
        breadcrumbs={
          <Breadcrumbs
            items={[
              { label: 'Projects', to: '/projects' },
              { label: project.name, to: `/projects/${project.id}` },
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

  return (
    <div className="max-w-4xl space-y-6 pb-12">
      <PageHeader
        breadcrumbs={
          <Breadcrumbs
            items={[
              { label: 'Projects', to: '/projects' },
              { label: project.name, to: `/projects/${project.id}` },
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
