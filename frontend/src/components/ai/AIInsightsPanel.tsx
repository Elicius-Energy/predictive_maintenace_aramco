import type { FC } from 'react';
import { 
    BrainCircuit, 
    AlertCircle, 
    ShieldCheck, 
    LineChart,
    ChevronRight,
    Zap,
    MoveRight
} from 'lucide-react';
import { useSensorData } from '../../hooks/useSensorData';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

const AIInsightsPanel: FC = () => {
  const { latestDiagnosis } = useSensorData();

  if (!latestDiagnosis) return (
     <aside className="w-80 border-l border-border bg-surface p-6 flex flex-col items-center justify-center text-center">
         <BrainCircuit size={48} className="text-border mb-4 animate-pulse" />
         <p className="text-text-muted text-sm">Waiting for AI engine to synthesize data models...</p>
     </aside>
  );

  return (
    <aside className="w-80 border-l border-border bg-surface overflow-y-auto z-40 relative">
      {/* AI Intelligence Header */}
      <div className="p-6 border-b border-border sticky top-0 bg-surface z-10">
        <div className="flex items-center gap-3">
          <div className={cn(
             "w-11 h-11 rounded-xl flex items-center justify-center",
             latestDiagnosis.severity === 'critical' ? "bg-accent-red-light text-accent-red" : "bg-primary-light text-primary"
          )}>
            <BrainCircuit size={24} />
          </div>
          <div>
            <h2 className="font-bold text-text-primary text-lg tracking-tight">AI COPILOT</h2>
            <p className="text-[11px] text-primary font-semibold tracking-[0.15em] uppercase">Claude 3.5 Sonnet</p>
          </div>
        </div>
      </div>

      <div className="p-6 space-y-6">
        {/* Latest Diagnosis */}
        <div className={cn(
            "p-5 rounded-xl border-l-4 relative overflow-hidden",
            latestDiagnosis.severity === 'critical' ? "bg-accent-red-light border-accent-red" : 
            latestDiagnosis.severity === 'warning' ? "bg-accent-amber-light border-accent-amber" : "bg-primary-light border-primary"
        )}>
           <div className="flex items-center gap-2 mb-3">
              {latestDiagnosis.severity === 'critical' ? <AlertCircle size={16} className="text-accent-red" /> : <ShieldCheck size={16} className="text-primary" />}
              <span className="text-xs uppercase font-bold tracking-wider text-text-muted">Diagnosis Overview</span>
           </div>
           
           <h3 className="text-lg font-bold text-text-primary mb-2">{latestDiagnosis.fault_type}</h3>
           <div className="flex items-center gap-2 mb-4">
              <div className="flex-1 h-2 bg-border rounded-full overflow-hidden">
                 <div 
                   className={cn("h-full rounded-full", latestDiagnosis.severity === 'critical' ? "bg-accent-red" : "bg-primary")} 
                   style={{ width: `${latestDiagnosis.confidence * 100}%` }}
                 />
              </div>
              <span className="text-xs font-bold text-text-secondary">{(latestDiagnosis.confidence * 100).toFixed(0)}%</span>
           </div>

           <p className="text-sm text-text-secondary leading-relaxed mb-4">
             "{latestDiagnosis.explanation}"
           </p>
        </div>

        {/* Physics Reasoning Section */}
        <div className="space-y-3">
           <div className="flex items-center gap-2">
              <LineChart size={16} className="text-primary" />
              <span className="text-xs uppercase font-bold tracking-wider text-text-muted">Signal Analysis</span>
           </div>
           <div className="bg-surface-muted p-4 rounded-xl border border-border text-sm text-text-secondary leading-relaxed font-mono">
              {latestDiagnosis.physics_reasoning}
           </div>
        </div>

        {/* Recommended Action */}
        <div className="space-y-3">
           <div className="flex items-center gap-2">
              <MoveRight size={16} className="text-accent-green" />
              <span className="text-xs uppercase font-bold tracking-wider text-text-muted">Prescribed Measures</span>
           </div>
           <div className="p-4 rounded-xl bg-accent-green-light border border-emerald-200 group cursor-pointer hover:shadow-md transition-all">
              <div className="flex gap-3">
                 <Zap size={18} className="text-accent-green flex-shrink-0 mt-0.5" />
                 <p className="text-sm font-bold text-accent-green leading-snug">
                    {latestDiagnosis.recommended_action}
                 </p>
              </div>
           </div>
        </div>

        {/* Knowledge Base Citation */}
        <div className="pt-4 border-t border-border">
           <span className="text-[10px] text-text-muted uppercase font-bold flex items-center gap-1">
              <ChevronRight size={12} /> Context Retrieval Sources
           </span>
           <p className="text-xs text-text-muted mt-2 line-clamp-2">
              {latestDiagnosis.retrieved_context_summary}
           </p>
        </div>
      </div>
    </aside>
  );
};

export default AIInsightsPanel;
