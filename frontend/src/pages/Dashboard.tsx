import React from 'react';
import { motion } from 'framer-motion';
import { ShieldCheck, Activity, FolderOpen, AlertTriangle, FileText, ArrowRight } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Link } from 'react-router-dom';

const MOCK_STATS = [
  { title: "Projects", value: "12", icon: FolderOpen, color: "text-blue-500" },
  { title: "Critical Vulnerabilities", value: "3", icon: AlertTriangle, color: "text-destructive" },
  { title: "Reports", value: "18", icon: FileText, color: "text-purple-500" },
  { title: "Risk Score", value: "81%", icon: ShieldCheck, color: "text-emerald-500" },
];

const RECENT_PROJECTS = [
  { id: '1', name: 'Payment App', fw: 'Spring Boot', lastScan: 'Yesterday', status: 'Open' },
  { id: '2', name: 'Bank API', fw: 'Node.js', lastScan: '2 days ago', status: 'Open' },
  { id: '3', name: 'Shopping Cart', fw: 'React', lastScan: '3 days ago', status: 'Open' },
];

export default function Dashboard() {
  return (
    <div className="space-y-8 pb-12 max-w-6xl mx-auto">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground flex items-center gap-2">
            Hello Rahul 👋
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
        {MOCK_STATS.map((stat, i) => (
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
                  <div className="text-3xl font-bold">{stat.value}</div>
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
            <div className="overflow-x-auto">
              <table className="w-full text-sm text-left">
                <thead className="text-xs text-muted-foreground uppercase bg-background border-y border-border">
                  <tr>
                    <th className="px-6 py-4 font-medium">Project</th>
                    <th className="px-6 py-4 font-medium">Framework</th>
                    <th className="px-6 py-4 font-medium">Last Scan</th>
                    <th className="px-6 py-4 font-medium">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {RECENT_PROJECTS.map((project, i) => (
                    <tr key={project.id} className={`border-b border-border/50 hover:bg-muted/30 transition-colors ${i === RECENT_PROJECTS.length - 1 ? 'border-b-0' : ''}`}>
                      <td className="px-6 py-4 font-medium text-foreground">{project.name}</td>
                      <td className="px-6 py-4 text-muted-foreground">{project.fw}</td>
                      <td className="px-6 py-4 text-muted-foreground">{project.lastScan}</td>
                      <td className="px-6 py-4">
                        <Link to={`/projects/${project.id}`}>
                          <Button variant="outline" size="sm">
                            {project.status}
                          </Button>
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>

        {/* Charts Mockups */}
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
              [Donut Chart Graphic]
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
