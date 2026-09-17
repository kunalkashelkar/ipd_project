import React, { useEffect, useState } from 'react';
import {
  BarChart3,
  AlertTriangle,
  ShieldCheck,
  Activity,
  RefreshCw,
  FolderOpen,
  Info,
} from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Spinner } from '../components/ui/Spinner';
import { analyticsService } from '../services/analyticsService';
import { DashboardMetrics } from '../types';
import { useAuthStore } from '../store';

export default function Analytics() {
  const { activeOrganization } = useAuthStore();
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAnalytics = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await analyticsService.getDashboardMetrics();
      setMetrics(data);
    } catch (err: any) {
      setError(
        err?.response?.data?.message ||
        err?.message ||
        'Failed to load analytics metrics'
      );
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalytics();
  }, [activeOrganization?.id]);

  const totalScans = metrics?.total_scans ?? 0;
  const criticalIssues =
    metrics?.severity_breakdown?.critical ??
    metrics?.severity_breakdown?.CRITICAL ??
    0;
  const totalFindings = metrics?.total_vulnerabilities ?? 0;
  const totalProjects = metrics?.total_projects ?? 0;

  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-12">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold font-display tracking-tight text-foreground">
            Security Analytics & Posture
          </h1>
          <p className="text-xs text-muted-foreground mt-1">
            Persisted organization security posture for{' '}
            <span className="font-semibold text-foreground">
              {activeOrganization?.name || 'Workspace'}
            </span>
            .
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={fetchAnalytics}
          disabled={isLoading}
          className="gap-2 shrink-0 text-xs"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} /> Refresh
        </Button>
      </div>

      {error ? (
        <Card className="border-destructive/30 bg-destructive/5 p-6 text-center">
          <div className="flex flex-col items-center justify-center gap-3">
            <AlertTriangle className="w-8 h-8 text-destructive" />
            <div>
              <h3 className="text-sm font-semibold text-foreground">Failed to retrieve analytics</h3>
              <p className="text-xs text-muted-foreground mt-1">{error}</p>
            </div>
            <Button size="sm" variant="outline" onClick={fetchAnalytics} className="gap-2 mt-2">
              <RefreshCw className="w-3.5 h-3.5" /> Retry
            </Button>
          </div>
        </Card>
      ) : (
        <>
          {/* Key Metrics Cards from Authoritative Finding & Scan Domain */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card className="p-4 border-border/80">
              <div className="flex justify-between items-start">
                <div>
                  <p className="text-xs font-medium text-muted-foreground mb-1">Active Projects</p>
                  <div className="text-2xl font-bold text-foreground">
                    {isLoading ? <Spinner size="sm" /> : totalProjects}
                  </div>
                </div>
                <div className="p-2 bg-blue-500/10 rounded-lg">
                  <FolderOpen className="w-4 h-4 text-blue-400" />
                </div>
              </div>
              <div className="mt-3 text-[11px] text-muted-foreground">
                Repositories in workspace
              </div>
            </Card>

            <Card className="p-4 border-border/80">
              <div className="flex justify-between items-start">
                <div>
                  <p className="text-xs font-medium text-muted-foreground mb-1">Total Scans</p>
                  <div className="text-2xl font-bold text-foreground">
                    {isLoading ? <Spinner size="sm" /> : totalScans}
                  </div>
                </div>
                <div className="p-2 bg-purple-500/10 rounded-lg">
                  <Activity className="w-4 h-4 text-purple-400" />
                </div>
              </div>
              <div className="mt-3 text-[11px] text-muted-foreground">
                Pipeline runs executed
              </div>
            </Card>

            <Card className="p-4 border-border/80">
              <div className="flex justify-between items-start">
                <div>
                  <p className="text-xs font-medium text-muted-foreground mb-1">Total Findings</p>
                  <div className="text-2xl font-bold text-foreground">
                    {isLoading ? <Spinner size="sm" /> : totalFindings}
                  </div>
                </div>
                <div className="p-2 bg-emerald-500/10 rounded-lg">
                  <ShieldCheck className="w-4 h-4 text-emerald-400" />
                </div>
              </div>
              <div className="mt-3 text-[11px] text-muted-foreground">
                Persistent weaknesses identified
              </div>
            </Card>

            <Card className="p-4 border-destructive/30 bg-destructive/5">
              <div className="flex justify-between items-start">
                <div>
                  <p className="text-xs font-medium text-destructive mb-1">Critical Issues</p>
                  <div className="text-2xl font-bold text-destructive">
                    {isLoading ? <Spinner size="sm" /> : criticalIssues}
                  </div>
                </div>
                <div className="p-2 bg-destructive/10 rounded-lg">
                  <AlertTriangle className="w-4 h-4 text-destructive" />
                </div>
              </div>
              <div className="mt-3 text-[11px] text-destructive/80 font-medium">
                Immediate triage required
              </div>
            </Card>
          </div>

          {/* Explicit Phase 7 Analytics Availability Boundary */}
          <Card className="p-6 border-border/80 bg-card/40">
            <div className="flex items-start gap-3.5">
              <div className="p-2 rounded-lg bg-primary/10 text-primary shrink-0 mt-0.5">
                <Info className="w-5 h-5" />
              </div>
              <div className="space-y-2">
                <h3 className="text-sm font-semibold text-foreground">
                  Platform Analytics Pipeline (Phase 7 Reserved)
                </h3>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  Detailed cross-scan vulnerability trend charts, temporal risk score trajectories, MTTR tracking,
                  and CWE distribution aggregations are part of the Phase 7 Analytics and Compliance reporting milestone.
                  Currently, vulnerability investigation and evidence traces are evaluated directly within individual
                  scan workspaces and project findings lists.
                </p>
                <div className="pt-2 text-xs text-muted-foreground font-mono">
                  Current Engine: <span className="text-foreground">Phase 5 Correlation & Finding Domain</span> (active)
                </div>
              </div>
            </div>
          </Card>
        </>
      )}
    </div>
  );
}
