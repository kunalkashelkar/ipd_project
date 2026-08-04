import React, { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Play, Settings, ShieldCheck, FileCode2, Layers, AlertTriangle, Github, CheckCircle2, Folder, Clock, FileText } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';

export default function ProjectDetail() {
  const { id } = useParams();
  const [activeTab, setActiveTab] = useState('overview');

  // Hardcoded as requested
  const project = {
    id,
    name: 'Payment API',
    lang: 'Java',
    framework: 'Spring Boot',
    visibility: 'Private',
    status: 'Connected',
    risk: 'HIGH',
    vulns: 22,
    files: 145,
    functions: 890,
    lastScan: 'Yesterday',
  };

  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-12">
      {/* Header section */}
      <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-bold tracking-tight">{project.name}</h1>
            <Badge variant="outline" className="text-muted-foreground">{project.visibility}</Badge>
          </div>
          <div className="flex items-center gap-4 text-sm text-muted-foreground mt-3">
            <span className="flex items-center gap-1.5"><FileCode2 className="w-4 h-4" /> {project.lang}</span>
            <span className="flex items-center gap-1.5"><Layers className="w-4 h-4" /> {project.framework}</span>
            <span className="flex items-center gap-1.5 text-emerald-500"><CheckCircle2 className="w-4 h-4" /> {project.status}</span>
          </div>
        </div>

        <div className="flex gap-3">
          <Link to={`/projects/${project.id}/scan-config`}>
            <Button>
              <Play className="w-4 h-4 mr-2" />
              Run Security Scan
            </Button>
          </Link>
        </div>
      </div>

      <div className="border-b border-border mt-4">
        <div className="flex gap-6">
          {['overview', 'repository', 'scans', 'reports', 'settings'].map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`pb-3 text-sm font-medium transition-colors capitalize ${activeTab === tab
                  ? 'border-b-2 border-primary text-foreground'
                  : 'text-muted-foreground hover:text-foreground border-transparent'
                }`}
            >
              {tab}
            </button>
          ))}
        </div>
      </div>

      {activeTab === 'overview' && (
        <div className="space-y-6">
          {/* Summary Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Card className="hover:border-primary/50 transition-colors">
              <CardContent className="p-6">
                <div className="flex items-center justify-between space-y-0 pb-2">
                  <p className="text-sm font-medium text-muted-foreground">Monitored Files</p>
                  <FileCode2 className="h-4 w-4 text-muted-foreground" />
                </div>
                <div className="text-2xl font-bold">{project.files}</div>
              </CardContent>
            </Card>

            <Card className="hover:border-primary/50 transition-colors">
              <CardContent className="p-6">
                <div className="flex items-center justify-between space-y-0 pb-2">
                  <p className="text-sm font-medium text-muted-foreground">Functions</p>
                  <Layers className="h-4 w-4 text-muted-foreground" />
                </div>
                <div className="text-2xl font-bold">{project.functions}</div>
              </CardContent>
            </Card>

            <Card className="hover:border-primary/50 transition-colors">
              <CardContent className="p-6">
                <div className="flex items-center justify-between space-y-0 pb-2">
                  <p className="text-sm font-medium text-muted-foreground">Last Scan</p>
                  <Clock className="h-4 w-4 text-muted-foreground" />
                </div>
                <div className="text-2xl font-bold text-base mt-1">{project.lastScan}</div>
              </CardContent>
            </Card>

            <Card className="border-red-500/30 bg-red-500/5">
              <CardContent className="p-6">
                <div className="flex items-center justify-between space-y-0 pb-2">
                  <p className="text-sm font-medium text-red-500/80">Risk Level</p>
                  <AlertTriangle className="h-4 w-4 text-red-500" />
                </div>
                <div className="text-2xl font-bold text-red-500">{project.risk}</div>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>Historical Risk</CardTitle>
                <div className="text-sm text-muted-foreground mt-1">Vulnerability severity over past 30 days</div>
              </div>
            </CardHeader>
            <CardContent className="h-64 flex items-center justify-center text-muted-foreground bg-muted/10 m-6 mt-0 rounded-lg border border-dashed border-border">
              [Vulnerability Chart Graphic]
            </CardContent>
          </Card>
        </div>
      )}

      {activeTab !== 'overview' && (
        <div className="flex flex-col items-center justify-center py-20 text-muted-foreground border border-dashed border-border rounded-card bg-muted/5">
          <Folder className="w-12 h-12 mb-4 opacity-50" />
          <p className="capitalize">{activeTab} view not implemented in this demo.</p>
        </div>
      )}
    </div>
  );
}
