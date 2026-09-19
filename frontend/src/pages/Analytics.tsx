import React, { useEffect, useState, useCallback } from 'react';
import {
  BarChart3,
  ShieldCheck,
  AlertTriangle,
  TrendingDown,
  Clock,
  CheckCircle2,
  RefreshCw,
  GitCompare,
  Layers,
  ArrowUpRight,
  ArrowDownRight,
  Filter,
} from 'lucide-react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  AreaChart,
  Area,
  Cell,
} from 'recharts';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { Spinner } from '../components/ui/Spinner';
import { analyticsService } from '../services/analyticsService';
import { projectService } from '../services/projectService';
import { scanService } from '../services/scanService';
import { AnalyticsMetrics, Project, Scan, ScanComparisonResult } from '../types';
import { useAuthStore } from '../store';
import toast from 'react-hot-toast';

const SEVERITY_COLORS: Record<string, string> = {
  critical: '#ef4444',
  high: '#f97316',
  medium: '#eab308',
  low: '#3b82f6',
  info: '#64748b',
};

export default function Analytics() {
  const { activeOrganization } = useAuthStore();
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>('all');
  const [dateRange, setDateRange] = useState<'7d' | '30d' | '90d' | 'all'>('30d');

  const [metrics, setMetrics] = useState<AnalyticsMetrics | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Scan Comparison State
  const [projectScans, setProjectScans] = useState<Scan[]>([]);
  const [baselineScanId, setBaselineScanId] = useState<string>('');
  const [currentScanId, setCurrentScanId] = useState<string>('');
  const [comparisonResult, setComparisonResult] = useState<ScanComparisonResult | null>(null);
  const [isComparing, setIsComparing] = useState<boolean>(false);

  // 1. Fetch Projects
  useEffect(() => {
    projectService
      .listProjects({ page_size: 100 })
      .then((res) => {
        setProjects(res.items || []);
      })
      .catch(() => {});
  }, [activeOrganization?.id]);

  // 2. Fetch Authoritative Analytics
  const fetchAnalytics = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      let res: AnalyticsMetrics;
      if (selectedProjectId === 'all') {
        res = await analyticsService.getOrganizationAnalytics();
      } else {
        res = await analyticsService.getProjectAnalytics(selectedProjectId);
      }
      setMetrics(res);
    } catch (err: any) {
      setError(err?.response?.data?.message || 'Failed to load authoritative analytics');
    } finally {
      setIsLoading(false);
    }
  }, [selectedProjectId]);

  useEffect(() => {
    fetchAnalytics();
  }, [fetchAnalytics]);

  // 3. Fetch Scans for Comparison when project is selected
  useEffect(() => {
    if (selectedProjectId === 'all') {
      setProjectScans([]);
      setComparisonResult(null);
      return;
    }
    scanService
      .listScans({ project_id: selectedProjectId, page_size: 50 })
      .then((res) => {
        const completed = (res.items || []).filter((s) => s.status === 'completed');
        setProjectScans(completed);
        if (completed.length >= 2) {
          setBaselineScanId(completed[1].id);
          setCurrentScanId(completed[0].id);
        } else if (completed.length === 1) {
          setCurrentScanId(completed[0].id);
          setBaselineScanId('');
        }
      })
      .catch(() => {});
  }, [selectedProjectId]);

  // 4. Handle Scan Comparison
  const handleCompare = async () => {
    if (!baselineScanId || !currentScanId) {
      toast.error('Please select both a baseline and current scan');
      return;
    }
    setIsComparing(true);
    try {
      const res = await analyticsService.compareScans(
        selectedProjectId,
        baselineScanId,
        currentScanId
      );
      setComparisonResult(res);
      toast.success('Authoritative scan comparison completed');
    } catch (err: any) {
      toast.error(err?.response?.data?.message || 'Failed to compare scans');
    } finally {
      setIsComparing(false);
    }
  };

  const getRatingBadge = (rating: string) => {
    switch (rating) {
      case 'A':
        return <span className="text-emerald-500 font-bold text-2xl">A</span>;
      case 'B':
        return <span className="text-sky-500 font-bold text-2xl">B</span>;
      case 'C':
        return <span className="text-amber-500 font-bold text-2xl">C</span>;
      case 'D':
        return <span className="text-orange-500 font-bold text-2xl">D</span>;
      default:
        return <span className="text-rose-500 font-bold text-2xl">F</span>;
    }
  };

  // Format Severity breakdown for Chart
  const severityChartData = metrics
    ? Object.entries(metrics.severity_breakdown).map(([sev, count]) => ({
        severity: sev.toUpperCase(),
        count: count,
        color: SEVERITY_COLORS[sev.toLowerCase()] || '#64748b',
      }))
    : [];

  // Format CWE breakdown for Chart
  const cweChartData = metrics?.cwe_distribution || [];

  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-12">
      {/* Header & Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold font-display tracking-tight text-foreground">
            Project Security Analytics
          </h1>
          <p className="text-xs text-muted-foreground mt-1">
            {selectedProjectId !== 'all'
              ? `Authoritative security metrics and trend analysis for ${
                  projects.find((p) => (p.public_id || p.id) === selectedProjectId)?.name || 'Selected Project'
                }.`
              : `Authoritative security metrics across projects in ${
                  activeOrganization?.name || 'Workspace'
                }.`}
          </p>
        </div>

        <div className="flex items-center gap-2">
          {/* Scope Select */}
          <select
            className="h-8 rounded-md border border-input bg-background px-2.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
            value={selectedProjectId}
            onChange={(e) => setSelectedProjectId(e.target.value)}
          >
            <option value="all">Organization-Wide (All Projects)</option>
            {projects.map((p) => (
              <option key={p.id} value={p.public_id || p.id}>
                {p.name}
              </option>
            ))}
          </select>

          <Button
            variant="outline"
            size="sm"
            onClick={fetchAnalytics}
            disabled={isLoading}
            className="gap-1.5 h-8 text-xs shrink-0"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} /> Refresh
          </Button>
        </div>
      </div>

      {isLoading ? (
        <div className="py-24 text-center">
          <Spinner className="w-8 h-8 mx-auto text-primary" />
          <p className="text-xs text-muted-foreground mt-3">Computing authoritative metrics...</p>
        </div>
      ) : error ? (
        <Card className="border-destructive/30 bg-destructive/5 p-6 text-center">
          <div className="flex flex-col items-center justify-center gap-3">
            <AlertTriangle className="w-8 h-8 text-destructive" />
            <h3 className="text-sm font-semibold text-foreground">Failed to load analytics</h3>
            <p className="text-xs text-muted-foreground">{error}</p>
            <Button size="sm" variant="outline" onClick={fetchAnalytics} className="gap-2 mt-2">
              Retry
            </Button>
          </div>
        </Card>
      ) : !metrics ? (
        <Card className="p-12 text-center">
          <p className="text-sm text-muted-foreground">No data for selected period</p>
        </Card>
      ) : (
        <>
          {/* Top Row: Security Health Score & Core KPIs */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Health Score Card */}
            <Card className="p-4 border-border/80 flex flex-col justify-between">
              <div>
                <div className="flex justify-between items-start">
                  <p className="text-xs font-medium text-muted-foreground">Security Health Score</p>
                  <Badge variant="outline" className="text-[10px] uppercase font-mono">
                    {metrics.health_score?.version || 'v1.0.0'}
                  </Badge>
                </div>
                {metrics.health_score?.status === 'NO_DATA' || metrics.health_score?.score === null || metrics.health_score?.score === undefined ? (
                  <div className="mt-3">
                    <div className="flex items-center gap-2">
                      <span className="text-xl font-bold text-muted-foreground">No data</span>
                      <Badge variant="outline" className="text-[10px] bg-muted/30 text-muted-foreground">
                        Unscored
                      </Badge>
                    </div>
                    <p className="text-xs text-muted-foreground mt-2">
                      Run your first security scan to establish a security health score.
                    </p>
                  </div>
                ) : (
                  <div className="flex items-baseline gap-3 mt-3">
                    <span className="text-3xl font-extrabold text-foreground tracking-tight">
                      {Math.round(metrics.health_score.score)}
                    </span>
                    <span className="text-xs text-muted-foreground">/ 100</span>
                    <div className="ml-auto flex items-center gap-1.5">
                      <span className="text-xs text-muted-foreground">Rating:</span>
                      {getRatingBadge(metrics.health_score.rating || 'A')}
                    </div>
                  </div>
                )}
              </div>
              <p className="text-[11px] text-muted-foreground mt-3 pt-2 border-t border-border/40">
                Authoritative formula based on active vulnerabilities and remediation velocity.
              </p>
            </Card>

            {/* Active & Critical Findings */}
            <Card className="p-4 border-border/80 flex flex-col justify-between">
              <div>
                <div className="flex justify-between items-start">
                  <p className="text-xs font-medium text-muted-foreground">Active Findings</p>
                  <ShieldCheck className="w-4 h-4 text-primary" />
                </div>
                <div className="mt-3">
                  <div className="text-3xl font-extrabold text-foreground tracking-tight">
                    {metrics.active_findings}
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    {metrics.critical_findings > 0 ? (
                      <span className="text-rose-500 font-semibold">
                        {metrics.critical_findings} Critical
                      </span>
                    ) : (
                      <span className="text-emerald-500 font-medium">0 Critical</span>
                    )}{' '}
                    requiring immediate action
                  </p>
                </div>
              </div>
              <div className="text-[11px] text-muted-foreground pt-2 border-t border-border/40">
                Total lifecycle observations: {metrics.total_findings}
              </div>
            </Card>

            {/* Remediation Rate & MTTR */}
            <Card className="p-4 border-border/80 flex flex-col justify-between">
              <div>
                <div className="flex justify-between items-start">
                  <p className="text-xs font-medium text-muted-foreground">Remediation Rate</p>
                  <TrendingDown className="w-4 h-4 text-emerald-500" />
                </div>
                <div className="mt-3">
                  <div className="text-3xl font-extrabold text-foreground tracking-tight">
                    {Math.round(metrics.remediation_rate * 100)}%
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    {metrics.resolved_findings} of {metrics.total_findings} findings resolved
                  </p>
                </div>
              </div>
              <div className="text-[11px] text-muted-foreground pt-2 border-t border-border/40 flex justify-between">
                <span>MTTR:</span>
                <span className="font-semibold text-foreground">
                  {metrics.mttr_hours !== null ? `${metrics.mttr_hours} hrs` : 'N/A'}
                </span>
              </div>
            </Card>

            {/* False Positive Rate */}
            <Card className="p-4 border-border/80 flex flex-col justify-between">
              <div>
                <div className="flex justify-between items-start">
                  <p className="text-xs font-medium text-muted-foreground">False Positive Rate</p>
                  <Clock className="w-4 h-4 text-muted-foreground" />
                </div>
                <div className="mt-3">
                  <div className="text-3xl font-extrabold text-foreground tracking-tight">
                    {Math.round(metrics.false_positive_rate * 100)}%
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    Marked via human review lifecycle
                  </p>
                </div>
              </div>
              <div className="text-[11px] text-muted-foreground pt-2 border-t border-border/40">
                Authoritative verification metrics
              </div>
            </Card>
          </div>

          {/* Charts Row */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Severity Distribution */}
            <Card className="border-border/80">
              <CardHeader className="pb-2 border-b border-border/40">
                <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
                  <BarChart3 className="w-4 h-4 text-primary" /> Active Severity Distribution
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-4">
                {severityChartData.every((d) => d.count === 0) ? (
                  <div className="h-64 flex items-center justify-center text-xs text-muted-foreground">
                    0 findings across all severity levels
                  </div>
                ) : (
                  <div className="h-64 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={severityChartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#334155" opacity={0.3} />
                        <XAxis dataKey="severity" stroke="#94a3b8" fontSize={11} />
                        <YAxis stroke="#94a3b8" fontSize={11} allowDecimals={false} />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: '#0f172a',
                            borderColor: '#334155',
                            borderRadius: '6px',
                            fontSize: '12px',
                          }}
                        />
                        <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                          {severityChartData.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={entry.color} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Top CWE Categories */}
            <Card className="border-border/80">
              <CardHeader className="pb-2 border-b border-border/40">
                <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
                  <Layers className="w-4 h-4 text-primary" /> Top CWE Classifications
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-4">
                {cweChartData.length === 0 ? (
                  <div className="h-64 flex items-center justify-center text-xs text-muted-foreground">
                    No CWE vulnerabilities detected
                  </div>
                ) : (
                  <div className="h-64 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart
                        data={cweChartData}
                        layout="vertical"
                        margin={{ top: 10, right: 20, left: 30, bottom: 0 }}
                      >
                        <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#334155" opacity={0.3} />
                        <XAxis type="number" stroke="#94a3b8" fontSize={11} allowDecimals={false} />
                        <YAxis dataKey="cwe_id" type="category" stroke="#94a3b8" fontSize={11} />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: '#0f172a',
                            borderColor: '#334155',
                            borderRadius: '6px',
                            fontSize: '12px',
                          }}
                        />
                        <Bar dataKey="count" fill="#38bdf8" radius={[0, 4, 4, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Scan Comparison Tool */}
          {selectedProjectId !== 'all' && (
            <Card className="border-border/80">
              <CardHeader className="pb-3 border-b border-border/40">
                <CardTitle className="text-sm font-semibold flex items-center gap-2">
                  <GitCompare className="w-4 h-4 text-primary" /> Authoritative Scan-to-Scan Comparison
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-4 space-y-4">
                {projectScans.length < 2 ? (
                  <div className="py-6 text-center">
                    <p className="text-xs font-semibold text-muted-foreground">No comparable baseline</p>
                    <p className="text-[11px] text-muted-foreground mt-1 max-w-sm mx-auto">
                      At least two completed scans within the selected project are required to perform an authoritative finding diff comparison.
                    </p>
                  </div>
                ) : (
                  <>
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 items-end">
                      <div>
                        <label className="block text-xs font-medium text-muted-foreground mb-1.5">
                          Baseline Scan
                        </label>
                        <select
                          className="w-full h-9 rounded-md border border-input bg-background px-3 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                          value={baselineScanId}
                          onChange={(e) => setBaselineScanId(e.target.value)}
                        >
                          <option value="">Select baseline scan...</option>
                          {projectScans.map((s) => (
                            <option key={s.id} value={s.id}>
                              {s.public_id} ({s.completed_at ? new Date(s.completed_at).toLocaleDateString() : ''})
                            </option>
                          ))}
                        </select>
                      </div>

                      <div>
                        <label className="block text-xs font-medium text-muted-foreground mb-1.5">
                          Current / Target Scan
                        </label>
                        <select
                          className="w-full h-9 rounded-md border border-input bg-background px-3 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                          value={currentScanId}
                          onChange={(e) => setCurrentScanId(e.target.value)}
                        >
                          <option value="">Select current scan...</option>
                          {projectScans.map((s) => (
                            <option key={s.id} value={s.id}>
                              {s.public_id} ({s.completed_at ? new Date(s.completed_at).toLocaleDateString() : ''})
                            </option>
                          ))}
                        </select>
                      </div>

                      <Button
                        onClick={handleCompare}
                        disabled={isComparing || !baselineScanId || !currentScanId}
                        className="h-9 gap-2 text-xs font-medium"
                      >
                        {isComparing ? <Spinner className="w-3.5 h-3.5" /> : <GitCompare className="w-3.5 h-3.5" />}
                        Compare Scans
                      </Button>
                    </div>

                    {comparisonResult && (
                      <div className="mt-4 pt-4 border-t border-border/40 space-y-3">
                        <div className="grid grid-cols-3 gap-3 text-center">
                          <div className="p-3 bg-muted/20 rounded-md border border-border/40">
                            <p className="text-xs text-muted-foreground">Existing Findings</p>
                            <p className="text-xl font-bold text-foreground mt-1">
                              {comparisonResult.existing_count}
                            </p>
                          </div>
                          <div className="p-3 bg-rose-500/10 rounded-md border border-rose-500/20">
                            <p className="text-xs text-rose-400">New Findings (Introduced)</p>
                            <p className="text-xl font-bold text-rose-500 mt-1">
                              +{comparisonResult.new_count}
                            </p>
                          </div>
                          <div className="p-3 bg-emerald-500/10 rounded-md border border-emerald-500/20">
                            <p className="text-xs text-emerald-400">Fixed Findings (Resolved)</p>
                            <p className="text-xl font-bold text-emerald-500 mt-1">
                              {comparisonResult.fixed_count}
                            </p>
                          </div>
                        </div>

                    {comparisonResult.new_findings.length > 0 && (
                      <div className="mt-3">
                        <h4 className="text-xs font-semibold text-rose-400 mb-2">
                          New Findings in Current Scan
                        </h4>
                        <div className="space-y-1.5">
                          {comparisonResult.new_findings.map((f) => (
                            <div
                              key={f.id}
                              className="p-2 bg-muted/30 rounded border border-border/40 flex items-center justify-between text-xs"
                            >
                              <span className="font-medium text-foreground">{f.title}</span>
                              <Badge variant="outline" className="text-[10px] uppercase">
                                {f.severity}
                              </Badge>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </>
            )}
          </CardContent>
        </Card>
      )}
        </>
      )}
    </div>
  );
}
