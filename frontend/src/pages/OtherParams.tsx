import type { FC } from 'react';
import { useSensorData } from '../hooks/useSensorData';
import { useHistory } from '../contexts/HistoryContext';
import TimeSeriesChart from '../components/charts/TimeSeriesChart';
import GaugeChart from '../components/charts/GaugeChart';
import { Thermometer, Gauge, Radio, ShieldCheck, AlertTriangle, Activity, Waves } from 'lucide-react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer } from 'recharts';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

const OtherParams: FC = () => {
  const { latestFeatures, latestHealth } = useSensorData();
  const { tempHistory, anomalyHistory } = useHistory();

  const healthScore = latestFeatures?.health_score || 0;
  const anomalyScore = latestFeatures?.anomaly_score || 0;
  const temperature = latestFeatures?.temperature || 0;

  // Process FFT data if available (Limit to 0-100Hz for readability)
  const fftData = [];
  if (latestFeatures?.vibration?.fft_frequencies && latestFeatures?.vibration?.fft_magnitudes) {
    const freqs = latestFeatures.vibration.fft_frequencies;
    const mags = latestFeatures.vibration.fft_magnitudes;
    for (let i = 0; i < Math.min(freqs.length, mags.length); i++) {
      if (freqs[i] >= 0 && freqs[i] <= 100) {
        fftData.push({ frequency: parseFloat(freqs[i].toFixed(1)), magnitude: mags[i] });
      }
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-end">
         <div className="flex items-center gap-3">
           <Gauge className="text-primary" size={28} />
           <h2 className="text-3xl font-extrabold text-text-primary tracking-tight">Auxiliary Metrics</h2>
         </div>
         <div className="flex gap-2">
            <span className="px-3 py-1.5 bg-surface-muted rounded-lg text-xs font-semibold text-text-secondary border border-border">AI ENGINE: ACTIVE</span>
            <span className={cn(
              "px-3 py-1.5 rounded-lg text-xs font-semibold border",
              anomalyScore > 0.5 ? "bg-accent-red-light text-accent-red border-red-200" : "bg-accent-green-light text-accent-green border-emerald-200"
            )}>
              {anomalyScore > 0.5 ? 'ANOMALY DETECTED' : 'NOMINAL'}
            </span>
         </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
        <div className="industrial-card p-5 flex flex-col items-center">
           <GaugeChart value={temperature} min={0} max={120} unit="°C" label="Temperature" thresholds={{ warning: 75, critical: 95 }} />
        </div>
        <div className="industrial-card p-5 flex flex-col items-center">
           <GaugeChart value={healthScore} min={0} max={100} unit="%" label="Health Score" thresholds={{ warning: 70, critical: 50 }} />
        </div>
        <div className="industrial-card p-5 flex flex-col items-center">
           <GaugeChart value={anomalyScore * 100} min={0} max={100} unit="%" label="Anomaly Score" thresholds={{ warning: 40, critical: 60 }} />
        </div>
        <div className="industrial-card p-5 flex flex-col items-center">
           <GaugeChart value={latestFeatures?.electrical?.frequency || 0} min={49} max={51} unit="Hz" label="Grid Frequency" thresholds={{ warning: 50.5, critical: 50.8 }} />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="industrial-card p-6 h-[350px]">
           <TimeSeriesChart 
             data={tempHistory} 
             title="Temperature Trend (°C)"
             lines={[
               { key: 'temperature', color: '#dc2626', name: 'Temperature' },
             ]}
             yDomain={[0, 120]}
           />
        </div>
        <div className="industrial-card p-6 h-[350px]">
           <TimeSeriesChart 
             data={anomalyHistory} 
             title="AI Health & Anomaly Scores"
             lines={[
               { key: 'health', color: '#059669', name: 'Health Score' },
               { key: 'anomaly', color: '#d97706', name: 'Anomaly Score' },
             ]}
             yDomain={[0, 100]}
           />
        </div>
      </div>

      {/* Real-time Frequency Spectrum */}
      <div className="industrial-card p-6">
        <h3 className="text-xs uppercase font-bold tracking-wider text-text-muted mb-4 flex items-center gap-2">
          <Waves size={16} className="text-primary" />
          Real-Time Frequency Spectrum (FFT)
        </h3>
        <div className="h-[250px] w-full">
          {fftData.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={fftData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorMagnitude" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.5} />
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--color-border)" opacity={0.5} />
                <XAxis 
                  dataKey="frequency" 
                  type="number"
                  domain={[0, 100]}
                  axisLine={false} 
                  tickLine={false} 
                  tick={{ fontSize: 12, fill: 'var(--color-text-muted)' }} 
                  tickFormatter={(val) => `${val}Hz`}
                />
                <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: 'var(--color-text-muted)' }} />
                <RechartsTooltip
                  contentStyle={{ backgroundColor: 'var(--color-surface)', borderColor: 'var(--color-border)', borderRadius: '8px' }}
                  itemStyle={{ color: 'var(--color-text-primary)' }}
                  formatter={(value: any) => [Number(value).toFixed(3), 'Magnitude']}
                  labelFormatter={(label) => `${label} Hz`}
                />
                <Area 
                  type="monotone" 
                  dataKey="magnitude" 
                  stroke="#3b82f6" 
                  strokeWidth={2} 
                  fillOpacity={1} 
                  fill="url(#colorMagnitude)" 
                  isAnimationActive={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-text-muted text-base italic">
              <Radio size={36} className="opacity-20 mb-3 animate-pulse" />
              Awaiting vibration FFT telemetry...
            </div>
          )}
        </div>
      </div>

      {/* System Status */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="industrial-card p-6">
          <h3 className="text-xs uppercase font-bold tracking-wider text-text-muted mb-5">System Status Summary</h3>
          <div className="space-y-4">
            <div className="flex items-center gap-3 p-4 bg-surface-muted rounded-xl border border-border">
              <ShieldCheck size={22} className={cn(healthScore > 80 ? "text-accent-green" : healthScore > 50 ? "text-accent-amber" : "text-accent-red")} />
              <div className="flex-1">
                <p className="text-sm font-bold text-text-primary">Overall Health</p>
                <p className="text-xs text-text-muted">Machine operational assessment</p>
              </div>
              <span className={cn("text-xl font-extrabold scada-number", healthScore > 80 ? "text-accent-green" : healthScore > 50 ? "text-accent-amber" : "text-accent-red")}>
                {healthScore.toFixed(1)}%
              </span>
            </div>
            <div className="flex items-center gap-3 p-4 bg-surface-muted rounded-xl border border-border">
              <AlertTriangle size={22} className={cn(anomalyScore < 0.3 ? "text-accent-green" : anomalyScore < 0.6 ? "text-accent-amber" : "text-accent-red")} />
              <div className="flex-1">
                <p className="text-sm font-bold text-text-primary">Anomaly Detection</p>
                <p className="text-xs text-text-muted">ML-based pattern deviation</p>
              </div>
              <span className={cn("text-xl font-extrabold scada-number", anomalyScore < 0.3 ? "text-accent-green" : anomalyScore < 0.6 ? "text-accent-amber" : "text-accent-red")}>
                {(anomalyScore * 100).toFixed(1)}%
              </span>
            </div>
            <div className="flex items-center gap-3 p-4 bg-surface-muted rounded-xl border border-border">
              <Thermometer size={22} className={cn(temperature < 75 ? "text-accent-green" : temperature < 95 ? "text-accent-amber" : "text-accent-red")} />
              <div className="flex-1">
                <p className="text-sm font-bold text-text-primary">Thermal Status</p>
                <p className="text-xs text-text-muted">Operating temperature</p>
              </div>
              <span className={cn("text-xl font-extrabold scada-number", temperature < 75 ? "text-accent-green" : temperature < 95 ? "text-accent-amber" : "text-accent-red")}>
                {temperature.toFixed(1)}°C
              </span>
            </div>
          </div>
        </div>

        <div className="lg:col-span-2 industrial-card p-6">
          <h3 className="text-xs uppercase font-bold tracking-wider text-text-muted mb-5">Diagnostic Indicators</h3>
          <div className="space-y-5">
            {latestHealth?.indicators.map((ind, i) => (
              <div key={i} className="space-y-2">
                <div className="flex justify-between items-center text-sm">
                  <span className="text-text-primary font-semibold flex items-center gap-2">
                    <Activity size={16} className={cn(ind.status === 'healthy' ? "text-accent-green" : "text-accent-amber")} />
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
                {ind.description && (
                  <p className="text-xs text-text-muted">{ind.description}</p>
                )}
              </div>
            )) || (
              <div className="flex flex-col items-center justify-center h-40 text-text-muted text-base italic">
                <Radio size={36} className="opacity-20 mb-3 animate-pulse" />
                Awaiting diagnostic telemetry...
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default OtherParams;
