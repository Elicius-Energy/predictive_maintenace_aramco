import type { FC } from 'react';
import { useSensorData } from '../hooks/useSensorData';
import { useHistory } from '../contexts/HistoryContext';
import TimeSeriesChart from '../components/charts/TimeSeriesChart';
import FFTChart from '../components/charts/FFTChart';
import GaugeChart from '../components/charts/GaugeChart';
import FormulaPanel from '../components/common/FormulaPanel';
import { FORMULAS } from '../data/formulas';
import { Activity, ShieldAlert, Cpu, Layers } from 'lucide-react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

const MechanicalParams: FC = () => {
  const { latestFeatures, latestHealth } = useSensorData();
  const { mechanicalHistory, latestHistoricalFeatures } = useHistory();

  const vibe = latestFeatures?.vibration || latestHistoricalFeatures?.vibration;
  const isoZone = latestFeatures?.iso_zone || latestHistoricalFeatures?.iso_zone;

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-end">
         <div className="flex items-center gap-3">
           <Activity className="text-primary" size={28} />
           <h2 className="text-3xl font-extrabold text-text-primary tracking-tight">Mechanical Diagnostics</h2>
         </div>
         <div className="flex gap-2">
            <span className="px-3 py-1.5 bg-surface-muted rounded-lg text-xs font-semibold text-text-secondary border border-border">SAMPLE RATE: 100Hz</span>
            <span className="px-3 py-1.5 bg-primary-light rounded-lg text-xs font-semibold text-primary border border-cyan-200">ISO 10816: CLASS II</span>
         </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Core Gauges */}
        <div className="lg:col-span-1 industrial-card p-5 space-y-4 flex flex-col items-center justify-center">
           <GaugeChart 
             value={vibe?.rms_overall || 0} 
             min={0} max={15} 
             unit="mm/s" 
             label="Overall Velocity" 
             thresholds={{ warning: 2.8, critical: 7.1 }}
           />
           <div className="grid grid-cols-2 gap-4 w-full">
              <div className="bg-surface-muted p-3 rounded-xl border border-border text-center">
                 <p className="text-[10px] text-text-muted uppercase font-semibold">Kurtosis</p>
                 <p className={cn("text-lg font-bold scada-number", (vibe?.kurtosis_x || 0) > 4 ? "text-accent-amber" : "text-text-primary")}>
                    {vibe?.kurtosis_x?.toFixed(2) || '0.00'}
                 </p>
              </div>
              <div className="bg-surface-muted p-3 rounded-xl border border-border text-center">
                 <p className="text-[10px] text-text-muted uppercase font-semibold">Crest Factor</p>
                 <p className="text-lg font-bold scada-number text-text-primary">
                    {vibe?.crest_factor?.toFixed(2) || '0.00'}
                 </p>
              </div>
           </div>
           <FormulaPanel items={[...FORMULAS.vibrationVelocity, ...FORMULAS.vibrationShape]} className="w-full" />
        </div>

        {/* Real-time Acceleration Trace */}
        <div className="lg:col-span-3 industrial-card p-6">
           <div className="h-[300px]">
             <TimeSeriesChart 
               data={mechanicalHistory} 
               title="Acceleration Waveform (g)"
               lines={[
                 { key: 'ax', color: '#0891b2', name: 'X-Axis' },
                 { key: 'ay', color: '#059669', name: 'Y-Axis' },
                 { key: 'az', color: '#7c3aed', name: 'Z-Axis' }
               ]}
               yDomain={[-5, 5]}
             />
           </div>
           <FormulaPanel items={FORMULAS.vibrationVelocity} />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* FFT Spectrum */}
        <div className="industrial-card p-6">
           <div className="h-[350px]">
             <FFTChart 
               magnitudes={vibe?.fft_magnitudes || []} 
               frequencies={vibe?.fft_frequencies || []} 
             />
           </div>
           <FormulaPanel items={FORMULAS.fft} />
        </div>

        {/* Health Indicators */}
        <div className="industrial-card p-6 flex flex-col">
           <h3 className="text-xs uppercase font-bold tracking-wider text-text-muted mb-6">Failure Probabilities</h3>
           <div className="space-y-6 flex-1">
              {latestHealth?.indicators.map((ind, i) => (
                <div key={i} className="space-y-2">
                   <div className="flex justify-between items-center text-sm">
                      <span className="text-text-primary font-semibold flex items-center gap-2">
                         {ind.name === 'Bearing Health' ? <ShieldAlert size={16} className="text-accent-amber" /> : <Layers size={16} className="text-primary" />}
                         {ind.name}
                      </span>
                      <span className={cn("font-bold scada-number text-base", ind.status === 'healthy' ? "text-accent-green" : "text-accent-amber")}>
                         {(ind.probability * 100).toFixed(1)}%
                      </span>
                   </div>
                   <div className="h-2.5 bg-surface-muted rounded-full overflow-hidden border border-border">
                      <div 
                        className={cn("h-full transition-all duration-1000 rounded-full", ind.status === 'healthy' ? "bg-accent-green" : "bg-accent-amber")}
                        style={{ width: `${ind.probability * 100}%` }}
                      />
                   </div>
                </div>
              )) || (
                 <div className="flex flex-col items-center justify-center h-full text-text-muted text-base italic">
                    <Cpu size={40} className="opacity-20 mb-3" />
                    Calculating diagnostic signatures...
                 </div>
              )}
           </div>
           
           <div className="mt-8 p-5 bg-surface-muted rounded-xl border border-border">
              <div className="flex items-center justify-between">
                 <span className="text-xs text-text-muted uppercase font-bold">ISO 10816 Zone</span>
                 <div className="flex gap-1.5">
                    {['A', 'B', 'C', 'D'].map(z => (
                       <div 
                         key={z} 
                         className={cn(
                           "w-9 h-9 flex items-center justify-center rounded-lg font-bold text-sm",
                           isoZone === z 
                            ? (z === 'A' ? "bg-accent-green text-white" : z === 'B' ? "bg-accent-green/60 text-white" : z === 'C' ? "bg-accent-amber text-white" : "bg-accent-red text-white")
                            : "bg-surface text-text-muted border border-border"
                         )}
                       >
                         {z}
                       </div>
                    ))}
                 </div>
              </div>
           </div>
           <FormulaPanel items={[...FORMULAS.bearingHealth, ...FORMULAS.imbalance, ...FORMULAS.isoZone]} />
        </div>
      </div>
    </div>
  );
};

export default MechanicalParams;
