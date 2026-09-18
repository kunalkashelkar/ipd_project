// ============================================================
// ScanProgress.tsx — Phase 4 Real-Time Scan Pipeline Progress
// ============================================================

import React, { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate, useSearchParams, Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  Check,
  Loader2,
  AlertCircle,
  XCircle,
  Clock,
  ArrowRight,
  Shield,
  Layers,
  Network,
  Cpu,
  FileCode2,
  FolderGit2,
  StopCircle,
} from 'lucide-react';
import { Card } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';
import { useScanProgress } from '../../hooks/useScanProgress';
import { scanService } from '../../services/scanService';
import { Scan } from '../../types';
import { getProjectUrl, getResultsUrl, getScanProgressUrl } from '../../utils/routes';
import toast from 'react-hot-toast';

interface PipelineStageDef {
  id: string;
  name: string;
  description: string;
  icon: any;
  isAiReserved?: boolean;
}

const PIPELINE_STAGES: PipelineStageDef[] = [
  {
    id: 'created',
    name: 'Created',
    description: 'Scan record initialized and bound to immutable snapshot.',
    icon: Shield,
  },
  {
    id: 'queued',
    name: 'Queued',
    description: 'Enqueued in Celery worker task backlog.',
    icon: Clock,
  },
  {
    id: 'preparing',
    name: 'Preparing',
    description: 'Setting up isolated sandbox execution environment.',
    icon: FolderGit2,
  },
  {
    id: 'checkout',
    name: 'Checkout',
    description: 'Retrieving immutable source snapshot archive from storage.',
    icon: FileCode2,
  },
  {
    id: 'preprocessing',
    name: 'Preprocessing',
    description: 'Discovering files, validating manifests, and checking encodings.',
    icon: Layers,
  },
  {
    id: 'static_analysis',
    name: 'Static Analysis',
    description: 'Executing static analysis engine and Joern CLI parsers.',
    icon: Cpu,
  },
  {
    id: 'graph_processing',
    name: 'Graph Processing',
    description: 'Generating canonical AST, CFG, PDG, CPG, and Call Graph.',
    icon: Network,
  },
  {
    id: 'ai_analysis',
    name: 'AI Analysis',
    description: 'Deep learning classification (Phase 5 reserved — not configured).',
    icon: Cpu,
    isAiReserved: true,
  },
  {
    id: 'post_processing',
    name: 'Post-Processing',
    description: 'Propagating taint and extracting attack path evidence.',
    icon: Layers,
  },
  {
    id: 'completed',
    name: 'Completed',
    description: 'All canonical graph artifacts and taint evidence stored.',
    icon: Check,
  },
];

const STAGE_ORDER = PIPELINE_STAGES.map((s) => s.id);

