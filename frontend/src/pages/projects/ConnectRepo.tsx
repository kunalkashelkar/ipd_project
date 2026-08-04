import React, { useState } from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { useNavigate } from 'react-router-dom';
import { Github, Search, PlusCircle, CheckCircle2, Copy } from 'lucide-react';

const REPOS = [
  { id: '1', name: 'Payment API', updated: '2 hours ago', branch: 'main' },
  { id: '2', name: 'Bank API', updated: '1 day ago', branch: 'main' },
  { id: '3', name: 'Shopping Cart', updated: '3 days ago', branch: 'develop' },
  { id: '4', name: 'Inventory', updated: '5 days ago', branch: 'main' },
];

export default function ConnectRepo() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<'github' | 'gitlab' | 'bitbucket' | 'zip' | 'paste'>('github');
  const [selectedRepo, setSelectedRepo] = useState<string | null>(null);
  const [isImporting, setIsImporting] = useState(false);
  const [isAuthorized, setIsAuthorized] = useState(false);

  const handleImport = () => {
    setIsImporting(true);
    setTimeout(() => {
      navigate('/projects/1?onboarding=true');
    }, 1500);
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8 pb-12">
      <div className="text-center max-w-xl mx-auto pt-8">
        <h1 className="text-3xl font-bold tracking-tight">Connect your repository</h1>
        <p className="text-muted-foreground mt-2">
          Select a Git provider to import an existing project or upload your source code directly to begin vulnerability detection.
        </p>
      </div>

      <Card className="mt-8">
        <div className="flex border-b border-border bg-muted/20 overflow-x-auto scrollbar-none">
          {[
            { id: 'github', label: 'GitHub', icon: Github },
            { id: 'gitlab', label: 'GitLab', icon: () => <span className="font-bold text-orange-500 mr-2">🦊</span> },
            { id: 'bitbucket', label: 'Bitbucket', icon: () => <span className="font-bold text-blue-500 mr-2">B</span> },
            { id: 'zip', label: 'ZIP File', icon: PlusCircle },
            { id: 'paste', label: 'Paste Code', icon: Copy },
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center px-6 py-4 text-sm font-medium transition-colors border-b-2 whitespace-nowrap ${
                activeTab === tab.id 
                  ? 'border-primary text-foreground' 
                  : 'border-transparent text-muted-foreground hover:text-foreground hover:bg-muted/50'
              }`}
            >
              {tab.id === 'github' ? <Github className="w-4 h-4 mr-2" /> : <tab.icon className="w-4 h-4 mr-2" />}
              {tab.label}
            </button>
          ))}
        </div>

        <CardContent className="p-8 min-h-[400px]">
          {activeTab === 'github' && (
            <div className="space-y-6">
              {!isAuthorized ? (
                <div className="flex flex-col items-center justify-center p-12 text-center border border-dashed border-border rounded-card bg-muted/10 h-full">
                  <Github className="w-12 h-12 mb-4 text-foreground" />
                  <h3 className="text-xl font-semibold mb-2">Connect to GitHub</h3>
                  <p className="text-muted-foreground text-sm max-w-sm mb-6">
                    Install the Aegis Kinetic app on your GitHub account or organization to safely import repositories.
                  </p>
                  <Button onClick={() => setIsAuthorized(true)}>
                    <Github className="w-4 h-4 mr-2" /> Authorize GitHub Access
                  </Button>
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="flex justify-between items-center mb-6">
                    <h3 className="text-lg font-semibold flex items-center gap-2">
                      <CheckCircle2 className="w-5 h-5 text-emerald-500" /> Connected as rahul-dev
                    </h3>
                    <div className="relative w-64">
                      <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                      <input 
                        type="text" 
                        placeholder="Search repositories..." 
                        className="w-full bg-background border border-border rounded-input pl-8 pr-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
                      />
                    </div>
                  </div>

                  <div className="border border-border rounded-card overflow-hidden">
                    <div className="bg-muted/30 px-4 py-3 border-b border-border text-sm font-medium">Select a repository</div>
                    <div className="divide-y divide-border/50 max-h-[300px] overflow-y-auto">
                      {REPOS.map((repo) => (
                         <label 
                          key={repo.id}
                          className={`flex items-center justify-between p-4 cursor-pointer transition-colors hover:bg-muted/20 ${selectedRepo === repo.id ? 'bg-primary/5' : ''}`}
                        >
                          <div className="flex items-center gap-3">
                            <input 
                              type="radio" 
                              name="repo_selection" 
                              className="accent-primary w-4 h-4"
                              checked={selectedRepo === repo.id}
                              onChange={() => setSelectedRepo(repo.id)}
                            />
                            <div>
                              <div className="font-medium text-foreground">{repo.name}</div>
                              <div className="text-xs text-muted-foreground mt-0.5">Updated {repo.updated}</div>
                            </div>
                          </div>
                          {selectedRepo === repo.id && (
                             <select className="h-8 px-2 bg-background border border-border rounded text-xs focus:ring-1 focus:ring-primary outline-none">
                               <option>{repo.branch}</option>
                               <option>master</option>
                             </select>
                          )}
                        </label>
                      ))}
                    </div>
                  </div>

                  <div className="flex justify-end pt-4">
                    <Button 
                      onClick={handleImport}
                      disabled={!selectedRepo || isImporting}
                      className="min-w-[150px]"
                    >
                      {isImporting ? (
                        <div className="flex items-center gap-2">
                          <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                          Importing...
                        </div>
                      ) : (
                        'Import Repository'
                      )}
                    </Button>
                  </div>
                </div>
              )}
            </div>
          )}
          
          {activeTab !== 'github' && (
             <div className="flex flex-col items-center justify-center p-12 text-center text-muted-foreground h-full">
               <p>This integration is mocked out for the scope of the current demo.</p>
               <p className="text-sm mt-2">Please select GitHub to proceed.</p>
             </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
