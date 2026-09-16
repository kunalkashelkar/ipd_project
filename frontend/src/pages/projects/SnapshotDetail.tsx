// ============================================================
// SnapshotDetail.tsx — Phase 3 Immutable Source Snapshot Viewer
// ============================================================

import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  FileCode2,
  GitCommit,
  Layers,
  Search,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Loader2,
  ArrowLeft,
  Copy,
  Check,
  FileText,
  Binary,
  Code2,
  ShieldAlert,
  Play,
  Filter,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';
import { snapshotService } from '../../services/snapshotService';
import { SourceSnapshot, SourceFile, SourceFileContent, FunctionModel } from '../../types';
import toast from 'react-hot-toast';

export default function SnapshotDetail() {
  const { projectId, snapshotId } = useParams<{ projectId: string; snapshotId: string }>();

  const [snapshot, setSnapshot] = useState<SourceSnapshot | null>(null);
  const [files, setFiles] = useState<SourceFile[]>([]);
  const [totalFiles, setTotalFiles] = useState<number>(0);
  const [functions, setFunctions] = useState<FunctionModel[]>([]);
  const [totalFunctions, setTotalFunctions] = useState<number>(0);

  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'files' | 'functions'>('files');

  // Search & Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedLang, setSelectedLang] = useState<string>('');
  const [page, setPage] = useState(1);

  // File content inspection state
  const [selectedFile, setSelectedFile] = useState<SourceFile | null>(null);
  const [fileContent, setFileContent] = useState<SourceFileContent | null>(null);
  const [loadingContent, setLoadingContent] = useState(false);
  const [copiedHash, setCopiedHash] = useState(false);

  useEffect(() => {
    if (!projectId || !snapshotId) return;

    async function loadSnapshot() {
      setLoading(true);
      try {
        const snap = await snapshotService.getSnapshot(projectId!, snapshotId!);
        setSnapshot(snap);

        const filesData = await snapshotService.listFiles(projectId!, snapshotId!, {
          page: 1,
          page_size: 50,
        });
        setFiles(filesData.items);
        setTotalFiles(filesData.total);

        const funcData = await snapshotService.listFunctions(projectId!, snapshotId!, {
          page: 1,
          page_size: 50,
        });
        setFunctions(funcData.items);
        setTotalFunctions(funcData.total);
      } catch (err: any) {
        toast.error(err?.response?.data?.message || 'Failed to load source snapshot');
      } finally {
        setLoading(false);
      }
    }

    loadSnapshot();
  }, [projectId, snapshotId]);

  // Handle Search/Filter changes for files
  useEffect(() => {
    if (!projectId || !snapshotId || activeTab !== 'files') return;

    const timer = setTimeout(async () => {
      try {
        const data = await snapshotService.listFiles(projectId!, snapshotId!, {
          page,
          page_size: 50,
          search: searchQuery || undefined,
          language: selectedLang || undefined,
        });
        setFiles(data.items);
        setTotalFiles(data.total);
      } catch {
        // Handled
      }
    }, 250);

    return () => clearTimeout(timer);
  }, [projectId, snapshotId, searchQuery, selectedLang, page, activeTab]);

  // Handle viewing file content
  const handleSelectFile = async (file: SourceFile) => {
    setSelectedFile(file);
    setLoadingContent(true);
    try {
      const content = await snapshotService.getFileContent(projectId!, snapshotId!, file.id);
      setFileContent(content);
    } catch (err: any) {
      toast.error(err?.response?.data?.message || 'Failed to fetch file content');
      setFileContent(null);
    } finally {
      setLoadingContent(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedHash(true);
    setTimeout(() => setCopiedHash(false), 2000);
    toast.success('Copied to clipboard');
  };

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!snapshot) {
    return (
      <div className="text-center py-20 text-muted-foreground">
        <p className="text-sm font-medium text-foreground">Source Snapshot not found.</p>
        <Link to={`/projects/${projectId}`}>
          <Button variant="outline" size="sm" className="mt-4 text-xs">
            Back to Project
          </Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Header & Breadcrumb */}
      <div className="flex flex-col md:flex-row md:items-start justify-between gap-4 pb-4 border-b border-border/50">
        <div>
          <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1.5">
            <Link to={`/projects/${projectId}`} className="hover:text-foreground flex items-center gap-1">
              <ArrowLeft className="w-3.5 h-3.5" /> Back to Project
            </Link>
            <span>/</span>
            <span className="font-mono">Snapshot {snapshot.id.slice(0, 8)}</span>
          </div>

          <div className="flex items-center gap-3">
            <h1 className="text-xl font-bold tracking-tight text-foreground flex items-center gap-2">
              <Layers className="w-5 h-5 text-primary" />
              Source Snapshot
            </h1>
            <Badge
              variant={
                snapshot.status === 'ready'
                  ? 'default'
                  : snapshot.status === 'failed'
                  ? 'destructive'
                  : 'secondary'
              }
              className="text-[10px] capitalize"
            >
              {snapshot.status}
            </Badge>
            <Badge variant="outline" className="text-[10px] uppercase font-mono">
              {snapshot.source_type}
            </Badge>
          </div>

          <div className="flex flex-wrap items-center gap-4 text-xs text-muted-foreground mt-2 font-mono">
            {snapshot.commit_sha && (
              <span className="flex items-center gap-1">
                <GitCommit className="w-3.5 h-3.5 text-primary" />
                commit {snapshot.commit_sha.slice(0, 8)}
              </span>
            )}
            <span className="flex items-center gap-1">
              <Clock className="w-3.5 h-3.5" /> Created {new Date(snapshot.created_at).toLocaleString()}
            </span>
            <span className="flex items-center gap-1">
              SHA-256: {snapshot.content_hash.slice(0, 12)}...
              <button
                onClick={() => copyToClipboard(snapshot.content_hash)}
                className="hover:text-foreground ml-1"
                title="Copy full hash"
              >
                {copiedHash ? <Check className="w-3 h-3 text-emerald-500" /> : <Copy className="w-3 h-3" />}
              </button>
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {snapshot.status === 'ready' && (
            <Link to={`/projects/${projectId}/scan-config`}>
              <Button size="sm" className="text-xs gap-1.5">
                <Play className="w-3.5 h-3.5" />
                Scan this Snapshot
              </Button>
            </Link>
          )}
        </div>
      </div>

      {/* Snapshot Provenance & Preprocessing Metrics */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
        <Card className="bg-card/60">
          <CardContent className="p-3.5">
            <span className="text-[10px] font-medium text-muted-foreground block">Source Files</span>
            <span className="text-lg font-bold text-foreground mt-0.5 block">{snapshot.file_count}</span>
          </CardContent>
        </Card>
        <Card className="bg-card/60">
          <CardContent className="p-3.5">
            <span className="text-[10px] font-medium text-muted-foreground block">Total Size</span>
            <span className="text-lg font-bold text-foreground mt-0.5 block">{formatBytes(snapshot.total_bytes)}</span>
          </CardContent>
        </Card>
        <Card className="bg-card/60">
          <CardContent className="p-3.5">
            <span className="text-[10px] font-medium text-muted-foreground block">Functions Extracted</span>
            <span className="text-lg font-bold text-foreground mt-0.5 block">{totalFunctions}</span>
          </CardContent>
        </Card>
        <Card className="bg-card/60">
          <CardContent className="p-3.5">
            <span className="text-[10px] font-medium text-muted-foreground block">Preprocessing Spec</span>
            <span className="text-lg font-bold text-foreground mt-0.5 block font-mono text-xs">
              {snapshot.preprocessing_version}
            </span>
          </CardContent>
        </Card>
        <Card className="bg-card/60">
          <CardContent className="p-3.5">
            <span className="text-[10px] font-medium text-muted-foreground block">Detected Languages</span>
            <div className="flex flex-wrap gap-1 mt-1">
              {Object.keys(snapshot.detected_languages || {}).length > 0 ? (
                Object.entries(snapshot.detected_languages).map(([lang, count]) => (
                  <span
                    key={lang}
                    className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-muted text-foreground"
                  >
                    {lang} ({count})
                  </span>
                ))
              ) : (
                <span className="text-xs text-muted-foreground">None</span>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Tabs: Files vs Functions */}
      <div className="border-b border-border">
        <div className="flex gap-6 text-xs">
          {[
            { id: 'files', label: `Source Files (${totalFiles})` },
            { id: 'functions', label: `Extracted Functions (${totalFunctions})` },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => {
                setActiveTab(tab.id as any);
                setSelectedFile(null);
                setFileContent(null);
              }}
              className={`pb-2.5 font-medium transition-colors border-b-2 ${
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

      {/* TAB 1: Source Files & Code Inspector */}
      {activeTab === 'files' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* File Browser Table */}
          <div className={`${selectedFile ? 'lg:col-span-5' : 'lg:col-span-12'} space-y-4`}>
            <div className="flex items-center gap-3">
              <div className="relative flex-1">
                <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                <input
                  type="text"
                  placeholder="Filter files by path..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full bg-card border border-border rounded-md pl-8 pr-3 py-1.5 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>

              {Object.keys(snapshot.detected_languages || {}).length > 0 && (
                <select
                  value={selectedLang}
                  onChange={(e) => setSelectedLang(e.target.value)}
                  className="bg-card border border-border rounded-md px-2.5 py-1.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                >
                  <option value="">All Languages</option>
                  {Object.keys(snapshot.detected_languages).map((l) => (
                    <option key={l} value={l}>
                      {l}
                    </option>
                  ))}
                </select>
              )}
            </div>

            <Card className="overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="border-b border-border bg-muted/40 text-muted-foreground">
                      <th className="py-2.5 px-3 font-medium">Path</th>
                      <th className="py-2.5 px-3 font-medium">Language</th>
                      <th className="py-2.5 px-3 font-medium text-right">Size</th>
                      <th className="py-2.5 px-3 font-medium text-right">Lines</th>
                      <th className="py-2.5 px-3 font-medium">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/60">
                    {files.length === 0 ? (
                      <tr>
                        <td colSpan={5} className="py-8 text-center text-muted-foreground text-xs">
                          No source files found matching criteria.
                        </td>
                      </tr>
                    ) : (
                      files.map((file) => (
                        <tr
                          key={file.id}
                          onClick={() => handleSelectFile(file)}
                          className={`group cursor-pointer hover:bg-muted/40 transition-colors ${
                            selectedFile?.id === file.id ? 'bg-primary/10' : ''
                          }`}
                        >
                          <td className="py-2.5 px-3 font-mono font-medium text-foreground flex items-center gap-2">
                            {file.is_binary ? (
                              <Binary className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
                            ) : (
                              <FileCode2 className="w-3.5 h-3.5 text-primary shrink-0" />
                            )}
                            <span
                              className={`truncate ${selectedFile ? 'max-w-[220px] sm:max-w-[280px]' : 'max-w-[400px] sm:max-w-[550px] lg:max-w-none'}`}
                              title={file.relative_path}
                            >
                              {file.relative_path}
                            </span>
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                copyToClipboard(file.relative_path);
                              }}
                              className="opacity-0 group-hover:opacity-100 hover:text-foreground text-muted-foreground transition-opacity p-0.5 shrink-0"
                              title="Copy relative path"
                            >
                              <Copy className="w-3 h-3" />
                            </button>
                          </td>
                          <td className="py-2.5 px-3">
                            <span className="inline-block px-1.5 py-0.5 rounded text-[10px] font-mono bg-muted text-foreground">
                              {file.language || 'Plain'}
                            </span>
                          </td>
                          <td className="py-2.5 px-3 font-mono text-right text-muted-foreground">
                            {formatBytes(file.size_bytes)}
                          </td>
                          <td className="py-2.5 px-3 font-mono text-right text-muted-foreground">
                            {file.line_count}
                          </td>
                          <td className="py-2.5 px-3">
                            <Button variant="ghost" size="sm" className="h-6 px-2 text-[10px]">
                              Inspect
                            </Button>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </Card>
          </div>

          {/* Side Code Viewer */}
          {selectedFile && (
            <div className="lg:col-span-7 space-y-3">
              <Card className="h-full flex flex-col overflow-hidden border-border/80">
                <CardHeader className="py-2.5 px-4 bg-muted/30 border-b border-border flex flex-row items-center justify-between space-y-0">
                  <div className="flex items-center gap-2 min-w-0 mr-2">
                    <FileCode2 className="w-4 h-4 text-primary shrink-0" />
                    <div className="min-w-0">
                      <div className="flex items-center gap-1.5 min-w-0">
                        <span
                          className="font-mono text-xs font-semibold text-foreground break-all"
                          title={selectedFile.relative_path}
                        >
                          {selectedFile.relative_path}
                        </span>
                        <button
                          onClick={() => copyToClipboard(selectedFile.relative_path)}
                          className="hover:text-foreground text-muted-foreground p-0.5 shrink-0"
                          title="Copy file path"
                        >
                          <Copy className="w-3 h-3" />
                        </button>
                      </div>
                      <span className="text-[10px] text-muted-foreground font-mono block">
                        SHA-256: {selectedFile.content_hash.slice(0, 16)}...
                      </span>
                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-6 text-xs text-muted-foreground hover:text-foreground shrink-0"
                    onClick={() => setSelectedFile(null)}
                  >
                    Close
                  </Button>
                </CardHeader>

                <CardContent className="p-0 flex-1 relative min-h-[450px] max-h-[650px] overflow-auto bg-[#0d1117] text-gray-200">
                  {loadingContent ? (
                    <div className="flex items-center justify-center h-48">
                      <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
                    </div>
                  ) : fileContent ? (
                    <div className="flex font-mono text-xs leading-5">
                      {/* Line Numbers */}
                      <div className="select-none py-3 px-3 text-right text-gray-500 bg-[#161b22] border-r border-[#30363d] min-w-[40px]">
                        {fileContent.content.split('\n').map((_, idx) => (
                          <div key={idx}>{idx + 1}</div>
                        ))}
                      </div>

                      {/* Source Content */}
                      <pre className="py-3 px-4 overflow-x-auto whitespace-pre flex-1 text-gray-200">
                        {fileContent.content}
                      </pre>
                    </div>
                  ) : (
                    <div className="p-8 text-center text-xs text-muted-foreground">
                      Unable to preview content.
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          )}
        </div>
      )}

      {/* TAB 2: Extracted Functions */}
      {activeTab === 'functions' && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm flex items-center gap-2">
              <Code2 className="w-4 h-4 text-primary" />
              Extracted Functions & Methods
            </CardTitle>
            <CardDescription className="text-xs">
              Deterministic, syntax-extracted functions with provenance IDs, signature, and duplicate detection.
            </CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="border-b border-border bg-muted/40 text-muted-foreground">
                    <th className="py-2.5 px-3 font-medium">Function Name</th>
                    <th className="py-2.5 px-3 font-medium">Deterministic ID</th>
                    <th className="py-2.5 px-3 font-medium">Language</th>
                    <th className="py-2.5 px-3 font-medium">Lines</th>
                    <th className="py-2.5 px-3 font-medium text-right">Tokens</th>
                    <th className="py-2.5 px-3 font-medium">Duplicate Group</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/60">
                  {functions.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="py-8 text-center text-muted-foreground text-xs">
                        No functions extracted for this snapshot.
                      </td>
                    </tr>
                  ) : (
                    functions.map((fn) => (
                      <tr key={fn.id} className="hover:bg-muted/30 transition-colors">
                        <td className="py-2.5 px-3 font-mono font-medium text-foreground">
                          {fn.qualified_name || fn.name}
                          {fn.signature && (
                            <span className="text-muted-foreground font-normal ml-1">
                              {fn.signature}
                            </span>
                          )}
                        </td>
                        <td className="py-2.5 px-3 font-mono text-[11px] text-muted-foreground">
                          {fn.function_id.slice(0, 16)}...
                        </td>
                        <td className="py-2.5 px-3">
                          <span className="inline-block px-1.5 py-0.5 rounded text-[10px] font-mono bg-muted text-foreground">
                            {fn.language}
                          </span>
                        </td>
                        <td className="py-2.5 px-3 font-mono text-muted-foreground">
                          L{fn.start_line} - L{fn.end_line}
                        </td>
                        <td className="py-2.5 px-3 font-mono text-right text-muted-foreground">
                          {fn.token_count}
                        </td>
                        <td className="py-2.5 px-3">
                          {fn.duplicate_group_id ? (
                            <Badge variant="secondary" className="text-[9px] font-mono">
                              {fn.duplicate_group_id.slice(0, 10)}
                            </Badge>
                          ) : (
                            <span className="text-[10px] text-muted-foreground">Unique</span>
                          )}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
