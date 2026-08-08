import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { ShieldCheck, Activity, FolderOpen, AlertTriangle, FileText, ArrowRight, Loader2 } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Link } from 'react-router-dom';
import { useAuthStore } from '../store';
import { analyticsService } from '../services/analyticsService';
import { projectService } from '../services/projectService';
import { Project, DashboardMetrics } from '../types';

export default function Dashboard() {
  const { user } = useAuthStore();
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
        // Errors are handled by the API interceptor
      } finally {
        setLoading(false);
      }
    }
    loadDashboard();
  }, []);

  const stats = [
    {
      title: 'Projects',
      value: metrics?.total_projects?.toString() ?? '—',
      icon: FolderOpen,
      color: 'text-blue-500',
    },
    {
      title: 'Critical Vulnerabilities',
      value: metrics?.severity_breakdown?.CRITICAL?.toString() ?? metrics?.severity_breakdown?.critical?.toString() ?? '—',
      icon: AlertTriangle,
      color: 'text-destructive',
    },
    {
      title: 'Total Scans',
      value: metrics?.total_scans?.toString() ?? '—',
      icon: Activity,
      color: 'text-purple-500',
    },
    {
      title: 'Total Findings',
      value: metrics?.total_vulnerabilities?.toString() ?? '—',
      icon: ShieldCheck,
      color: 'text-emerald-500',
    },
  ];

  const firstName = user?.name?.split(' ')[0] || 'User';

  return (
    <div className="space-y-8 pb-12 max-w-6xl mx-auto">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground flex items-center gap-2">
            Hello {firstName} 👋
          </h1>
          <p className="text-muted-foreground mt-1">Here is your security overview.</p>
        </div>
        <div className="flex gap-3">
          <Link to="/projects/create">
            <Button>
              <FolderOpen className="w-4 h-4 mr-2" />
              New Project
            </Button>
          </Link>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((stat, i) => (
          <motion.div
            key={stat.title}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.1, duration: 0.3 }}
          >
            <Card className="hover:border-primary/50 transition-colors">
              <CardContent className="p-6">
                <div className="flex items-center justify-between space-y-0 pb-2">
                  <p className="text-sm font-medium text-muted-foreground">{stat.title}</p>
                  <div className={`p-2 rounded-lg bg-background ${stat.color}`}>
                    <stat.icon className="h-4 w-4" />
                  </div>
                </div>
                <div className="flex items-baseline gap-2">
                  {loading ? (
                    <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
                  ) : (
                    <div className="text-3xl font-bold">{stat.value}</div>
                  )}
                </div>
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-8">
        {/* Recent Projects Table */}
        <Card>
          <CardHeader>
            <CardTitle>Recent Projects</CardTitle>
            <CardDescription>Your integrated repositories</CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            {loading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
              </div>
            ) : projects.length === 0 ? (
              <div className="text-center py-12 text-muted-foreground">
                <FolderOpen className="w-10 h-10 mx-auto mb-3 opacity-50" />
                <p className="font-medium">No projects yet</p>
                <p className="text-sm mt-1">Create your first project to get started.</p>
                <Link to="/projects/create">
                  <Button className="mt-4" variant="outline">
                    <FolderOpen className="w-4 h-4 mr-2" />
                    Create Project
                  </Button>
                </Link>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm text-left">
                  <thead className="text-xs text-muted-foreground uppercase bg-background border-y border-border">
                    <tr>
                      <th className="px-6 py-4 font-medium">Project</th>
                      <th className="px-6 py-4 font-medium">Language</th>
                      <th className="px-6 py-4 font-medium">Created</th>
                      <th className="px-6 py-4 font-medium">Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {projects.map((project, i) => (
                      <tr key={project.id} className={`border-b border-border/50 hover:bg-muted/30 transition-colors ${i === projects.length - 1 ? 'border-b-0' : ''}`}>
                        <td className="px-6 py-4 font-medium text-foreground">{project.name}</td>
                        <td className="px-6 py-4 text-muted-foreground">{project.language || '—'}</td>
                        <td className="px-6 py-4 text-muted-foreground">
                          {new Date(project.created_at).toLocaleDateString()}
                        </td>
                        <td className="px-6 py-4">
                          <Link to={`/projects/${project.id}`}>
                            <Button variant="outline" size="sm">
                              Open <ArrowRight className="w-3 h-3 ml-1" />
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

        {/* Charts */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Risk Trend</CardTitle>
            </CardHeader>
            <CardContent className="h-48 flex items-center justify-center text-muted-foreground bg-muted/10 m-6 mt-0 rounded-lg border border-dashed border-border">
              [Line Chart Graphic]
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Severity Distribution</CardTitle>
            </CardHeader>
            <CardContent className="h-48 flex items-center justify-center text-muted-foreground bg-muted/10 m-6 mt-0 rounded-lg border border-dashed border-border">
              {metrics?.severity_breakdown ? (
                <div className="text-center space-y-1">
                  {Object.entries(metrics.severity_breakdown).map(([k, v]) => (
                    <div key={k} className="text-xs">
                      <span className="font-medium uppercase">{k}</span>: {v}
                    </div>
                  ))}
                </div>
              ) : (
                '[Donut Chart Graphic]'
              )}
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Most Common CWE</CardTitle>
            </CardHeader>
            <CardContent className="h-48 flex items-center justify-center text-muted-foreground bg-muted/10 m-6 mt-0 rounded-lg border border-dashed border-border">
              [Bar Chart Graphic]
            </CardContent>
          </Card>
        </div>

      </div>
    </div>
  );
}
