import React from 'react';
import { ShieldCheck, Plus, Search, Filter, FolderGit2, Calendar, Activity, ChevronRight, Hash } from 'lucide-react';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';
import { Card } from '../../components/ui/Card';
import { Link, useNavigate } from 'react-router-dom';

const MOCK_PROJECTS = [
  { id: '1', name: 'payment-gateway-service', lang: 'C', size: '4.2 MB', risk: 'HIGH', vulns: 12, lastScan: '2023-11-20T10:30:00Z', status: 'active' },
  { id: '2', name: 'auth-microservice', lang: 'C++', size: '8.1 MB', risk: 'MEDIUM', vulns: 5, lastScan: '2023-11-19T14:15:00Z', status: 'active' },
  { id: '3', name: 'user-dashboard-ui', lang: 'TypeScript', size: '1.2 MB', risk: 'LOW', vulns: 0, lastScan: '2023-11-18T09:00:00Z', status: 'active' },
  { id: '4', name: 'core-banking-api', lang: 'C', size: '12.5 MB', risk: 'CRITICAL', vulns: 28, lastScan: '2023-11-15T16:45:00Z', status: 'archived' },
  { id: '5', name: 'crypto-utils', lang: 'C++', size: '0.8 MB', risk: 'SAFE', vulns: 0, lastScan: '2023-11-10T11:20:00Z', status: 'active' },
];

export default function ProjectsList() {
  const navigate = useNavigate();

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Projects</h1>
          <p className="text-muted-foreground mt-1">Manage and monitor all your source code repositories.</p>
        </div>
        <Link to="/projects/create">
          <Button>
            <Plus className="w-4 h-4 mr-2" />
            New Project
          </Button>
        </Link>
      </div>

      {/* Filters */}
      <Card className="p-4 bg-card/40 border-border/50">
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <input 
              type="text" 
              placeholder="Search projects by name..." 
              className="w-full pl-9 h-10 bg-background border border-border rounded-md text-sm focus:ring-1 focus:ring-primary outline-none"
            />
          </div>
          <div className="flex gap-2">
            <Button variant="outline" className="bg-background">
              <Filter className="w-4 h-4 mr-2" />
              Status: All
            </Button>
            <Button variant="outline" className="bg-background">
              Risk: Any
            </Button>
          </div>
        </div>
      </Card>

      {/* List */}
      <div className="space-y-4">
        {MOCK_PROJECTS.map(project => (
          <Card 
            key={project.id} 
            className="p-0 overflow-hidden hover:border-primary/50 transition-colors cursor-pointer group bg-card/60"
            onClick={() => navigate(`/projects/${project.id}`)}
          >
            <div className="flex flex-col md:flex-row items-center p-4 sm:p-6 gap-6">
              
              <div className="flex items-center gap-4 flex-1">
                <div className="w-12 h-12 rounded-xl bg-primary/10 flex flex-shrink-0 items-center justify-center">
                  <FolderGit2 className="w-6 h-6 text-primary" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold group-hover:text-primary transition-colors flex items-center gap-2">
                    {project.name}
                    {project.status === 'archived' && <Badge variant="secondary" className="ml-2">Archived</Badge>}
                  </h3>
                  <div className="flex items-center gap-4 text-sm text-muted-foreground mt-1">
                    <span className="flex items-center gap-1.5"><Hash className="w-3.5 h-3.5"/>{project.lang}</span>
                    <span className="flex items-center gap-1.5"><Activity className="w-3.5 h-3.5"/>{project.size}</span>
                  </div>
                </div>
              </div>

              <div className="flex justify-between w-full md:w-auto md:gap-12 items-center">
                <div className="flex flex-col gap-1 items-start md:items-center">
                  <span className="text-xs text-muted-foreground font-medium uppercase tracking-wider">Risk Level</span>
                  <Badge 
                    variant={
                      project.risk === 'CRITICAL' ? 'destructive' : 
                      project.risk === 'HIGH' ? 'destructive' : 
                      project.risk === 'MEDIUM' ? 'warning' : 'safe'
                    }
                    className="w-24 justify-center"
                  >
                    {project.risk}
                  </Badge>
                </div>
                
                <div className="flex flex-col gap-1 items-start md:items-center">
                  <span className="text-xs text-muted-foreground font-medium uppercase tracking-wider">Vulns</span>
                  <span className="font-semibold text-lg">{project.vulns}</span>
                </div>

                <div className="hidden lg:flex flex-col gap-1 items-start md:items-end">
                  <span className="text-xs text-muted-foreground font-medium uppercase tracking-wider flex items-center gap-1">
                    <Calendar className="w-3 h-3" /> Last Scan
                  </span>
                  <span className="text-sm">{new Date(project.lastScan).toLocaleDateString()}</span>
                </div>

                <div className="text-muted-foreground group-hover:text-foreground transition-colors hidden sm:block">
                  <ChevronRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                </div>
              </div>

            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
