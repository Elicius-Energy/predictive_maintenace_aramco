import { useEffect, useState, useMemo } from 'react';
import type { FC } from 'react';
// unused navigate
import { useSensorData } from '../hooks/useSensorData';
import { useHistory } from '../contexts/HistoryContext';
import { useMotorDetails } from '../contexts/MotorDetailsContext';
import { useMachine } from '../contexts/MachineContext';
import TimeSeriesChart from '../components/charts/TimeSeriesChart';
import GaugeChart from '../components/charts/GaugeChart';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip as RechartsTooltip } from 'recharts';
import { estimateMotorEfficiency } from '../data/motorEfficiency';
import { TrendingUp, ShieldAlert, WifiOff } from 'lucide-react';

// removed unused fmt

const DashboardOverview: FC = () => {
  const { latestFeatures, isConnected } = useSensorData();
  const { electricalHistory, latestHistoricalFeatures, periodEnergy } = useHistory();
  const { motorDetails } = useMotorDetails();
  const { timeRange, isAutoUpdate } = useMachine();
  
  const [targetEfficiency, setTargetEfficiency] = useState<number>(95);
  const [nowTs, setNowTs] = useState<number>(Date.now());

  // Force re-render for real-time updates when auto is selected
  useEffect(() => {
    if (!isAutoUpdate) return;
    const interval = setInterval(() => setNowTs(Date.now()), 1000);
    return () => clearInterval(interval);
  }, [isAutoUpdate]);

  const e = latestFeatures?.electrical || latestHistoricalFeatures?.electrical;
  const hasData = e !== undefined && e !== null;

  // Efficiency Computation
  const efficiencyCalc = useMemo(() => {
    if (!hasData) return null;
    const pMeasuredKW = e?.t_kw ?? e?.active_power ?? 0;
    const pMeasuredW = pMeasuredKW * 1000;

    if (pMeasuredW <= 0) return null;

    const result = estimateMotorEfficiency(pMeasuredW, {
      voltage: e?.vll_avg ?? e?.voltage,
      current: e?.i_avg ?? e?.current,
      pf: e?.pf_avg ?? e?.power_factor,
      frequency: e?.frequency,
    });

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

  // Period metrics
  const startTs = new Date(timeRange.start).getTime();
  const endTs = isAutoUpdate ? nowTs : new Date(timeRange.end).getTime();
  const totalPeriodHours = Math.max(0, (endTs - startTs) / (1000 * 60 * 60));
  
  // Calculate running hours in this period from electricalHistory
  const periodRunTimeHours = useMemo(() => {
    if (electricalHistory.length < 2) return 0;
    let runMs = 0;
    for (let i = 1; i < electricalHistory.length; i++) {
      const prev = electricalHistory[i - 1];
      const curr = electricalHistory[i];
      // Assume running if active power (p) > 0.5 kW
      if ((prev.p || 0) > 0.5 || (curr.p || 0) > 0.5) {
        const tzPrev = (prev.timestamp.endsWith('Z') || prev.timestamp.includes('+')) ? prev.timestamp : prev.timestamp + 'Z';
        const tzCurr = (curr.timestamp.endsWith('Z') || curr.timestamp.includes('+')) ? curr.timestamp : curr.timestamp + 'Z';
        const prevTs = new Date(tzPrev).getTime();
        const currTs = new Date(tzCurr).getTime();
        const dt = currTs - prevTs;
        if (dt > 0 && dt < 24 * 60 * 60 * 1000) { // Max 1 day gap
          runMs += dt;
        }
      }
    }
    return runMs / (1000 * 60 * 60);
  }, [electricalHistory]);

  const idleHours = Math.max(0, totalPeriodHours - periodRunTimeHours);
  
  const donutData = [
    { name: 'Run Time', value: periodRunTimeHours },
    { name: 'Idle Time', value: idleHours }
  ];
  const donutColors = ['#0891b2', '#94a3b8'];

  // ROI inputs (hardcoded defaults for layout)
  const annualHours = 8000;

  // ROI Computation
  const roiCalc = useMemo(() => {
    if (!efficiencyCalc || !motorDetails) return null;
    const { etaActual, pMeasured } = efficiencyCalc;
    const etaTarget = targetEfficiency;
    const elecCost = motorDetails.electricityCost;
    const motorPrice = motorDetails.motorPrice;

    if (etaTarget <= 0 || etaActual <= 0 || pMeasured <= 0) return null;

    const powerSaved = pMeasured * (1 - etaActual / etaTarget);
    const energySaved = powerSaved * annualHours;
    const costSaved = energySaved * elecCost;
    const payback = costSaved > 0 ? motorPrice / costSaved : Infinity;

    return { powerSaved, energySaved, costSaved, payback };
  }, [efficiencyCalc, motorDetails, targetEfficiency, annualHours]);

  return (
    <div className="h-full flex flex-col gap-4 overflow-hidden">
      {!hasData && (
        <div className="flex items-center justify-center gap-3 p-3 industrial-card border-l-4 border-l-amber-400 shrink-0">
          <WifiOff size={18} className="text-accent-amber" />
          <p className="text-sm font-semibold text-accent-amber">
            {isConnected ? 'Waiting for 3-phase data...' : 'WebSocket disconnected — no live data'}
          </p>
        </div>
      )}

      {/* Row 1: 3 Gauges (20% height approx) */}
      <div id="report-row-1" className="grid grid-cols-1 md:grid-cols-3 gap-4 shrink-0 h-44">
        <div className="industrial-card p-3 flex flex-col items-center justify-center">
          <GaugeChart 
            value={e?.vll_avg ?? 0} 
            min={0} 
            max={500} 
            unit="V" 
            label="Average L-L Voltage" 
            thresholds={{ warning: 430, critical: 450 }} 
          />
        </div>
        <div className="industrial-card p-3 flex flex-col items-center justify-center">
          <GaugeChart 
            value={e?.pf_avg ?? 0} 
            min={0} 
            max={1.05} 
            unit="cos φ" 
            label="Average Power Factor" 
            thresholds={{ warning: 0.85, critical: 0.7 }} 
          />
        </div>
        <div className="industrial-card p-3 grid grid-cols-2">
          <div className="text-center flex flex-col justify-center border-r border-white/30 px-2">
            <h3 className="text-[10px] font-bold text-text-secondary uppercase tracking-wider mb-2">Energy Consumed</h3>
            <p className="text-3xl font-extrabold text-teal-600 scada-number">{periodEnergy.toFixed(1)}</p>
            <p className="text-xs font-semibold text-teal-700 mt-1">kWh (Period)</p>
          </div>
          <div className="flex flex-col items-center justify-center relative px-2">
            <h3 className="text-[10px] font-bold text-text-secondary uppercase tracking-wider mb-1">Run Time vs Idle</h3>
            <div className="w-full h-[90px]">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={donutData}
                    cx="50%"
                    cy="50%"
                    innerRadius={25}
                    outerRadius={40}
                    paddingAngle={2}
                    dataKey="value"
                    stroke="none"
                  >
                    {donutData.map((_, index) => (
                      <Cell key={`cell-${index}`} fill={donutColors[index % donutColors.length]} />
                    ))}
                  </Pie>
                  <RechartsTooltip 
                    formatter={(value: any) => [`${Number(value).toFixed(1)} hrs`, '']}
                    contentStyle={{ 
                      background: 'rgba(255,255,255,0.75)', 
                      backdropFilter: 'blur(12px)',
                      border: '1px solid rgba(255,255,255,0.5)', 
                      borderRadius: '10px', 
                      color: '#0f172a', 
                      fontSize: '12px',
                      boxShadow: '0 4px 16px rgba(0,0,0,0.08)'
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <p className="text-xs font-semibold text-text-secondary absolute bottom-1">
              <span className="font-extrabold text-primary">{periodRunTimeHours.toFixed(1)}h</span> / {totalPeriodHours.toFixed(1)}h
            </p>
          </div>
        </div>
      </div>

      {/* Row 2: Line Charts (45% height approx) */}
      <div id="report-row-2" className="grid grid-cols-1 md:grid-cols-2 gap-4 flex-1 min-h-0">
        <div className="industrial-card p-4 flex flex-col">
          <div className="flex-1 min-h-0">
            <TimeSeriesChart
              data={electricalHistory}
              title="Current Profile (A)"
              lines={[
                { key: 'i1', color: '#ef4444', name: 'L1 Current', dashed: true },
                { key: 'i2', color: '#f59e0b', name: 'L2 Current', dashed: true },
                { key: 'i3', color: '#3b82f6', name: 'L3 Current', dashed: true },
                { key: 'i', color: '#0891b2', name: 'Avg Current', dashed: false },
              ]}
              threshold={motorDetails?.ratedCurrent ? {
                value: motorDetails.ratedCurrent,
                label: `Rated: ${motorDetails.ratedCurrent}A`,
                color: '#dc2626'
              } : undefined}
            />
          </div>
        </div>
        <div className="industrial-card p-4 flex flex-col">
          <div className="flex-1 min-h-0">
            <TimeSeriesChart
              data={electricalHistory}
              title="Active Power (kW)"
              lines={[
                { key: 'kw1', color: '#ef4444', name: 'L1 kW', dashed: true },
                { key: 'kw2', color: '#f59e0b', name: 'L2 kW', dashed: true },
                { key: 'kw3', color: '#3b82f6', name: 'L3 kW', dashed: true },
                { key: 'p', color: '#10b981', name: 'Total kW', dashed: false },
              ]}
              threshold={motorDetails?.ratedPower ? {
                value: motorDetails.ratedPower,
                label: `Rated: ${motorDetails.ratedPower}kW`,
                color: '#dc2626'
              } : undefined}
            />
          </div>
        </div>
      </div>

      {/* Row 3: Efficiency Analysis (35% height approx) */}
      <div className="shrink-0 h-64 overflow-y-auto">
        {efficiencyCalc && (
          <div className="industrial-card p-4 border-l-4 border-l-cyan-500 h-full flex flex-col">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-3 shrink-0 gap-3">
              <h3 className="text-sm font-bold text-text-primary uppercase tracking-wider flex items-center gap-2">
                <TrendingUp className="text-primary" size={18} />
                Motor Efficiency & ROI Analysis
              </h3>
              
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-2">
                  <label className="text-xs font-bold text-text-secondary uppercase">New Motor η:</label>
                  <div className="relative">
                    <input 
                      type="number" 
                      value={targetEfficiency}
                      onChange={(e) => setTargetEfficiency(Number(e.target.value))}
                      className="w-20 glass-input text-sm font-mono font-bold text-primary pl-2 pr-6 py-1 rounded-lg"
                      step="0.1"
                      min="50"
                      max="100"
                    />
                    <span className="absolute right-2 top-1/2 -translate-y-1/2 text-xs font-bold text-text-muted">%</span>
                  </div>
                </div>

                {efficiencyCalc.extrapolated && (
                  <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg glass-badge text-[10px] font-extrabold text-amber-700 uppercase tracking-wider border-amber-300/50">
                    <ShieldAlert size={12} />
                    Extrapolated
                  </span>
                )}
              </div>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-6 gap-3 flex-1 min-h-0 items-center">
              {/* η rated */}
              <div className="p-3 rounded-xl bg-emerald-500/10 backdrop-blur-sm border border-emerald-200/40 text-center flex flex-col justify-center h-full">
                <p className="text-[10px] font-extrabold text-emerald-700 uppercase tracking-wider mb-1">η Rated</p>
                <p className="text-xl font-mono font-extrabold text-emerald-600">{efficiencyCalc.etaRated.toFixed(1)}<span className="text-xs">%</span></p>
              </div>
              {/* η actual */}
              <div className={`p-3 rounded-xl text-center flex flex-col justify-center h-full backdrop-blur-sm border ${efficiencyCalc.gap > 5
                ? 'bg-red-500/10 border-red-200/40'
                : efficiencyCalc.gap > 2
                  ? 'bg-amber-500/10 border-amber-200/40'
                  : 'bg-cyan-500/10 border-cyan-200/40'
                }`}>
                <p className="text-[10px] font-extrabold text-text-secondary uppercase tracking-wider mb-1">η Estimated</p>
                <p className={`text-xl font-mono font-extrabold ${efficiencyCalc.gap > 5
                  ? 'text-accent-red'
                  : efficiencyCalc.gap > 2
                    ? 'text-accent-amber'
                    : 'text-primary'
                  }`}>{efficiencyCalc.etaActual.toFixed(1)}<span className="text-xs">%</span></p>
              </div>
              {/* Load % */}
              <div className={`p-3 rounded-xl text-center flex flex-col justify-center h-full backdrop-blur-sm border ${efficiencyCalc.loadPct > 115
                  ? 'bg-red-500/10 border-red-200/40'
                  : efficiencyCalc.loadPct > 100
                    ? 'bg-amber-500/10 border-amber-200/40'
                    : 'bg-violet-500/10 border-violet-200/40'
                }`}>
                <p className="text-[10px] font-extrabold text-text-secondary uppercase tracking-wider mb-1">Load</p>
                <p className={`text-xl font-mono font-extrabold ${efficiencyCalc.loadPct > 115 ? 'text-accent-red'
                    : efficiencyCalc.loadPct > 100 ? 'text-accent-amber'
                      : 'text-violet-600'
                  }`}>{efficiencyCalc.loadPct.toFixed(1)}<span className="text-xs">%</span></p>
              </div>
              
              {/* ROI block 1 */}
              <div className="p-3 rounded-xl bg-white/30 backdrop-blur-sm border border-white/50 text-center flex flex-col justify-center h-full">
                <p className="text-[10px] text-text-muted uppercase font-bold tracking-tight mb-1">Energy Saved/Yr</p>
                <p className="text-xl font-extrabold text-accent-green scada-number">
                  {roiCalc ? roiCalc.energySaved.toFixed(0) : '--'} <span className="text-xs text-text-muted">kWh</span>
                </p>
              </div>
              {/* ROI block 2 */}
              <div className="p-3 rounded-xl bg-white/30 backdrop-blur-sm border border-white/50 text-center flex flex-col justify-center h-full">
                <p className="text-[10px] text-text-muted uppercase font-bold tracking-tight mb-1">Cost Saved/Yr</p>
                <p className="text-xl font-extrabold text-emerald-600 scada-number">
                  {roiCalc ? `₹${roiCalc.costSaved.toFixed(0)}` : '--'}
                </p>
              </div>
              {/* ROI block 3 */}
              <div className="p-3 rounded-xl bg-white/30 backdrop-blur-sm border border-white/50 text-center flex flex-col justify-center h-full">
                <p className="text-[10px] text-text-muted uppercase font-bold tracking-tight mb-1">Simple Payback</p>
                <p className={`text-xl font-extrabold scada-number ${roiCalc && roiCalc.payback < 3 ? 'text-accent-green' : roiCalc && roiCalc.payback < 7 ? 'text-accent-amber' : 'text-accent-red'}`}>
                  {roiCalc ? (roiCalc.payback === Infinity ? '∞' : roiCalc.payback.toFixed(1)) : '--'} <span className="text-xs text-text-muted">yrs</span>
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default DashboardOverview;
