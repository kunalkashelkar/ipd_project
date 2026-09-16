// ============================================================
// ProjectDetail.tsx — Phase 3 Source Provenance & Management
// ============================================================

import React, { useEffect, useState, useRef } from 'react';
import { useParams, Link, useSearchParams } from 'react-router-dom';
import {
  Play,
  FileCode2,
  Layers,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Loader2,
  Upload as UploadIcon,
  Trash2,
  FileText,
  GitBranch,
  GitCommit,
  ShieldCheck,
  ArrowRight,
  ShieldAlert,
  FolderGit2,
  Github,
  RefreshCw,
  Archive,
  ExternalLink,
  Plus,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';
import { projectService } from '../../services/projectService';
import { snapshotService } from '../../services/snapshotService';
import { repositoryService } from '../../services/repositoryService';
import { scanService } from '../../services/scanService';
import { Project, SourceSnapshot, Repository, Scan } from '../../types';
import toast from 'react-hot-toast';

export default function ProjectDetail() {
  const params = useParams<{ id?: string; projectId?: string }>();
  const id = params.projectId || params.id;

  const [project, setProject] = useState<Project | null>(null);
  const [snapshots, setSnapshots] = useState<SourceSnapshot[]>([]);
  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [scans, setScans] = useState<Scan[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchParams, setSearchParams] = useSearchParams();
  const tabParam = searchParams.get('tab') as any;
  const validTabs = ['overview', 'snapshots', 'repositories', 'scans', 'findings', 'reports'];
  const [activeTab, setActiveTab] = useState<
    'overview' | 'snapshots' | 'repositories' | 'scans' | 'findings' | 'reports'
  >(validTabs.includes(tabParam) ? tabParam : 'overview');

  useEffect(() => {
    if (tabParam && validTabs.includes(tabParam) && tabParam !== activeTab) {
      setActiveTab(tabParam);
    }
  }, [tabParam]);

  const handleTabChange = (tabId: string) => {
    setActiveTab(tabId as any);
    setSearchParams({ tab: tabId });
  };

  const [syncingRepoId, setSyncingRepoId] = useState<string | null>(null);
  const [archiving, setArchiving] = useState(false);

  useEffect(() => {
    if (!id) return;
    async function load() {
      setLoading(true);
      try {
        const [proj, snapsData, reposData, scansData] = await Promise.allSettled([
          projectService.getProject(id!),
          snapshotService.listSnapshots(id!, { page_size: 50 }),
          repositoryService.listRepositories(id!),
          scanService.listScans({ project_id: id!, page_size: 50 }),
        ]);

        if (proj.status === 'fulfilled') setProject(proj.value);
        if (snapsData.status === 'fulfilled') setSnapshots(snapsData.value.items);
        if (reposData.status === 'fulfilled') setRepositories(reposData.value);
        if (scansData.status === 'fulfilled') setScans(scansData.value.items);
      } catch {
        // Handled
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [id]);

  const handleSyncRepository = async (repoId: string) => {
    if (!id) return;
    setSyncingRepoId(repoId);
    try {
      await repositoryService.syncRepository(id, repoId);
      toast.success('Repository sync initiated in background!');
      // Refresh snapshots and repositories after initiating
      const [snaps, repos] = await Promise.all([
        snapshotService.listSnapshots(id, { page_size: 50 }),
        repositoryService.listRepositories(id),
      ]);
      setSnapshots(snaps.items);
      setRepositories(repos);
    } catch (err: any) {
      toast.error(err?.response?.data?.message || 'Sync failed');
    } finally {
      setSyncingRepoId(null);
    }
  };

  const handleDisconnectRepository = async (repoId: string) => {
    if (!id) return;
    if (!window.confirm('Disconnect repository? Existing historical snapshots and scans will be preserved.')) {
      return;
    }

    try {
      await repositoryService.disconnectRepository(id, repoId);
      toast.success('Repository disconnected.');
      const repos = await repositoryService.listRepositories(id);
      setRepositories(repos);
    } catch (err: any) {
      toast.error(err?.response?.data?.message || 'Failed to disconnect');
    }
  };

  const handleToggleArchive = async () => {
    if (!id || !project) return;
    setArchiving(true);
    try {
      const res = await projectService.archiveProject(id);
      setProject({ ...project, is_archived: res.is_archived });
      toast.success(res.is_archived ? 'Project archived' : 'Project unarchived');
    } catch (err: any) {
      toast.error(err?.response?.data?.message || 'Archive operation failed');
    } finally {
      setArchiving(false);
    }
  };

  if (loading) {
    return (
      <div className="h-64 flex flex-col items-center justify-center gap-2">
        <Loader2 className="w-6 h-6 animate-spin text-primary" />
        <span className="text-xs text-muted-foreground">Loading security project...</span>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="p-8 text-center space-y-3">
        <AlertTriangle className="w-8 h-8 mx-auto text-destructive" />
        <h2 className="text-base font-semibold text-foreground">Project Not Found</h2>
        <p className="text-xs text-muted-foreground">The requested project does not exist in this organization.</p>
        <Link to="/projects">
          <Button variant="outline" size="sm" className="mt-2 text-xs">
            Back to Projects
          </Button>
        </Link>
      </div>
    );
  }

  const latestScan = scans.length > 0 ? scans[0] : null;
  const readySnapshots = snapshots.filter((s) => s.status === 'ready');

  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-12">
      {/* Header section */}
      <div className="flex flex-col md:flex-row md:items-start justify-between gap-4 pb-4 border-b border-border/50">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-xl font-bold tracking-tight text-foreground">{project.name}</h1>
            <Badge variant={project.is_archived ? 'secondary' : 'outline'} className="text-[10px]">
              {project.is_archived ? 'Archived' : 'Active'}
            </Badge>
          </div>
          <div className="flex flex-wrap items-center gap-4 text-xs text-muted-foreground mt-2">
            <span className="flex items-center gap-1 font-mono">
              <FileCode2 className="w-3.5 h-3.5 text-primary" /> {project.language || 'Multi-Language'}
            </span>
            <span className="flex items-center gap-1 font-mono">
              <GitBranch className="w-3.5 h-3.5 text-muted-foreground" /> {project.default_branch || 'main'}
            </span>
            <span className="flex items-center gap-1">
              <Clock className="w-3.5 h-3.5 text-muted-foreground" /> Created {new Date(project.created_at).toLocaleDateString()}
            </span>
          </div>
          {project.description && (
            <p className="text-xs text-muted-foreground mt-2 max-w-2xl leading-relaxed">
              {project.description}
            </p>
          )}
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <Link to={`/projects/${project.id}/repository`}>
            <Button size="sm" className="text-xs gap-1.5 bg-primary text-primary-foreground hover:bg-primary/90">
              <Plus className="w-3.5 h-3.5" />
              Connect Repository
            </Button>
          </Link>

          <Button
            variant="ghost"
            size="sm"
            className="text-xs gap-1.5 text-muted-foreground"
            disabled={archiving}
            onClick={handleToggleArchive}
          >
            <Archive className="w-3.5 h-3.5" />
            {project.is_archived ? 'Unarchive' : 'Archive'}
          </Button>

          {readySnapshots.length > 0 && (
            <Link to={`/projects/${project.id}/scan-config`}>
              <Button size="sm" variant="outline" className="text-xs gap-1.5">
                <Play className="w-3.5 h-3.5" />
                Run Security Scan
              </Button>
            </Link>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-border">
        <div className="flex gap-6 text-xs overflow-x-auto scrollbar-none">
          {[
            { id: 'overview', label: 'Overview' },
            { id: 'snapshots', label: `Snapshots (${snapshots.length})` },
            { id: 'repositories', label: `Repositories (${repositories.length})` },
            { id: 'scans', label: `Scans (${scans.length})` },
            { id: 'findings', label: 'Findings' },
            { id: 'reports', label: 'Reports' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => handleTabChange(tab.id)}
              className={`pb-2.5 font-medium transition-colors border-b-2 whitespace-nowrap ${
                activeTab === tab.id
                  ? 'border-primary text-foreground font-semibold'
                  : 'border-transparent text-muted-foreground hover:text-foreground'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* TAB 1: Overview */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          {/* Quick Metrics */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <Card>
              <CardContent className="p-4">
                <span className="text-[11px] font-medium text-muted-foreground block">Source Snapshots</span>
                <span className="text-xl font-bold text-foreground mt-1 block">{snapshots.length}</span>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <span className="text-[11px] font-medium text-muted-foreground block">Connected Repos</span>
                <span className="text-xl font-bold text-foreground mt-1 block">{repositories.length}</span>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <span className="text-[11px] font-medium text-muted-foreground block">Completed Scans</span>
                <span className="text-xl font-bold text-foreground mt-1 block">
                  {scans.filter((s) => s.status === 'completed').length}
                </span>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <span className="text-[11px] font-medium text-muted-foreground block">Latest Scan Status</span>
                <span className="text-xl font-bold text-foreground mt-1 block capitalize text-sm">
                  {latestScan ? latestScan.status : 'None'}
                </span>
              </CardContent>
            </Card>
          </div>

          {/* Repositories & Ingested Sources Section */}
          <Card>
            <CardHeader className="pb-3 flex flex-row items-center justify-between space-y-0">
              <div>
                <CardTitle className="text-sm">Repositories & Ingested Sources</CardTitle>
                <CardDescription>
                  Immutable provenance boundary: Every security scan references a deterministic, tamper-proof source snapshot.
                </CardDescription>
              </div>
              <Link to={`/projects/${project.id}/repository`}>
                <Button size="sm" className="text-xs gap-1.5 bg-primary text-primary-foreground hover:bg-primary/90">
                  <Plus className="w-3.5 h-3.5" /> Connect Repository
                </Button>
              </Link>
            </CardHeader>
            <CardContent className="space-y-4">
              {repositories.length === 0 && snapshots.length === 0 ? (
                <div className="text-center py-8 px-4 border border-dashed border-border rounded-lg bg-muted/20">
                  <FolderGit2 className="w-8 h-8 mx-auto mb-2 text-muted-foreground opacity-60" />
                  <p className="text-xs font-semibold text-foreground">No source code connected to this project</p>
                  <p className="text-[11px] text-muted-foreground mt-0.5 max-w-md mx-auto">
                    Connect a GitHub or Git repository, or upload a source archive to create an immutable snapshot for vulnerability scanning.
                  </p>
                  <Link to={`/projects/${project.id}/repository`}>
                    <Button size="sm" variant="outline" className="mt-3 text-xs gap-1.5">
                      <Plus className="w-3.5 h-3.5" /> Connect Source Code
                    </Button>
                  </Link>
                </div>
              ) : (
                <div className="space-y-4">
                  {/* Connected Repositories preview */}
                  {repositories.length > 0 && (
                    <div className="border border-border rounded-lg overflow-hidden">
                      <div className="px-4 py-2 bg-muted/30 border-b border-border flex items-center justify-between text-xs font-medium text-muted-foreground">
                        <span className="flex items-center gap-1.5">
                          <FolderGit2 className="w-3.5 h-3.5 text-primary" /> Connected Repositories ({repositories.length})
                        </span>
                        <button
                          onClick={() => handleTabChange('repositories')}
                          className="text-[11px] text-primary hover:underline"
                        >
                          Manage All
                        </button>
                      </div>
                      <div className="divide-y divide-border">
                        {repositories.slice(0, 3).map((repo) => (
                          <div key={repo.id} className="p-3 px-4 flex items-center justify-between gap-4 text-xs">
                            <div className="flex items-center gap-2.5 min-w-0">
                              {repo.provider === 'github' ? (
                                <Github className="w-4 h-4 text-foreground shrink-0" />
                              ) : (
                                <FolderGit2 className="w-4 h-4 text-primary shrink-0" />
                              )}
                              <div className="min-w-0">
                                <div className="font-semibold text-foreground truncate">{repo.display_name}</div>
                                <div className="text-[10px] text-muted-foreground font-mono truncate">{repo.repo_url}</div>
                              </div>
                            </div>

                            <div className="flex items-center gap-3 shrink-0">
                              <span className="font-mono text-[11px] text-muted-foreground flex items-center gap-1">
                                <GitBranch className="w-3 h-3" /> {repo.selected_branch || repo.default_branch}
                              </span>
                              <Badge
                                variant={
                                  repo.status === 'ready'
                                    ? 'safe'
                                    : repo.status === 'disconnected'
                                    ? 'secondary'
                                    : repo.status === 'error'
                                    ? 'destructive'
                                    : 'warning'
                                }
                                className="text-[10px] capitalize"
                              >
                                {repo.status}
                              </Badge>
                              <Button
                                size="sm"
                                variant="ghost"
                                className="h-7 text-xs gap-1"
                                disabled={syncingRepoId === repo.id}
                                onClick={() => handleSyncRepository(repo.id)}
                              >
                                {syncingRepoId === repo.id ? (
                                  <Loader2 className="w-3 h-3 animate-spin" />
                                ) : (
                                  <RefreshCw className="w-3 h-3" />
                                )}
                                Sync
                              </Button>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Recent Snapshots preview */}
                  {snapshots.length > 0 && (
                    <div className="border border-border rounded-lg overflow-hidden">
                      <div className="px-4 py-2 bg-muted/30 border-b border-border flex items-center justify-between text-xs font-medium text-muted-foreground">
                        <span className="flex items-center gap-1.5">
                          <Layers className="w-3.5 h-3.5 text-primary" /> Recent Source Snapshots ({snapshots.length})
                        </span>
                        <button
                          onClick={() => handleTabChange('snapshots')}
                          className="text-[11px] text-primary hover:underline"
                        >
                          View All Snapshots
                        </button>
                      </div>
                      <div className="divide-y divide-border">
                        {snapshots.slice(0, 3).map((snap) => (
                          <div key={snap.id} className="p-3 px-4 flex items-center justify-between gap-4 text-xs">
                            <div className="flex items-center gap-2.5 min-w-0">
                              <Layers className="w-4 h-4 text-primary shrink-0" />
                              <div className="min-w-0">
                                <Link
                                  to={`/projects/${project.id}/snapshots/${snap.id}`}
                                  className="font-mono text-xs font-medium text-primary hover:underline"
                                >
                                  {snap.id.slice(0, 8)}...
                                </Link>
                                <div className="text-[10px] text-muted-foreground flex items-center gap-2 mt-0.5">
                                  <span className="uppercase font-mono">{snap.source_type}</span>
                                  <span>•</span>
                                  <span>{snap.file_count} files</span>
                                  {snap.commit_sha && (
                                    <>
                                      <span>•</span>
                                      <span className="font-mono">{snap.commit_sha.slice(0, 7)}</span>
                                    </>
                                  )}
                                </div>
                              </div>
                            </div>

                            <div className="flex items-center gap-2 shrink-0">
                              <Badge
                                variant={
                                  snap.status === 'ready'
                                    ? 'safe'
                                    : snap.status === 'failed'
                                    ? 'destructive'
                                    : 'warning'
                                }
                                className="text-[10px] capitalize"
                              >
                                {snap.status}
                              </Badge>
                              <Link to={`/projects/${project.id}/snapshots/${snap.id}`}>
                                <Button size="sm" variant="ghost" className="h-7 text-xs">
                                  Inspect
                                </Button>
                              </Link>
                              {snap.status === 'ready' && (
                                <Link to={`/projects/${project.id}/scan-config`}>
                                  <Button size="sm" variant="outline" className="h-7 text-xs gap-1">
                                    <Play className="w-3 h-3" /> Scan
                                  </Button>
                                </Link>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* TAB 2: Source Snapshots */}
      {activeTab === 'snapshots' && (
        <Card>
          <CardHeader className="pb-3 flex flex-row items-center justify-between space-y-0">
            <div>
              <CardTitle className="text-sm">Immutable Source Snapshots</CardTitle>
              <CardDescription>
                Canonical source states stored in object storage with deterministic metadata.
              </CardDescription>
            </div>
            <Link to={`/projects/${project.id}/repository`}>
              <Button size="sm" variant="outline" className="text-xs gap-1.5">
                <Plus className="w-3.5 h-3.5" /> New Snapshot
              </Button>
            </Link>
          </CardHeader>
          <CardContent className="p-0">
            {snapshots.length === 0 ? (
              <div className="text-center py-12 px-4 text-muted-foreground">
                <Layers className="w-8 h-8 mx-auto mb-2 opacity-40" />
                <p className="text-sm font-medium text-foreground">No source snapshots available</p>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Upload an archive, individual files, or connect a Git repository to generate a snapshot.
                </p>
                <Link to={`/projects/${project.id}/repository`}>
                  <Button variant="outline" size="sm" className="mt-4 text-xs gap-1.5">
                    <Plus className="w-3.5 h-3.5" /> Connect Source
                  </Button>
                </Link>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-xs text-left">
                  <thead className="text-[11px] font-semibold text-muted-foreground uppercase bg-muted/30 border-y border-border">
                    <tr>
                      <th className="px-5 py-3">Snapshot ID</th>
                      <th className="px-5 py-3">Source Type</th>
                      <th className="px-5 py-3">Status</th>
                      <th className="px-5 py-3">Commit</th>
                      <th className="px-5 py-3 text-right">Files</th>
                      <th className="px-5 py-3">Languages</th>
                      <th className="px-5 py-3">Created</th>
                      <th className="px-5 py-3 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/60">
                    {snapshots.map((snap) => (
                      <tr key={snap.id} className="hover:bg-hover transition-colors">
                        <td className="px-5 py-3 font-mono text-foreground font-medium">
                          <Link
                            to={`/projects/${project.id}/snapshots/${snap.id}`}
                            className="hover:underline text-primary"
                          >
                            {snap.id.slice(0, 8)}...
                          </Link>
                        </td>
                        <td className="px-5 py-3">
                          <Badge variant="outline" className="text-[10px] uppercase font-mono">
                            {snap.source_type}
                          </Badge>
                        </td>
                        <td className="px-5 py-3">
                          <Badge
                            variant={
                              snap.status === 'ready'
                                ? 'safe'
                                : snap.status === 'failed'
                                ? 'destructive'
                                : 'warning'
                            }
                            className="text-[10px] capitalize"
                          >
                            {snap.status}
                          </Badge>
                        </td>
                        <td className="px-5 py-3 font-mono text-muted-foreground">
                          {snap.commit_sha ? (
                            <span className="flex items-center gap-1">
                              <GitCommit className="w-3 h-3 text-primary" />
                              {snap.commit_sha.slice(0, 8)}
                            </span>
                          ) : (
                            '—'
                          )}
                        </td>
                        <td className="px-5 py-3 font-mono text-right text-foreground">
                          {snap.file_count}
                        </td>
                        <td className="px-5 py-3">
                          <div className="flex flex-wrap gap-1 max-w-[180px]">
                            {Object.keys(snap.detected_languages || {}).length > 0 ? (
                              Object.keys(snap.detected_languages).map((l) => (
                                <span
                                  key={l}
                                  className="px-1 py-0.5 rounded text-[9px] font-mono bg-muted text-muted-foreground"
                                >
                                  {l}
                                </span>
                              ))
                            ) : (
                              <span className="text-[10px] text-muted-foreground">—</span>
                            )}
                          </div>
                        </td>
                        <td className="px-5 py-3 text-muted-foreground font-mono">
                          {new Date(snap.created_at).toLocaleString()}
                        </td>
                        <td className="px-5 py-3 text-right">
                          <div className="flex items-center justify-end gap-2">
                            <Link to={`/projects/${project.id}/snapshots/${snap.id}`}>
                              <Button variant="ghost" size="sm" className="h-7 text-xs">
                                View
                              </Button>
                            </Link>
                            {snap.status === 'ready' && (
                              <Link to={`/projects/${project.id}/scan-config`}>
                                <Button size="sm" variant="outline" className="h-7 text-xs gap-1">
                                  <Play className="w-3 h-3" /> Scan
                                </Button>
                              </Link>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* TAB 3: Repositories */}
      {activeTab === 'repositories' && (
        <Card>
          <CardHeader className="pb-3 flex flex-row items-center justify-between space-y-0">
            <div>
              <CardTitle className="text-sm">Connected Git & GitHub Repositories</CardTitle>
              <CardDescription>
                Remote repositories synchronized with automated commit tracking and branch selection.
              </CardDescription>
            </div>
            <Link to={`/projects/${project.id}/repository`}>
              <Button size="sm" variant="outline" className="text-xs gap-1.5">
                <Plus className="w-3.5 h-3.5" /> Connect Repository
              </Button>
            </Link>
          </CardHeader>
          <CardContent className="p-0">
            {repositories.length === 0 ? (
              <div className="text-center py-12 px-4 text-muted-foreground">
                <FolderGit2 className="w-8 h-8 mx-auto mb-2 opacity-40" />
                <p className="text-sm font-medium text-foreground">No repositories connected</p>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Connect a Git or GitHub repository to sync code commits into immutable snapshots.
                </p>
                <Link to={`/projects/${project.id}/repository`}>
                  <Button variant="outline" size="sm" className="mt-4 text-xs gap-1.5">
                    <Plus className="w-3.5 h-3.5" /> Connect Repository
                  </Button>
                </Link>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-xs text-left">
                  <thead className="text-[11px] font-semibold text-muted-foreground uppercase bg-muted/30 border-y border-border">
                    <tr>
                      <th className="px-5 py-3">Repository</th>
                      <th className="px-5 py-3">Provider</th>
                      <th className="px-5 py-3">Selected Branch</th>
                      <th className="px-5 py-3">Current Commit</th>
                      <th className="px-5 py-3">Status</th>
                      <th className="px-5 py-3">Last Synced</th>
                      <th className="px-5 py-3 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/60">
                    {repositories.map((repo) => (
                      <tr key={repo.id} className="hover:bg-hover transition-colors">
                        <td className="px-5 py-3 font-medium text-foreground">
                          <div className="flex items-center gap-2">
                            {repo.provider === 'github' ? (
                              <Github className="w-3.5 h-3.5 text-foreground shrink-0" />
                            ) : (
                              <FolderGit2 className="w-3.5 h-3.5 text-primary shrink-0" />
                            )}
                            <div>
                              <span>{repo.display_name}</span>
                              <span className="block text-[10px] text-muted-foreground font-mono truncate max-w-[200px]">
                                {repo.repo_url}
                              </span>
                            </div>
                          </div>
                        </td>
                        <td className="px-5 py-3 font-mono uppercase text-[10px]">
                          {repo.provider}
                        </td>
                        <td className="px-5 py-3 font-mono text-muted-foreground">
                          <span className="flex items-center gap-1">
                            <GitBranch className="w-3 h-3 text-muted-foreground" />
                            {repo.selected_branch}
                          </span>
                        </td>
                        <td className="px-5 py-3 font-mono text-muted-foreground">
                          {repo.current_commit_sha ? (
                            <span className="flex items-center gap-1">
                              <GitCommit className="w-3 h-3 text-primary" />
                              {repo.current_commit_sha.slice(0, 8)}
                            </span>
                          ) : (
                            'Pending sync'
                          )}
                        </td>
                        <td className="px-5 py-3">
                          <Badge
                            variant={
                              repo.status === 'ready'
                                ? 'safe'
                                : repo.status === 'disconnected'
                                ? 'secondary'
                                : repo.status === 'error'
                                ? 'destructive'
                                : 'warning'
                            }
                            className="text-[10px] capitalize"
                          >
                            {repo.status}
                          </Badge>
                        </td>
                        <td className="px-5 py-3 font-mono text-muted-foreground">
                          {repo.last_synced_at ? new Date(repo.last_synced_at).toLocaleString() : 'Never'}
                        </td>
                        <td className="px-5 py-3 text-right">
                          <div className="flex items-center justify-end gap-2">
                            {repo.status !== 'disconnected' && (
                              <Button
                                variant="outline"
                                size="sm"
                                className="h-7 text-xs gap-1"
                                disabled={syncingRepoId === repo.id}
                                onClick={() => handleSyncRepository(repo.id)}
                              >
                                <RefreshCw
                                  className={`w-3 h-3 ${syncingRepoId === repo.id ? 'animate-spin' : ''}`}
                                />
                                Sync
                              </Button>
                            )}
                            {repo.status !== 'disconnected' && (
                              <Button
                                variant="ghost"
                                size="sm"
                                className="h-7 text-xs text-destructive hover:bg-destructive/10"
                                onClick={() => handleDisconnectRepository(repo.id)}
                              >
                                Disconnect
                              </Button>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* TAB 4: Scans */}
      {activeTab === 'scans' && (
        <Card>
          <CardHeader className="pb-3 flex flex-row items-center justify-between space-y-0">
            <div>
              <CardTitle className="text-sm">Scan Executions</CardTitle>
              <CardDescription>Historical and running vulnerability analysis pipelines for this project.</CardDescription>
            </div>
            {readySnapshots.length > 0 && (
              <Link to={`/projects/${project.id}/scan-config`}>
                <Button size="sm" className="text-xs gap-1.5">
                  <Play className="w-3.5 h-3.5" /> Start Scan
                </Button>
              </Link>
            )}
          </CardHeader>
          <CardContent className="p-0">
            {scans.length === 0 ? (
              <div className="text-center py-12 px-4 text-muted-foreground">
                <Layers className="w-8 h-8 mx-auto mb-2 opacity-40" />
                <p className="text-sm font-medium text-foreground">No scans recorded yet</p>
                <p className="text-xs text-muted-foreground mt-0.5">
                  {readySnapshots.length > 0
                    ? 'Configure and trigger your first security scan.'
                    : 'Ingest a source snapshot before triggering a scan.'}
                </p>
                {readySnapshots.length > 0 && (
                  <Link to={`/projects/${project.id}/scan-config`}>
                    <Button size="sm" className="mt-4 text-xs gap-1.5">
                      <Play className="w-3.5 h-3.5" /> Start First Scan
                    </Button>
                  </Link>
                )}
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-xs text-left">
                  <thead className="text-[11px] font-semibold text-muted-foreground uppercase bg-muted/30 border-y border-border">
                    <tr>
                      <th className="px-5 py-3">Scan ID</th>
                      <th className="px-5 py-3">Snapshot</th>
                      <th className="px-5 py-3">Status</th>
                      <th className="px-5 py-3">Stage</th>
                      <th className="px-5 py-3">Progress</th>
                      <th className="px-5 py-3">Started</th>
                      <th className="px-5 py-3 text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/60">
                    {scans.map((scan) => (
                      <tr key={scan.id} className="hover:bg-hover transition-colors">
                        <td className="px-5 py-3 font-mono text-foreground">{scan.id.slice(0, 8)}...</td>
                        <td className="px-5 py-3 font-mono text-muted-foreground">
                          {scan.source_snapshot_id ? (
                            <Link
                              to={`/projects/${project.id}/snapshots/${scan.source_snapshot_id}`}
                              className="hover:underline text-primary"
                            >
                              {scan.source_snapshot_id.slice(0, 8)}...
                            </Link>
                          ) : (
                            'Legacy upload'
                          )}
                        </td>
                        <td className="px-5 py-3">
                          <Badge
                            variant={
                              scan.status === 'completed' ? 'safe' :
                              scan.status === 'failed' ? 'destructive' :
                              'warning'
                            }
                            className="text-[10px]"
                          >
                            {scan.status}
                          </Badge>
                        </td>
                        <td className="px-5 py-3 text-muted-foreground">{scan.current_stage || scan.status}</td>
                        <td className="px-5 py-3 text-muted-foreground font-mono">{scan.progress}%</td>
                        <td className="px-5 py-3 text-muted-foreground font-mono">
                          {new Date(scan.created_at).toLocaleString()}
                        </td>
                        <td className="px-5 py-3 text-right">
                          {scan.status === 'completed' ? (
                            <Link to={`/projects/${project.id}/results?scan_id=${scan.id}`}>
                              <Button variant="ghost" size="sm" className="h-7 text-xs gap-1">
                                View Results <ArrowRight className="w-3 h-3" />
                              </Button>
                            </Link>
                          ) : (
                            <Link to={`/projects/${project.id}/scan-progress?scan_id=${scan.id}`}>
                              <Button variant="ghost" size="sm" className="h-7 text-xs gap-1">
                                Progress <ArrowRight className="w-3 h-3" />
                              </Button>
                            </Link>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* TAB 5: Findings */}
      {activeTab === 'findings' && (
        <Card>
          <CardContent className="p-8 text-center text-muted-foreground">
            <ShieldAlert className="w-8 h-8 mx-auto mb-2 opacity-40 text-muted-foreground" />
            <p className="text-sm font-semibold text-foreground">Project Vulnerability Findings</p>
            <p className="text-xs text-muted-foreground mt-1 max-w-md mx-auto">
              Vulnerabilities are evaluated per scan execution.
              {scans.some((s) => s.status === 'completed')
                ? ' Completed scans have findings available in the analysis workspace.'
                : ' Run a security scan on this project to view vulnerability attributions and patches.'}
            </p>
            {latestScan && latestScan.status === 'completed' && (
              <Link to={`/projects/${project.id}/results?scan_id=${latestScan.id}`}>
                <Button size="sm" variant="outline" className="mt-4 text-xs gap-1.5">
                  Open Latest Scan Workspace <ArrowRight className="w-3.5 h-3.5" />
                </Button>
              </Link>
            )}
          </CardContent>
        </Card>
      )}

      {/* TAB 6: Reports */}
      {activeTab === 'reports' && (
        <Card>
          <CardContent className="p-8 text-center text-muted-foreground">
            <FileText className="w-8 h-8 mx-auto mb-2 opacity-40 text-muted-foreground" />
            <p className="text-sm font-semibold text-foreground">Project Compliance & Export Reports</p>
            <p className="text-xs text-muted-foreground mt-1 max-w-md mx-auto">
              Executive vulnerability summaries and PDF/CSV compliance reports can be requested from completed scan runs.
            </p>
            {scans.length === 0 && (
              <p className="text-[11px] text-muted-foreground/70 mt-2">
                No scans executed yet for this project.
              </p>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
