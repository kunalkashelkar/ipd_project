// ============================================================
// ScanConfig.tsx — Phase 3 Provenance-Bound Scan Configuration
// ============================================================

import React, { useEffect, useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { useNavigate, useParams, Link } from 'react-router-dom';
import {
  Play,
  Settings2,
  Shield,
  X,
  ScanEye,
  Zap,
  FileText,
  Loader2,
  Layers,
  GitCommit,
  AlertCircle,
  Plus,
  Network,
  CheckCircle2,
  Lock,
  FileDiff,
} from 'lucide-react';
import { motion } from 'framer-motion';
import { snapshotService } from '../../services/snapshotService';
import { uploadService } from '../../services/uploadService';
import { scanService } from '../../services/scanService';
import { SourceSnapshot, Upload } from '../../types';
import { getScanProgressUrl, getConnectRepoUrl } from '../../utils/routes';
import toast from 'react-hot-toast';

export default function ScanConfig() {
  const navigate = useNavigate();
  const params = useParams<{ id?: string; projectId?: string }>();
  const id = params.projectId || params.id;

  const [isStarting, setIsStarting] = useState(false);
  const [snapshots, setSnapshots] = useState<SourceSnapshot[]>([]);
  const [selectedSnapshotId, setSelectedSnapshotId] = useState<string>('');
  const [loadingSources, setLoadingSources] = useState(true);

  // Fallback legacy uploads
  const [uploads, setUploads] = useState<Upload[]>([]);
  const [selectedUploadId, setSelectedUploadId] = useState<string>('');

  useEffect(() => {
    if (!id) return;
    async function loadSources() {
      setLoadingSources(true);
      try {
        const [snapsRes, uploadsRes] = await Promise.allSettled([
          snapshotService.listSnapshots(id!, { page_size: 50 }),
          uploadService.listUploads(id!, { page_size: 50 }),
        ]);

        if (snapsRes.status === 'fulfilled') {
          setSnapshots(snapsRes.value.items);
          const firstReady = snapsRes.value.items.find((s) => s.status === 'ready');
          if (firstReady) {
            setSelectedSnapshotId(firstReady.id);
          } else if (snapsRes.value.items.length > 0) {
            setSelectedSnapshotId(snapsRes.value.items[0].id);
          }
        }

        if (uploadsRes.status === 'fulfilled') {
          setUploads(uploadsRes.value.items);
          if (uploadsRes.value.items.length > 0) {
            setSelectedUploadId(uploadsRes.value.items[0].id);
          }
        }
      } catch {
        // Handled
      } finally {
        setLoadingSources(false);
      }
    }
    loadSources();
  }, [id]);

  const selectedSnapshot = snapshots.find((s) => s.id === selectedSnapshotId);
  const isSnapshotReady = selectedSnapshot?.status === 'ready';

  const handleStartScan = async () => {
    if (!id) return;

    if (snapshots.length > 0) {
      if (!selectedSnapshotId) {
        toast.error('Please select a source snapshot to scan.');
        return;
      }
      if (!isSnapshotReady) {
        toast.error('Only snapshots in READY state can be scanned.');
        return;
      }

      setIsStarting(true);
      try {
        const scan = await scanService.createScan({
          project_id: id,
          source_snapshot_id: selectedSnapshotId,
        });
        toast.success('Scan started against source snapshot!');
        navigate(getScanProgressUrl(id, scan));
      } catch (err: any) {
        toast.error(err?.response?.data?.message || 'Failed to start scan.');
      } finally {
        setIsStarting(false);
      }
    } else if (selectedUploadId) {
      // Legacy fallback
      setIsStarting(true);
      try {
        const scan = await scanService.createScan({
          project_id: id,
          upload_id: selectedUploadId,
        });
        toast.success('Scan started!');
        navigate(getScanProgressUrl(id, scan));
      } catch (err: any) {
        toast.error(err?.response?.data?.message || 'Failed to start scan.');
      } finally {
        setIsStarting(false);
      }
    } else {
      toast.error('Please attach or upload source code first.');
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="w-full max-w-lg"
      >
        <Card className="border-border shadow-2xl relative overflow-hidden">
          <div className="absolute top-0 left-0 w-full h-1 bg-primary" />
          <Button
            variant="ghost"
            size="sm"
            className="absolute top-4 right-4 w-8 h-8 p-0"
            onClick={() => navigate(-1)}
          >
            <X className="w-4 h-4" />
          </Button>

          <CardHeader className="pb-4">
            <CardTitle className="text-lg font-semibold flex items-center gap-2">
              <Settings2 className="w-5 h-5 text-primary" /> Configure Analysis Run
            </CardTitle>
            <p className="text-xs text-muted-foreground mt-1">
              Select an immutable source snapshot as the scan provenance boundary.
            </p>
          </CardHeader>

          <CardContent className="space-y-4">
            {/* Source Snapshot Selector */}
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-foreground flex items-center justify-between">
                <span>Target Source Snapshot *</span>
                <span className="text-[10px] text-muted-foreground font-mono">Immutable Provenance</span>
              </label>

              {loadingSources ? (
                <div className="flex items-center gap-2 text-sm text-muted-foreground py-2">
                  <Loader2 className="w-4 h-4 animate-spin text-primary" /> Loading snapshots...
                </div>
              ) : snapshots.length === 0 && uploads.length === 0 ? (
                <div className="text-xs text-muted-foreground p-3 bg-muted/30 rounded-md border border-border space-y-2">
                  <p>No source code found. Ingest source code to create an immutable snapshot.</p>
                  <Link to={getConnectRepoUrl(id)}>
                    <Button size="sm" variant="outline" className="text-xs h-7 gap-1">
                      <Plus className="w-3 h-3" /> Connect Source
                    </Button>
                  </Link>
                </div>
              ) : snapshots.length > 0 ? (
                <div className="space-y-2">
                  <select
                    value={selectedSnapshotId}
                    onChange={(e) => setSelectedSnapshotId(e.target.value)}
                    className="w-full h-9 px-3 bg-background border border-border rounded-md text-xs focus:ring-1 focus:ring-primary outline-none"
                  >
                    {snapshots.map((s) => (
                      <option key={s.id} value={s.id} disabled={s.status !== 'ready'}>
                        [{s.status.toUpperCase()}] {s.source_type.toUpperCase()} • {s.file_count} files •{' '}
                        {s.commit_sha ? `commit ${s.commit_sha.slice(0, 7)}` : new Date(s.created_at).toLocaleDateString()}
                        {s.status !== 'ready' ? ' (Not Ready)' : ''}
                      </option>
                    ))}
                  </select>

                  {/* Selected Snapshot Details Preview */}
                  {selectedSnapshot && (
                    <div className="p-3 bg-muted/30 border border-border rounded-md space-y-1.5 text-xs">
                      <div className="flex items-center justify-between">
                        <span className="text-muted-foreground">Snapshot Status:</span>
                        <span
                          className={`font-semibold capitalize ${
                            selectedSnapshot.status === 'ready'
                              ? 'text-emerald-500'
                              : selectedSnapshot.status === 'failed'
                              ? 'text-destructive'
                              : 'text-amber-500'
                          }`}
                        >
                          {selectedSnapshot.status}
                        </span>
                      </div>

                      {selectedSnapshot.commit_sha && (
                        <div className="flex items-center justify-between font-mono text-[11px]">
                          <span className="text-muted-foreground flex items-center gap-1">
                            <GitCommit className="w-3 h-3 text-primary" /> Commit:
                          </span>
                          <span>{selectedSnapshot.commit_sha.slice(0, 10)}</span>
                        </div>
                      )}

                      <div className="flex items-center justify-between text-[11px]">
                        <span className="text-muted-foreground">Detected Languages:</span>
                        <span className="font-mono">
                          {Object.keys(selectedSnapshot.detected_languages || {}).join(', ') || 'General'}
                        </span>
                      </div>

                      {!isSnapshotReady && (
                        <div className="flex items-center gap-1.5 text-[11px] text-amber-500 pt-1 border-t border-border/40">
                          <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                          <span>Only READY snapshots can be scanned. Wait for processing to complete.</span>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ) : (
                /* Legacy Upload selector if no Phase 3 snapshots yet */
                <select
                  value={selectedUploadId}
                  onChange={(e) => setSelectedUploadId(e.target.value)}
                  className="w-full h-9 px-3 bg-background border border-border rounded-md text-xs focus:ring-1 focus:ring-primary outline-none"
                >
                  {uploads.map((u) => (
                    <option key={u.id} value={u.id}>
                      {u.original_filename} ({(u.file_size / 1024).toFixed(1)} KB)
                    </option>
                  ))}
                </select>
              )}
            </div>

            {/* Analysis Pipeline Modules */}
            <div className="space-y-2">
              <label className="text-xs font-medium text-foreground">Analysis Pipeline Modules</label>
              {[
                {
                  id: 'static',
                  label: 'Static Code & Canonical Graph Pipeline',
                  desc: 'AST, CFG, CPG, and Call Graph generation with cryptographic checksums. (PDG: Unsupported in native fallback; requires Joern engine).',
                  icon: Shield,
                  statusLabel: 'Native Engine',
                  active: true,
                },
                {
                  id: 'taint',
                  label: 'Data Flow & Taint Analysis Engine',
                  desc: 'Source, sink, and sanitizer detection with attack path evidence extraction. (Zero detected taint paths does not guarantee code is secure).',
                  icon: Network,
                  statusLabel: 'Active Pipeline',
                  active: true,
                },
                {
                  id: 'ai',
                  label: 'AI Vulnerability Detection',
                  desc: 'Inference via configured AI provider (MockAIProvider / LocalTorchProvider boundary). Model registry tracks active runtime and version.',
                  icon: ScanEye,
                  statusLabel: 'Inference Runtime',
                  active: true,
                },
                {
                  id: 'explain',
                  label: 'Explainability & Evidence Attribution',
                  desc: 'Evidence-aware explanations and normalized attribution (Captum IG, SHAP, GNNExplainer, Attention). Unconfigured runtimes report explicit MODEL_NOT_READY.',
                  icon: Zap,
                  statusLabel: 'Attribution Engine',
                  active: true,
                },
                {
                  id: 'fix',
                  label: 'Remediation & Verification Sandbox',
                  desc: 'Remediation proposal generation, human review, isolated sandbox validation, and verification scans. No automatic merging or direct deployment.',
                  icon: FileDiff,
                  statusLabel: 'Sandbox Verification',
                  active: true,
                },
              ].map((opt) => (
                <div
                  key={opt.id}
                  className={`flex items-start gap-3 p-2.5 rounded-md border transition-colors ${
                    opt.active ? 'border-emerald-500/40 bg-emerald-500/5' : 'border-border/60 bg-muted/20 opacity-70'
                  }`}
                >
                  <div className="pt-0.5">
                    {opt.active ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    ) : (
                      <Lock className="w-3.5 h-3.5 text-muted-foreground/60" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-xs text-foreground flex items-center justify-between">
                      <span className="flex items-center gap-1.5">
                        <opt.icon className="w-3.5 h-3.5 text-muted-foreground" /> {opt.label}
                      </span>
                      <span
                        className={`text-[10px] px-2 py-0.5 rounded border ${
                          opt.active
                            ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400 font-medium'
                            : 'border-border/40 bg-muted/30 text-muted-foreground'
                        }`}
                      >
                        {opt.statusLabel}
                      </span>
                    </div>
                    <div className="text-[11px] text-muted-foreground mt-0.5">{opt.desc}</div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>

          <CardFooter className="bg-muted/20 border-t border-border p-6 flex justify-between mt-2">
            <Button variant="ghost" onClick={() => navigate(-1)}>
              Cancel
            </Button>
            <Button
              onClick={handleStartScan}
              disabled={
                isStarting ||
                (snapshots.length > 0 ? !isSnapshotReady : !selectedUploadId)
              }
              className="min-w-[140px]"
            >
              {isStarting ? (
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Starting...
                </div>
              ) : (
                <>
                  <Play className="w-4 h-4 mr-2" /> Start Scan
                </>
              )}
            </Button>
          </CardFooter>
        </Card>
      </motion.div>
    </div>
  );
}
