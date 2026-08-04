import React from 'react';
import { motion } from 'framer-motion';
import { ShieldCheck, Activity, FolderOpen, AlertTriangle, ArrowUpRight, CheckCircle2, Clock } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Link } from 'react-router-dom';

const MOCK_STATS = [
  { title: "Total Projects", value: "12", icon: FolderOpen, trend: "+2 this month", color: "text-blue-500" },
  { title: "Active Scans", value: "3", icon: Activity, trend: "Processing...", color: "text-amber-500" },
  { title: "Critical Vulns", value: "7", icon: AlertTriangle, trend: "-4 from last week", color: "text-destructive" },
  { title: "System Health", value: "99.8%", icon: ShieldCheck, trend: "Optimal", color: "text-emerald-500" },
];

const RECENT_PROJECTS = [
  { id: '1', name: 'payment-gateway-service', risk: 'HIGH', lastScan: '2 hours ago', status: 'completed' },
  { id: '2', name: 'auth-microservice', risk: 'MEDIUM', lastScan: '5 hours ago', status: 'completed' },
  { id: '3', name: 'user-dashboard-ui', risk: 'LOW', lastScan: '1 day ago', status: 'completed' },
  { id: '4', name: 'core-banking-api', risk: 'CRITICAL', lastScan: 'Just now', status: 'running' },
];

export default function Dashboard() {
  return (
    <div className="space-y-8 pb-12">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground">Dashboard Overview</h1>
          <p className="text-muted-foreground mt-1">Welcome back. Here's what's happening in your workspace.</p>
        </div>
        <div className="flex gap-3">
          <Link to="/projects/create">
            <Button>
              <FolderOpen className="w-4 h-4 mr-2" />
              New Project
            </Button>
          </Link>
          <Link to="/upload">
            <Button variant="outline" className="border-dashed bg-card/20">
              Legacy Upload
            </Button>
          </Link>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {MOCK_STATS.map((stat, i) => (
          <motion.div
            key={stat.title}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.1, duration: 0.4 }}
          >
            <Card className="interactive-card border-none bg-card/50">
              <CardContent className="p-6">
                <div className="flex items-center justify-between space-y-0 pb-2">
                  <p className="text-sm font-medium text-muted-foreground">{stat.title}</p>
                  <div className={`p-2 rounded-lg bg-background/50 ${stat.color}`}>
                    <stat.icon className="h-4 w-4" />
                  </div>
                </div>
                <div className="flex items-baseline gap-2">
                  <div className="text-3xl font-bold">{stat.value}</div>
                </div>
                <p className="text-xs text-muted-foreground mt-1 flex items-center gap-1">
                  <ArrowUpRight className="w-3 h-3" />
                  {stat.trend}
                </p>
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Recent Projects */}
        <Card className="lg:col-span-2 glass-panel border-none bg-card/30">
          <CardHeader>
            <CardTitle>Recent Projects</CardTitle>
            <CardDescription>Your recently scanned code repositories.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {RECENT_PROJECTS.map((project) => (
                <div key={project.id} className="flex items-center justify-between p-4 rounded-lg bg-background/40 hover:bg-muted/50 border border-border/50 transition-colors group cursor-pointer">
                  <div className="flex items-center gap-4">
                    <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
                      <FolderOpen className="w-5 h-5 text-primary" />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-foreground group-hover:text-primary transition-colors">{project.name}</p>
                      <div className="flex items-center gap-2 text-xs text-muted-foreground mt-0.5">
                        <Clock className="w-3 h-3" />
                        {project.lastScan}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    {project.status === 'running' ? (
                      <Badge variant="warning" className="animate-pulse">Scanning...</Badge>
                    ) : (
                      <Badge 
                        variant={
                          project.risk === 'CRITICAL' ? 'destructive' : 
                          project.risk === 'HIGH' ? 'destructive' : 
                          project.risk === 'MEDIUM' ? 'warning' : 'safe'
                        }
                      >
                        {project.risk} RISK
                      </Badge>
                    )}
                    <Button variant="ghost" size="sm" className="opacity-0 group-hover:opacity-100 transition-opacity">
                      View
                    </Button>
                  </div>
                </div>
              ))}
            </div>
            <Button variant="ghost" className="w-full mt-4 text-primary">View all projects</Button>
          </CardContent>
        </Card>

        {/* Action Center */}
        <Card className="glass-panel border-none bg-card/30">
          <CardHeader>
            <CardTitle>Action Center</CardTitle>
            <CardDescription>Required attention</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="flex gap-4">
              <div className="mt-0.5 w-8 h-8 rounded-full bg-destructive/10 flex flex-shrink-0 items-center justify-center">
                <AlertTriangle className="w-4 h-4 text-destructive" />
              </div>
              <div className="space-y-1">
                <p className="text-sm font-medium leading-none">Critical Vuln Detected</p>
                <p className="text-xs text-muted-foreground">SQL Injection found in payment-gateway-service.</p>
                <p className="text-xs text-primary font-medium cursor-pointer hover:underline mt-1">Review now</p>
              </div>
            </div>

            <div className="flex gap-4">
              <div className="mt-0.5 w-8 h-8 rounded-full bg-emerald-500/10 flex flex-shrink-0 items-center justify-center">
                <CheckCircle2 className="w-4 h-4 text-emerald-500" />
              </div>
              <div className="space-y-1">
                <p className="text-sm font-medium leading-none">Scan Completed</p>
                <p className="text-xs text-muted-foreground">auth-microservice scan finished with 0 critical issues.</p>
              </div>
            </div>
            
            <div className="flex gap-4">
              <div className="mt-0.5 w-8 h-8 rounded-full bg-amber-500/10 flex flex-shrink-0 items-center justify-center">
                <Activity className="w-4 h-4 text-amber-500" />
              </div>
              <div className="space-y-1">
                <p className="text-sm font-medium leading-none">System Load High</p>
                <p className="text-xs text-muted-foreground">Multiple parse jobs are queuing. Consider adding workers.</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
