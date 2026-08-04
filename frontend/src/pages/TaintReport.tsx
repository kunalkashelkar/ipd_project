import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import clsx from 'clsx';
import {
  FiLoader, FiAlertCircle, FiCheckCircle,
  FiAlertTriangle, FiShield, FiArrowRight,
} from 'react-icons/fi';
import { getTaintStatus, getTaintReport, TaintStatusResponse, TaintReportResponse, AttackPath } from '../services/api';

const POLL_MS = 3000;

const SEVERITY_CONFIG: Record<string, { color: string; bg: string; border: string; icon: React.ReactNode }> = {
  CRITICAL: { color: 'text-red-700', bg: 'bg-red-50', border: 'border-red-200', icon: <FiAlertCircle className="w-4 h-4" /> },
  HIGH: { color: 'text-orange-700', bg: 'bg-orange-50', border: 'border-orange-200', icon: <FiAlertTriangle className="w-4 h-4" /> },
  MEDIUM: { color: 'text-yellow-700', bg: 'bg-yellow-50', border: 'border-yellow-200', icon: <FiAlertTriangle className="w-4 h-4" /> },
  LOW: { color: 'text-blue-700', bg: 'bg-blue-50', border: 'border-blue-200', icon: <FiShield className="w-4 h-4" /> },
  SAFE: { color: 'text-emerald-700', bg: 'bg-emerald-50', border: 'border-emerald-200', icon: <FiCheckCircle className="w-4 h-4" /> },
};

function SeverityBadge({ severity }: { severity: string }) {
  const cfg = SEVERITY_CONFIG[severity] ?? SEVERITY_CONFIG.SAFE;
  return (
    <span className={clsx('inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold border', cfg.color, cfg.bg, cfg.border)}>
      {cfg.icon} {severity}
    </span>
  );
}

function StatCard({ label, value, color = 'text-surface-900' }: { label: string; value: number; color?: string }) {
  return (
    <div className="bg-white rounded-xl border border-surface-200 p-4 text-center shadow-sm">
      <div className={clsx('text-3xl font-bold', color)}>{value}</div>
      <div className="text-xs text-surface-500 mt-1 font-medium uppercase tracking-wide">{label}</div>
    </div>
  );
}