export default function ScanProgress() {
  const params = useParams<{ id?: string; projectId?: string; scanId?: string }>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const id = params.projectId || params.id;
  const rawScanId = params.scanId || searchParams.get('scan_id') || searchParams.get('scan');
  const [scan, setScan] = useState<Scan | null>(null);

  useEffect(() => {
    if (!rawScanId) return;
    scanService.getScan(rawScanId).then((data) => {
      setScan(data);
      const canonicalProject = data.project_public_id || data.project_id || id;
      const canonicalScan = data.public_id || data.id || rawScanId;
      if ((data.public_id && rawScanId === data.id && rawScanId !== data.public_id) ||
          (data.project_public_id && id === data.project_id && id !== data.project_public_id)) {
        navigate(getScanProgressUrl(canonicalProject, canonicalScan), { replace: true });
      }
    }).catch(() => {});
  }, [rawScanId, id, navigate]);

  const scanId = scan?.public_id || rawScanId;
  const { status, progress, currentStage, errorMessage } = useScanProgress(rawScanId);
  const [isCancelling, setIsCancelling] = useState(false);

  // Determine stage progression index
  const activeStageId = (currentStage || status || 'created').toLowerCase();
  let currentIndex = STAGE_ORDER.indexOf(activeStageId);
  if (currentIndex === -1) {
    if (status === 'completed') currentIndex = STAGE_ORDER.length - 1;
    else if (status === 'running') currentIndex = 5;
    else currentIndex = 1;
  }

  const isCompleted = status === 'completed';
  const isFailed = status === 'failed';
  const isCancelled = status === 'cancelled';
  const isTimedOut = status === 'timed_out';
  const isTerminal = isCompleted || isFailed || isCancelled || isTimedOut;

  const handleCancel = useCallback(async () => {
    if (!rawScanId || isCancelling) return;
    setIsCancelling(true);
    try {
      await scanService.cancelScan(rawScanId);
      toast.success('Scan cancellation requested.');
    } catch (err: any) {
      toast.error(err?.response?.data?.message || 'Failed to cancel scan.');
    } finally {
      setIsCancelling(false);
    }
  }, [rawScanId, isCancelling]);

  if (!rawScanId) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh]">
        <AlertCircle className="w-12 h-12 text-muted-foreground mb-4" />
        <p className="text-muted-foreground">No scan ID provided.</p>
        <Button className="mt-4" onClick={() => navigate(getProjectUrl(id))}>
          Back to Project
        </Button>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto py-8 px-4">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold font-display text-foreground">
              Scan Pipeline Execution
            </h1>
            <Badge
              variant={
                isCompleted
                  ? 'safe'
                  : isFailed
                  ? 'destructive'
                  : isCancelled || isTimedOut
                  ? 'warning'
                  : 'default'
              }
            >
              {status.toUpperCase().replace('_', ' ')}
            </Badge>
          </div>
          <p className="text-xs text-muted-foreground font-mono mt-1">
            Scan ID: {scanId}
          </p>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2">
          {!isTerminal && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleCancel}
              disabled={isCancelling}
              className="text-destructive hover:bg-destructive/10 border-destructive/30"
            >
              <StopCircle className="w-4 h-4 mr-1.5" />
              {isCancelling ? 'Cancelling...' : 'Cancel Scan'}
            </Button>
          )}

          {isCompleted && (
            <Button
              size="sm"
              onClick={() => navigate(getResultsUrl(scan?.project_public_id || id, scan?.public_id || scanId))}
              className="gap-1.5 shadow-sm"
            >
              View Analysis Results <ArrowRight className="w-4 h-4" />
            </Button>
          )}

          <Link to={getProjectUrl(scan?.project_public_id || id)}>
            <Button variant="ghost" size="sm">
              Back to Project
            </Button>
          </Link>
        </div>
      </div>

      {/* Main Execution Card */}
      <Card className="p-6 border-border relative overflow-hidden bg-card/60">
        {/* Top Continuous Progress Bar */}
        <div className="absolute top-0 left-0 w-full h-1.5 bg-muted">
          <motion.div
            className={`h-full ${
              isCompleted
                ? 'bg-emerald-500'
                : isFailed
                ? 'bg-destructive'
                : isCancelled || isTimedOut
                ? 'bg-amber-500'
                : 'bg-primary'
            }`}
            initial={{ width: '0%' }}
            animate={{ width: `${Math.min(100, Math.max(5, progress))}%` }}
            transition={{ duration: 0.4 }}
          />
        </div>

        {/* Status Banner */}
        <div className="flex items-center justify-between py-2 border-b border-border/60 mb-6">
          <div className="flex items-center gap-2 text-sm">
            {!isTerminal ? (
              <>
                <Loader2 className="w-4 h-4 text-primary animate-spin" />
                <span className="text-foreground font-medium">
                  Current Stage:{' '}
                  <span className="text-primary capitalize">
                    {activeStageId.replace('_', ' ')}
                  </span>
                </span>
              </>
            ) : isCompleted ? (
              <>
                <Check className="w-4 h-4 text-emerald-400" />
                <span className="text-emerald-400 font-medium">
                  Static Analysis & Graph Pipeline Completed Successfully
                </span>
              </>
            ) : isCancelled ? (
              <>
                <StopCircle className="w-4 h-4 text-amber-400" />
                <span className="text-amber-400 font-medium">
                  Scan was cancelled by user request
                </span>
              </>
            ) : isTimedOut ? (
              <>
                <Clock className="w-4 h-4 text-amber-400" />
                <span className="text-amber-400 font-medium">
                  Scan execution timed out
                </span>
              </>
            ) : (
              <>
                <XCircle className="w-4 h-4 text-destructive" />
                <span className="text-destructive font-medium">
                  Scan Execution Failed
                </span>
              </>
            )}
          </div>
          <span className="text-sm font-semibold text-foreground">
            {Math.round(progress)}%
          </span>
        </div>

        {/* Error diagnostics banner */}
        {errorMessage && isTerminal && !isCompleted && (
          <div className="mb-6 p-3.5 rounded-lg bg-destructive/10 border border-destructive/30 text-xs text-destructive flex items-start gap-2.5">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
            <div className="flex-1">
              <span className="font-semibold">Execution Error: </span>
              {errorMessage}
            </div>
          </div>
        )}

        {/* Real 10-Stage Pipeline Timeline */}
        <div className="space-y-3">
          {PIPELINE_STAGES.map((stage, idx) => {
            const isStageDone = isCompleted || idx < currentIndex;
            const isStageActive = idx === currentIndex && !isTerminal;
            const isStageFailed = idx === currentIndex && isFailed;

            return (
              <div
                key={stage.id}
                className={`flex items-center justify-between p-3 rounded-lg border transition-all ${
                  isStageActive
                    ? 'border-primary/50 bg-primary/5 shadow-sm'
                    : isStageDone
                    ? 'border-border/40 bg-card/40'
                    : isStageFailed
                    ? 'border-destructive/40 bg-destructive/5'
                    : 'border-border/30 bg-muted/10 opacity-50'
                }`}
              >
                <div className="flex items-center gap-3.5 min-w-0">
                  {/* Step status circle */}
                  <div
                    className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 text-xs font-semibold ${
                      isStageDone
                        ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                        : isStageActive
                        ? 'bg-primary/20 text-primary border border-primary animate-pulse'
                        : isStageFailed
                        ? 'bg-destructive/20 text-destructive border border-destructive'
                        : 'bg-muted text-muted-foreground border border-border'
                    }`}
                  >
                    {isStageDone ? (
                      <Check className="w-4 h-4" />
                    ) : isStageActive ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : isStageFailed ? (
                      <XCircle className="w-4 h-4" />
                    ) : (
                      <span>{idx + 1}</span>
                    )}
                  </div>

                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span
                        className={`text-sm font-medium ${
                          isStageActive
                            ? 'text-primary font-semibold'
                            : isStageDone
                            ? 'text-foreground'
                            : 'text-muted-foreground'
                        }`}
                      >
                        {stage.name}
                      </span>

                      {stage.isAiReserved && (
                        <span className="text-[10px] px-2 py-0.5 rounded bg-muted text-muted-foreground border border-border font-medium">
                          Phase 5 Reserved (Not Configured)
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground truncate">
                      {stage.description}
                    </p>
                  </div>
                </div>

                {/* State Tag */}
                <div className="shrink-0 text-xs">
                  {isStageDone ? (
                    <span className="text-emerald-400 font-medium">Completed</span>
                  ) : isStageActive ? (
                    <span className="text-primary font-medium flex items-center gap-1">
                      <span className="w-1.5 h-1.5 rounded-full bg-primary animate-ping" />
                      In Progress
                    </span>
                  ) : isStageFailed ? (
                    <span className="text-destructive font-medium">Failed</span>
                  ) : (
                    <span className="text-muted-foreground">Pending</span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </Card>
    </div>
  );
}
