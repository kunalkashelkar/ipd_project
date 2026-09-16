import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Blocks, Github, GitFork, Cloud, CheckCircle2, Clock, ExternalLink, ArrowRight, FolderGit2 } from 'lucide-react';
import { PageHeader, Card, CardHeader, CardTitle, CardDescription, CardContent, Badge, Button } from '../components/ui';
import toast from 'react-hot-toast';

export default function Integrations() {
  const navigate = useNavigate();

  const activeIntegrations = [
    {
      name: 'GitHub Repository Synchronization',
      category: 'Source Control (Active)',
      icon: <Github className="w-6 h-6 text-foreground" />,
      description: 'Ingest public or token-authenticated GitHub repositories. Supports automated branch discovery, commit SHA provenance tracking, and isolated archive extraction into immutable snapshots.',
      status: 'Active in Projects',
      statusBadge: 'default' as const,
      statusNote: 'GitHub repository connections are managed per project. You can attach a repository from any project workspace.',
      actionLabel: 'Connect in Projects',
      actionTo: '/projects',
    },
    {
      name: 'Git Remote & Clone Connector',
      category: 'Source Control (Active)',
      icon: <FolderGit2 className="w-6 h-6 text-primary" />,
      description: 'Standard Git repository synchronization over HTTPS. Hardened worker clone pipeline with Git hooks disabled, depth limits, branch tracking, and commit verification.',
      status: 'Active in Projects',
      statusBadge: 'default' as const,
      statusNote: 'Git repository connections are configured per project workspace. Navigate to a project to add a Git source.',
      actionLabel: 'Connect in Projects',
      actionTo: '/projects',
    },
    {
      name: 'S3 & MinIO Object Storage',
      category: 'Artifact Storage (Infrastructure)',
      icon: <Cloud className="w-6 h-6 text-cyan-400" />,
      description: 'High-performance S3-compatible object storage for immutable source archives, canonical files, normalized syntax representations, token streams, and manifests.',
      status: 'Active (MinIO)',
      statusBadge: 'secondary' as const,
      statusNote: 'MinIO object storage is active and healthy in development. Production supports AWS S3 or any S3-compatible cloud bucket.',
      actionLabel: 'Infrastructure Active',
      actionTo: null,
    },
  ];

  const plannedIntegrations = [
    {
      name: 'GitHub App / Organization OAuth',
      category: 'Enterprise VCS',
      icon: <Github className="w-6 h-6 text-muted-foreground" />,
      description: 'Organization-wide GitHub App installation for automated pull request inline checks, security gate comments, and webhook-driven incremental scans.',
      phase: 'Roadmap',
      statusNote: 'Organization-level GitHub App installation is planned for future enterprise CI/CD releases. Project-level GitHub repository ingestion is currently active.',
    },
    {
      name: 'GitLab & Bitbucket VCS Connectors',
      category: 'Source Control',
      icon: <GitFork className="w-6 h-6 text-muted-foreground" />,
      description: 'GitLab and Bitbucket OAuth authentication, merge request annotations, and repository synchronization.',
      phase: 'Roadmap',
      statusNote: 'GitLab and Bitbucket providers are planned for a subsequent integration phase. Git and GitHub are currently active.',
    },
    {
      name: 'CI/CD Webhook Dispatcher',
      category: 'Pipeline Automation',
      icon: <Blocks className="w-6 h-6 text-muted-foreground" />,
      description: 'Inbound webhooks to trigger asynchronous scanning pipelines from external build systems (Jenkins, CircleCI, Tekton).',
      phase: 'Phase 7',
      statusNote: 'Generic build system dispatchers and webhook integrations are scheduled for Phase 7.',
    },
  ];

  const handleAction = (item: typeof activeIntegrations[0]) => {
    if (item.actionTo) {
      navigate(item.actionTo);
    } else {
      toast(item.statusNote, {
        icon: 'ℹ️',
        duration: 4000,
      });
    }
  };

  const handlePlannedClick = (note: string) => {
    toast(note, {
      icon: 'ℹ️',
      duration: 4000,
    });
  };

  return (
    <div className="max-w-5xl mx-auto space-y-8 pb-12">
      <PageHeader
        title="Integrations & Connectors"
        description="Version control systems, artifact storage backends, and pipeline automation connectors."
      />

      {/* Active Integrations */}
      <div className="space-y-4">
        <div>
          <h2 className="text-sm font-semibold text-foreground tracking-tight">Active Platform Connectors</h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            These connectors are currently operational and available for attaching to project workspaces.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {activeIntegrations.map((item, index) => (
            <Card key={index} className="flex flex-col justify-between">
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                  <div className="p-2.5 rounded-xl bg-muted/60 flex items-center justify-center">
                    {item.icon}
                  </div>
                  <Badge variant={item.statusBadge} className="text-[10px]">
                    {item.status}
                  </Badge>
                </div>
                <CardTitle className="text-sm mt-3">{item.name}</CardTitle>
                <CardDescription className="text-xs leading-relaxed">
                  {item.description}
                </CardDescription>
              </CardHeader>
              <CardContent className="pt-0 border-t border-border/40 mt-3 pt-3 flex items-center justify-between">
                <span className="text-[11px] text-muted-foreground flex items-center gap-1.5 font-mono">
                  <Clock className="w-3 h-3" /> {item.category}
                </span>
                <Button
                  size="sm"
                  variant={item.actionTo ? 'default' : 'secondary'}
                  onClick={() => handleAction(item)}
                  className="text-xs gap-1"
                >
                  {item.actionLabel}
                  {item.actionTo && <ArrowRight className="w-3 h-3" />}
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>

      {/* Planned Roadmap Integrations */}
      <div className="space-y-4 pt-4 border-t border-border/50">
        <div>
          <h2 className="text-sm font-semibold text-foreground tracking-tight">Roadmap & Future Connectors</h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            Planned for subsequent development phases. Architecture permits seamless extension without schema changes.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {plannedIntegrations.map((item, index) => (
            <Card key={index} className="flex flex-col justify-between opacity-80 hover:opacity-100 transition-opacity">
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                  <div className="p-2.5 rounded-xl bg-muted/40 flex items-center justify-center">
                    {item.icon}
                  </div>
                  <Badge variant="outline" className="text-[10px] text-muted-foreground">
                    {item.phase}
                  </Badge>
                </div>
                <CardTitle className="text-sm mt-3 text-muted-foreground">{item.name}</CardTitle>
                <CardDescription className="text-xs leading-relaxed">
                  {item.description}
                </CardDescription>
              </CardHeader>
              <CardContent className="pt-0 border-t border-border/40 mt-3 pt-3 flex items-center justify-between">
                <span className="text-[11px] text-muted-foreground flex items-center gap-1.5 font-mono">
                  <Clock className="w-3 h-3" /> {item.category}
                </span>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => handlePlannedClick(item.statusNote)}
                  className="text-xs text-muted-foreground"
                >
                  Roadmap Info
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}
