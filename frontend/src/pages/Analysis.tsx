import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { FiLoader, FiCheckCircle, FiAlertCircle, FiCpu, FiGitMerge, FiCode, FiShield } from 'react-icons/fi';
import clsx from 'clsx';
import { getParseStatus, ParseStatusResponse, analyzeTaint } from '../services/api';

const POLL_INTERVAL_MS = 3000;

function StatCard({ label, value, icon }: { label: string; value: number | string; icon: React.ReactNode }) {
  return (
    <div className="bg-white rounded-xl border border-surface-200 p-4 flex flex-col gap-1 shadow-sm">
      <div className="flex items-center gap-2 text-surface-500 text-sm font-medium">
        {icon}
        {label}
      </div>
      <div className="text-2xl font-bold text-surface-900">{value.toLocaleString()}</div>
    </div>
  );
}

export default function Analysis() {
  const { jobId } = useParams<{ jobId: string }>();
  const [status, setStatus]       = useState<ParseStatusResponse | null>(null);
  const [error, setError]         = useState('');
  const [taintJobId, setTaintJobId] = useState<string | null>(null);
  const [taintTriggered, setTaintTriggered] = useState(false);

  useEffect(() => {
    if (!jobId) return;
    let timer: ReturnType<typeof setInterval>;

    const poll = async () => {
      try {
        const data = await getParseStatus(jobId);
        setStatus(data);
        if (data.status === 'completed') {
          clearInterval(timer);
          // Auto-trigger taint analysis once
          if (!taintTriggered) {
            setTaintTriggered(true);
            try {
              const taintJob = await analyzeTaint(jobId, data.project_id);
              setTaintJobId(taintJob.taint_job_id);
            } catch {
              // Taint trigger is best-effort; don't block the parse result display
            }
          }
        } else if (data.status === 'failed') {
          clearInterval(timer);
        }
      } catch {
        setError('Failed to fetch job status.');
        clearInterval(timer);
      }
    };

    poll();
    timer = setInterval(poll, POLL_INTERVAL_MS);
    return () => clearInterval(timer);
  }, [jobId, taintTriggered]);

  const statusColor: Record<string, string> = {
    queued:    'text-amber-500',
    running:   'text-primary-500',
    completed: 'text-accent-emerald',
    failed:    'text-accent-rose',
  };

  const StatusIcon = () => {
    if (!status) return <FiLoader className="animate-spin w-5 h-5" />;
    if (status.status === 'completed') return <FiCheckCircle className="w-5 h-5 text-accent-emerald" />;
    if (status.status === 'failed') return <FiAlertCircle className="w-5 h-5 text-accent-rose" />;
    return <FiLoader className="animate-spin w-5 h-5 text-primary-500" />;
  };

  return (
    <div className="max-w-3xl mx-auto py-8 animate-slide-up">
      <h1 className="text-3xl font-bold text-surface-900 mb-2">Parsing Analysis</h1>
      <p className="text-surface-500 mb-8 font-mono text-sm">Job ID: {jobId}</p>

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 mb-6">{error}</div>
      )}

      {/* Status banner */}
      <div className={clsx(
        'flex items-center gap-3 p-4 rounded-xl border mb-8 font-semibold',
        status?.status === 'completed' ? 'bg-emerald-50 border-emerald-200' :
        status?.status === 'failed'    ? 'bg-red-50 border-red-200' :
                                         'bg-primary-50 border-primary-200',
      )}>
        <StatusIcon />
        <span className={clsx('capitalize', statusColor[status?.status ?? 'queued'])}>
          {status?.status ?? 'Loading…'}
        </span>
        {status?.status === 'running' && <span className="text-surface-400 text-sm font-normal">— Joern is parsing your code</span>}
      </div>

      {/* Stats grid */}
      {status && status.status === 'completed' && (
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 mb-8 animate-fade-in">
          <StatCard label="Files"       value={status.file_count}     icon={<FiCode className="w-4 h-4" />} />
          <StatCard label="Functions"   value={status.function_count} icon={<FiCpu className="w-4 h-4" />} />
          <StatCard label="AST Nodes"   value={status.ast_nodes}      icon={<FiGitMerge className="w-4 h-4" />} />
          <StatCard label="CFG Nodes"   value={status.cfg_nodes}      icon={<FiGitMerge className="w-4 h-4" />} />
          <StatCard label="DFG Nodes"   value={status.dfg_nodes}      icon={<FiGitMerge className="w-4 h-4" />} />
          <StatCard label="Total Edges" value={status.total_edges}    icon={<FiGitMerge className="w-4 h-4" />} />
        </div>
      )}

      {/* Error detail */}
      {status?.status === 'failed' && status.error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm font-mono mb-6">
          {status.error}
        </div>
      )}

      {/* Actions */}
      {status?.status === 'completed' && jobId && (
        <div className="flex flex-wrap gap-3 animate-fade-in">
          <Link to={`/graph/${jobId}`} className="btn-primary">
            Open Graph Viewer →
          </Link>
          {taintJobId ? (
            <Link
              to={`/taint/${taintJobId}`}
              className="inline-flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white font-semibold rounded-xl transition-all shadow"
            >
              <FiShield className="w-4 h-4" />
              View Taint Report →
            </Link>
          ) : (
            <span className="inline-flex items-center gap-2 px-4 py-2 bg-purple-100 text-purple-500 font-medium rounded-xl text-sm">
              <FiLoader className="w-4 h-4 animate-spin" />
              Queuing taint analysis…
            </span>
          )}
        </div>
      )}
    </div>
  );
}
