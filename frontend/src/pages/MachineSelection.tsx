import type { FC } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMachine } from '../contexts/MachineContext';
import { Factory, Cog, CheckCircle2, AlertTriangle, ShieldX, ChevronRight, MapPin } from 'lucide-react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

const MachineSelection: FC = () => {
  const { machines, activeMachine, setActiveMachine } = useMachine();
  const navigate = useNavigate();

  const handleSelectMachine = (machine: any) => {
    setActiveMachine(machine);
    navigate('/dashboard/mechanical');
  };

  return (
    <div className="min-h-screen bg-surface-muted p-8 md:p-12 font-sans overflow-y-auto w-full">
      <div className="max-w-[1600px] mx-auto space-y-10">
        <div className="flex flex-col gap-3">
        <div className="flex items-center gap-3">
          <Factory size={28} className="text-primary" />
          <h2 className="text-3xl font-extrabold tracking-tight text-text-primary">Asset Fleet Manager</h2>
        </div>
        <div className="flex items-center gap-3">
          <p className="text-text-secondary text-base max-w-2xl">
            Industrial assets across LEDL facilities. Select a machine to view real-time diagnostics.
          </p>
         </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {machines.map((machine) => (
          <div 
            key={machine.machine_id}
            onClick={() => handleSelectMachine(machine)}
            className={cn(
              "industrial-card p-6 flex flex-col gap-4 cursor-pointer transition-all duration-300 relative overflow-hidden group",
              activeMachine?.machine_id === machine.machine_id 
                ? "border-primary ring-2 ring-primary/20 shadow-md" 
                : "hover:border-primary/40 hover:shadow-md"
            )}
          >

            {/* Background Icon Watermark */}
            <Cog size={120} className="absolute -right-8 -bottom-8 text-gray-100 -rotate-12 group-hover:rotate-0 transition-transform duration-700" />

            <div className="flex justify-between items-start relative z-10">
              <div className="w-14 h-14 rounded-xl bg-surface-muted border border-border flex items-center justify-center">
                 <Cog size={28} className={cn(
                     "transition-colors",
                     machine.status === 'healthy' ? "text-accent-green" : 
                     machine.status === 'warning' ? "text-accent-amber" : "text-accent-red"
                 )} />
              </div>
              <div className={cn(
                "px-2.5 py-1 rounded-full text-xs font-bold uppercase tracking-wider flex items-center gap-1.5",
                machine.status === 'healthy' ? "bg-accent-green-light text-accent-green border border-emerald-200" : 
                machine.status === 'warning' ? "bg-accent-amber-light text-accent-amber border border-amber-200" : "bg-accent-red-light text-accent-red border border-red-200"
              )}>
                {machine.status === 'healthy' ? <CheckCircle2 size={12} /> : machine.status === 'warning' ? <AlertTriangle size={12} /> : <ShieldX size={12} />}
                {machine.status}
              </div>
            </div>

            <div className="relative z-10">
              <h3 className="text-xl font-bold text-text-primary group-hover:text-primary transition-colors">{machine.name}</h3>
              <div className="flex items-center gap-1.5 text-text-muted text-sm mt-1">
                <MapPin size={14} />
                {machine.location} • {machine.unit}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4 mt-2 relative z-10">
              <div className="bg-surface-muted p-4 rounded-xl border border-border">
                 <p className="text-xs text-text-muted uppercase tracking-tight font-semibold">Health Score</p>
                 <div className={cn(
                    "text-2xl font-extrabold scada-number mt-1",
                    machine.health_score > 90 ? "text-accent-green" : 
                    machine.health_score > 60 ? "text-accent-amber" : "text-accent-red"
                 )}>
                    {machine.health_score}%
                 </div>
              </div>
              <div className="bg-surface-muted p-4 rounded-xl border border-border">
                 <p className="text-xs text-text-muted uppercase tracking-tight font-semibold">Runtime</p>
                 <div className="text-2xl font-extrabold scada-number text-text-primary mt-1">
                    {Math.floor(machine.uptime_hours)}<span className="text-sm text-text-muted ml-1">HRS</span>
                 </div>
              </div>
            </div>

            <button className={cn(
                "w-full py-3 flex items-center justify-center gap-2 text-sm font-bold uppercase tracking-wide rounded-xl transition-all mt-2 relative z-10",
                activeMachine?.machine_id === machine.machine_id 
                    ? "bg-primary text-white shadow-md" 
                    : "bg-surface-muted text-text-secondary group-hover:bg-primary/10 group-hover:text-primary border border-border"
            )}>
                {activeMachine?.machine_id === machine.machine_id ? 'Selected Active' : 'Monitor Asset'}
                <ChevronRight size={16} />
            </button>
          </div>
        ))}
      </div>
    </div>
  </div>
  );
};

export default MachineSelection;
