import type { FC } from 'react';
import { useSensorData } from '../hooks/useSensorData';
import { useHistory } from '../contexts/HistoryContext';
import TimeSeriesChart from '../components/charts/TimeSeriesChart';
import GaugeChart from '../components/charts/GaugeChart';
import { Zap, TrendingUp, BarChart3, Info } from 'lucide-react';

const ElectricalParams: FC = () => {
  const { latestFeatures } = useSensorData();
  const { electricalHistory } = useHistory();

  const electrical = latestFeatures?.electrical;

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-end">
         <div className="flex items-center gap-3">
           <Zap className="text-primary" size={28} />
           <h2 className="text-3xl font-extrabold text-text-primary tracking-tight">Electrical Quality Feed</h2>
         </div>
         <div className="flex gap-2">
            <span className="px-3 py-1.5 bg-surface-muted rounded-lg text-xs font-semibold text-text-secondary border border-border">VOLTAGE: 3-PHASE 415V</span>
            <span className="px-3 py-1.5 bg-primary-light rounded-lg text-xs font-semibold text-primary border border-cyan-200">IE3 MOTOR STD</span>
         </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
        <div className="industrial-card p-5 flex flex-col items-center">
           <GaugeChart value={electrical?.voltage || 0} min={350} max={450} unit="V" label="Voltage" thresholds={{ warning: 440, critical: 460 }} />
        </div>
        <div className="industrial-card p-5 flex flex-col items-center">
           <GaugeChart value={electrical?.current || 0} min={0} max={20} unit="A" label="Current" thresholds={{ warning: 15, critical: 18 }} />
        </div>
        <div className="industrial-card p-5 flex flex-col items-center">
           <GaugeChart value={electrical?.power_factor || 0} min={0.5} max={1.0} unit="cos φ" label="Power Factor" thresholds={{ warning: 0.8, critical: 0.7 }} />
        </div>
        <div className="industrial-card p-5 flex flex-col items-center">
           <GaugeChart value={electrical?.efficiency || 0} min={0} max={100} unit="%" label="Efficiency" />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Power Trends */}
        <div className="lg:col-span-2 industrial-card p-6 h-[350px]">
           <TimeSeriesChart 
             data={electricalHistory} 
             title="Power Consumption Profile (kW / kVA)"
             lines={[
               { key: 'p', color: '#0891b2', name: 'Active Power (kW)' },
               { key: 'kva', color: '#7c3aed', name: 'Apparent Power (kVA)' }
             ]}
           />
        </div>

        {/* Load Analysis */}
        <div className="industrial-card p-6">
           <h3 className="text-xs uppercase font-bold tracking-wider text-text-muted mb-6">Load Analysis</h3>
           <div className="space-y-6">
              <div className="bg-surface-muted p-6 rounded-xl border border-border flex flex-col items-center justify-center gap-2 relative overflow-hidden">
                 <p className="text-xs text-text-muted uppercase tracking-widest font-bold">Current Operational Load</p>
                 <div className="text-5xl font-extrabold scada-number text-primary">
                    {electrical?.load_percentage?.toFixed(1) || '0.0'}%
                 </div>
                 <div className="w-full h-2 bg-border rounded-full mt-3 overflow-hidden">
                    <div className="h-full bg-primary rounded-full shadow-[0_0_8px_#0891b2]" style={{ width: `${electrical?.load_percentage || 0}%` }} />
                 </div>
                 <TrendingUp size={64} className="absolute -right-4 -bottom-4 text-gray-100" />
              </div>

              <div className="space-y-4">
                 <div className="flex justify-between items-center text-sm">
                    <span className="text-text-secondary flex items-center gap-2 font-semibold"><BarChart3 size={16} /> Energy (kWh)</span>
                    <span className="text-text-primary font-mono font-bold text-base">{electrical?.energy_cumulative?.toFixed(2) || '0.00'}</span>
                 </div>
                 <div className="flex justify-between items-center text-sm">
                    <span className="text-text-secondary flex items-center gap-2 font-semibold"><Zap size={16} /> Frequency (Hz)</span>
                    <span className="text-text-primary font-mono font-bold text-base">{electrical?.frequency?.toFixed(1) || '0.0'}</span>
                 </div>
              </div>

              <div className="p-4 bg-primary-light rounded-xl border border-cyan-100 flex gap-3">
                 <Info size={18} className="text-primary flex-shrink-0 mt-0.5" />
                 <p className="text-xs text-text-secondary leading-relaxed">
                    Motor operating at optimal load factor for IE3 standard compliance. Power factor correction not currently required.
                 </p>
              </div>
           </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="industrial-card p-6 h-[300px]">
           <TimeSeriesChart 
             data={electricalHistory} 
             title="Current Draw Pattern (Amperes)"
             lines={[
               { key: 'i', color: '#f59e0b', name: 'Line Current (A)' }
             ]}
           />
        </div>
        <div className="industrial-card p-6 h-[300px]">
           <TimeSeriesChart 
             data={electricalHistory} 
             title="Power Factor Variation (cos φ)"
             lines={[
               { key: 'pf', color: '#10b981', name: 'Power Factor' }
             ]}
           />
        </div>
      </div>
    </div>
  );
};

export default ElectricalParams;
