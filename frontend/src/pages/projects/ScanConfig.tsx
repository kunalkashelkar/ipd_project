import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { 
  Play, 
  Settings, 
  ShieldCheck, 
  GitBranch, 
  FileCode2, 
  AlertTriangle,
  Cpu
} from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent, CardDescription, CardFooter } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';

export default function ScanConfig() {
  const { id } = useParams();
  const navigate = useNavigate();
  
  const [useGnn, setUseGnn] = useState(true);
  const [useLLM, setUseLLM] = useState(true);
  const [depth, setDepth] = useState<'shallow' | 'standard' | 'deep'>('standard');

  const handleStartScan = () => {
    // Navigate to progress page
    navigate(`/projects/${id}/scan-progress`);
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold font-display tracking-tight text-foreground">Configure Pipeline</h1>
          <p className="text-muted-foreground mt-1">Select the AI models and analysis depth for this scan.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="md:col-span-2 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Settings className="w-5 h-5 text-primary" /> Analysis Engines
              </CardTitle>
              <CardDescription>Toggle which security engines to run during this scan.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              
              <div className="flex items-start justify-between p-4 border border-border rounded-lg bg-card/50 hover:bg-muted/20 transition-colors">
                <div className="flex gap-3">
                  <div className="bg-primary/20 p-2 rounded-md h-fit">
                    <FileCode2 className="w-5 h-5 text-primary" />
                  </div>
                  <div>
                    <h3 className="font-medium text-foreground">Static & Taint Analysis</h3>
                    <p className="text-sm text-muted-foreground mt-1">Base requirement. Extracts Code Property Graphs (CPGs) using Joern.</p>
                  </div>
                </div>
                <div className="h-6 w-11 rounded-full bg-primary relative cursor-not-allowed">
                  <div className="h-4 w-4 rounded-full bg-white absolute right-1 top-1"></div>
                </div>
              </div>

              <div className="flex items-start justify-between p-4 border border-border rounded-lg bg-card/50 hover:bg-muted/20 transition-colors">
                <div className="flex gap-3">
                  <div className="bg-primary/20 p-2 rounded-md h-fit">
                    <GitBranch className="w-5 h-5 text-primary" />
                  </div>
                  <div>
                    <h3 className="font-medium text-foreground">GNN Vulnerability Classifier</h3>
                    <p className="text-sm text-muted-foreground mt-1">Uses pre-trained Graph Neural Networks to identify zero-day patterns in the CPG.</p>
                  </div>
                </div>
                <button 
                  onClick={() => setUseGnn(!useGnn)}
                  className={`h-6 w-11 rounded-full relative transition-colors ${useGnn ? 'bg-primary' : 'bg-muted'}`}
                >
                  <div className={`h-4 w-4 rounded-full bg-white absolute top-1 transition-all ${useGnn ? 'right-1' : 'left-1'}`}></div>
                </button>
              </div>

              <div className="flex items-start justify-between p-4 border border-border rounded-lg bg-card/50 hover:bg-muted/20 transition-colors">
                <div className="flex gap-3">
                  <div className="bg-primary/20 p-2 rounded-md h-fit">
                    <Cpu className="w-5 h-5 text-primary" />
                  </div>
                  <div>
                    <h3 className="font-medium text-foreground">LLM Explainability Module</h3>
                    <p className="text-sm text-muted-foreground mt-1">Generates human-readable explanations and remediation suggestions for detected issues.</p>
                  </div>
                </div>
                <button 
                  onClick={() => setUseLLM(!useLLM)}
                  className={`h-6 w-11 rounded-full relative transition-colors ${useLLM ? 'bg-primary' : 'bg-muted'}`}
                >
                  <div className={`h-4 w-4 rounded-full bg-white absolute top-1 transition-all ${useLLM ? 'right-1' : 'left-1'}`}></div>
                </button>
              </div>

            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <ShieldCheck className="w-5 h-5 text-primary" /> Scan Depth
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-3 gap-4">
                {(['shallow', 'standard', 'deep'] as const).map(d => (
                  <button
                    key={d}
                    onClick={() => setDepth(d)}
                    className={`p-4 border rounded-lg text-center flex flex-col items-center gap-2 transition-all ${depth === d ? 'border-primary bg-primary/10 text-primary' : 'border-border text-foreground hover:bg-muted/50'}`}
                  >
                    <span className="font-semibold capitalize">{d}</span>
                  </button>
                ))}
              </div>
              
              <div className="mt-4 p-3 bg-muted/30 border border-border rounded-md text-sm text-muted-foreground flex gap-2">
                <AlertTriangle className="w-4 h-4 text-warning flex-shrink-0" />
                <span>
                  {depth === 'shallow' && 'Fastest scan. Only checks for known CVE patterns and basic semantic flaws.'}
                  {depth === 'standard' && 'Recommended. Full AI pipeline with medium-depth taint tracking.'}
                  {depth === 'deep' && 'Exhaustive data flow analysis. This can take a very long time for large codebases.'}
                </span>
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6">
          <Card className="bg-primary/5 border-primary/20">
            <CardHeader>
               <CardTitle>Scan Summary</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Target</span>
                <span className="font-medium text-foreground">main branch</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Lang</span>
                <span className="font-medium text-foreground">C/C++</span>
              </div>
              <div className="my-2 border-t border-border"></div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Est. Time</span>
                <span className="font-medium text-foreground">
                  {depth === 'shallow' ? '~2 mins' : depth === 'standard' ? '~5-8 mins' : '~20+ mins'}
                </span>
              </div>
            </CardContent>
            <CardFooter>
              <Button onClick={handleStartScan} className="w-full h-12 text-lg shadow-[0_0_20px_-5px_hsl(var(--primary))] hover:shadow-[0_0_25px_-5px_hsl(var(--primary))]">
                <Play className="w-5 h-5 mr-2" fill="currentColor" /> Initiatize Scan
              </Button>
            </CardFooter>
          </Card>
        </div>
      </div>
    </div>
  );
}
