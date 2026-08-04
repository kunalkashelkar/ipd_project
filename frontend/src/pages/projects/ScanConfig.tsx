import React, { useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { useNavigate, useParams } from 'react-router-dom';
import { Play, Settings2, Shield, X, ScanEye, Zap, FileText } from 'lucide-react';
import { motion } from 'framer-motion';

export default function ScanConfig() {
  const navigate = useNavigate();
  const { id } = useParams();
  const [isStarting, setIsStarting] = useState(false);

  const [options, setOptions] = useState({
    static: true,
    ai: true,
    explain: true,
    fix: true,
    report: true
  });

  const handleStartScan = () => {
    setIsStarting(true);
    setTimeout(() => {
      navigate(`/projects/${id}/scan-progress`);
    }, 800);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm p-4">
      <motion.div 
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="w-full max-w-lg"
      >
        <Card className="border-border shadow-2xl relative overflow-hidden">
          <div className="absolute top-0 left-0 w-full h-1 bg-primary" />
          <Button 
            variant="ghost" 
            size="sm" 
            className="absolute top-4 right-4 w-8 h-8 p-0"
            onClick={() => navigate(-1)}
          >
            <X className="w-4 h-4" />
          </Button>

          <CardHeader className="pb-4">
            <CardTitle className="text-2xl flex items-center gap-2">
              <Settings2 className="w-6 h-6 text-primary" /> Choose Analysis
            </CardTitle>
            <p className="text-sm text-muted-foreground mt-1">Configure vulnerability detection parameters for Payment API.</p>
          </CardHeader>
          
          <CardContent className="space-y-4">
            <div className="space-y-3">
              {[
                { id: 'static', label: 'Static Analysis', desc: 'Basic AST pattern matching and linting.', icon: Shield },
                { id: 'ai', label: 'AI Detection', desc: 'Deep Graph Neural Network vulnerability inference.', icon: ScanEye },
                { id: 'explain', label: 'Explainability', desc: 'Generate SHAP heatmaps for vulnerable nodes.', icon: Zap },
                { id: 'fix', label: 'AI Fix', desc: 'Pre-compute automated LLM remediation steps.', icon: Zap },
                { id: 'report', label: 'Generate Report', desc: 'Compile findings into a downloadable format.', icon: FileText },
              ].map(opt => (
                <label 
                  key={opt.id} 
                  className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                    options[opt.id as keyof typeof options] 
                      ? 'border-primary/50 bg-primary/5' 
                      : 'border-border bg-card hover:bg-muted/50'
                  }`}
                >
                  <div className="pt-0.5">
                    <input 
                      type="checkbox" 
                      className="w-4 h-4 accent-primary rounded text-primary focus:ring-primary focus:ring-offset-background" 
                      checked={options[opt.id as keyof typeof options]}
                      onChange={(e) => setOptions({...options, [opt.id]: e.target.checked})}
                    />
                  </div>
                  <div>
                    <div className="font-medium text-sm text-foreground flex items-center gap-2">
                      {<opt.icon className="w-3.5 h-3.5 text-muted-foreground" />} {opt.label}
                    </div>
                    <div className="text-xs text-muted-foreground mt-0.5">{opt.desc}</div>
                  </div>
                </label>
              ))}
            </div>
          </CardContent>
          
          <CardFooter className="bg-muted/20 border-t border-border p-6 flex justify-between mt-2">
            <Button variant="ghost" onClick={() => navigate(-1)}>Cancel</Button>
            <Button onClick={handleStartScan} disabled={isStarting} className="min-w-[140px]">
              {isStarting ? (
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Starting...
                </div>
              ) : (
                <><Play className="w-4 h-4 mr-2" /> Start Scan</>
              )}
            </Button>
          </CardFooter>
        </Card>
      </motion.div>
    </div>
  );
}
