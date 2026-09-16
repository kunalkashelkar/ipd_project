import React, { useEffect, useState } from 'react';
import { Plus, Search, FolderGit2, ArrowRight, Loader2, GitBranch } from 'lucide-react';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';
import { Card, CardContent } from '../../components/ui/Card';
import { Link, useNavigate } from 'react-router-dom';
import { projectService } from '../../services/projectService';
import { Project } from '../../types';

export default function ProjectsList() {
  const navigate = useNavigate();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');

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
    <div className="space-y-6 max-w-6xl mx-auto pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-border/50">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-foreground">Projects</h1>
          <p className="text-xs text-muted-foreground mt-0.5">
            Manage source code repositories, direct uploads, and scan configurations.
          </p>
        </div>
        <Link to="/projects/create">
          <Button size="sm" className="gap-1.5 text-xs">
            <Plus className="w-3.5 h-3.5" />
            New Project
          </Button>
        </Link>
      </div>

      {/* Search Filter */}
      <div className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
        <input
          type="text"
          placeholder="Search projects by name..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full pl-9 h-9 bg-card border border-border rounded-md text-xs text-foreground focus:ring-1 focus:ring-primary outline-none placeholder:text-muted-foreground/60 transition-colors"
        />
      </div>

      {/* Projects Table */}
      <Card>
        <CardContent className="p-0">
          {loading ? (
            <div className="flex items-center justify-center py-16">
              <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
            </div>
          ) : projects.length === 0 ? (
            <div className="text-center py-16 px-4 text-muted-foreground">
              <FolderGit2 className="w-8 h-8 mx-auto mb-2 opacity-40" />
              <p className="text-sm font-medium text-foreground">No projects found</p>
              <p className="text-xs text-muted-foreground mt-1 max-w-sm mx-auto">
                {search ? 'No projects match your search query.' : 'Create your first project to configure security scans.'}
              </p>
              {!search && (
                <Link to="/projects/create">
                  <Button variant="outline" size="sm" className="mt-4 gap-1.5 text-xs">
                    <Plus className="w-3.5 h-3.5" /> Create Project
                  </Button>
                </Link>
              )}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="text-[11px] font-semibold text-muted-foreground uppercase bg-muted/30 border-b border-border">
                  <tr>
                    <th className="px-5 py-3">Project Name</th>
                    <th className="px-5 py-3">Default Branch</th>
                    <th className="px-5 py-3">Language</th>
                    <th className="px-5 py-3">Status</th>
                    <th className="px-5 py-3">Created</th>
                    <th className="px-5 py-3 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/60">
                  {projects.map((project) => (
                    <tr
                      key={project.id}
                      onClick={() => navigate(`/projects/${project.id}`)}
                      className="hover:bg-hover transition-colors cursor-pointer group"
                    >
                      <td className="px-5 py-3 font-medium text-foreground">
                        <div className="flex items-center gap-2">
                          <FolderGit2 className="w-4 h-4 text-primary shrink-0" />
                          <span className="group-hover:text-primary transition-colors font-medium">
                            {project.name}
                          </span>
                        </div>
                        {project.description && (
                          <p className="text-[11px] text-muted-foreground line-clamp-1 mt-0.5 ml-6">
                            {project.description}
                          </p>
                        )}
                      </td>
                      <td className="px-5 py-3 text-muted-foreground font-mono">
                        <span className="inline-flex items-center gap-1">
                          <GitBranch className="w-3 h-3 text-muted-foreground/60" />
                          {project.default_branch || 'main'}
                        </span>
                      </td>
                      <td className="px-5 py-3 text-muted-foreground uppercase font-mono text-[11px]">
                        {project.language || '—'}
                      </td>
                      <td className="px-5 py-3">
                        <Badge variant={project.is_archived ? 'secondary' : 'outline'} className="text-[10px]">
                          {project.is_archived ? 'Archived' : 'Active'}
                        </Badge>
                      </td>
                      <td className="px-5 py-3 text-muted-foreground font-mono">
                        {new Date(project.created_at).toLocaleDateString()}
                      </td>
                      <td className="px-5 py-3 text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-7 text-xs gap-1 group-hover:bg-primary/10 group-hover:text-primary"
                          onClick={(e) => {
                            e.stopPropagation();
                            navigate(`/projects/${project.id}`);
                          }}
                        >
                          View <ArrowRight className="w-3 h-3" />
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
