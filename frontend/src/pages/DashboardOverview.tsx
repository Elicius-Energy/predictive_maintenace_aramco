import { useMemo } from 'react';
import type { FC } from 'react';
// unused navigate
import { useSensorData } from '../hooks/useSensorData';
import { useHistory } from '../contexts/HistoryContext';
import { useMotorDetails } from '../contexts/MotorDetailsContext';
import TimeSeriesChart from '../components/charts/TimeSeriesChart';
import GaugeChart from '../components/charts/GaugeChart';
import { estimateMotorEfficiency } from '../data/motorEfficiency';
import { TrendingUp, ShieldAlert, WifiOff } from 'lucide-react';

// removed unused fmt

const DashboardOverview: FC = () => {
  const { latestFeatures, isConnected } = useSensorData();
  const { electricalHistory, latestHistoricalFeatures, periodEnergy, runTimeHours } = useHistory();
  const { motorDetails } = useMotorDetails();

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

  // ROI inputs (hardcoded defaults for layout)
  const targetEfficiency = 95;
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
        <div className="flex items-center justify-center gap-3 p-3 bg-accent-amber-light rounded-xl border border-amber-200 shrink-0">
          <WifiOff size={18} className="text-accent-amber" />
          <p className="text-sm font-semibold text-accent-amber">
            {isConnected ? 'Waiting for 3-phase data...' : 'WebSocket disconnected — no live data'}
          </p>
        </div>
      )}

      {/* Row 1: 3 Gauges (20% height approx) */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 shrink-0 h-44">
        <div className="industrial-card p-3 flex flex-col items-center justify-center bg-gradient-to-br from-surface to-cyan-50/20">
          <GaugeChart 
            value={e?.vll_avg ?? 0} 
            min={0} 
            max={500} 
            unit="V" 
            label="Average L-L Voltage" 
            thresholds={{ warning: 430, critical: 450 }} 
          />
        </div>
        <div className="industrial-card p-3 flex flex-col items-center justify-center bg-gradient-to-br from-surface to-cyan-50/20">
          <GaugeChart 
            value={e?.pf_avg ?? 0} 
            min={0} 
            max={1.05} 
            unit="cos φ" 
            label="Average Power Factor" 
            thresholds={{ warning: 0.85, critical: 0.7 }} 
          />
        </div>
        <div className="industrial-card p-3 grid grid-cols-2 bg-gradient-to-br from-surface to-cyan-50/20">
          <div className="text-center flex flex-col justify-center border-r border-cyan-500/20">
            <h3 className="text-[10px] font-bold text-text-secondary uppercase tracking-wider mb-2">Energy Consumed</h3>
            <p className="text-3xl font-extrabold text-teal-600 scada-number">{periodEnergy.toFixed(1)}</p>
            <p className="text-xs font-semibold text-teal-800 mt-1">kWh (Period)</p>
          </div>
          <div className="text-center flex flex-col justify-center">
            <h3 className="text-[10px] font-bold text-text-secondary uppercase tracking-wider mb-2">Run Time</h3>
            <p className="text-3xl font-extrabold text-blue-600 scada-number">{runTimeHours.toFixed(1)}</p>
            <p className="text-xs font-semibold text-blue-800 mt-1">Hours</p>
          </div>
        </div>
      </div>

      {/* Row 2: Line Charts (45% height approx) */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 flex-1 min-h-0">
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
          <div className="industrial-card p-4 border-l-4 border-l-cyan-500 bg-gradient-to-br from-surface to-cyan-50/20 h-full flex flex-col">
            <div className="flex items-center justify-between mb-3 shrink-0">
              <h3 className="text-sm font-bold text-text-primary uppercase tracking-wider flex items-center gap-2">
                <TrendingUp className="text-primary" size={18} />
                Motor Efficiency & ROI Analysis
              </h3>
              {efficiencyCalc.extrapolated && (
                <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gradient-to-r from-amber-50 to-orange-50 border border-amber-300 text-[10px] font-extrabold text-amber-800 uppercase tracking-wider">
                  <ShieldAlert size={12} />
                  Extrapolated
                </span>
              )}
            </div>

            <div className="grid grid-cols-2 md:grid-cols-6 gap-3 flex-1 min-h-0 items-center">
              {/* η rated */}
              <div className="p-3 rounded-xl bg-gradient-to-br from-emerald-50 to-emerald-100/40 border border-emerald-200/60 text-center flex flex-col justify-center h-full">
                <p className="text-[10px] font-extrabold text-emerald-700 uppercase tracking-wider mb-1">η Rated</p>
                <p className="text-xl font-mono font-extrabold text-emerald-600">{efficiencyCalc.etaRated.toFixed(1)}<span className="text-xs">%</span></p>
              </div>
              {/* η actual */}
              <div className={`p-3 rounded-xl text-center flex flex-col justify-center h-full border ${efficiencyCalc.gap > 5
                ? 'bg-gradient-to-br from-red-50 to-red-100/40 border-red-200/60'
                : efficiencyCalc.gap > 2
                  ? 'bg-gradient-to-br from-amber-50 to-amber-100/40 border-amber-200/60'
                  : 'bg-gradient-to-br from-cyan-50 to-cyan-100/40 border-cyan-200/60'
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
              <div className={`p-3 rounded-xl text-center flex flex-col justify-center h-full border ${efficiencyCalc.loadPct > 115
                  ? 'bg-gradient-to-br from-red-50 to-red-100/40 border-red-200/60'
                  : efficiencyCalc.loadPct > 100
                    ? 'bg-gradient-to-br from-amber-50 to-amber-100/40 border-amber-200/60'
                    : 'bg-gradient-to-br from-violet-50 to-violet-100/40 border-violet-200/60'
                }`}>
                <p className="text-[10px] font-extrabold text-text-secondary uppercase tracking-wider mb-1">Load</p>
                <p className={`text-xl font-mono font-extrabold ${efficiencyCalc.loadPct > 115 ? 'text-accent-red'
                    : efficiencyCalc.loadPct > 100 ? 'text-accent-amber'
                      : 'text-violet-600'
                  }`}>{efficiencyCalc.loadPct.toFixed(1)}<span className="text-xs">%</span></p>
              </div>
              
              {/* ROI block 1 */}
              <div className="p-3 bg-surface rounded-xl border border-border text-center flex flex-col justify-center h-full">
                <p className="text-[10px] text-text-muted uppercase font-bold tracking-tight mb-1">Energy Saved/Yr</p>
                <p className="text-xl font-extrabold text-accent-green scada-number">
                  {roiCalc ? roiCalc.energySaved.toFixed(0) : '--'} <span className="text-xs text-text-muted">kWh</span>
                </p>
              </div>
              {/* ROI block 2 */}
              <div className="p-3 bg-surface rounded-xl border border-border text-center flex flex-col justify-center h-full">
                <p className="text-[10px] text-text-muted uppercase font-bold tracking-tight mb-1">Cost Saved/Yr</p>
                <p className="text-xl font-extrabold text-emerald-600 scada-number">
                  {roiCalc ? `₹${roiCalc.costSaved.toFixed(0)}` : '--'}
                </p>
              </div>
              {/* ROI block 3 */}
              <div className="p-3 bg-surface rounded-xl border border-border text-center flex flex-col justify-center h-full">
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
