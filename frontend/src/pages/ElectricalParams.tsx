import { useState, useMemo } from 'react';
import type { FC } from 'react';
import { useNavigate } from 'react-router-dom';
import { useSensorData } from '../hooks/useSensorData';
import { useHistory } from '../contexts/HistoryContext';
import { useMotorDetails } from '../contexts/MotorDetailsContext';
import MotorDetailsForm from './MotorDetailsForm';
import TimeSeriesChart from '../components/charts/TimeSeriesChart';
import GaugeChart from '../components/charts/GaugeChart';
import PhasorDiagram from '../components/charts/PhasorDiagram';
import PowerTriangle from '../components/charts/PowerTriangle';
import { estimateMotorEfficiency } from '../data/motorEfficiency';
import { Zap, WifiOff, Gauge, BarChart3, Activity, Bolt, ArrowUpDown, TrendingUp, AlertTriangle, DollarSign, Target, ShieldAlert, Info } from 'lucide-react';

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

/* ──────────────── MAIN PAGE ──────────────── */
const ElectricalParams: FC = () => {
  const navigate = useNavigate();
  const { latestFeatures, isConnected } = useSensorData();
  const { electricalHistory, latestHistoricalFeatures, periodEnergy } = useHistory();
  const { motorDetails, resetMotorDetails } = useMotorDetails();

  const handleResetConfig = async () => {
    if (window.confirm("Are you sure you want to clear the saved motor configuration?")) {
      try {
        await resetMotorDetails();
        navigate('/machines');
      } catch (e) {
        alert("Failed to reset configuration.");
      }
    }
  };

  const e = latestFeatures?.electrical || latestHistoricalFeatures?.electrical;
  const hasData = e !== undefined && e !== null;

  // ── ROI inputs (local state) ──
  const [targetEfficiency, setTargetEfficiency] = useState(95);
  const [annualHours, setAnnualHours] = useState(8000);
  const [showSetupModal, setShowSetupModal] = useState(false);

  // ── Efficiency Computation (Manufacturer Curve — PCHIP Interpolation) ──
  const efficiencyCalc = useMemo(() => {
    if (!hasData) return null;
    const pMeasuredKW = e?.t_kw ?? e?.active_power ?? 0; // kW (electrical input)
    const pMeasuredW = pMeasuredKW * 1000;                // convert to watts

    if (pMeasuredW <= 0) return null;

    const result = estimateMotorEfficiency(pMeasuredW, {
      voltage: e?.vll_avg ?? e?.voltage,
      current: e?.i_avg ?? e?.current,
      pf: e?.pf_avg ?? e?.power_factor,
      frequency: e?.frequency,
    });

    // η at rated load point (≈98 % load → 85.33 % from manufacturer curve)
    const etaRatedResult = estimateMotorEfficiency(6431); // rated ~98 % load point
    const etaRated = etaRatedResult.efficiencyPct;
    const gap = etaRated - result.efficiencyPct;

    return {
      etaRated,
      etaActual: result.efficiencyPct,
      gap,
      pMeasured: pMeasuredKW,
      pMeasuredW,
      pOutW: result.outputPowerW,
      loadPct: result.loadPct,
      extrapolated: result.extrapolated,
      validationFlags: result.validationFlags,
    };
  }, [e, hasData]);

  // ── ROI Computation ──
  const roiCalc = useMemo(() => {
    if (!efficiencyCalc || !motorDetails) return null;
    const { etaActual, pMeasured } = efficiencyCalc;
    const etaTarget = targetEfficiency;
    const elecCost = motorDetails.electricityCost;
    const motorPrice = motorDetails.motorPrice;

    if (etaTarget <= 0 || etaActual <= 0 || pMeasured <= 0) return null;

    const powerSaved = pMeasured * (1 - etaActual / etaTarget); // kW
    const energySaved = powerSaved * annualHours;                // kWh/year
    const costSaved = energySaved * elecCost;                    // ₹/year
    const payback = costSaved > 0 ? motorPrice / costSaved : Infinity; // years

    return { powerSaved, energySaved, costSaved, payback };
  }, [efficiencyCalc, motorDetails, targetEfficiency, annualHours]);

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
          <GaugeChart value={e?.v12 ?? 0} min={0} max={500} unit="V" label="L1-L2 Voltage" thresholds={{ warning: 430, critical: 450 }} />
          <div className="w-full mt-3 flex justify-between text-xs font-mono font-bold bg-red-50 p-2 rounded-lg">
            <span className="text-text-muted">V₁N (L-N)</span>
            <span className="text-[#ef4444]">{fmt(e?.v1n, 1)} V</span>
          </div>
        </div>
        {/* L2 */}
        <div className="industrial-card p-5 flex flex-col items-center border-t-4 border-[#f59e0b]">
          <GaugeChart value={e?.v23 ?? 0} min={0} max={500} unit="V" label="L2-L3 Voltage" thresholds={{ warning: 430, critical: 450 }} />
          <div className="w-full mt-3 flex justify-between text-xs font-mono font-bold bg-amber-50 p-2 rounded-lg">
            <span className="text-text-muted">V₂N (L-N)</span>
            <span className="text-[#f59e0b]">{fmt(e?.v2n, 1)} V</span>
          </div>
        </div>
        {/* L3 */}
        <div className="industrial-card p-5 flex flex-col items-center border-t-4 border-[#3b82f6]">
          <GaugeChart value={e?.v31 ?? 0} min={0} max={500} unit="V" label="L3-L1 Voltage" thresholds={{ warning: 430, critical: 450 }} />
          <div className="w-full mt-3 flex justify-between text-xs font-mono font-bold bg-blue-50 p-2 rounded-lg">
            <span className="text-text-muted">V₃N (L-N)</span>
            <span className="text-[#3b82f6]">{fmt(e?.v3n, 1)} V</span>
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

      {/* ═══════════════ ROW 5 — Time Series (Line Plots) ═══════════════ */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <div className="industrial-card p-5">
          <div className="h-[320px]">
            <TimeSeriesChart
              data={electricalHistory}
              title="3-Phase L-L Voltage Trend (V)"
              yDomain={[0, 500]}
              lines={[
                { key: 'v12', color: '#ef4444', name: 'L1-L2 Voltage' },
                { key: 'v23', color: '#f59e0b', name: 'L2-L3 Voltage' },
                { key: 'v31', color: '#3b82f6', name: 'L3-L1 Voltage' },
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
            {/* Lifetime Energy */}
            <div className="flex justify-between items-center p-3 rounded-xl bg-gradient-to-r from-emerald-50 to-emerald-100/30 border border-emerald-200/60">
              <div>
                <span className="text-xs font-extrabold text-emerald-800">Lifetime Energy (kWh)</span>
                <p className="text-[10px] text-emerald-600 font-medium mt-0.5">Cumulative meter reading</p>
              </div>
              <span className="text-xl font-mono font-extrabold text-emerald-600">{fmt(e?.kwh_imp, 1)}</span>
            </div>
            {/* Period Energy — computed from power integration */}
            <div className="flex justify-between items-center p-3 rounded-xl bg-gradient-to-r from-teal-50 to-teal-100/30 border border-teal-200/60">
              <div>
                <span className="text-xs font-extrabold text-teal-800">Period Energy (kWh)</span>
                <p className="text-[10px] text-teal-600 font-medium mt-0.5">∫ P(t) dt over selected window</p>
              </div>
              <span className="text-xl font-mono font-extrabold text-teal-600">{periodEnergy.toFixed(3)}</span>
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

      {/* ═══════════════ EFFICIENCY ANALYSIS ═══════════════ */}
      {efficiencyCalc && (
        <div className="industrial-card p-6 border-l-4 border-l-cyan-500 bg-gradient-to-br from-surface to-cyan-50/20">
          <div className="flex items-center justify-between mb-5">
            <h3 className="text-sm font-bold text-text-primary uppercase tracking-wider flex items-center gap-2">
              <TrendingUp className="text-primary" size={18} />
              Motor Efficiency Analysis
            </h3>
            {efficiencyCalc.extrapolated && (
              <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gradient-to-r from-amber-50 to-orange-50 border border-amber-300 text-[10px] font-extrabold text-amber-800 uppercase tracking-wider animate-pulse">
                <ShieldAlert size={12} />
                Extrapolated
              </span>
            )}
          </div>

          <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-4">
            {/* η rated */}
            <div className="p-4 rounded-xl bg-gradient-to-br from-emerald-50 to-emerald-100/40 border border-emerald-200/60 text-center">
              <p className="text-[10px] font-extrabold text-emerald-700 uppercase tracking-wider mb-2">η Rated (Test Report)</p>
              <p className="text-2xl font-mono font-extrabold text-emerald-600">{efficiencyCalc.etaRated.toFixed(1)}<span className="text-sm">%</span></p>
            </div>
            {/* η actual */}
            <div className={`p-4 rounded-xl text-center border ${efficiencyCalc.gap > 5
                ? 'bg-gradient-to-br from-red-50 to-red-100/40 border-red-200/60'
                : efficiencyCalc.gap > 2
                  ? 'bg-gradient-to-br from-amber-50 to-amber-100/40 border-amber-200/60'
                  : 'bg-gradient-to-br from-cyan-50 to-cyan-100/40 border-cyan-200/60'
              }`}>
              <p className="text-[10px] font-extrabold text-text-secondary uppercase tracking-wider mb-2">η Estimated</p>
              <p className={`text-2xl font-mono font-extrabold ${efficiencyCalc.gap > 5
                  ? 'text-accent-red'
                  : efficiencyCalc.gap > 2
                    ? 'text-accent-amber'
                    : 'text-primary'
                }`}>{efficiencyCalc.etaActual.toFixed(1)}<span className="text-sm">%</span></p>
              <p className="text-[10px] text-text-muted mt-1 font-mono">P_in = {efficiencyCalc.pMeasured.toFixed(2)} kW</p>
            </div>
            {/* P_out */}
            <div className="p-4 rounded-xl bg-gradient-to-br from-sky-50 to-sky-100/40 border border-sky-200/60 text-center">
              <p className="text-[10px] font-extrabold text-sky-700 uppercase tracking-wider mb-2">P_out (Shaft)</p>
              <p className="text-2xl font-mono font-extrabold text-sky-600">{(efficiencyCalc.pOutW / 1000).toFixed(2)}<span className="text-sm"> kW</span></p>
            </div>
            {/* Load % */}
            <div className={`p-4 rounded-xl text-center border ${
              efficiencyCalc.loadPct > 115
                ? 'bg-gradient-to-br from-red-50 to-red-100/40 border-red-200/60'
                : efficiencyCalc.loadPct > 100
                  ? 'bg-gradient-to-br from-amber-50 to-amber-100/40 border-amber-200/60'
                  : 'bg-gradient-to-br from-violet-50 to-violet-100/40 border-violet-200/60'
              }`}>
              <p className="text-[10px] font-extrabold text-text-secondary uppercase tracking-wider mb-2">Load</p>
              <p className={`text-2xl font-mono font-extrabold ${
                efficiencyCalc.loadPct > 115 ? 'text-accent-red'
                  : efficiencyCalc.loadPct > 100 ? 'text-accent-amber'
                  : 'text-violet-600'
                }`}>{efficiencyCalc.loadPct.toFixed(1)}<span className="text-sm">%</span></p>
              <p className="text-[10px] text-text-muted mt-1 font-mono">of 5.5 kW rated</p>
            </div>
            {/* Δη gap */}
            <div className={`p-4 rounded-xl text-center border ${efficiencyCalc.gap > 5
                ? 'bg-gradient-to-br from-red-50 to-red-100/40 border-red-200/60'
                : efficiencyCalc.gap > 2
                  ? 'bg-gradient-to-br from-amber-50 to-amber-100/40 border-amber-200/60'
                  : 'bg-gradient-to-br from-emerald-50 to-emerald-100/40 border-emerald-200/60'
              }`}>
              <p className="text-[10px] font-extrabold text-text-secondary uppercase tracking-wider mb-2" title="Difference between rated and estimated efficiency">Δ Efficiency Gap</p>
              <p className={`text-2xl font-mono font-extrabold ${efficiencyCalc.gap > 5
                  ? 'text-accent-red'
                  : efficiencyCalc.gap > 2
                    ? 'text-accent-amber'
                    : 'text-accent-green'
                }`}>{efficiencyCalc.gap > 0 ? '+' : ''}{efficiencyCalc.gap.toFixed(1)}<span className="text-sm"> pp</span></p>
              <p className="text-[10px] text-text-muted mt-1 font-mono">(Percentage Points)</p>
            </div>
          </div>

          {/* Validation flags */}
          {efficiencyCalc.validationFlags.length > 0 && (
            <div className="flex flex-wrap gap-2 mb-4">
              {efficiencyCalc.validationFlags.map((flag, i) => (
                <span key={i} className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-amber-50 border border-amber-200 text-[10px] font-bold text-amber-700">
                  <AlertTriangle size={10} />
                  {flag}
                </span>
              ))}
            </div>
          )}

          {/* Method disclaimer */}
          <div className="flex items-start gap-2 p-3 bg-cyan-50 border border-cyan-200 rounded-lg">
            <TrendingUp size={14} className="text-primary flex-shrink-0 mt-0.5" />
            <p className="text-[11px] text-cyan-800 font-medium leading-relaxed">
              <strong>Manufacturer Curve (PCHIP):</strong> Efficiency is estimated via monotone cubic Hermite (PCHIP) interpolation of 6 tested η vs P_in points from the 5.5 kW / 415 V / 4-pole motor type-test report. Calibration range: 1742–8265 W. Values outside this range are clamped to the nearest boundary.
            </p>
          </div>
        </div>
      )}

      {/* ═══════════════ ROI / ENERGY SAVINGS ═══════════════ */}
      {efficiencyCalc && (
        <div className="industrial-card p-6 border-l-4 border-l-emerald-500 bg-gradient-to-br from-surface to-emerald-50/20">
          <div className="flex items-center justify-between mb-5">
            <h3 className="text-sm font-bold text-text-primary uppercase tracking-wider flex items-center gap-2">
              <DollarSign className="text-accent-green" size={18} />
              ROI & Energy Savings Estimation
            </h3>
            <div className="flex gap-3">
              <button onClick={() => setShowSetupModal(true)} className="px-3 py-1.5 rounded-lg border border-primary text-xs font-bold text-primary hover:bg-primary/10 transition-colors">
                Edit Config
              </button>
              <button onClick={handleResetConfig} className="px-3 py-1.5 rounded-lg border border-accent-red text-xs font-bold text-accent-red hover:bg-accent-red/10 transition-colors">
                Reset
              </button>
            </div>
          </div>

          {/* User inputs */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
            <div>
              <label className="block text-xs font-bold text-text-secondary uppercase tracking-wide mb-1.5">
                <Target size={12} className="inline mr-1" />
                Target Motor Efficiency η_target (%)
              </label>
              <input
                type="number"
                step="0.1"
                min="0"
                max="100"
                value={targetEfficiency}
                onChange={(e) => setTargetEfficiency(parseFloat(e.target.value) || 0)}
                className="w-full px-4 py-2.5 rounded-xl border border-border bg-surface focus:outline-none focus:ring-2 focus:ring-primary/40 text-sm font-mono font-bold text-text-primary transition-all"
              />
            </div>
            <div>
              <label className="block text-xs font-bold text-text-secondary uppercase tracking-wide mb-1.5">
                Annual Operating Hours (h/year)
              </label>
              <input
                type="number"
                step="1"
                min="0"
                value={annualHours}
                onChange={(e) => setAnnualHours(parseInt(e.target.value) || 0)}
                className="w-full px-4 py-2.5 rounded-xl border border-border bg-surface focus:outline-none focus:ring-2 focus:ring-primary/40 text-sm font-mono font-bold text-text-primary transition-all"
              />
            </div>
          </div>

          {/* Results */}
          {roiCalc && (
            <>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-5">
                <div className="p-4 bg-surface rounded-xl border border-border">
                  <p className="text-[10px] text-text-muted uppercase font-bold tracking-tight">Power Saved</p>
                  <p className="text-xl font-extrabold text-primary scada-number mt-1">
                    {roiCalc.powerSaved.toFixed(2)} <span className="text-sm text-text-muted">kW</span>
                  </p>
                </div>
                <div className="p-4 bg-surface rounded-xl border border-border">
                  <p className="text-[10px] text-text-muted uppercase font-bold tracking-tight">Energy Saved / Year</p>
                  <p className="text-xl font-extrabold text-accent-green scada-number mt-1">
                    {roiCalc.energySaved.toFixed(0)} <span className="text-sm text-text-muted">kWh</span>
                  </p>
                </div>
                <div className="p-4 bg-surface rounded-xl border border-border">
                  <p className="text-[10px] text-text-muted uppercase font-bold tracking-tight">Cost Saved / Year</p>
                  <p className="text-xl font-extrabold text-emerald-600 scada-number mt-1">
                    ₹{roiCalc.costSaved.toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
                  </p>
                </div>
                <div className="p-4 bg-surface rounded-xl border border-border">
                  <p className="text-[10px] text-text-muted uppercase font-bold tracking-tight">Simple Payback</p>
                  <p className={`text-xl font-extrabold scada-number mt-1 ${roiCalc.payback < 3 ? 'text-accent-green' : roiCalc.payback < 7 ? 'text-accent-amber' : 'text-accent-red'}`}>
                    {roiCalc.payback === Infinity ? '∞' : roiCalc.payback.toFixed(1)} <span className="text-sm text-text-muted">years</span>
                  </p>
                </div>
              </div>

              {/* Payback timeline bar */}
              <div className="p-4 bg-surface-muted rounded-xl border border-border">
                <div className="flex items-center justify-between mb-2">
                  <p className="text-[10px] font-extrabold uppercase tracking-wider text-text-muted">Payback Timeline</p>
                  <p className="text-xs font-mono font-bold text-text-secondary">
                    {roiCalc.payback === Infinity ? 'N/A' : `${roiCalc.payback.toFixed(1)} years`}
                  </p>
                </div>
                <div className="h-4 bg-border rounded-full overflow-hidden relative">
                  <div
                    className={`h-full rounded-full transition-all duration-1000 ease-out ${roiCalc.payback < 3 ? 'bg-gradient-to-r from-emerald-400 to-emerald-600' : roiCalc.payback < 7 ? 'bg-gradient-to-r from-amber-400 to-amber-600' : 'bg-gradient-to-r from-red-400 to-red-600'}`}
                    style={{ width: `${Math.min(100, roiCalc.payback === Infinity ? 0 : Math.max(5, (1 / roiCalc.payback) * 100))}%` }}
                  />
                  {/* Year markers */}
                  {[1, 2, 3, 5, 7, 10].map(yr => (
                    <div
                      key={yr}
                      className="absolute top-0 h-full w-px bg-white/40"
                      style={{ left: `${Math.min(100, (1 / yr) * 100)}%` }}
                    />
                  ))}
                </div>
                <div className="flex justify-between mt-1 text-[9px] text-text-muted font-mono">
                  <span>0</span>
                  <span>1yr</span>
                  <span>3yr</span>
                  <span>5yr</span>
                  <span>10yr</span>
                </div>
              </div>

              {/* ROI Calculation Disclaimer */}
              <div className="mt-5 flex items-start gap-2 p-3 bg-emerald-50 border border-emerald-200 rounded-lg">
                <Info size={14} className="text-emerald-700 flex-shrink-0 mt-0.5" />
                <p className="text-[11px] text-emerald-800 font-medium leading-relaxed">
                  <strong>Payback Calculation:</strong> The simple payback time is calculated by taking the Motor Price (from config) and dividing it by the Annual Cost Saved. Cost Saved is derived from the power difference between current efficiency and the target efficiency, multiplied by the assumed Annual Operating Hours and the Electricity Unit Cost.
                </p>
              </div>
            </>
          )}
        </div>
      )}

      {showSetupModal && (
        <MotorDetailsForm 
          onClose={() => setShowSetupModal(false)}
          onSuccess={() => setShowSetupModal(false)}
        />
      )}

    </div>
  );
};

export default ElectricalParams;