function PathRow({ path, expanded, onToggle }: { path: AttackPath; expanded: boolean; onToggle: () => void }) {
  const cfg = SEVERITY_CONFIG[path.severity] ?? SEVERITY_CONFIG.SAFE;
  return (
    <div className={clsx('rounded-xl border mb-3 overflow-hidden', cfg.border)}>
      <button
        onClick={onToggle}
        className={clsx('w-full flex items-center gap-3 px-4 py-3 text-left hover:opacity-90 transition-opacity', cfg.bg)}
      >
        <SeverityBadge severity={path.severity} />
        <span className="flex-1 text-sm font-medium text-surface-800 truncate">
          {path.source_code || 'source'} → {path.sink_code || 'sink'}
        </span>
        <span className="text-xs text-surface-400">{path.length} hops</span>
        <span className={clsx('text-xs font-bold', cfg.color)}>
          score: {path.risk_score.toFixed(1)}
        </span>
        {path.sanitized && (
          <span className="text-xs text-emerald-600 font-medium bg-emerald-100 px-2 py-0.5 rounded-full">sanitized</span>
        )}
        <FiArrowRight className={clsx('w-4 h-4 text-surface-400 transition-transform', expanded && 'rotate-90')} />
      </button>

      {expanded && (
        <div className="px-4 py-3 border-t border-surface-100 bg-white animate-fade-in">
          <div className="grid grid-cols-2 gap-2 text-xs mb-3">
            <div><span className="text-surface-400">Category:</span> <span className="font-medium">{path.sink_category}</span></div>
            <div><span className="text-surface-400">File:</span> <span className="font-mono">{path.filename ?? 'unknown'}</span></div>
            <div><span className="text-surface-400">Source line:</span> <span>{path.source_line ?? '?'}</span></div>
            <div><span className="text-surface-400">Sink line:</span> <span>{path.sink_line ?? '?'}</span></div>
          </div>

          <div className="flex flex-wrap gap-1 items-center text-xs">
            {path.nodes.map((n, i) => (
              <React.Fragment key={n}>
                <span className={clsx(
                  'px-2 py-1 rounded font-mono',
                  n === path.source_node_id ? 'bg-green-100 text-green-800' :
                    n === path.sink_node_id ? 'bg-red-100 text-red-800' :
                      path.sanitized && path.nodes.indexOf(n) > 0 ? 'bg-yellow-100 text-yellow-800' :
                        'bg-surface-100 text-surface-600',
                )}>
                  {n.length > 8 ? n.slice(0, 8) + '…' : n}
                </span>
                {i < path.nodes.length - 1 && <span className="text-surface-300">→</span>}
              </React.Fragment>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default function TaintReport() {
  const { taintJobId } = useParams<{ taintJobId: string }>();
  const [status, setStatus] = useState<TaintStatusResponse | null>(null);
  const [report, setReport] = useState<TaintReportResponse | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!taintJobId) return;
    let timer: ReturnType<typeof setInterval>;

    const poll = async () => {
      try {
        const s = await getTaintStatus(taintJobId);
        setStatus(s);
        if (s.status === 'completed') {
          clearInterval(timer);
          const r = await getTaintReport(taintJobId);
          setReport(r);
        } else if (s.status === 'failed') {
          clearInterval(timer);
        }
      } catch {
        setError('Failed to fetch taint status.');
        clearInterval(timer);
      }
    };

    poll();
    timer = setInterval(poll, POLL_MS);
    return () => clearInterval(timer);
  }, [taintJobId]);

  const isLoading = !status || status.status === 'queued' || status.status === 'running';

  return (
    <div className="max-w-4xl mx-auto py-8 animate-slide-up">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold text-surface-900">Taint Analysis Report</h1>
          <p className="text-sm text-surface-400 font-mono mt-1">{taintJobId}</p>
        </div>
        {taintJobId && status?.status === 'completed' && (
          <Link to={`/graph/taint/${taintJobId}`} className="btn-primary text-sm">
            View Security Graph →
          </Link>
        )}
      </div>

      {error && <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 mb-6">{error}</div>}

      {/* Loading state */}
      {isLoading && (
        <div className="flex items-center gap-3 p-6 bg-primary-50 border border-primary-200 rounded-xl text-primary-600 mb-6 animate-pulse-slow">
          <FiLoader className="animate-spin w-5 h-5" />
          <span className="font-medium capitalize">{status?.status ?? 'Loading'} — performing taint analysis…</span>
        </div>
      )}

      {/* Summary stats */}
      {status && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-8">
          <StatCard label="Sources" value={status.source_count} color="text-primary-600" />
          <StatCard label="Sinks" value={status.sink_count} color="text-red-600" />
          <StatCard label="Tainted Nodes" value={status.tainted_node_count} color="text-yellow-600" />
          <StatCard label="Attack Paths" value={status.attack_path_count} color="text-purple-600" />
        </div>
      )}

      {/* Severity breakdown */}
      {status && status.status === 'completed' && (
        <div className="grid grid-cols-4 gap-3 mb-8 animate-fade-in">
          <StatCard label="Critical" value={status.critical_path_count} color="text-red-700" />
          <StatCard label="High" value={status.high_path_count} color="text-orange-600" />
          <StatCard label="Medium" value={status.medium_path_count} color="text-yellow-600" />
          <StatCard label="Low" value={status.low_path_count} color="text-blue-600" />
        </div>
      )}

      {/* Attack paths list */}
      {report && (
        <div className="animate-fade-in">
          <h2 className="text-lg font-semibold text-surface-800 mb-4">
            Attack Paths ({report.attack_paths.length})
          </h2>
          {report.attack_paths.length === 0 ? (
            <div className="flex items-center gap-3 p-6 bg-emerald-50 border border-emerald-200 rounded-xl text-emerald-700">
              <FiCheckCircle className="w-5 h-5" />
              <span className="font-medium">No attack paths detected — no direct taint flow from sources to sinks.</span>
            </div>
          ) : (
            report.attack_paths.map(path => (
              <PathRow
                key={path.path_id}
                path={path}
                expanded={expanded === path.path_id}
                onToggle={() => setExpanded(prev => prev === path.path_id ? null : path.path_id)}
              />
            ))
          )}
        </div>
      )}

      {/* Failed state */}
      {status?.status === 'failed' && status.error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm font-mono">
          {status.error}
        </div>
      )}
    </div>
  );
}
