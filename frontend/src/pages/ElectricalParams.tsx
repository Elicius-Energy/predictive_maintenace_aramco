import type { FC } from 'react';
import { useSensorData } from '../hooks/useSensorData';
import { useHistory } from '../contexts/HistoryContext';
import TimeSeriesChart from '../components/charts/TimeSeriesChart';
import GaugeChart from '../components/charts/GaugeChart';
import PhasorDiagram from '../components/charts/PhasorDiagram';
import PowerTriangle from '../components/charts/PowerTriangle';
import { Zap, WifiOff, Gauge, BarChart3, Activity, Bolt, ArrowUpDown } from 'lucide-react';

/* ──────────────── tiny helper ──────────────── */
const fmt = (v?: number, d = 2) => (v ?? 0).toFixed(d);

/* ──────────────── phase badge ──────────────── */
const PhaseBadge: FC<{ phase: string; color: string }> = ({ phase, color }) => (
  <span
    className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-extrabold uppercase tracking-wider text-white"
    style={{ backgroundColor: color }}
  >
    {phase}
  </span>
);

/* ──────────────── stat card ──────────────── */
const StatCard: FC<{
  label: string;
  value: string;
  unit?: string;
  color: string;
  icon?: React.ReactNode;
}> = ({ label, value, unit, color, icon }) => (
  <div className="flex items-center gap-3 p-3 rounded-xl border border-border bg-surface hover:shadow-md transition-shadow">
    <div
      className="w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0"
      style={{ backgroundColor: color + '18' }}
    >
      {icon || <Bolt size={18} style={{ color }} />}
    </div>
    <div className="min-w-0">
      <p className="text-[10px] font-bold uppercase tracking-wider text-text-muted truncate">{label}</p>
      <p className="text-lg font-mono font-extrabold text-text-primary leading-tight">
        {value}
        {unit && <span className="text-xs text-text-muted ml-1">{unit}</span>}
      </p>
    </div>
  </div>
);

