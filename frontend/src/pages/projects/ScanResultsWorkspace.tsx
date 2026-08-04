import React, { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { ArrowLeft, Bug, Search, Filter, ShieldAlert, Zap, BookOpen, Layers, Terminal, X, Code2, GitBranch } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';

// Monaco editor for code viewing
import Editor from '@monaco-editor/react';

const MOCK_VULNS = [
  { id: 'v1', title: 'SQL Injection', severity: 'CRITICAL', file: 'src/db/auth.c', line: 142, cwe: 'CWE-89' },
  { id: 'v2', title: 'Buffer Overflow', severity: 'HIGH', file: 'src/core/parser.cpp', line: 89, cwe: 'CWE-119' },
  { id: 'v3', title: 'Use After Free', severity: 'HIGH', file: 'src/memory/gc.c', line: 312, cwe: 'CWE-416' },
  { id: 'v4', title: 'Path Traversal', severity: 'MEDIUM', file: 'src/api/routes.c', line: 55, cwe: 'CWE-22' },
];

export default function ScanResultsWorkspace() {
  const { id } = useParams();
  const [selectedVuln, setSelectedVuln] = useState<typeof MOCK_VULNS[0] | null>(null);
  const [activeTab, setActiveTab] = useState<'ai' | 'code' | 'graph' | 'taint'>('ai');

  return (
    <div className="flex h-[calc(100vh-8rem)] -mt-4 bg-background border border-border rounded-card overflow-hidden relative shadow-soft">
      
      {/* Left Panel: Vulnerability List */}
      <div className={`flex-shrink-0 w-full lg:w-[400px] border-r border-border bg-card flex flex-col transition-all ${selectedVuln ? 'hidden lg:flex' : 'flex'}`}>
        <div className="p-4 border-b border-border bg-card sticky top-0 z-10 flex items-center justify-between">
          <div>
            <Link to={`/projects/${id}`} className="text-muted-foreground hover:text-foreground flex items-center gap-2 text-sm font-medium mb-2">
              <ArrowLeft className="w-4 h-4" /> Back to Project
            </Link>
            <h2 className="font-bold text-lg flex items-center gap-2">
              <ShieldAlert className="w-5 h-5 text-primary" />
              Scan Results
            </h2>
          </div>
          <Badge variant="destructive">4 Issues</Badge>
        </div>
        
        <div className="p-3 border-b border-border bg-card">
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <input 
              type="text" 
              placeholder="Filter vulnerabilities..." 
              className="w-full bg-background border border-border rounded-input pl-8 pr-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary transition-colors"
            />
          </div>
        </div>

        <div className="flex-1 overflow-y-auto scrollbar-thin scrollbar-thumb-border">
          {MOCK_VULNS.map((vuln) => (
            <div 
              key={vuln.id}
              onClick={() => setSelectedVuln(vuln)}
              className={`p-4 border-b border-border/50 cursor-pointer transition-colors ${selectedVuln?.id === vuln.id ? 'bg-primary/10 border-l-2 border-l-primary' : 'hover:bg-muted/50'}`}
            >
              <div className="flex justify-between items-start mb-2">
                <h3 className={`font-medium text-sm ${selectedVuln?.id === vuln.id ? 'text-primary' : 'text-foreground'}`}>{vuln.title}</h3>
                <Badge variant={vuln.severity === 'CRITICAL' || vuln.severity === 'HIGH' ? 'destructive' : 'warning'} className="text-[10px] px-1.5 py-0">
                  {vuln.severity}
                </Badge>
              </div>
              
              <div className="flex flex-col gap-1 text-xs text-muted-foreground mt-2">
                <span className="flex items-center gap-1.5">
                  <Terminal className="w-3.5 h-3.5" /> {vuln.file}:{vuln.line}
                </span>
                <span className="flex items-center gap-1.5">
                  <BookOpen className="w-3.5 h-3.5" /> {vuln.cwe}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Right Panel: Detail Workspace */}
      <div className={`flex-1 flex flex-col bg-background ${!selectedVuln ? 'hidden lg:flex' : 'flex'}`}>
        {!selectedVuln ? (
          <div className="flex-1 flex flex-col items-center justify-center text-muted-foreground p-8 text-center space-y-4">
            <div className="w-16 h-16 rounded-2xl bg-muted flex items-center justify-center">
              <Bug className="w-8 h-8 opacity-50" />
            </div>
            <h3 className="text-xl font-semibold text-foreground">Select a vulnerability</h3>
            <p className="max-w-md">Choose an item from the list on the left to begin the 16-layer vulnerability analysis.</p>
          </div>
        ) : (
          <div className="flex-1 flex flex-col overflow-hidden relative">
            
            {/* Detail Header */}
            <header className="p-6 border-b border-border bg-card flex items-start justify-between">
              <div className="flex items-center gap-4 lg:hidden mb-4">
                <Button variant="ghost" size="sm" onClick={() => setSelectedVuln(null)}>
                  <ArrowLeft className="w-4 h-4 mr-2" /> Back
                </Button>
              </div>
              <div>
                <div className="flex items-center gap-3 mb-2">
                  <Badge variant={selectedVuln.severity === 'CRITICAL' || selectedVuln.severity === 'HIGH' ? 'destructive' : 'warning'}>
                    {selectedVuln.severity}
                  </Badge>
                  <span className="text-sm font-medium text-muted-foreground">{selectedVuln.cwe}</span>
                </div>
                <h2 className="text-2xl font-bold">{selectedVuln.title}</h2>
                <div className="flex items-center gap-2 text-sm text-primary mt-2 cursor-pointer hover:underline">
                  <Code2 className="w-4 h-4" />
                  {selectedVuln.file}:{selectedVuln.line}
                </div>
              </div>
              <Button>Resolve Issue</Button>
            </header>

            {/* Analysis Tabs */}
            <div className="flex border-b border-border bg-muted/20 px-6">
              {[
                { id: 'ai', label: 'AI Explainability', icon: Zap },
                { id: 'code', label: 'Code Viewer', icon: Code2 },
                { id: 'graph', label: 'GNN Graph', icon: Layers },
                { id: 'taint', label: 'Taint Flow', icon: GitBranch },
              ].map(tab => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as any)}
                  className={`flex items-center gap-2 px-4 py-3 text-sm font-medium transition-colors border-b-2 ${activeTab === tab.id ? 'border-primary text-primary' : 'border-transparent text-muted-foreground hover:text-foreground hover:bg-muted/50'}`}
                >
                  <tab.icon className="w-4 h-4" />
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Tab Content Area */}
            <div className="flex-1 overflow-y-auto p-6 scrollbar-thin scrollbar-thumb-border">
              <AnimatePresence mode="wait">
                <motion.div
                  key={activeTab}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  transition={{ duration: 0.15 }}
                  className="h-full"
                >
                  {activeTab === 'ai' && (
                    <div className="space-y-6 max-w-4xl">
                      <Card className="bg-primary/5 border-primary/20">
                        <CardHeader>
                          <CardTitle className="text-lg flex items-center gap-2">
                            <Zap className="w-5 h-5 text-primary" /> AI Diagnosis
                          </CardTitle>
                        </CardHeader>
                        <CardContent className="text-sm leading-relaxed text-foreground/90">
                          The Hybrid GNN-LLM model detected a lack of parameterization in the database query constructed at line {selectedVuln.line}. User input from the HTTP request is directly concatenated into the SQL statement without validation, allowing an attacker to inject arbitrary SQL commands.
                        </CardContent>
                      </Card>

                      <div>
                        <h4 className="font-semibold mb-3">SHAP Value Heatmap (Important Nodes)</h4>
                        <div className="h-64 rounded-xl bg-card border border-border flex items-center justify-center relative overflow-hidden">
                          {/* Placeholder for actual GNN heatmap visualization */}
                          <div className="absolute inset-0 opacity-20 bg-[url('https://www.transparenttextures.com/patterns/cubes.png')]" />
                          <p className="text-muted-foreground z-10">Advanced Heatmap Visualization Loads Here</p>
                        </div>
                      </div>

                      <div>
                        <h4 className="font-semibold mb-3">Remediation Suggestion</h4>
                        <div className="rounded-lg bg-card border border-border p-4">
                          <pre className="text-xs text-primary-400 font-mono">
                            <span className="text-red-400">- string query = "SELECT * FROM users WHERE email = '" + req.body.email + "'";</span>
                            <br />
                            <span className="text-emerald-400">+ string query = "SELECT * FROM users WHERE email = ?";</span>
                            <br />
                            <span className="text-emerald-400">+ db.execute(query, req.body.email);</span>
                          </pre>
                        </div>
                      </div>
                    </div>
                  )}

                  {activeTab === 'code' && (
                    <div className="h-full rounded-xl overflow-hidden border border-border">
                      <Editor
                        height="100%"
                        defaultLanguage="c"
                        theme="vs-dark"
                        options={{
                          minimap: { enabled: false },
                          fontSize: 14,
                          readOnly: true,
                          padding: { top: 16 }
                        }}
                        defaultValue={`// Sample Code Viewer
void authenticate_user(Request* req) {
    char query[256];
    
    // VULNERABLE LINE:
    sprintf(query, "SELECT * FROM users WHERE email = '%s'", req->body->email);
    
    db_execute(query);
}`}
                      />
                    </div>
                  )}

                  {activeTab === 'graph' && (
                    <div className="h-full flex items-center justify-center border border-border rounded-xl bg-card">
                      <div className="text-center text-muted-foreground">
                        <Layers className="w-12 h-12 mx-auto mb-4 opacity-50" />
                        <p>Cytoscape Graph Visualization renders here</p>
                        <p className="text-xs mt-2">Integrating existing GraphViewer.tsx</p>
                      </div>
                    </div>
                  )}

                  {activeTab === 'taint' && (
                    <div className="h-full flex items-center justify-center border border-border rounded-xl bg-card">
                      <div className="text-center text-muted-foreground">
                        <GitBranch className="w-12 h-12 mx-auto mb-4 opacity-50" />
                        <p>Taint Analysis Data Flow renders here</p>
                        <p className="text-xs mt-2">Integrating existing TaintReport.tsx flow trees</p>
                      </div>
                    </div>
                  )}
                </motion.div>
              </AnimatePresence>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
