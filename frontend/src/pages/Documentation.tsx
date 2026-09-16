import React from 'react';
import { BookOpen, Shield, Cpu, Network, Layers, GitBranch, ArrowUpRight } from 'lucide-react';
import { PageHeader, Card, CardHeader, CardTitle, CardDescription, CardContent, Badge } from '../components/ui';

export default function Documentation() {
  const sections = [
    {
      title: 'Architecture & System Overview',
      icon: <Layers className="w-5 h-5 text-primary" />,
      description: 'Understanding the 4-layer representation: AST, CFG, DFG, and PDG graph integration.',
      phase: 'Phase 0 / Phase 1',
      status: 'Active Baseline',
    },
    {
      title: 'Repository Ingestion & Preprocessing',
      icon: <GitBranch className="w-5 h-5 text-cyan-400" />,
      description: 'ZIP/file ingestion, Git/GitHub synchronization, immutable S3 snapshots, and deterministic code preprocessing.',
      phase: 'Phase 3',
      status: 'Active Platform Capability',
    },
    {
      title: 'Static & Graph Analysis Pipeline',
      icon: <Network className="w-5 h-5 text-emerald-400" />,
      description: 'CPG generation, data-flow traversal, and taint analysis using Joern and custom query passes.',
      phase: 'Phase 4',
      status: 'Deferred',
    },
    {
      title: 'Hybrid AI Classification Engine',
      icon: <Cpu className="w-5 h-5 text-purple-400" />,
      description: 'Graph Neural Networks (GNN) and semantic transformer embeddings for vulnerability detection.',
      phase: 'Phase 5',
      status: 'Deferred',
    },
    {
      title: 'Explainability & Automated Remediation',
      icon: <Shield className="w-5 h-5 text-amber-400" />,
      description: 'Sub-graph attribution (Captum) and LLM-driven patch synthesis with validation checks.',
      phase: 'Phase 6',
      status: 'Deferred',
    },
  ];

  return (
    <div className="max-w-5xl mx-auto space-y-6 pb-12">
      <PageHeader
        title="Platform Documentation"
        description="Comprehensive technical reference and architectural specifications for the Hybrid XAI Vulnerability Detection Framework."
      />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {sections.map((section, idx) => (
          <Card key={idx} className="hover:border-primary/40 transition-colors">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <div className="p-2 rounded-lg bg-muted/60">{section.icon}</div>
                <Badge variant={section.status === 'Active Baseline' ? 'default' : 'outline'}>
                  {section.phase}
                </Badge>
              </div>
              <CardTitle className="text-base mt-3 flex items-center gap-1.5">
                {section.title}
              </CardTitle>
              <CardDescription className="text-xs leading-relaxed">
                {section.description}
              </CardDescription>
            </CardHeader>
            <CardContent className="pt-0">
              <div className="text-xs font-medium text-muted-foreground flex items-center justify-between border-t border-border/50 pt-3 mt-1">
                <span>Implementation Status:</span>
                <span className="font-semibold text-foreground">{section.status}</span>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
