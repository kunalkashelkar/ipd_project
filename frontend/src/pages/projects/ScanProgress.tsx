import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Check, Loader2, Database, Network, Zap, ShieldCheck } from 'lucide-react';
import { Card } from '../../components/ui/Card';

const SCAN_STEPS = [
  { id: 'parse', label: 'Parsing Source Code (Joern)', icon: Database, duration: 2000 },
  { id: 'taint', label: 'Extracting Data Flow & Taint Paths', icon: Network, duration: 3000 },
  { id: 'gnn', label: 'GNN Vulnerability Classification', icon: Zap, duration: 4000 },
  { id: 'llm', label: 'LLM Explainability Generation', icon: ShieldCheck, duration: 3000 }
];

export default function ScanProgress() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [completed, setCompleted] = useState(false);

  useEffect(() => {
    let timeoutId: ReturnType<typeof setTimeout>;

    const runStep = (index: number) => {
      if (index >= SCAN_STEPS.length) {
        setCompleted(true);
        timeoutId = setTimeout(() => {
          navigate(`/projects/${id}/results`);
        }, 1000);
        return;
      }

      timeoutId = setTimeout(() => {
        setCurrentStepIndex(index + 1);
        runStep(index + 1);
      }, SCAN_STEPS[index].duration);
    };

    runStep(0);

    return () => clearTimeout(timeoutId);
  }, [id, navigate]);

  const progressPercentage = Math.min(((currentStepIndex) / SCAN_STEPS.length) * 100, 100);

  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] max-w-2xl mx-auto py-12">
      <div className="text-center mb-12">
        <h1 className="text-3xl font-bold font-display text-foreground mb-4">Pipeline Execution in Progress</h1>
        <p className="text-muted-foreground max-w-md mx-auto">
          The hybrid XAI vulnerability detection engine is currently analyzing your codebase. Please do not close this window.
        </p>
      </div>

      <Card className="w-full p-8 relative overflow-hidden bg-card/50">
        
        {/* Progress bar background */}
        <div className="absolute top-0 left-0 h-1 bg-muted w-full">
           <motion.div 
             className="h-full bg-primary"
             initial={{ width: 0 }}
             animate={{ width: `${progressPercentage}%` }}
             transition={{ duration: 0.5, ease: "easeInOut" }}
           />
        </div>

        <div className="space-y-6 mt-4">
          {SCAN_STEPS.map((step, index) => {
            const isCompleted = index < currentStepIndex;
            const isCurrent = index === currentStepIndex;
            const isPending = index > currentStepIndex;

            return (
              <div 
                key={step.id} 
                className={`flex items-center gap-4 transition-all duration-500 ${isPending ? 'opacity-40' : 'opacity-100'} ${isCurrent ? 'scale-105' : 'scale-100'}`}
              >
                <div className={`
                  w-10 h-10 rounded-full flex items-center justify-center shrink-0 transition-colors
                  ${isCompleted ? 'bg-emerald-500/20 text-emerald-500' : 
                    isCurrent ? 'bg-primary/20 text-primary ring-2 ring-primary ring-offset-2 ring-offset-background' : 
                    'bg-muted text-muted-foreground'}
                `}>
                  {isCompleted ? (
                    <Check className="w-5 h-5" />
                  ) : isCurrent ? (
                    <Loader2 className="w-5 h-5 animate-spin" />
                  ) : (
                    <step.icon className="w-5 h-5" />
                  )}
                </div>
                
                <div className="flex-1">
                  <h3 className={`font-medium ${isCurrent ? 'text-primary' : isCompleted ? 'text-foreground' : 'text-muted-foreground'}`}>
                    {step.label}
                  </h3>
                  <AnimatePresence>
                    {isCurrent && (
                      <motion.p 
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        className="text-sm text-muted-foreground mt-1"
                      >
                        {index === 0 && 'Generating Abstract Syntax Trees & Control Flow Graphs...'}
                        {index === 1 && 'Identifying sources, sinks, and vulnerable edges...'}
                        {index === 2 && 'Running node classification against trained models...'}
                        {index === 3 && 'Compiling explanations and mitigation strategies...'}
                      </motion.p>
                    )}
                  </AnimatePresence>
                </div>
              </div>
            );
          })}
        </div>
      </Card>
      
      {completed && (
        <motion.div 
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mt-8 text-emerald-500 flex items-center gap-2 font-medium"
        >
          <Check className="w-5 h-5" />
          Pipeline Complete. Redirecting to workspace...
        </motion.div>
      )}
    </div>
  );
}
