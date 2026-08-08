import React, { useEffect, useState } from 'react';
import { ShieldCheck, Plus, Search, Filter, FolderGit2, Calendar, Activity, ChevronRight, Hash, Loader2 } from 'lucide-react';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';
import { Card } from '../../components/ui/Card';
import { Link, useNavigate } from 'react-router-dom';
import { projectService } from '../../services/projectService';
import { Project } from '../../types';

export default function ProjectsList() {
  const navigate = useNavigate();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [total, setTotal] = useState(0);

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const data = await projectService.listProjects({
          page: 1,
          page_size: 50,
          search: search || undefined,
        });
        setProjects(data.items);
        setTotal(data.total);
      } catch {
        // Handled by interceptor
      } finally {
        setLoading(false);
      }
    }
    const debounce = setTimeout(load, 300);
    return () => clearTimeout(debounce);
  }, [search]);

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
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 h-10 bg-background border border-border rounded-md text-sm focus:ring-1 focus:ring-primary outline-none"
            />
          </div>
          <div className="flex gap-2">
            <Button variant="outline" className="bg-background">
              <Filter className="w-4 h-4 mr-2" />
              Status: All
            </Button>
          </div>
        </div>
      </Card>

      {/* List */}
      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
        </div>
      ) : projects.length === 0 ? (
        <div className="text-center py-20 text-muted-foreground">
          <FolderGit2 className="w-12 h-12 mx-auto mb-4 opacity-50" />
          <p className="text-lg font-medium text-foreground">No projects found</p>
          <p className="text-sm mt-1">
            {search ? 'Try a different search term.' : 'Create your first project to get started.'}
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {projects.map(project => (
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
                      {project.is_archived && <Badge variant="secondary" className="ml-2">Archived</Badge>}
                    </h3>
                    <div className="flex items-center gap-4 text-sm text-muted-foreground mt-1">
                      <span className="flex items-center gap-1.5"><Hash className="w-3.5 h-3.5"/>{project.language || 'Unknown'}</span>
                      {project.description && (
                        <span className="flex items-center gap-1.5 truncate max-w-[200px]">
                          <Activity className="w-3.5 h-3.5"/>{project.description}
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                <div className="flex justify-between w-full md:w-auto md:gap-12 items-center">
                  <div className="hidden lg:flex flex-col gap-1 items-start md:items-end">
                    <span className="text-xs text-muted-foreground font-medium uppercase tracking-wider flex items-center gap-1">
                      <Calendar className="w-3 h-3" /> Created
                    </span>
                    <span className="text-sm">{new Date(project.created_at).toLocaleDateString()}</span>
                  </div>

                  <div className="text-muted-foreground group-hover:text-foreground transition-colors hidden sm:block">
                    <ChevronRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                  </div>
                </div>

              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
