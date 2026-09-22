import React from 'react';
import { motion } from 'framer-motion';
import {
  ArrowRight,
  ShieldCheck,
  Terminal,
  Cpu,
  Layers,
  FileCode2,
  CheckCircle2,
  Zap,
  Lock,
  Network,
  BookOpen,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { Button } from '../components/ui/Button';
import { VulnScanLogo } from '../components/VulnScanLogo';

export default function Landing() {
  const pipelineSteps = [
    { label: 'Source Snapshot', desc: 'Immutable code provenance & hash verification', icon: FileCode2 },
    { label: 'Static Analysis', desc: 'AST, CFG, PDG & Taint tracking across call paths', icon: Network },
    { label: 'AI Detection', desc: 'Fine-tuned vulnerability classification & confidence', icon: Cpu },
    { label: 'XAI Attribution', desc: 'Token & line-level interpretability evidence', icon: Zap },
    { label: 'Verified Patch', desc: 'Automated remediation with authoritative verification', icon: ShieldCheck },
  ];

  return (
    <div className="relative isolate bg-background min-h-screen flex flex-col selection:bg-primary/30">
      {/* Public Navigation */}
      <header className="px-6 lg:px-12 h-16 flex items-center justify-between border-b border-border bg-background/80 backdrop-blur-md sticky top-0 z-40">
        <div className="flex items-center gap-8">
          <VulnScanLogo variant="full" size="md" linkTo="/" />
          <nav className="hidden md:flex items-center gap-6 text-xs font-medium text-muted-foreground">
            <Link to="/documentation" className="hover:text-foreground transition-colors flex items-center gap-1.5">
              <BookOpen className="w-3.5 h-3.5" /> Documentation
            </Link>
            <a href="#pipeline" className="hover:text-foreground transition-colors">Architecture</a>
            <a href="#features" className="hover:text-foreground transition-colors">Capabilities</a>
          </nav>
        </div>
        <div className="flex items-center gap-3">
          <Link
            to="/login"
            className="text-xs font-medium text-muted-foreground hover:text-foreground transition-colors px-3 py-1.5"
          >
            Sign in
          </Link>
          <Link to="/register">
            <Button size="sm" className="btn-primary">
              <span>Open Workstation</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Button>
          </Link>
        </div>
      </header>

      {/* Hero Section */}
      <main className="flex-1">
        <section className="mx-auto max-w-6xl px-6 pt-20 pb-16 sm:pt-28 sm:pb-20 text-center">
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
            className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-border bg-card/80 text-[11px] font-mono text-muted-foreground mb-8"
          >
            <span className="w-2 h-2 rounded-full bg-brand-orange animate-pulse" />
            <span>VulnScan Core v2.4 • Deterministic Graph + Explainable AI</span>
          </motion.div>

          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.1 }}
            className="text-4xl sm:text-6xl font-bold tracking-tight text-foreground font-display max-w-4xl mx-auto leading-tight sm:leading-none"
          >
            Developer-Focused Application Security{' '}
            <span className="bg-gradient-to-r from-brand-orange via-brand-amber to-primary bg-clip-text text-transparent">
              Workstation
            </span>
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="mt-6 text-base sm:text-lg text-muted-foreground max-w-2xl mx-auto leading-relaxed"
          >
            Trace taint paths, inspect canonical control-flow graphs, explain AI vulnerability detections, and apply authoritative verified patches in one unified workspace.
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.3 }}
            className="mt-10 flex flex-wrap items-center justify-center gap-3"
          >
            <Link to="/register">
              <Button size="lg" className="h-11 px-6 btn-primary text-sm font-medium">
                Get Started Free
                <ArrowRight className="ml-2 w-4 h-4" />
              </Button>
            </Link>
            <Link to="/documentation">
              <Button size="lg" variant="outline" className="h-11 px-6 border-border hover:bg-card-hover text-sm font-medium">
                <Terminal className="mr-2 w-4 h-4 text-primary" /> Read Technical Docs
              </Button>
            </Link>
          </motion.div>

          {/* Technical Workflow Pipeline */}
          <div id="pipeline" className="mt-20 pt-10 border-t border-border/60 text-left">
            <div className="text-center mb-10">
              <h2 className="text-xl font-bold font-display text-foreground">
                Authoritative Investigation Pipeline
              </h2>
              <p className="text-xs text-muted-foreground mt-1">
                Zero fabricated metrics. Complete end-to-end provenance from source code to verified patch.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
              {pipelineSteps.map((step, idx) => {
                const Icon = step.icon;
                return (
                  <div
                    key={step.label}
                    className="p-4 bg-card border border-border rounded-card hover:border-primary/40 transition-colors relative group shadow-soft"
                  >
                    <div className="flex items-center justify-between mb-3">
                      <div className="w-8 h-8 rounded-md bg-sidebar border border-border/80 flex items-center justify-center text-primary">
                        <Icon className="w-4 h-4" />
                      </div>
                      <span className="font-mono text-[10px] text-muted-foreground font-semibold">
                        0{idx + 1}
                      </span>
                    </div>
                    <div className="font-medium text-xs text-foreground font-display">
                      {step.label}
                    </div>
                    <p className="text-[11px] text-muted-foreground mt-1 leading-relaxed">
                      {step.desc}
                    </p>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Workstation Console Mockup */}
          <div id="features" className="mt-16 bg-card border border-border rounded-lg shadow-2xl overflow-hidden text-left font-mono text-xs">
            <div className="px-4 py-2.5 bg-sidebar border-b border-border flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-destructive/60 inline-block" />
                <span className="w-2.5 h-2.5 rounded-full bg-severity-medium/60 inline-block" />
                <span className="w-2.5 h-2.5 rounded-full bg-severity-success/60 inline-block" />
                <span className="ml-2 text-[11px] text-muted-foreground">vulnscan-cli --scan ./src --strict</span>
              </div>
              <span className="text-[10px] text-muted-foreground">SECURITY BOUNDARY: READY</span>
            </div>
            <div className="p-5 bg-background space-y-2 text-[12px] leading-relaxed text-muted-foreground">
              <div className="text-foreground flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-severity-success shrink-0" />
                <span>Immutable Source Snapshot created: <strong className="text-primary">snp_e91b4f128c92</strong> (SHA-256 verified)</span>
              </div>
              <div className="text-foreground flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-severity-success shrink-0" />
                <span>Static Call Graph & Taint Engine: 12 sinks identified across 4 attack vectors</span>
              </div>
              <div className="text-foreground flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-severity-success shrink-0" />
                <span>AI Inferred Vulnerability: <strong className="text-brand-orange">CWE-89 SQL Injection</strong> [Confidence: 0.96]</span>
              </div>
              <div className="text-foreground flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-severity-success shrink-0" />
                <span>Automated Remediation: Parameterized query patch verified authoritative</span>
              </div>
            </div>
          </div>
        </section>
      </main>

      {/* Clean Technical Footer */}
      <footer className="py-6 px-6 lg:px-12 border-t border-border bg-sidebar/50 flex flex-col sm:flex-row items-center justify-between text-xs text-muted-foreground gap-4">
        <div className="flex items-center gap-2">
          <VulnScanLogo variant="icon" size="xs" />
          <span>© {new Date().getFullYear()} VulnScan. Security operations workstation.</span>
        </div>
        <div className="flex items-center gap-6">
          <Link to="/documentation" className="hover:text-foreground transition-colors">Documentation</Link>
          <Link to="/login" className="hover:text-foreground transition-colors">Sign in</Link>
          <Link to="/register" className="hover:text-foreground transition-colors">Register</Link>
        </div>
      </footer>
    </div>
  );
}
