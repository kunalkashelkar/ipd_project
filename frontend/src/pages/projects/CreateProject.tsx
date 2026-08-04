import React, { useState } from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { useNavigate, Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';

export default function CreateProject() {
  const navigate = useNavigate();
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setTimeout(() => {
      navigate('/projects/1/connect');
    }, 1000);
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <Link to="/dashboard" className="text-sm font-medium text-muted-foreground flex items-center gap-2 hover:text-foreground w-fit">
        <ArrowLeft className="w-4 h-4" /> Back to Dashboard
      </Link>
      
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Create a new project</h1>
        <p className="text-muted-foreground mt-1">A project contains all files, scans, and settings for a given codebase.</p>
      </div>

      <form onSubmit={handleSubmit}>
        <Card>
          <CardContent className="space-y-6 pt-6">
            <div className="space-y-2">
              <label className="text-sm font-medium">Project Name *</label>
              <input
                type="text"
                required
                className="w-full h-10 px-3 bg-background border border-border rounded-input text-sm focus:ring-1 focus:ring-primary outline-none"
                placeholder="Payment Gateway"
                defaultValue="Payment Gateway"
              />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Description</label>
              <textarea
                className="w-full p-3 bg-background border border-border rounded-input text-sm focus:ring-1 focus:ring-primary outline-none min-h-[100px]"
                placeholder="Core payment processing microservice..."
              />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Primary Language</label>
              <select className="w-full h-10 px-3 bg-background border border-border rounded-input text-sm focus:ring-1 focus:ring-primary outline-none">
                <option value="java">Java</option>
                <option value="c">C / C++</option>
                <option value="python">Python</option>
                <option value="js">JavaScript / TypeScript</option>
              </select>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Repository URL</label>
              <input
                type="url"
                className="w-full h-10 px-3 bg-background border border-border rounded-input text-sm focus:ring-1 focus:ring-primary outline-none"
                placeholder="https://github.com/organization/repo"
              />
              <p className="text-xs text-muted-foreground">Optional at this stage. You can connect it via OAuth in the next step.</p>
            </div>

            <div className="space-y-3 pt-4 border-t border-border">
              <label className="text-sm font-medium flex items-center gap-2">Visibility</label>
              
              <label className="flex items-start gap-3 p-3 border border-border rounded-card cursor-pointer hover:bg-muted/50 transition-colors">
                <div className="pt-0.5">
                  <input type="radio" name="visibility" value="public" className="accent-primary" />
                </div>
                <div>
                  <div className="font-medium text-sm">Public</div>
                  <div className="text-xs text-muted-foreground mt-0.5">Anyone on the internet can see this project. You choose who can scan.</div>
                </div>
              </label>

              <label className="flex items-start gap-3 p-3 border border-border rounded-card cursor-pointer bg-primary/5 hover:bg-primary/10 transition-colors">
                <div className="pt-0.5">
                  <input type="radio" name="visibility" value="private" className="accent-primary" defaultChecked />
                </div>
                <div>
                  <div className="font-medium text-sm">Private</div>
                  <div className="text-xs text-muted-foreground mt-0.5">You choose who can see and commit to this project.</div>
                </div>
              </label>
            </div>
            
          </CardContent>
          <CardFooter className="flex justify-between border-t border-border p-6 bg-muted/20">
            <Button variant="ghost" onClick={() => navigate(-1)} type="button">Cancel</Button>
            <Button type="submit" disabled={isSubmitting} className="min-w-[120px]">
              {isSubmitting ? (
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                'Create Project'
              )}
            </Button>
          </CardFooter>
        </Card>
      </form>
    </div>
  );
}
