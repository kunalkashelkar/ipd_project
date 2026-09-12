import React from 'react';
import { motion } from 'framer-motion';
import { ShieldCheck, ArrowRight, ArrowDown } from 'lucide-react';
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
    <div className="relative isolate bg-background min-h-screen flex flex-col">
      {/* Public Navigation */}
      <header className="px-6 lg:px-8 h-16 flex items-center justify-between border-b border-border bg-background">
        <div className="flex items-center gap-8">
          <Link to="/" className="flex items-center gap-2 font-bold text-foreground">
            <ShieldCheck className="w-5 h-5 text-primary" />
            XAI Tool
          </Link>
          <nav className="hidden md:flex gap-6 text-sm font-medium text-muted-foreground">
            <Link to="#" className="hover:text-foreground transition-colors">Features</Link>
            <Link to="#" className="hover:text-foreground transition-colors">Documentation</Link>
            <Link to="#" className="hover:text-foreground transition-colors">Pricing</Link>
          </nav>
        </div>
        <div className="flex items-center gap-4">
          <Link to="/login" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">
            Login
          </Link>
          <Link to="/register">
            <Button size="sm">Get Started</Button>
          </Link>
        </div>
      </header>

      {/* Hero Section */}
      <div className="mx-auto max-w-5xl px-6 py-24 sm:py-32 lg:px-8 flex-1 flex flex-col items-center justify-center">
        <motion.div
          className="text-center w-full"
          variants={containerVariants}
          initial="hidden"
          animate="show"
        >
          <motion.h1 variants={itemVariants} className="text-5xl font-bold tracking-tight text-foreground sm:text-7xl mb-6">
            AI Powered <span className="text-primary">Vulnerability</span> Detection
          </motion.h1>

          <motion.p variants={itemVariants} className="mt-4 text-xl leading-8 text-muted-foreground max-w-2xl mx-auto">
            Find security vulnerabilities before attackers do.
          </motion.p>

          <motion.div variants={itemVariants} className="mt-10 flex items-center justify-center gap-x-4">
            <Link to="/register">
              <Button size="lg" className="rounded-full h-12 px-8">
                Get Started
              </Button>
            </Link>
            <Button size="lg" variant="outline" className="rounded-full h-12 px-8">
              Watch Demo
              <ArrowRight className="ml-2 w-4 h-4" />
            </Button>
          </motion.div>

          {/* Workflow Animation Text */}
          <motion.div variants={itemVariants} className="mt-24 max-w-sm mx-auto space-y-4">
            <div className="bg-card border border-border rounded-card p-4 text-center font-medium shadow-soft">
              Upload Code
            </div>
            <div className="flex justify-center text-primary">
              <ArrowDown className="w-6 h-6 animate-bounce" />
            </div>
            <div className="bg-card border border-border rounded-card p-4 text-center font-medium shadow-soft">
              AI Analysis
            </div>
            <div className="flex justify-center text-primary">
              <ArrowDown className="w-6 h-6 animate-bounce" />
            </div>
            <div className="bg-card border border-border rounded-card p-4 text-center font-medium shadow-soft">
              LLM Fix
            </div>
            <div className="flex justify-center text-primary">
              <ArrowDown className="w-6 h-6 animate-bounce" />
            </div>
            <div className="bg-card border border-border rounded-card p-4 text-center font-medium shadow-soft">
              Report
            </div>
          </motion.div>
        </motion.div>
      </div>

      <footer className="text-center py-8 text-sm text-muted-foreground border-t border-border">
        © {new Date().getFullYear()} XAI Tool. All rights reserved.
      </footer>
    </div>
  );
}
