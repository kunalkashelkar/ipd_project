// ============================================================
// ConnectRepo.tsx — Phase 3 Source Ingestion & VCS Connection
// ============================================================

import React, { useState, useRef } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  Github,
  GitBranch,
  UploadCloud,
  FileCode2,
  Layers,
  ArrowLeft,
  CheckCircle2,
  AlertTriangle,
  Loader2,
  FolderGit2,
  KeyRound,
  FileUp,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Breadcrumbs } from '../../components/ui/Breadcrumbs';
import { PageHeader } from '../../components/ui/PageHeader';
import { Alert } from '../../components/ui/Alert';
import { snapshotService } from '../../services/snapshotService';
import { repositoryService } from '../../services/repositoryService';
import { getProjectUrl, getSnapshotUrl } from '../../utils/routes';
import toast from 'react-hot-toast';

export default function ConnectRepo() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();

  const [activeTab, setActiveTab] = useState<'zip' | 'files' | 'git' | 'github'>('zip');

  // ZIP upload state
  const [zipFile, setZipFile] = useState<File | null>(null);
  const [zipUploading, setZipUploading] = useState(false);
  const [zipProgress, setZipProgress] = useState(0);
  const zipInputRef = useRef<HTMLInputElement>(null);

  // Individual files upload state
  const [sourceFiles, setSourceFiles] = useState<File[]>([]);
  const [filesUploading, setFilesUploading] = useState(false);
  const [filesProgress, setFilesProgress] = useState(0);
  const filesInputRef = useRef<HTMLInputElement>(null);

  // Git repo state
  const [gitUrl, setGitUrl] = useState('');
  const [gitDisplayName, setGitDisplayName] = useState('');
  const [gitBranch, setGitBranch] = useState('');
  const [gitConnecting, setGitConnecting] = useState(false);

  // GitHub repo state
  const [githubUrl, setGithubUrl] = useState('');
  const [githubToken, setGithubToken] = useState('');
  const [githubBranch, setGithubBranch] = useState('');
  const [githubConnecting, setGithubConnecting] = useState(false);

  // ── Handle ZIP Upload ──────────────────────────────────────
  const handleZipUpload = async () => {
    if (!zipFile || !projectId) {
      toast.error('Please select a ZIP archive first');
      return;
    }

    setZipUploading(true);
    setZipProgress(0);
    try {
      const snapshot = await snapshotService.uploadZip(
        projectId,
        zipFile,
        (progressEvent) => {
          if (progressEvent.total) {
            setZipProgress(Math.round((progressEvent.loaded * 100) / progressEvent.total));
          }
        }
      );
      toast.success('Archive uploaded. Source snapshot queued for processing!');
      navigate(getSnapshotUrl(projectId, snapshot));
    } catch (err: any) {
      toast.error(err?.response?.data?.message || 'Failed to upload ZIP archive');
    } finally {
      setZipUploading(false);
    }
  };

  // ── Handle Individual Files Upload ─────────────────────────
  const handleFilesUpload = async () => {
    if (sourceFiles.length === 0 || !projectId) {
      toast.error('Please select at least one source file');
      return;
    }

    setFilesUploading(true);
    setFilesProgress(0);
    try {
      const snapshot = await snapshotService.uploadFiles(
        projectId,
        sourceFiles,
        undefined,
        (progressEvent) => {
          if (progressEvent.total) {
            setFilesProgress(Math.round((progressEvent.loaded * 100) / progressEvent.total));
          }
        }
      );
      toast.success(`${sourceFiles.length} files uploaded to snapshot!`);
      navigate(getSnapshotUrl(projectId, snapshot));
    } catch (err: any) {
      toast.error(err?.response?.data?.message || 'Failed to upload source files');
    } finally {
      setFilesUploading(false);
    }
  };

  // ── Handle Git Connect ─────────────────────────────────────
  const handleGitConnect = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!gitUrl.trim() || !projectId) {
      toast.error('Repository URL is required');
      return;
    }

    setGitConnecting(true);
    try {
      const repo = await repositoryService.connectRepository(projectId, {
        provider: 'local_git',
        repo_url: gitUrl.trim(),
        display_name: gitDisplayName.trim() || undefined,
        default_branch: gitBranch.trim() || undefined,
      });
      toast.success(`Git repository '${repo.display_name}' connected and sync queued!`);
      navigate(`${getProjectUrl(projectId)}?tab=repositories`);
    } catch (err: any) {
      toast.error(err?.response?.data?.message || 'Failed to connect Git repository');
    } finally {
      setGitConnecting(false);
    }
  };

  // ── Handle GitHub Connect ──────────────────────────────────
  const handleGithubConnect = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!githubUrl.trim() || !projectId) {
      toast.error('GitHub repository URL is required');
      return;
    }

    setGithubConnecting(true);
    try {
      const repo = await repositoryService.connectRepository(projectId, {
        provider: 'github',
        repo_url: githubUrl.trim(),
        access_token: githubToken.trim() || undefined,
        default_branch: githubBranch.trim() || undefined,
      });
      toast.success(`GitHub repository '${repo.display_name}' connected and sync queued!`);
      navigate(`${getProjectUrl(projectId)}?tab=repositories`);
    } catch (err: any) {
      toast.error(err?.response?.data?.message || 'Failed to connect GitHub repository');
    } finally {
      setGithubConnecting(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6 pb-12">
      <PageHeader
        breadcrumbs={
          <Breadcrumbs
            items={[
              { label: 'Projects', to: '/projects' },
              { label: 'Project', to: projectId ? getProjectUrl(projectId) : '/projects' },
              { label: 'Connect Source' },
            ]}
          />
        }
        title="Connect Source Code"
        description="Attach source code to create immutable snapshots for static graph analysis and vulnerability detection."
      />

      <Card>
        {/* Navigation Tabs */}
        <div className="flex border-b border-border bg-muted/20 overflow-x-auto scrollbar-none">
          {[
            { id: 'zip', label: 'Upload ZIP Archive', icon: <UploadCloud className="w-4 h-4 mr-2" /> },
            { id: 'files', label: 'Upload Files', icon: <FileUp className="w-4 h-4 mr-2" /> },
            { id: 'git', label: 'Git Repository', icon: <FolderGit2 className="w-4 h-4 mr-2" /> },
            { id: 'github', label: 'GitHub Repository', icon: <Github className="w-4 h-4 mr-2" /> },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center px-6 py-4 text-sm font-medium transition-colors border-b-2 whitespace-nowrap ${
                activeTab === tab.id
                  ? 'border-primary text-foreground'
                  : 'border-transparent text-muted-foreground hover:text-foreground hover:bg-muted/50'
              }`}
            >
              {tab.icon}
              {tab.label}
            </button>
          ))}
        </div>

        <CardContent className="p-8 min-h-[360px]">
          {/* TAB 1: ZIP Upload */}
          {activeTab === 'zip' && (
            <div className="space-y-6 max-w-xl mx-auto">
              <input
                ref={zipInputRef}
                type="file"
                accept=".zip,.tar,.gz,.jar"
                className="hidden"
                onChange={(e) => {
                  if (e.target.files?.[0]) setZipFile(e.target.files[0]);
                }}
              />

              <div
                onClick={() => zipInputRef.current?.click()}
                className="border-2 border-dashed border-border rounded-xl p-8 text-center cursor-pointer hover:border-primary/50 hover:bg-muted/20 transition-all space-y-3"
              >
                <div className="w-12 h-12 rounded-full bg-primary/10 text-primary flex items-center justify-center mx-auto">
                  <UploadCloud className="w-6 h-6" />
                </div>
                {zipFile ? (
                  <div>
                    <p className="text-sm font-semibold text-foreground">{zipFile.name}</p>
                    <p className="text-xs text-muted-foreground font-mono mt-0.5">
                      {(zipFile.size / (1024 * 1024)).toFixed(2)} MB
                    </p>
                  </div>
                ) : (
                  <div>
                    <h3 className="text-sm font-semibold text-foreground">Select or Drag ZIP Archive</h3>
                    <p className="text-xs text-muted-foreground mt-1">
                      Max upload size: 100 MB. Extracted in isolated worker environment with strict path traversal protection.
                    </p>
                  </div>
                )}
              </div>

              {zipUploading && (
                <div className="space-y-2">
                  <div className="flex justify-between text-xs text-muted-foreground">
                    <span>Uploading archive to object storage...</span>
                    <span>{zipProgress}%</span>
                  </div>
                  <div className="w-full bg-muted rounded-full h-1.5 overflow-hidden">
                    <div className="bg-primary h-full transition-all" style={{ width: `${zipProgress}%` }} />
                  </div>
                </div>
              )}

              <Button
                className="w-full text-xs"
                disabled={!zipFile || zipUploading}
                onClick={handleZipUpload}
              >
                {zipUploading ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin mr-2" />
                    Uploading & Ingesting...
                  </>
                ) : (
                  'Upload and Process Snapshot'
                )}
              </Button>
            </div>
          )}

          {/* TAB 2: Individual Files Upload */}
          {activeTab === 'files' && (
            <div className="space-y-6 max-w-xl mx-auto">
              <input
                ref={filesInputRef}
                type="file"
                multiple
                accept=".c,.cpp,.h,.hpp,.java,.py,.js,.jsx,.ts,.tsx,.go,.rs,.cs,.php"
                className="hidden"
                onChange={(e) => {
                  if (e.target.files) {
                    setSourceFiles(Array.from(e.target.files));
                  }
                }}
              />

              <div
                onClick={() => filesInputRef.current?.click()}
                className="border-2 border-dashed border-border rounded-xl p-8 text-center cursor-pointer hover:border-primary/50 hover:bg-muted/20 transition-all space-y-3"
              >
                <div className="w-12 h-12 rounded-full bg-primary/10 text-primary flex items-center justify-center mx-auto">
                  <FileUp className="w-6 h-6" />
                </div>
                {sourceFiles.length > 0 ? (
                  <div>
                    <p className="text-sm font-semibold text-foreground">
                      {sourceFiles.length} file(s) selected
                    </p>
                    <p className="text-xs text-muted-foreground font-mono mt-0.5">
                      Total: {(sourceFiles.reduce((acc, f) => acc + f.size, 0) / 1024).toFixed(1)} KB
                    </p>
                  </div>
                ) : (
                  <div>
                    <h3 className="text-sm font-semibold text-foreground">Select Individual Source Files</h3>
                    <p className="text-xs text-muted-foreground mt-1">
                      Select one or multiple code files. All selected files will be bound to a single immutable snapshot.
                    </p>
                  </div>
                )}
              </div>

              {sourceFiles.length > 0 && (
                <div className="max-h-40 overflow-y-auto border border-border rounded-md p-2 space-y-1 text-xs">
                  {sourceFiles.map((f, idx) => (
                    <div key={idx} className="flex justify-between font-mono text-muted-foreground">
                      <span className="truncate max-w-sm">{f.name}</span>
                      <span>{(f.size / 1024).toFixed(1)} KB</span>
                    </div>
                  ))}
                </div>
              )}

              {filesUploading && (
                <div className="space-y-2">
                  <div className="flex justify-between text-xs text-muted-foreground">
                    <span>Uploading files...</span>
                    <span>{filesProgress}%</span>
                  </div>
                  <div className="w-full bg-muted rounded-full h-1.5 overflow-hidden">
                    <div className="bg-primary h-full transition-all" style={{ width: `${filesProgress}%` }} />
                  </div>
                </div>
              )}

              <Button
                className="w-full text-xs"
                disabled={sourceFiles.length === 0 || filesUploading}
                onClick={handleFilesUpload}
              >
                {filesUploading ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin mr-2" />
                    Uploading Files...
                  </>
                ) : (
                  `Upload ${sourceFiles.length} Files to Snapshot`
                )}
              </Button>
            </div>
          )}

          {/* TAB 3: Git Repository */}
          {activeTab === 'git' && (
            <form onSubmit={handleGitConnect} className="space-y-4 max-w-xl mx-auto">
              <div className="p-3 bg-muted/30 border border-border rounded-lg text-xs text-muted-foreground space-y-1">
                <div className="font-semibold text-foreground flex items-center gap-1.5">
                  <FolderGit2 className="w-3.5 h-3.5 text-primary" /> Git Clone & Ingestion Pipeline
                </div>
                <p className="text-[11px] leading-relaxed">
                  Synchronize with any remote Git repository over HTTPS. Cloned in an isolated sandbox with Git hooks disabled, depth limits, and strict path verification.
                </p>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-medium text-foreground">Git Repository URL *</label>
                <input
                  type="text"
                  placeholder="https://github.com/example/repo.git or https://gitlab.com/..."
                  value={gitUrl}
                  onChange={(e) => setGitUrl(e.target.value)}
                  className="w-full bg-card border border-border rounded-md px-3 py-2 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary font-mono"
                  required
                />
                <p className="text-[11px] text-muted-foreground">
                  Standard Git clone reference. Worker clones with hooks disabled and safe depth limits.
                </p>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-foreground">Display Name (Optional)</label>
                  <input
                    type="text"
                    placeholder="my-core-service"
                    value={gitDisplayName}
                    onChange={(e) => setGitDisplayName(e.target.value)}
                    className="w-full bg-card border border-border rounded-md px-3 py-2 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-foreground">Tracking Branch (Optional)</label>
                  <input
                    type="text"
                    placeholder="Auto-detect (e.g. main or master)"
                    value={gitBranch}
                    onChange={(e) => setGitBranch(e.target.value)}
                    className="w-full bg-card border border-border rounded-md px-3 py-2 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary font-mono"
                  />
                  <p className="text-[11px] text-muted-foreground">
                    Leave blank to automatically discover the remote repository's default branch.
                  </p>
                </div>
              </div>

              <Button
                type="submit"
                className="w-full text-xs mt-2"
                disabled={gitConnecting || !gitUrl.trim()}
              >
                {gitConnecting ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin mr-2" />
                    Connecting Repository...
                  </>
                ) : (
                  'Connect Git Repository'
                )}
              </Button>
            </form>
          )}

          {/* TAB 4: GitHub Repository */}
          {activeTab === 'github' && (
            <form onSubmit={handleGithubConnect} className="space-y-4 max-w-xl mx-auto">
              <div className="p-3 bg-muted/30 border border-border rounded-lg text-xs text-muted-foreground space-y-1">
                <div className="font-semibold text-foreground flex items-center gap-1.5">
                  <Github className="w-3.5 h-3.5 text-foreground" /> Direct GitHub VCS Synchronization
                </div>
                <p className="text-[11px] leading-relaxed">
                  Connect any public or token-authenticated GitHub repository. VulnScan automatically discovers remote branches, tracks commit SHA provenance, and creates an immutable snapshot via isolated worker extraction.
                </p>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-medium text-foreground">GitHub Repository URL / Slug *</label>
                <input
                  type="text"
                  placeholder="https://github.com/org/repo or owner/repo"
                  value={githubUrl}
                  onChange={(e) => setGithubUrl(e.target.value)}
                  className="w-full bg-card border border-border rounded-md px-3 py-2 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary font-mono"
                  required
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-medium text-foreground flex items-center justify-between">
                  <span>Personal Access Token (Optional)</span>
                  <span className="text-[10px] text-muted-foreground">Required for private repositories</span>
                </label>
                <input
                  type="password"
                  placeholder="ghp_..."
                  value={githubToken}
                  onChange={(e) => setGithubToken(e.target.value)}
                  className="w-full bg-card border border-border rounded-md px-3 py-2 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary font-mono"
                />
                <p className="text-[11px] text-muted-foreground">
                  Public repositories do not require a token. Tokens are encrypted/redacted and never exposed in responses or logs.
                </p>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-medium text-foreground">Default / Tracking Branch (Optional)</label>
                <input
                  type="text"
                  placeholder="Auto-detect (e.g. main or master)"
                  value={githubBranch}
                  onChange={(e) => setGithubBranch(e.target.value)}
                  className="w-full bg-card border border-border rounded-md px-3 py-2 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary font-mono"
                />
                <p className="text-[11px] text-muted-foreground">
                  Leave blank to automatically discover the repository's default branch (main or master).
                </p>
              </div>

              <Button
                type="submit"
                className="w-full text-xs mt-2"
                disabled={githubConnecting || !githubUrl.trim()}
              >
                {githubConnecting ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin mr-2" />
                    Connecting & Syncing GitHub Repo...
                  </>
                ) : (
                  'Connect GitHub Repository'
                )}
              </Button>
            </form>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