/* ──────────────── MAIN PAGE ──────────────── */
const ElectricalParams: FC = () => {
  const { latestFeatures, isConnected } = useSensorData();
  const { electricalHistory, latestHistoricalFeatures } = useHistory();

  const e = latestFeatures?.electrical || latestHistoricalFeatures?.electrical;
  const hasData = e !== undefined && e !== null;

  return (
    <div className="space-y-6">
      {/* ───── Header ───── */}
      <div className="flex flex-wrap justify-between items-end gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 shadow-lg shadow-cyan-500/20">
            <Zap className="text-white" size={26} />
          </div>
          <div>
            <h2 className="text-3xl font-extrabold text-text-primary tracking-tight">3-Phase Power Monitor</h2>
            <p className="text-sm text-text-secondary font-medium">Live telemetry · Energy analysis · L1 / L2 / L3</p>
          </div>
        </div>
        <div className="flex gap-2 items-center flex-wrap">
          <PhaseBadge phase="L1" color="#ef4444" />
          <PhaseBadge phase="L2" color="#f59e0b" />
          <PhaseBadge phase="L3" color="#3b82f6" />
          <span className="ml-2 px-3 py-1.5 bg-gradient-to-r from-cyan-50 to-violet-50 rounded-lg text-xs font-extrabold text-primary border border-cyan-200">
            LEDL_Demo · 3Φ
          </span>
        </div>
      </div>

      {/* ───── No-data banner ───── */}
      {!hasData && (
        <div className="flex items-center justify-center gap-3 p-4 bg-accent-amber-light rounded-xl border border-amber-200">
          <WifiOff size={18} className="text-accent-amber" />
          <p className="text-sm font-semibold text-accent-amber">
            {isConnected ? 'Waiting for 3-phase data on topic "ledl" …' : 'WebSocket disconnected — no live data'}
          </p>
        </div>
      )}

      {/* ═══════════════ ROW 1 — Phase Voltages + Frequency ═══════════════ */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-5">
        {/* L1 */}
        <div className="industrial-card p-5 flex flex-col items-center border-t-4 border-[#ef4444]">
          <GaugeChart value={e?.v1n ?? 0} min={0} max={300} unit="V" label="L1 Voltage" thresholds={{ warning: 250, critical: 270 }} />
          <div className="w-full mt-3 flex justify-between text-xs font-mono font-bold bg-red-50 p-2 rounded-lg">
            <span className="text-text-muted">V₁₂ (L-L)</span>
            <span className="text-[#ef4444]">{fmt(e?.v12, 1)} V</span>
          </div>
        </div>
        {/* L2 */}
        <div className="industrial-card p-5 flex flex-col items-center border-t-4 border-[#f59e0b]">
          <GaugeChart value={e?.v2n ?? 0} min={0} max={300} unit="V" label="L2 Voltage" thresholds={{ warning: 250, critical: 270 }} />
          <div className="w-full mt-3 flex justify-between text-xs font-mono font-bold bg-amber-50 p-2 rounded-lg">
            <span className="text-text-muted">V₂₃ (L-L)</span>
            <span className="text-[#f59e0b]">{fmt(e?.v23, 1)} V</span>
          </div>
        </div>
        {/* L3 */}
        <div className="industrial-card p-5 flex flex-col items-center border-t-4 border-[#3b82f6]">
          <GaugeChart value={e?.v3n ?? 0} min={0} max={300} unit="V" label="L3 Voltage" thresholds={{ warning: 250, critical: 270 }} />
          <div className="w-full mt-3 flex justify-between text-xs font-mono font-bold bg-blue-50 p-2 rounded-lg">
            <span className="text-text-muted">V₃₁ (L-L)</span>
            <span className="text-[#3b82f6]">{fmt(e?.v31, 1)} V</span>
          </div>
        </div>
        {/* Voltage Averages + Frequency */}
        <div className="industrial-card p-5 flex flex-col justify-between bg-gradient-to-br from-surface to-cyan-50/40">
          <h3 className="text-[10px] uppercase font-extrabold tracking-[0.2em] text-text-muted mb-4 flex items-center gap-1.5">
            <Gauge size={12} /> Voltage Summary
          </h3>
          <div className="space-y-3 flex-1">
            <div className="flex justify-between items-center">
              <span className="text-xs font-bold text-text-secondary">VLN avg</span>
              <span className="text-xl font-mono font-extrabold text-primary">{fmt(e?.vln_avg, 1)}<span className="text-xs ml-0.5">V</span></span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-xs font-bold text-text-secondary">VLL avg</span>
              <span className="text-xl font-mono font-extrabold text-primary">{fmt(e?.vll_avg, 1)}<span className="text-xs ml-0.5">V</span></span>
            </div>
          </div>
          <div className="mt-auto pt-3 border-t border-border flex items-center justify-between bg-surface/60 px-3 py-2 rounded-lg">
            <span className="text-xs font-bold text-text-muted flex items-center gap-1"><Activity size={12}/> Freq</span>
            <span className="text-lg font-mono font-extrabold text-emerald-600">{fmt(e?.frequency, 2)}<span className="text-[10px] ml-0.5">Hz</span></span>
          </div>
        </div>
      </div>

      {/* ═══════════════ ROW 2 — Phasor Diagram & Energy ═══════════════ */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Phasor Diagram + Currents */}
        <div className="industrial-card p-5 flex flex-col bg-gradient-to-b from-surface to-slate-50">
          <h3 className="text-xs uppercase font-extrabold tracking-wider text-text-muted mb-2 text-center flex items-center justify-center gap-1.5">
            <ArrowUpDown size={14}/> Phasor Diagram
          </h3>
          <div className="flex-1 flex items-center justify-center min-h-[240px]">
            <PhasorDiagram v1={e?.v1n || 0} v2={e?.v2n || 0} v3={e?.v3n || 0} i1={e?.i1 || 0} i2={e?.i2 || 0} i3={e?.i3 || 0} />
          </div>
          {/* Current row */}
          <div className="grid grid-cols-3 gap-2 mt-3 pt-3 border-t border-border">
            {[
              { label: 'I₁', val: e?.i1, color: '#ef4444' },
              { label: 'I₂', val: e?.i2, color: '#f59e0b' },
              { label: 'I₃', val: e?.i3, color: '#3b82f6' },
            ].map(p => (
              <div key={p.label} className="text-center p-2 rounded-lg" style={{ backgroundColor: p.color + '0d' }}>
                <p className="text-[10px] font-bold text-text-muted">{p.label}</p>
                <p className="text-sm font-mono font-extrabold" style={{ color: p.color }}>{fmt(p.val)} A</p>
              </div>
            ))}
          </div>
          <div className="text-center mt-2 bg-surface-muted py-1.5 rounded-lg">
            <span className="text-xs font-bold text-text-secondary">I_avg = </span>
            <span className="text-sm font-mono font-extrabold text-primary">{fmt(e?.i_avg)} A</span>
          </div>
        </div>

        {/* Energy Counters & Max Demand */}
        <div className="industrial-card p-5 flex flex-col">
          <h3 className="text-xs uppercase font-extrabold tracking-wider text-text-muted mb-4 flex items-center gap-1.5">
            <Bolt size={14}/> Energy & Demand
          </h3>
          <div className="space-y-3 flex-1">
            <div className="flex justify-between items-center p-3 rounded-xl bg-gradient-to-r from-emerald-50 to-emerald-100/30 border border-emerald-200/60">
              <span className="text-xs font-extrabold text-emerald-800">kWh Import</span>
              <span className="text-xl font-mono font-extrabold text-emerald-600">{fmt(e?.kwh_imp, 1)}</span>
            </div>
            <div className="flex justify-between items-center p-3 rounded-xl bg-gradient-to-r from-sky-50 to-sky-100/30 border border-sky-200/60">
              <span className="text-xs font-extrabold text-sky-800">kWh Export</span>
              <span className="text-xl font-mono font-extrabold text-sky-600">{fmt(e?.kwh_exp, 1)}</span>
            </div>
            <div className="flex justify-between items-center p-3 rounded-xl bg-gradient-to-r from-amber-50 to-amber-100/30 border border-amber-200/60">
              <span className="text-xs font-extrabold text-amber-800">kVARh Import</span>
              <span className="text-xl font-mono font-extrabold text-amber-600">{fmt(e?.kvarh_imp, 1)}</span>
            </div>
            <div className="flex justify-between items-center p-3 rounded-xl bg-gradient-to-r from-violet-50 to-violet-100/30 border border-violet-200/60">
              <span className="text-xs font-extrabold text-violet-800">Total kVAh</span>
              <span className="text-xl font-mono font-extrabold text-violet-600">{fmt(e?.t_kvah, 1)}</span>
            </div>
          </div>
          {/* Max Demand */}
          <div className="mt-4 pt-3 border-t border-border">
            <p className="text-[10px] font-extrabold uppercase tracking-[0.18em] text-text-muted mb-2">Maximum Demand</p>
            <div className="grid grid-cols-3 gap-2">
              {[
                { label: 'MD kW', val: e?.md_kw, color: '#10b981' },
                { label: 'MD kVAR', val: e?.md_kvar, color: '#f59e0b' },
                { label: 'MD kVA', val: e?.md_kva, color: '#8b5cf6' },
              ].map(p => (
                <div key={p.label} className="text-center p-2 bg-surface-muted rounded-lg">
                  <p className="text-[9px] font-bold text-text-muted">{p.label}</p>
                  <p className="text-sm font-mono font-extrabold" style={{ color: p.color }}>{fmt(p.val)}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* ═══════════════ ROW 2.5 — Power Triangle ═══════════════ */}
      <div className="industrial-card p-5 flex flex-col bg-gradient-to-b from-surface to-violet-50/30">
        <h3 className="text-xs uppercase font-extrabold tracking-wider text-text-muted mb-4 text-center flex items-center justify-center gap-1.5">
          <BarChart3 size={16}/> Power Triangle
        </h3>
        <div className="flex-1 flex items-center justify-center min-h-[350px]">
          <PowerTriangle kw={e?.t_kw || 0} kvar={e?.t_kvar || 0} kva={e?.t_kva || 0} />
        </div>
        
        {/* Totals row (Centered) */}
        <div className="mt-6 pt-4 border-t border-border flex justify-center">
          <div className="grid grid-cols-4 gap-6 w-full max-w-3xl">
            {[
              { label: 'Σ kW', val: e?.t_kw, color: '#10b981' },
              { label: 'Σ kVAR', val: e?.t_kvar, color: '#f59e0b' },
              { label: 'Σ kVA', val: e?.t_kva, color: '#8b5cf6' },
              { label: 'Avg PF', val: e?.pf_avg, color: '#0891b2', digits: 3 },
            ].map(p => (
              <div key={p.label} className="text-center p-3 rounded-xl" style={{ backgroundColor: p.color + '0d' }}>
                <p className="text-xs font-bold text-text-muted mb-1">{p.label}</p>
                <p className="text-lg font-mono font-extrabold" style={{ color: p.color }}>
                  {fmt(p.val, p.digits ?? 2)}
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ═══════════════ ROW 3 — Per-Phase Power Table ═══════════════ */}
      <div className="industrial-card overflow-hidden">
        <div className="px-5 pt-5 pb-3">
          <h3 className="text-xs uppercase font-extrabold tracking-wider text-text-muted flex items-center gap-1.5">
            <BarChart3 size={14}/> Per-Phase Power Breakdown
          </h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gradient-to-r from-slate-50 to-cyan-50/40 text-text-secondary">
                <th className="text-left px-5 py-3 text-xs font-extrabold uppercase tracking-wider">Phase</th>
                <th className="text-right px-5 py-3 text-xs font-extrabold uppercase tracking-wider">Voltage (V)</th>
                <th className="text-right px-5 py-3 text-xs font-extrabold uppercase tracking-wider">Current (A)</th>
                <th className="text-right px-5 py-3 text-xs font-extrabold uppercase tracking-wider">kW</th>
                <th className="text-right px-5 py-3 text-xs font-extrabold uppercase tracking-wider">kVAR</th>
                <th className="text-right px-5 py-3 text-xs font-extrabold uppercase tracking-wider">kVA</th>
                <th className="text-right px-5 py-3 text-xs font-extrabold uppercase tracking-wider">PF</th>
              </tr>
            </thead>
            <tbody className="font-mono">
              {[
                { phase: 'L1', color: '#ef4444', bg: 'bg-red-50/40', v: e?.v1n, i: e?.i1, kw: e?.kw1, kvar: e?.kvar1, kva: e?.kva1, pf: e?.pf1 },
                { phase: 'L2', color: '#f59e0b', bg: 'bg-amber-50/40', v: e?.v2n, i: e?.i2, kw: e?.kw2, kvar: e?.kvar2, kva: e?.kva2, pf: e?.pf2 },
                { phase: 'L3', color: '#3b82f6', bg: 'bg-blue-50/40', v: e?.v3n, i: e?.i3, kw: e?.kw3, kvar: e?.kvar3, kva: e?.kva3, pf: e?.pf3 },
              ].map(row => (
                <tr key={row.phase} className={`${row.bg} border-t border-border/50 hover:bg-surface-muted transition-colors`}>
                  <td className="px-5 py-3">
                    <PhaseBadge phase={row.phase} color={row.color} />
                  </td>
                  <td className="text-right px-5 py-3 font-bold">{fmt(row.v, 1)}</td>
                  <td className="text-right px-5 py-3 font-bold">{fmt(row.i, 2)}</td>
                  <td className="text-right px-5 py-3 font-bold text-emerald-600">{fmt(row.kw, 2)}</td>
                  <td className="text-right px-5 py-3 font-bold text-amber-600">{fmt(row.kvar, 2)}</td>
                  <td className="text-right px-5 py-3 font-bold text-violet-600">{fmt(row.kva, 2)}</td>
                  <td className="text-right px-5 py-3 font-bold">{fmt(row.pf, 3)}</td>
                </tr>
              ))}
              {/* Totals row */}
              <tr className="bg-gradient-to-r from-cyan-50/50 to-violet-50/50 border-t-2 border-primary/20 font-extrabold">
                <td className="px-5 py-3 text-xs uppercase tracking-wider text-text-secondary">Total / Avg</td>
                <td className="text-right px-5 py-3">{fmt(e?.vln_avg, 1)}</td>
                <td className="text-right px-5 py-3">{fmt(e?.i_avg, 2)}</td>
                <td className="text-right px-5 py-3 text-emerald-700">{fmt(e?.t_kw, 2)}</td>
                <td className="text-right px-5 py-3 text-amber-700">{fmt(e?.t_kvar, 2)}</td>
                <td className="text-right px-5 py-3 text-violet-700">{fmt(e?.t_kva, 2)}</td>
                <td className="text-right px-5 py-3">{fmt(e?.pf_avg, 3)}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* ═══════════════ ROW 4 — Power Factor Gauges ═══════════════ */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-5">
        {[
          { label: 'PF L1', val: e?.pf1, color: '#ef4444' },
          { label: 'PF L2', val: e?.pf2, color: '#f59e0b' },
          { label: 'PF L3', val: e?.pf3, color: '#3b82f6' },
          { label: 'PF Avg', val: e?.pf_avg, color: '#0891b2' },
        ].map(p => (
          <div key={p.label} className="industrial-card p-5 flex flex-col items-center" style={{ borderTop: `4px solid ${p.color}` }}>
            <GaugeChart value={p.val ?? 1} min={0} max={1.05} unit="cos φ" label={p.label} thresholds={{ warning: 0.85, critical: 0.7 }} />
          </div>
        ))}
      </div>

      {/* ═══════════════ ROW 5 — Time Series ═══════════════ */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <div className="industrial-card p-5">
          <div className="h-[320px]">
            <TimeSeriesChart
              data={electricalHistory}
              title="3-Phase Voltage Trend (V)"
              lines={[
                { key: 'v1n', color: '#ef4444', name: 'L1 Voltage' },
                { key: 'v2n', color: '#f59e0b', name: 'L2 Voltage' },
                { key: 'v3n', color: '#3b82f6', name: 'L3 Voltage' },
              ]}
            />
          </div>
        </div>
        <div className="industrial-card p-5">
          <div className="h-[320px]">
            <TimeSeriesChart
              data={electricalHistory}
              title="3-Phase Current Pattern (A)"
              lines={[
                { key: 'i1', color: '#ef4444', name: 'L1 Current' },
                { key: 'i2', color: '#f59e0b', name: 'L2 Current' },
                { key: 'i3', color: '#3b82f6', name: 'L3 Current' },
              ]}
            />
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <div className="industrial-card p-5">
          <div className="h-[300px]">
            <TimeSeriesChart
              data={electricalHistory}
              title="Active Power per Phase (kW)"
              lines={[
                { key: 'kw1', color: '#ef4444', name: 'L1 kW' },
                { key: 'kw2', color: '#f59e0b', name: 'L2 kW' },
                { key: 'kw3', color: '#3b82f6', name: 'L3 kW' },
              ]}
            />
          </div>
        </div>
        <div className="industrial-card p-5">
          <div className="h-[300px]">
            <TimeSeriesChart
              data={electricalHistory}
              title="Power Factor Trend (cos φ)"
              lines={[
                { key: 'pf', color: '#10b981', name: 'Avg PF' },
              ]}
            />
          </div>
        </div>
      </div>

    </div>
  );
};

export default ElectricalParams;
