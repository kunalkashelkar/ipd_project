import React, { useState } from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { FolderGit2, ShieldCheck, Github, Upload, Code } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export default function CreateProject() {
  const navigate = useNavigate();
  const [sourceType, setSourceType] = useState<'upload' | 'github'>('upload');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setTimeout(() => {
      navigate('/projects/1?onboarding=true');
    }, 1000);
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Create Project</h1>
        <p className="text-muted-foreground mt-1">Setup a new codebase for vulnerability analysis.</p>
      </div>

      <form onSubmit={handleSubmit}>
        <Card className="bg-card/50 border-border/50">
          <CardHeader>
            <CardTitle>Project Details</CardTitle>
            <CardDescription>Provide basic information about your code repository.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="space-y-2">
              <label className="text-sm font-medium">Project Name</label>
              <input
                type="text"
                required
                className="w-full h-10 px-3 bg-background border border-border rounded-md text-sm focus:ring-1 focus:ring-primary outline-none"
                placeholder="e.g. backend-api-service"
              />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Primary Language</label>
              <select className="w-full h-10 px-3 bg-background border border-border rounded-md text-sm focus:ring-1 focus:ring-primary outline-none">
                <option value="c">C / C++ (Supported)</option>
                <option value="java" disabled>Java (Coming Soon)</option>
                <option value="python" disabled>Python (Coming Soon)</option>
              </select>
              <p className="text-xs text-muted-foreground">The hybrid GNN model currently supports C/C++ projects via Joern.</p>
            </div>

            <div className="space-y-3">
              <label className="text-sm font-medium">Source Type</label>
              <div className="grid grid-cols-2 gap-4">
                <div 
                  onClick={() => setSourceType('upload')}
                  className={`p-4 rounded-xl border-2 cursor-pointer flex flex-col items-center justify-center gap-2 transition-all ${sourceType === 'upload' ? 'border-primary bg-primary/5 text-primary' : 'border-border/50 bg-background hover:bg-muted text-muted-foreground'}`}
                >
                  <Upload className="w-6 h-6" />
                  <span className="font-medium text-sm">Upload Source Zip</span>
                </div>
                <div 
                  onClick={() => setSourceType('github')}
                  className={`p-4 rounded-xl border-2 cursor-pointer flex flex-col items-center justify-center gap-2 transition-all ${sourceType === 'github' ? 'border-primary bg-primary/5 text-primary' : 'border-border/50 bg-background hover:bg-muted text-muted-foreground'}`}
                >
                  <Github className="w-6 h-6" />
                  <span className="font-medium text-sm">Connect Repository</span>
                </div>
              </div>
            </div>

            {sourceType === 'upload' && (
              <div className="mt-4 p-8 border-2 border-dashed border-border rounded-xl bg-background/50 flex flex-col items-center justify-center text-center">
                <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center mb-4">
                  <FolderGit2 className="w-6 h-6 text-primary" />
                </div>
                <h4 className="text-sm font-semibold">Upload project source code</h4>
                <p className="text-xs text-muted-foreground mt-1 max-w-xs mb-4">
                  Upload a ZIP file containing your C/C++ source code. Maximum size 50MB.
                </p>
                <Button variant="outline" type="button" className="relative cursor-pointer overflow-hidden">
                  Browse Files
                  <input type="file" className="absolute inset-0 opacity-0 cursor-pointer" accept=".zip" />
                </Button>
              </div>
            )}

            {sourceType === 'github' && (
              <div className="mt-4 space-y-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Repository URL</label>
                  <input
                    type="url"
                    className="w-full h-10 px-3 bg-background border border-border rounded-md text-sm focus:ring-1 focus:ring-primary outline-none"
                    placeholder="https://github.com/org/repo"
                  />
                </div>
                <Button variant="outline" type="button" className="w-full gap-2" disabled>
                  <ShieldCheck className="w-4 h-4" /> Connect with GitHub App
                </Button>
              </div>
            )}
          </CardContent>
          <CardFooter className="flex justify-between border-t border-border/50 p-6">
            <Button variant="ghost" onClick={() => navigate(-1)} type="button">Cancel</Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? 'Creating Project...' : 'Create Project'}
            </Button>
          </CardFooter>
        </Card>
      </form>
    </div>
  );
}
