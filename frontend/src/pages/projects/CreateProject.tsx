import React, { useState } from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { useNavigate, Link } from 'react-router-dom';
import { ArrowLeft, FolderPlus, UploadCloud, Info, GitBranch } from 'lucide-react';
import { projectService } from '../../services/projectService';
import toast from 'react-hot-toast';

import { getProjectUrl } from '../../utils/routes';

export default function CreateProject() {
  const navigate = useNavigate();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [language, setLanguage] = useState('java');
  const [defaultBranch, setDefaultBranch] = useState('main');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    setIsSubmitting(true);

    try {
      const project = await projectService.createProject({
        name: name.trim(),
        description: description.trim() || undefined,
        language,
        default_branch: defaultBranch.trim() || 'main',
      });
      toast.success(`Project "${project.name}" created successfully!`);
      navigate(getProjectUrl(project));
    } catch (err: any) {
      const message =
        err?.response?.data?.message ||
        err?.response?.data?.detail ||
        'Failed to create project.';
      toast.error(message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6 pb-12">
      <Link
        to="/projects"
        className="text-xs font-medium text-muted-foreground flex items-center gap-1.5 hover:text-foreground w-fit transition-colors"
      >
        <ArrowLeft className="w-3.5 h-3.5" /> Back to Projects
      </Link>

      <div className="pb-4 border-b border-border/50">
        <h1 className="text-xl font-bold tracking-tight text-foreground">Create Security Project</h1>
        <p className="text-xs text-muted-foreground mt-0.5">
          Establish a project space for code property graph extraction and vulnerability analysis.
        </p>
      </div>

      {/* Workflow Guidance Banner */}
      <div className="p-3.5 rounded-md bg-muted/40 border border-border flex items-start gap-2.5 text-xs text-muted-foreground leading-relaxed">
        <Info className="w-4 h-4 text-primary shrink-0 mt-0.5" />
        <div>
          <span className="font-semibold text-foreground">Workflow: </span>
          <span>Project Space → Add Source (ZIP, Files, Git, GitHub) → Immutable Snapshot → Vulnerability Scan. </span>
          <span className="block mt-1 text-[11px] text-muted-foreground/80">
            Source code is securely ingested into immutable snapshots and deterministically preprocessed for reproducible static graph analysis.
          </span>
        </div>
      </div>

      <form onSubmit={handleSubmit}>
        <Card>
          <CardContent className="space-y-4 pt-5">
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-foreground">Project Name *</label>
              <input
                type="text"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full h-9 px-3 bg-background border border-border rounded-md text-xs text-foreground focus:ring-1 focus:ring-primary outline-none"
                placeholder="e.g. payment-service"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-medium text-foreground">Description</label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="w-full p-3 bg-background border border-border rounded-md text-xs text-foreground focus:ring-1 focus:ring-primary outline-none min-h-[80px]"
                placeholder="Brief description of the service and codebase purpose..."
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-foreground">Primary Language</label>
                <select
                  value={language}
                  onChange={(e) => setLanguage(e.target.value)}
                  className="w-full h-9 px-3 bg-background border border-border rounded-md text-xs text-foreground focus:ring-1 focus:ring-primary outline-none"
                >
                  <option value="java">Java</option>
                  <option value="c">C / C++</option>
                  <option value="python">Python</option>
                  <option value="js">JavaScript / TypeScript</option>
                </select>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-medium text-foreground">Target Default Branch</label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <GitBranch className="h-3.5 w-3.5 text-muted-foreground" />
                  </div>
                  <input
                    type="text"
                    value={defaultBranch}
                    onChange={(e) => setDefaultBranch(e.target.value)}
                    className="w-full pl-9 h-9 bg-background border border-border rounded-md text-xs text-foreground focus:ring-1 focus:ring-primary outline-none font-mono"
                    placeholder="main"
                  />
                </div>
              </div>
            </div>
          </CardContent>

          <CardFooter className="flex justify-between border-t border-border p-4 bg-muted/20 mt-4">
            <Button variant="ghost" size="sm" onClick={() => navigate(-1)} type="button" className="text-xs">
              Cancel
            </Button>
            <Button type="submit" size="sm" disabled={isSubmitting || !name.trim()} className="text-xs gap-1.5">
              {isSubmitting ? (
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <>
                  <FolderPlus className="w-3.5 h-3.5" />
                  Create Project
                </>
              )}
            </Button>
          </CardFooter>
        </Card>
      </form>
    </div>
  );
}
