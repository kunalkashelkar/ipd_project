import React, { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Play, Settings, History, ShieldCheck, Activity, Hash, Layers, FileCode2 } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';

export default function ProjectDetail() {
  const { id } = useParams();
  const [isScanning, setIsScanning] = useState(false);

  // Mock project info
  const project = {
    id,
    name: 'payment-gateway-service',
    description: 'Core microservice for handling payment transactions.',
    risk: 'HIGH',
    lang: 'C',
    vulns: 12,
    files: 145,
    lastScan: '2023-11-20T10:30:00Z',
    status: 'active'
  };

  const handleStartScan = () => {
    setIsScanning(true);
    // Move to Scan Pipeline config or progress
  };

  return (
    <div className="space-y-6">
      {/* Header section with project title and primary actions */}
      <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-bold tracking-tight">{project.name}</h1>
            <Badge 
              variant={
                project.risk === 'CRITICAL' ? 'destructive' : 
                project.risk === 'HIGH' ? 'destructive' : 
                project.risk === 'MEDIUM' ? 'warning' : 'safe'
              }
            >
              {project.risk} RISK
            </Badge>
          </div>
          <p className="text-muted-foreground mt-1 max-w-2xl">{project.description}</p>
        </div>
        
        <div className="flex gap-3">
          <Button variant="outline" className="bg-background">
            <Settings className="w-4 h-4 mr-2" /> Settings
          </Button>
          <Button onClick={handleStartScan} disabled={isScanning}>
            <Play className="w-4 h-4 mr-2" />
            {isScanning ? 'Queuing Scan...' : 'Start New Scan'}
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Left column (Stats & Metadata) */}
        <div className="space-y-6 lg:col-span-1">
          <Card className="bg-card/40 border-border/50">
            <CardHeader>
              <CardTitle className="text-lg">Project Details</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex justify-between items-center text-sm">
                <span className="text-muted-foreground">Primary Language</span>
                <span className="font-medium flex items-center gap-2"><Hash className="w-4 h-4 text-primary"/>{project.lang}</span>
              </div>
              <div className="flex justify-between items-center text-sm">
                <span className="text-muted-foreground">Monitored Files</span>
                <span className="font-medium flex items-center gap-2"><FileCode2 className="w-4 h-4 text-emerald-500"/>{project.files}</span>
              </div>
              <div className="flex justify-between items-center text-sm">
                <span className="text-muted-foreground">Total Scans</span>
                <span className="font-medium flex items-center gap-2"><Layers className="w-4 h-4 text-blue-500"/>24</span>
              </div>
              <div className="flex justify-between items-center text-sm">
                <span className="text-muted-foreground">Last Scan</span>
                <span className="font-medium">{new Date(project.lastScan).toLocaleDateString()}</span>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Right column (Tabs / Recent Results) */}
        <div className="space-y-6 lg:col-span-3">
          <Card className="bg-card/40 border-border/50">
            <CardHeader>
              <div className="flex justify-between items-center">
                <div>
                  <CardTitle>Latest Scan Results</CardTitle>
                  <CardDescription>Overview from scan on {new Date(project.lastScan).toLocaleString()}</CardDescription>
                </div>
                <Button variant="ghost" size="sm" className="hidden sm:flex">
                  <History className="w-4 h-4 mr-2" /> View History
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {/* Vulnerability Severity Distribution */}
              <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8">
                {[
                  { severity: 'CRITICAL', count: 2, color: 'border-red-500/50 bg-red-500/10 text-red-500' },
                  { severity: 'HIGH', count: 5, color: 'border-orange-500/50 bg-orange-500/10 text-orange-500' },
                  { severity: 'MEDIUM', count: 3, color: 'border-amber-500/50 bg-amber-500/10 text-amber-500' },
                  { severity: 'LOW', count: 2, color: 'border-blue-500/50 bg-blue-500/10 text-blue-500' },
                  { severity: 'SAFE', count: 133, color: 'border-emerald-500/50 bg-emerald-500/10 text-emerald-500' }
                ].map(item => (
                  <div key={item.severity} className={`rounded-lg border p-4 flex flex-col items-center justify-center ${item.color}`}>
                    <span className="text-2xl font-bold">{item.count}</span>
                    <span className="text-xs font-semibold uppercase">{item.severity}</span>
                  </div>
                ))}
              </div>

              {/* Action to enter Results Workspace */}
              <div className="mt-6 flex flex-col items-center justify-center p-8 border border-dashed border-border/70 rounded-xl bg-muted/20">
                <ShieldCheck className="w-10 h-10 text-primary mb-3" />
                <h3 className="text-lg font-semibold mb-1">Interactive Results Workspace</h3>
                <p className="text-sm text-muted-foreground text-center max-w-md mb-6">
                  Dive into the 16-layer vulnerability analysis. Explore GNN explanations, understand taint sinks, and review AI-suggested fixes.
                </p>
                <Link to={`/projects/${project.id}/workspace`}>
                  <Button size="lg" className="shadow-[0_0_15px_rgba(6,182,212,0.3)]">
                    Enter Workspace
                  </Button>
                </Link>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
