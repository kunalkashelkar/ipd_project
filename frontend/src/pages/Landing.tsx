import React from 'react';
import { motion } from 'framer-motion';
import { ShieldCheck, Crosshair, Network, GitBranch, ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Button } from '../components/ui/Button';

export default function Landing() {
  const containerVariants = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: { staggerChildren: 0.2 }
    }
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    show: { opacity: 1, y: 0, transition: { duration: 0.5, ease: "easeOut" } }
  };

  return (
    <div className="relative isolate px-6 pt-14 lg:px-8 bg-background min-h-screen">
      <div className="mx-auto max-w-5xl py-24 sm:py-32 lg:py-40">
        <motion.div 
          className="text-center"
          variants={containerVariants}
          initial="hidden"
          animate="show"
        >
          <motion.div variants={itemVariants} className="mb-8 flex justify-center">
            <span className="relative rounded-full px-5 py-1.5 text-sm font-semibold leading-6 text-primary ring-1 ring-primary/30 hover:ring-primary/60 transition-all bg-primary/10 shadow-glow flex items-center gap-2">
              <ShieldCheck className="w-4 h-4" />
              Aegis Kinetic v1.0 is now live
            </span>
          </motion.div>
          
          <motion.h1 variants={itemVariants} className="text-5xl font-bold tracking-tight text-foreground sm:text-7xl mb-8">
            AI-Powered <span className="text-gradient hover:drop-shadow-[0_0_20px_rgba(6,182,212,0.6)] transition-all">Vulnerability Detection</span> <br /> Architecture
          </motion.h1>
          
          <motion.p variants={itemVariants} className="mt-6 text-lg leading-8 text-muted-foreground max-w-2xl mx-auto">
            Secure your entire software supply chain using our 16-layer hybrid XAI pipeline. 
            Identify vulnerabilities in code with unparalleled accuracy combining Graph Neural Networks and LLMs.
          </motion.p>
          
          <motion.div variants={itemVariants} className="mt-10 flex items-center justify-center gap-x-6">
            <Link to="/register">
              <Button size="lg" className="rounded-full h-12 px-8 text-base shadow-[0_0_25px_rgba(6,182,212,0.4)] hover:-translate-y-1">
                Get Started
                <ArrowRight className="ml-2 w-4 h-4" />
              </Button>
            </Link>
            <Link to="/login" className="text-sm font-semibold leading-6 text-foreground hover:text-primary transition-colors hover:translate-x-1 duration-300 flex items-center gap-2">
              Log in <span aria-hidden="true">→</span>
            </Link>
          </motion.div>
        </motion.div>

        {/* Feature grid */}
        <motion.div 
          variants={containerVariants}
          initial="hidden"
          whileInView="show"
          viewport={{ once: true }}
          className="mt-32 grid grid-cols-1 gap-8 sm:grid-cols-2 lg:grid-cols-3"
        >
          <motion.div variants={itemVariants} className="glass-panel p-8 hover:-translate-y-2 transition-transform duration-300 group">
            <div className="w-12 h-12 rounded-xl bg-primary/20 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
              <Network className="w-6 h-6 text-primary" />
            </div>
            <h3 className="text-xl font-semibold mb-3 text-foreground group-hover:text-primary transition-colors">16-Layer Analysis</h3>
            <p className="text-muted-foreground text-sm leading-relaxed">
              Synthesizing AST, CFG, PDG, and Call Graphs. Our hybrid model captures both structural and semantic vulnerability markers.
            </p>
          </motion.div>

          <motion.div variants={itemVariants} className="glass-panel p-8 hover:-translate-y-2 transition-transform duration-300 group">
            <div className="w-12 h-12 rounded-xl bg-amber-500/20 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
              <Crosshair className="w-6 h-6 text-amber-500" />
            </div>
            <h3 className="text-xl font-semibold mb-3 text-foreground group-hover:text-amber-500 transition-colors">AI Explainability</h3>
            <p className="text-muted-foreground text-sm leading-relaxed">
              Don't just detect vulnerabilities. Understand exactly why a node was flagged using state-of-the-art SHAP analysis and heatmaps.
            </p>
          </motion.div>

          <motion.div variants={itemVariants} className="glass-panel p-8 hover:-translate-y-2 transition-transform duration-300 group">
            <div className="w-12 h-12 rounded-xl bg-emerald-500/20 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
              <GitBranch className="w-6 h-6 text-emerald-500" />
            </div>
            <h3 className="text-xl font-semibold mb-3 text-foreground group-hover:text-emerald-500 transition-colors">Taint Flow Tracking</h3>
            <p className="text-muted-foreground text-sm leading-relaxed">
              Tracing attack paths from user inputs to critical sinks to identify SQL injections, Buffer Overflows and XSS automatically.
            </p>
          </motion.div>
        </motion.div>
      </div>

      {/* Statistics banner */}
      <div className="border-y border-border/50 bg-card/20 backdrop-blur-sm py-12 relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-r from-primary/5 via-transparent to-primary/5" />
        <div className="max-w-7xl mx-auto px-6 lg:px-8 relative z-10 flex flex-wrap gap-8 justify-around items-center">
          <div className="text-center">
            <div className="text-4xl font-bold bg-clip-text text-transparent bg-gradient-to-br from-white to-white/70">10M+</div>
            <div className="text-sm font-medium text-muted-foreground mt-2 uppercase tracking-widest">Lines Scanned</div>
          </div>
          <div className="text-center">
            <div className="text-4xl font-bold bg-clip-text text-transparent bg-gradient-to-br from-white to-white/70">C/C++</div>
            <div className="text-sm font-medium text-muted-foreground mt-2 uppercase tracking-widest">Languages</div>
          </div>
          <div className="text-center">
            <div className="text-4xl font-bold bg-clip-text text-transparent bg-gradient-to-br from-white to-white/70">99.3%</div>
            <div className="text-sm font-medium text-muted-foreground mt-2 uppercase tracking-widest">Detection Rate</div>
          </div>
        </div>
      </div>
      
      <footer className="text-center py-8 text-sm text-muted-foreground/60">
        © {new Date().getFullYear()} Aegis Kinetic. All rights reserved.
      </footer>
    </div>
  );
}
