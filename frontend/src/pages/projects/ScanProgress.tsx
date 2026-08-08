import React, { useEffect, useState } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Check, Loader2, Database, Network, Zap, ShieldCheck, AlertCircle } from 'lucide-react';
import { Card } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { useScanProgress } from '../../hooks/useScanProgress';

const SCAN_STEPS = [
  { id: 'parse', label: 'Parsing Source Code', icon: Database, stages: ['queued', 'preprocessing'] },
  { id: 'taint', label: 'Extracting Data Flow & Taint Paths', icon: Network, stages: ['preprocessing'] },
  { id: 'gnn', label: 'GNN Vulnerability Classification', icon: Zap, stages: ['ai_running'] },
  { id: 'llm', label: 'Generating Results & Report', icon: ShieldCheck, stages: ['storing_results', 'completed'] },
];

function getStepIndex(status: string, progress: number): number {
  if (status === 'completed') return SCAN_STEPS.length;
  if (status === 'storing_results') return 3;
  if (status === 'ai_running') return 2;
  if (status === 'preprocessing') return progress > 15 ? 1 : 0;
  return 0;
}

export default function ScanProgress() {
  const { id } = useParams<{ id: string }>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const scanId = searchParams.get('scan_id');

  const { status, progress, currentStage, errorMessage } = useScanProgress(scanId);
  const [redirecting, setRedirecting] = useState(false);

  const currentStepIndex = getStepIndex(status, progress);
  const progressPercentage = Math.min(progress, 100);
  const isFailed = status === 'failed' || status === 'cancelled';
  const isCompleted = status === 'completed';

  useEffect(() => {
    if (isCompleted && !redirecting) {
      setRedirecting(true);
      const timeout = setTimeout(() => {
        navigate(`/projects/${id}/results?scan_id=${scanId}`);
      }, 1500);
      return () => clearTimeout(timeout);
    }
  }, [isCompleted, id, scanId, navigate, redirecting]);

  if (!scanId) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh]">
        <AlertCircle className="w-12 h-12 text-muted-foreground mb-4" />
        <p className="text-muted-foreground">No scan ID provided.</p>
        <Button className="mt-4" onClick={() => navigate(`/projects/${id}`)}>
          Back to Project
        </Button>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] max-w-2xl mx-auto py-12">
      <div className="text-center mb-12">
        <h1 className="text-3xl font-bold font-display text-foreground mb-4">Pipeline Execution in Progress</h1>
        <p className="text-muted-foreground max-w-md mx-auto">
          {currentStage || 'The hybrid XAI vulnerability detection engine is currently analyzing your codebase.'}
        </p>
      </div>

      <Card className="w-full p-8 relative overflow-hidden bg-card/50">

        {/* Progress bar */}
        <div className="absolute top-0 left-0 h-1 bg-muted w-full">
          <motion.div
            className={`h-full ${isFailed ? 'bg-destructive' : 'bg-primary'}`}
            initial={{ width: 0 }}
            animate={{ width: `${progressPercentage}%` }}
            transition={{ duration: 0.5, ease: "easeInOut" }}
          />
        </div>

        <div className="flex items-center justify-between mb-6 mt-2">
          <span className="text-sm text-muted-foreground">
            {isFailed ? 'Scan Failed' : `${Math.round(progressPercentage)}% Complete`}
          </span>
        </div>

        <div className="space-y-6">
          {SCAN_STEPS.map((step, index) => {
            const isStepCompleted = index < currentStepIndex;
            const isCurrent = index === currentStepIndex && !isFailed && !isCompleted;
            const isPending = index > currentStepIndex;

            return (
              <div
                key={step.id}
                className={`flex items-center gap-4 transition-all duration-500 ${isPending ? 'opacity-40' : 'opacity-100'} ${isCurrent ? 'scale-105' : 'scale-100'}`}
              >
                <div className={`
                  w-10 h-10 rounded-full flex items-center justify-center shrink-0 transition-colors
                  ${isStepCompleted ? 'bg-emerald-500/20 text-emerald-500' :
                    isCurrent ? 'bg-primary/20 text-primary ring-2 ring-primary ring-offset-2 ring-offset-background' :
                      'bg-muted text-muted-foreground'}
                `}>
                  {isStepCompleted ? (
                    <Check className="w-5 h-5" />
                  ) : isCurrent ? (
                    <Loader2 className="w-5 h-5 animate-spin" />
                  ) : (
                    <step.icon className="w-5 h-5" />
                  )}
                </div>

                <div className="flex-1">
                  <h3 className={`font-medium ${isCurrent ? 'text-primary' : isStepCompleted ? 'text-foreground' : 'text-muted-foreground'}`}>
                    {step.label}
                  </h3>
                  <AnimatePresence>
                    {isCurrent && currentStage && (
                      <motion.p
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        className="text-sm text-muted-foreground mt-1"
                      >
                        {currentStage}
                      </motion.p>
                    )}
                  </AnimatePresence>
                </div>
              </div>
            );
          })}
        </div>
      </Card>

      {isFailed && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mt-8 text-center"
        >
          <p className="text-destructive flex items-center justify-center gap-2 font-medium">
            <AlertCircle className="w-5 h-5" />
            {errorMessage || 'Scan failed. Please try again.'}
          </p>
          <Button className="mt-4" variant="outline" onClick={() => navigate(`/projects/${id}`)}>
            Back to Project
          </Button>
        </motion.div>
      )}

      {isCompleted && (
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
