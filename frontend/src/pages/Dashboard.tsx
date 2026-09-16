import React, { useEffect, useState } from 'react';
import { ShieldCheck, Activity, FolderOpen, AlertTriangle, ArrowRight, Loader2, Plus } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Link } from 'react-router-dom';
import { useAuthStore } from '../store';
import { analyticsService } from '../services/analyticsService';
import { projectService } from '../services/projectService';
import { Project, DashboardMetrics } from '../types';

export default function Dashboard() {
  const { activeOrganization } = useAuthStore();
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadDashboard() {
      setLoading(true);
      try {
        const [metricsData, projectsData] = await Promise.allSettled([
          analyticsService.getDashboardMetrics(),
          projectService.listProjects({ page: 1, page_size: 5 }),
        ]);

        if (metricsData.status === 'fulfilled') {
          setMetrics(metricsData.value);
        }
        if (projectsData.status === 'fulfilled') {
          setProjects(projectsData.value.items);
        }
      } catch {
        // Handled by API interceptor
      } finally {
        setLoading(false);
      }
    }
    loadDashboard();
  }, [activeOrganization?.id]);

  const stats = [
    {
      title: 'Total Projects',
      value: metrics?.total_projects?.toString() ?? '0',
      caption: 'Active repositories',
      icon: FolderOpen,
      iconColor: 'text-blue-400 bg-blue-500/10',
    },
    {
      title: 'Critical Issues',
      value: (metrics?.severity_breakdown?.critical ?? metrics?.severity_breakdown?.CRITICAL ?? 0).toString(),
      caption: 'Immediate triage required',
      icon: AlertTriangle,
      iconColor: 'text-destructive bg-destructive/10',
    },
    {
      title: 'Total Scans',
      value: metrics?.total_scans?.toString() ?? '0',
      caption: 'Lifetime pipeline executions',
      icon: Activity,
      iconColor: 'text-purple-400 bg-purple-500/10',
    },
    {
      title: 'Total Findings',
      value: metrics?.total_vulnerabilities?.toString() ?? '0',
      caption: 'Detected weaknesses',
      icon: ShieldCheck,
      iconColor: 'text-emerald-400 bg-emerald-500/10',
    },
  ];

  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-12">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-border/50">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-foreground">
            Security Overview
          </h1>
          <p className="text-xs text-muted-foreground mt-0.5">
            Posture metrics and vulnerability monitoring for{' '}
            <span className="font-semibold text-foreground">
              {activeOrganization?.name || 'Workspace'}
            </span>
            .
          </p>
        </div>
        <div className="flex items-center gap-2.5">
          <Link to="/projects/create">
            <Button size="sm" className="gap-1.5 text-xs">
              <Plus className="w-3.5 h-3.5" />
              New Project
            </Button>
          </Link>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((stat) => (
          <Card key={stat.title}>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-muted-foreground">{stat.title}</span>
                <div className={`p-1.5 rounded-md ${stat.iconColor}`}>
                  <stat.icon className="h-4 w-4" />
                </div>
              </div>
              <div className="mt-2">
                {loading ? (
                  <Loader2 className="w-4 h-4 animate-spin text-muted-foreground my-1" />
                ) : (
                  <div className="text-2xl font-bold text-foreground tracking-tight">{stat.value}</div>
                )}
                <span className="text-[11px] text-muted-foreground block mt-0.5">{stat.caption}</span>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Main Content Area */}
      <div className="space-y-6">
        {/* Recent Projects Table */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-3">
            <div>
              <CardTitle>Recent Projects</CardTitle>
              <CardDescription>Managed codebases and repositories in this workspace.</CardDescription>
            </div>
            {projects.length > 0 && (
              <Link to="/projects" className="text-xs font-medium text-primary hover:underline flex items-center gap-1">
                View all <ArrowRight className="w-3 h-3" />
              </Link>
            )}
          </CardHeader>
          <CardContent className="p-0">
            {loading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
              </div>
            ) : projects.length === 0 ? (
              <div className="text-center py-12 px-4 text-muted-foreground">
                <FolderOpen className="w-8 h-8 mx-auto mb-2 opacity-40 text-muted-foreground" />
                <p className="text-sm font-medium text-foreground">No projects recorded yet</p>
                <p className="text-xs mt-1 text-muted-foreground max-w-sm mx-auto">
                  Create a project and attach source code archives to begin vulnerability analysis.
                </p>
                <Link to="/projects/create">
                  <Button className="mt-4 text-xs gap-1.5" size="sm" variant="outline">
                    <Plus className="w-3.5 h-3.5" />
                    Create First Project
                  </Button>
                </Link>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-xs text-left">
                  <thead className="text-[11px] font-semibold text-muted-foreground uppercase bg-muted/30 border-y border-border">
                    <tr>
                      <th className="px-5 py-3">Project Name</th>
                      <th className="px-5 py-3">Language</th>
                      <th className="px-5 py-3">Created</th>
                      <th className="px-5 py-3 text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/60">
                    {projects.map((project) => (
                      <tr key={project.id} className="hover:bg-hover transition-colors">
                        <td className="px-5 py-3 font-medium text-foreground">{project.name}</td>
                        <td className="px-5 py-3 text-muted-foreground">{project.language || '—'}</td>
                        <td className="px-5 py-3 text-muted-foreground font-mono">
                          {new Date(project.created_at).toLocaleDateString()}
                        </td>
                        <td className="px-5 py-3 text-right">
                          <Link to={`/projects/${project.id}`}>
                            <Button variant="ghost" size="sm" className="h-7 text-xs gap-1">
                              Open <ArrowRight className="w-3 h-3" />
                            </Button>
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Security Posture Section */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">Risk Timeline</CardTitle>
            </CardHeader>
            <CardContent className="h-40 flex flex-col items-center justify-center bg-muted/10 m-4 mt-0 rounded-md border border-dashed border-border p-4 text-center">
              <Activity className="w-6 h-6 opacity-30 mb-1.5 text-muted-foreground" />
              <p className="text-xs font-semibold text-foreground">No Timeline Records</p>
              <p className="text-[11px] text-muted-foreground mt-0.5">
                Vulnerability trends track over time once project scans complete.
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">Severity Distribution</CardTitle>
            </CardHeader>
            <CardContent className="h-40 flex flex-col items-center justify-center bg-muted/10 m-4 mt-0 rounded-md border border-dashed border-border p-4 text-center">
              {metrics?.severity_breakdown && Object.values(metrics.severity_breakdown).some((v) => v > 0) ? (
                <div className="space-y-1 w-full">
                  {Object.entries(metrics.severity_breakdown).map(([k, v]) => (
                    <div key={k} className="text-xs flex justify-between px-3">
                      <span className="font-medium uppercase">{k}</span>
                      <span className="font-mono">{v}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <>
                  <ShieldCheck className="w-6 h-6 text-emerald-400/50 mb-1.5" />
                  <p className="text-xs font-semibold text-foreground">Zero Active Vulnerabilities</p>
                  <p className="text-[11px] text-muted-foreground mt-0.5">
                    Identified issues categorize by severity here.
                  </p>
                </>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">Common Weaknesses (CWE)</CardTitle>
            </CardHeader>
            <CardContent className="h-40 flex flex-col items-center justify-center bg-muted/10 m-4 mt-0 rounded-md border border-dashed border-border p-4 text-center">
              <FolderOpen className="w-6 h-6 opacity-30 mb-1.5 text-muted-foreground" />
              <p className="text-xs font-semibold text-foreground">No CWE Attributions</p>
              <p className="text-[11px] text-muted-foreground mt-0.5">
                Weakness taxonomies will populate after static & AI inference passes.
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
