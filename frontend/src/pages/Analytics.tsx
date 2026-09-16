import React, { useEffect, useState } from 'react';
import {
  BarChart3,
  AlertTriangle,
  ShieldCheck,
  Layers,
  PieChart,
  Activity,
  RefreshCw,
  FolderOpen,
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
  const completedScans = metrics?.completed_scans ?? 0;
  const successRate = Math.round((metrics?.scan_success_rate ?? 0) * 100);

  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-12">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold font-display tracking-tight">Security Analytics</h1>
          <p className="text-muted-foreground mt-1">
            Real platform-wide vulnerability trends and risk metrics for{' '}
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
          className="gap-2 shrink-0"
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
          {/* Key Metrics Cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <Card>
              <CardContent className="p-6">
                <div className="flex justify-between items-start">
                  <div>
                    <p className="text-sm font-medium text-muted-foreground mb-1">Total Scans</p>
                    <div className="text-3xl font-bold text-foreground">
                      {isLoading ? <Spinner size="sm" /> : totalScans}
                    </div>
                  </div>
                  <div className="p-2 bg-primary/10 rounded-lg">
                    <Activity className="w-5 h-5 text-primary" />
                  </div>
                </div>
                <div className="mt-4 flex items-center text-xs text-muted-foreground">
                  <span>{totalScans === 0 ? 'No scans executed yet' : `${totalScans} lifetime scan runs`}</span>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-6">
                <div className="flex justify-between items-start">
                  <div>
                    <p className="text-sm font-medium text-muted-foreground mb-1">Critical Issues</p>
                    <div className="text-3xl font-bold text-foreground">
                      {isLoading ? <Spinner size="sm" /> : criticalIssues}
                    </div>
                  </div>
                  <div className="p-2 bg-destructive/10 rounded-lg">
                    <AlertTriangle className="w-5 h-5 text-destructive" />
                  </div>
                </div>
                <div className="mt-4 flex items-center text-xs text-muted-foreground">
                  <span>
                    {criticalIssues === 0
                      ? 'Zero critical vulnerabilities'
                      : `${criticalIssues} critical findings require triage`}
                  </span>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-6">
                <div className="flex justify-between items-start">
                  <div>
                    <p className="text-sm font-medium text-muted-foreground mb-1">Total Findings</p>
                    <div className="text-3xl font-bold text-foreground">
                      {isLoading ? <Spinner size="sm" /> : totalFindings}
                    </div>
                  </div>
                  <div className="p-2 bg-purple-500/10 rounded-lg">
                    <ShieldCheck className="w-5 h-5 text-purple-400" />
                  </div>
                </div>
                <div className="mt-4 flex items-center text-xs text-muted-foreground">
                  <span>
                    {totalFindings === 0
                      ? 'No vulnerabilities recorded'
                      : `${totalFindings} vulnerabilities identified`}
                  </span>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-6">
                <div className="flex justify-between items-start">
                  <div>
                    <p className="text-sm font-medium text-muted-foreground mb-1">Completed Scans</p>
                    <div className="text-3xl font-bold text-foreground">
                      {isLoading ? <Spinner size="sm" /> : completedScans}
                    </div>
                  </div>
                  <div className="p-2 bg-emerald-500/10 rounded-lg">
                    <ShieldCheck className="w-5 h-5 text-emerald-500" />
                  </div>
                </div>
                <div className="mt-4 flex items-center text-xs text-muted-foreground">
                  <span>{totalScans === 0 ? 'No completed scans yet' : `${successRate}% execution success rate`}</span>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Visualization Section with Honest Empty States */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card className="min-h-[360px] flex flex-col justify-center border-dashed">
              <CardHeader className="text-center pb-2">
                <CardTitle className="text-base text-foreground">Vulnerability Trends Over Time</CardTitle>
              </CardHeader>
              <CardContent className="flex-1 flex items-center justify-center p-6">
                <div className="text-center text-muted-foreground max-w-sm">
                  <div className="w-12 h-12 rounded-full bg-muted/60 flex items-center justify-center mx-auto mb-3">
                    <BarChart3 className="w-6 h-6 text-muted-foreground/60" />
                  </div>
                  <p className="font-medium text-sm text-foreground">No vulnerability trend data</p>
                  <p className="text-xs text-muted-foreground mt-1">
                    Temporal vulnerability plots will automatically populate as security scans are executed across repositories.
                  </p>
                </div>
              </CardContent>
            </Card>

            <Card className="min-h-[360px] flex flex-col justify-center border-dashed">
              <CardHeader className="text-center pb-2">
                <CardTitle className="text-base text-foreground">Issues by CWE Category</CardTitle>
              </CardHeader>
              <CardContent className="flex-1 flex items-center justify-center p-6">
                <div className="text-center text-muted-foreground max-w-sm">
                  <div className="w-12 h-12 rounded-full bg-muted/60 flex items-center justify-center mx-auto mb-3">
                    <PieChart className="w-6 h-6 text-muted-foreground/60" />
                  </div>
                  <p className="font-medium text-sm text-foreground">No CWE distribution recorded</p>
                  <p className="text-xs text-muted-foreground mt-1">
                    Common Weakness Enumerations will categorize here once vulnerabilities are detected by the analysis pipeline.
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
