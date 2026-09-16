import React, { useEffect, useState } from 'react';
import { useParams, useSearchParams, Link } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { ArrowLeft, Bug, Search, ShieldAlert, Zap, BookOpen, Layers, Terminal, Code2, GitBranch, Loader2 } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { resultService } from '../../services/resultService';
import { ScanResult } from '../../types';

// Monaco editor for code viewing
import Editor from '@monaco-editor/react';

export default function ScanResultsWorkspace() {
  const params = useParams<{ id?: string; projectId?: string }>();
  const id = params.projectId || params.id;
  const [searchParams] = useSearchParams();
  const scanId = searchParams.get('scan_id');

  const [results, setResults] = useState<ScanResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedResult, setSelectedResult] = useState<ScanResult | null>(null);
  const [activeTab, setActiveTab] = useState<'ai' | 'code' | 'graph' | 'taint'>('ai');
  const [filterText, setFilterText] = useState('');

  useEffect(() => {
    if (!scanId) return;
    async function loadResults() {
      setLoading(true);
      try {
        const data = await resultService.getScanResults(scanId!, { page_size: 100 });
        setResults(data.items);
      } catch {
        // Handled by interceptor
      } finally {
        setLoading(false);
      }
    }
    loadResults();
  }, [scanId]);

  const filteredResults = results.filter((r) => {
    if (!filterText) return true;
    const text = filterText.toLowerCase();
    return (
      r.file_path?.toLowerCase().includes(text) ||
      r.function_name?.toLowerCase().includes(text) ||
      r.severity?.toLowerCase().includes(text) ||
      r.cwe_id?.toLowerCase().includes(text)
    );
  });

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="flex h-[calc(100vh-8rem)] -mt-4 bg-background border border-border rounded-card overflow-hidden relative shadow-soft">

      {/* Left Panel: Vulnerability List */}
      <div className={`flex-shrink-0 w-full lg:w-[400px] border-r border-border bg-card flex flex-col transition-all ${selectedResult ? 'hidden lg:flex' : 'flex'}`}>
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
          <Badge variant={results.length > 0 ? 'destructive' : 'safe'}>
            {results.length} {results.length === 1 ? 'Issue' : 'Issues'}
          </Badge>
        </div>

        <div className="p-3 border-b border-border bg-card">
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <input
              type="text"
              placeholder="Filter vulnerabilities..."
              value={filterText}
              onChange={(e) => setFilterText(e.target.value)}
              className="w-full bg-background border border-border rounded-input pl-8 pr-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary transition-colors"
            />
          </div>
        </div>

        <div className="flex-1 overflow-y-auto scrollbar-thin scrollbar-thumb-border">
          {filteredResults.length === 0 ? (
            <div className="p-8 text-center text-muted-foreground">
              <ShieldAlert className="w-8 h-8 mx-auto mb-3 opacity-50" />
              <p className="text-sm">
                {results.length === 0 ? 'No vulnerabilities found!' : 'No results match your filter.'}
              </p>
            </div>
          ) : (
            filteredResults.map((result) => (
              <div
                key={result.id}
                onClick={() => setSelectedResult(result)}
                className={`p-4 border-b border-border/50 cursor-pointer transition-colors ${selectedResult?.id === result.id ? 'bg-primary/10 border-l-2 border-l-primary' : 'hover:bg-muted/50'}`}
              >
                <div className="flex justify-between items-start mb-2">
                  <h3 className={`font-medium text-sm ${selectedResult?.id === result.id ? 'text-primary' : 'text-foreground'}`}>
                    {result.cwe_id || 'Finding'} — {result.function_name || 'Unknown Function'}
                  </h3>
                  <Badge variant={result.severity === 'CRITICAL' || result.severity === 'HIGH' ? 'destructive' : result.severity === 'MEDIUM' ? 'warning' : 'safe'} className="text-[10px] px-1.5 py-0">
                    {result.severity}
                  </Badge>
                </div>

                <div className="flex flex-col gap-1 text-xs text-muted-foreground mt-2">
                  <span className="flex items-center gap-1.5">
                    <Terminal className="w-3.5 h-3.5" /> {result.file_path}:{result.line_number || '?'}
                  </span>
                  {result.cwe_id && (
                    <span className="flex items-center gap-1.5">
                      <BookOpen className="w-3.5 h-3.5" /> {result.cwe_id}
                    </span>
                  )}
                  <span className="text-[10px] text-muted-foreground/60">
                    Confidence: {Math.round((result.confidence ?? 0) * 100)}%
                  </span>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Right Panel: Detail Workspace */}
      <div className={`flex-1 flex flex-col bg-background ${!selectedResult ? 'hidden lg:flex' : 'flex'}`}>
        {!selectedResult ? (
          <div className="flex-1 flex flex-col items-center justify-center text-muted-foreground p-8 text-center space-y-4">
            <div className="w-16 h-16 rounded-2xl bg-muted flex items-center justify-center">
              <Bug className="w-8 h-8 opacity-50" />
            </div>
            <h3 className="text-xl font-semibold text-foreground">
              {results.length === 0 ? 'No vulnerabilities detected' : 'Select a vulnerability'}
            </h3>
            <p className="max-w-md">
              {results.length === 0
                ? 'The AI scan completed with no findings. Your code looks clean!'
                : 'Choose an item from the list on the left to begin the vulnerability analysis.'}
            </p>
          </div>
        ) : (
          <div className="flex-1 flex flex-col overflow-hidden relative">

            {/* Detail Header */}
            <header className="p-6 border-b border-border bg-card flex items-start justify-between">
              <div className="flex items-center gap-4 lg:hidden mb-4">
                <Button variant="ghost" size="sm" onClick={() => setSelectedResult(null)}>
                  <ArrowLeft className="w-4 h-4 mr-2" /> Back
                </Button>
              </div>
              <div>
                <div className="flex items-center gap-3 mb-2">
                  <Badge variant={selectedResult.severity === 'CRITICAL' || selectedResult.severity === 'HIGH' ? 'destructive' : selectedResult.severity === 'MEDIUM' ? 'warning' : 'safe'}>
                    {selectedResult.severity}
                  </Badge>
                  <span className="text-sm font-medium text-muted-foreground">{selectedResult.cwe_id || 'N/A'}</span>
                  <span className="text-xs text-muted-foreground">
                    Confidence: {Math.round((selectedResult.confidence ?? 0) * 100)}%
                  </span>
                </div>
                <h2 className="text-2xl font-bold">
                  {selectedResult.function_name || selectedResult.cwe_id || 'Vulnerability Finding'}
                </h2>
                <div className="flex items-center gap-2 text-sm text-primary mt-2 cursor-pointer hover:underline">
                  <Code2 className="w-4 h-4" />
                  {selectedResult.file_path}:{selectedResult.line_number || '?'}
                </div>
              </div>
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
                          {selectedResult.explanation || 'No AI explanation available for this finding.'}
                        </CardContent>
                      </Card>

                      {selectedResult.recommended_patch && (
                        <div>
                          <h4 className="font-semibold mb-3">Remediation Suggestion</h4>
                          <div className="rounded-lg bg-card border border-border p-4">
                            <pre className="text-xs text-emerald-400 font-mono whitespace-pre-wrap">
                              {selectedResult.recommended_patch}
                            </pre>
                          </div>
                        </div>
                      )}

                      <div>
                        <h4 className="font-semibold mb-3">Details</h4>
                        <div className="rounded-lg bg-card border border-border p-4 space-y-2 text-sm">
                          <div><span className="text-muted-foreground">File:</span> {selectedResult.file_path}</div>
                          <div><span className="text-muted-foreground">Function:</span> {selectedResult.function_name || '—'}</div>
                          <div><span className="text-muted-foreground">Line:</span> {selectedResult.line_number || '—'}</div>
                          <div><span className="text-muted-foreground">CWE:</span> {selectedResult.cwe_id || '—'}</div>
                          <div><span className="text-muted-foreground">Model:</span> {selectedResult.model_version || '—'}</div>
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
                        defaultValue={`// File: ${selectedResult.file_path}\n// Line: ${selectedResult.line_number || '?'}\n// Function: ${selectedResult.function_name || 'unknown'}\n\n// ${selectedResult.explanation || 'No additional context.'}`}
                      />
                    </div>
                  )}

                  {activeTab === 'graph' && (
                    <div className="h-full flex items-center justify-center border border-border rounded-xl bg-card">
                      <div className="text-center text-muted-foreground p-6 max-w-md">
                        <Layers className="w-12 h-12 mx-auto mb-4 opacity-50 text-primary" />
                        <p className="font-medium text-foreground">Interactive Code Property Graph Visualization</p>
                        <p className="text-xs text-muted-foreground mt-2 leading-relaxed">
                          Visual AST, CFG, and PDG graph rendering with interactive node inspection is scheduled for Phase 4 (Graph Construction & Preprocessing).
                        </p>
                      </div>
                    </div>
                  )}

                  {activeTab === 'taint' && (
                    <div className="h-full flex items-center justify-center border border-border rounded-xl bg-card">
                      <div className="text-center text-muted-foreground p-6 max-w-md">
                        <GitBranch className="w-12 h-12 mx-auto mb-4 opacity-50 text-primary" />
                        <p className="font-medium text-foreground">Taint Analysis Data Flow</p>
                        <p className="text-xs text-muted-foreground mt-2 leading-relaxed">
                          Source-to-sink taint propagation and data flow path traversal will populate in Phase 4 (Graph Construction & Preprocessing).
                        </p>
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
