import { forwardRef } from 'react';
import { AreaChart, Area, BarChart, Bar, CartesianGrid, XAxis, YAxis, ResponsiveContainer } from 'recharts';
import TimeSeriesChart from '../charts/TimeSeriesChart';
import FFTChart from '../charts/FFTChart';

export interface PdfReportProps {
  machineId: string;
  machineName: string;
  summary: string;
  healthScore: number;
  energyWaste: string;
  downtimeDays: string;
  roiData: any[];
  riskData: any[];
  mechanicalHistory: any[];
  electricalHistory: any[];
  fftFrequencies: number[];
  fftMagnitudes: number[];
}

export const PdfReportTemplate = forwardRef<HTMLDivElement, PdfReportProps>(({
  machineId,
  machineName,
  summary,
  healthScore,
  energyWaste,
  downtimeDays,
  roiData,
  riskData,
  mechanicalHistory,
  electricalHistory,
  fftFrequencies,
  fftMagnitudes
}, ref) => {
  return (
    <div 
      ref={ref} 
      className="bg-surface text-text-primary p-8 w-[800px] flex flex-col gap-6"
      style={{ fontFamily: 'Inter, sans-serif' }}
    >
      {/* Header */}
      <div className="border-b border-border pb-4 mb-4">
        <h1 className="text-3xl font-extrabold text-primary mb-1">AI Predictive Maintenance Report</h1>
        <h2 className="text-lg text-text-secondary">{machineName} ({machineId})</h2>
        <p className="text-sm text-text-muted mt-2">Generated on {new Date().toLocaleString()}</p>
      </div>

      {/* AI Summary Section */}
      <div className="bg-surface-muted border border-border p-5 rounded-xl">
        <h3 className="text-xl font-bold text-text-primary mb-3 uppercase tracking-wider border-b border-border pb-2">AI Summary & Diagnostics</h3>
        <p className="text-sm text-text-secondary leading-relaxed mb-4">{summary}</p>
        
        <div className="flex gap-4">
          <div className="bg-surface border border-border p-4 rounded-lg flex-1">
            <p className="text-xs text-text-muted font-bold uppercase">Health Score</p>
            <p className={`text-2xl font-bold ${healthScore > 80 ? 'text-accent-green' : 'text-accent-amber'}`}>{healthScore.toFixed(1)}%</p>
          </div>
          <div className="bg-surface border border-border p-4 rounded-lg flex-1">
            <p className="text-xs text-text-muted font-bold uppercase">Est. Energy Waste</p>
            <p className="text-2xl font-bold text-accent-red">{energyWaste} kWh/day</p>
          </div>
          <div className="bg-surface border border-border p-4 rounded-lg flex-1">
            <p className="text-xs text-text-muted font-bold uppercase">Predicted Downtime</p>
            <p className="text-2xl font-bold text-accent-amber">{downtimeDays} Days</p>
          </div>
        </div>
      </div>

      {/* Vibration & Mechanical */}
      <div className="page-break-inside-avoid">
        <h3 className="text-xl font-bold text-text-primary mb-3 mt-6 uppercase tracking-wider border-b border-border pb-2">Mechanical & Vibration Profile</h3>
        <div className="grid grid-cols-2 gap-4">
          <div className="h-[250px] bg-surface-muted border border-border p-3 rounded-xl">
            <p className="text-xs font-bold text-text-muted mb-2 uppercase">Acceleration Waveform (g)</p>
            <TimeSeriesChart 
              data={mechanicalHistory} 
              title="" 
              lines={[{ key: 'ax', color: '#0891b2', name: 'X-Axis' }, { key: 'ay', color: '#059669', name: 'Y-Axis' }, { key: 'az', color: '#7c3aed', name: 'Z-Axis' }]}
              yDomain={[-5, 5]}
            />
          </div>
          <div className="h-[250px] bg-surface-muted border border-border p-3 rounded-xl">
            <p className="text-xs font-bold text-text-muted mb-2 uppercase">Vibration Spectrum (FFT)</p>
            <FFTChart frequencies={fftFrequencies} magnitudes={fftMagnitudes} />
          </div>
        </div>
        <p className="text-xs text-text-secondary mt-2 bg-surface-muted p-2 rounded border border-border">
          <strong>Analysis:</strong> Continuous monitoring of triaxial vibration and its frequency spectrum. Spikes in specific frequency bands indicate potential bearing or alignment issues.
        </p>
      </div>

      {/* Electrical Quality */}
      <div className="page-break-inside-avoid">
        <h3 className="text-xl font-bold text-text-primary mb-3 mt-6 uppercase tracking-wider border-b border-border pb-2">Electrical Quality</h3>
        <div className="grid grid-cols-2 gap-4">
          <div className="h-[250px] bg-surface-muted border border-border p-3 rounded-xl">
            <p className="text-xs font-bold text-text-muted mb-2 uppercase">Power Consumption (kW/kVA)</p>
            <TimeSeriesChart 
              data={electricalHistory} 
              title="" 
              lines={[{ key: 'p', color: '#0891b2', name: 'Active Power (kW)' }, { key: 'kva', color: '#7c3aed', name: 'Apparent Power (kVA)' }]}
            />
          </div>
          <div className="h-[250px] bg-surface-muted border border-border p-3 rounded-xl">
            <p className="text-xs font-bold text-text-muted mb-2 uppercase">Current Draw Pattern (A)</p>
            <TimeSeriesChart 
              data={electricalHistory} 
              title="" 
              lines={[{ key: 'i', color: '#f59e0b', name: 'Line Current (A)' }]}
            />
          </div>
        </div>
        <p className="text-xs text-text-secondary mt-2 bg-surface-muted p-2 rounded border border-border">
          <strong>Analysis:</strong> Electrical signatures reveal motor efficiency and load anomalies. Consistent deviation between active and apparent power suggests power factor degradation.
        </p>
      </div>

      {/* Risk and ROI */}
      <div className="page-break-inside-avoid">
        <h3 className="text-xl font-bold text-text-primary mb-3 mt-6 uppercase tracking-wider border-b border-border pb-2">Investment & Risk Projection</h3>
        <div className="grid grid-cols-2 gap-4">
          <div className="h-[250px] bg-surface-muted border border-border p-3 rounded-xl">
            <p className="text-xs font-bold text-text-muted mb-2 uppercase">Component Vulnerability Matrix</p>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={riskData} layout="vertical" margin={{ top: 0, right: 10, left: 10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal={true} vertical={true} stroke="#374151" opacity={0.3} />
                <XAxis type="number" hide domain={[0, 100]} />
                <YAxis type="category" dataKey="component" axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: '#9ca3af' }} width={60} />
                <Bar dataKey="risk" fill="#f59e0b" radius={[0, 4, 4, 0]} isAnimationActive={false} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="h-[250px] bg-surface-muted border border-border p-3 rounded-xl">
            <p className="text-xs font-bold text-text-muted mb-2 uppercase">ROI Projection</p>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={roiData} margin={{ top: 0, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#374151" opacity={0.5} />
                <XAxis dataKey="month" axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: '#9ca3af' }} />
                <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: '#9ca3af' }} />
                <Area type="monotone" dataKey="efficiencyGain" stroke="#10b981" fill="#10b981" fillOpacity={0.3} isAnimationActive={false} />
                <Area type="monotone" dataKey="riskReduction" stroke="#8b5cf6" fill="#8b5cf6" fillOpacity={0.3} isAnimationActive={false} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
        <p className="text-xs text-text-secondary mt-2 bg-surface-muted p-2 rounded border border-border">
          <strong>Analysis:</strong> Proactive maintenance based on the vulnerability matrix directly translates to the projected efficiency gains and risk reduction over the next 12 months.
        </p>
      </div>
    </div>
  );
});

PdfReportTemplate.displayName = 'PdfReportTemplate';
