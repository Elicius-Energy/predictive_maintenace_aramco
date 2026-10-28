import React, { useState, useEffect } from 'react';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import {
  Calculator,
  TrendingUp,
  Zap,
  DollarSign,
  Clock,
  Sparkles,
  Globe,
  RefreshCw,
  AlertTriangle,
  CheckCircle2,
  ExternalLink,
  ShieldCheck,
  Leaf
} from 'lucide-react';

interface SmartRoiSectionProps {
  deviceId: string;
}

export const SmartRoiSection: React.FC<SmartRoiSectionProps> = ({ deviceId }) => {
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [roiData, setRoiData] = useState<any>(null);

  // Subjective user inputs
  const [selectedPresetId, setSelectedPresetId] = useState<string>('right_size_ie4');
  const [motorInvestment, setMotorInvestment] = useState<number>(55000);
  const [installationCost, setInstallationCost] = useState<number>(5000);
  const [tariff, setTariff] = useState<number>(10.0);
  const [annualHours, setAnnualHours] = useState<number>(4500);
  const [candidateEff, setCandidateEff] = useState<number>(94.5);
  const [candidateKw, setCandidateKw] = useState<number>(22.0);

  // Live calculated ROI
  const [calculatedRoi, setCalculatedRoi] = useState<any>(null);
  const [calcLoading, setCalcLoading] = useState<boolean>(false);

  // AI & Web Search State
  const [aiQuery, setAiQuery] = useState<string>('');
  const [includeWebSearch, setIncludeWebSearch] = useState<boolean>(true);
  const [aiLoading, setAiLoading] = useState<boolean>(false);
  const [aiReport, setAiReport] = useState<string | null>(null);
  const [aiSources, setAiSources] = useState<any[]>([]);
  const [aiModelUsed, setAiModelUsed] = useState<string>('gpt-5.6-luna');

  // Fetch initial smart ROI context on device change
  const fetchSmartRoiContext = async () => {
    if (!deviceId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await axios.get(`/api/devices/${deviceId}/smart-roi`, { withCredentials: true });
      const data = res.data;
      setRoiData(data);

      const defs = data.default_subjective_inputs || {};
      setSelectedPresetId(defs.selected_preset_id || 'ie4_upgrade');
      setMotorInvestment(defs.motor_investment || 55000);
      setInstallationCost(defs.installation_cost || 5000);
      setTariff(defs.electricity_tariff || 10.0);
      setAnnualHours(defs.annual_operating_hours || 4500);
      setCandidateEff(defs.candidate_efficiency_pct || 94.5);
      setCandidateKw(defs.candidate_rating_kw || data.device?.motor_rating_kw || 22.0);

      setCalculatedRoi(data.initial_calculated_roi);
    } catch (err: any) {
      console.error('Failed to load smart ROI context:', err);
      setError(err.response?.data?.detail || 'Unable to load smart ROI telemetry analysis.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSmartRoiContext();
    setAiReport(null);
    setAiSources([]);
  }, [deviceId]);

  // Recalculate ROI whenever subjective inputs change (debounced)
  useEffect(() => {
    if (!roiData) return;
    const timer = setTimeout(async () => {
      setCalcLoading(true);
      try {
        const payload = {
          avg_kw: roiData.telemetry_metrics?.avg_kw || 4.72,
          current_eff: roiData.device?.rated_efficiency_pct || 90.0,
          candidate_eff: candidateEff,
          candidate_kw: candidateKw,
          rated_kw: roiData.device?.motor_rating_kw || 22.0,
          annual_hours: annualHours,
          tariff: tariff,
          motor_investment: motorInvestment,
          installation_cost: installationCost,
        };
        const res = await axios.post(`/api/devices/${deviceId}/smart-roi-calculate`, payload, {
          withCredentials: true,
        });
        setCalculatedRoi(res.data);
      } catch (e) {
        console.error('Instant recalculation error:', e);
      } finally {
        setCalcLoading(false);
      }
    }, 200);

    return () => clearTimeout(timer);
  }, [motorInvestment, installationCost, tariff, annualHours, candidateEff, candidateKw]);

  // Select a preset scenario
  const handleSelectPreset = (preset: any) => {
    setSelectedPresetId(preset.id);
    setCandidateEff(preset.candidate_efficiency_pct);
    setCandidateKw(preset.candidate_rating_kw);
    setMotorInvestment(preset.estimated_investment);
    setInstallationCost(preset.installation_cost);
  };

  // Run AI Advisor with Web Search
  const handleRunAiConsult = async (customQuery?: string) => {
    if (!deviceId) return;
    setAiLoading(true);
    const q = customQuery !== undefined ? customQuery : aiQuery;
    try {
      const payload = {
        query: q,
        inputs: {
          motor_investment: motorInvestment,
          installation_cost: installationCost,
          electricity_tariff: tariff,
          annual_operating_hours: annualHours,
          candidate_efficiency_pct: candidateEff,
          candidate_rating_kw: candidateKw,
          selected_preset_id: selectedPresetId,
        },
        include_web_search: includeWebSearch,
      };
      const res = await axios.post(`/api/devices/${deviceId}/smart-roi-ai`, payload, {
        withCredentials: true,
      });
      setAiReport(res.data.analysis);
      setAiSources(res.data.sources || []);
      if (res.data.model_used) {
        setAiModelUsed(res.data.model_used);
      }
      if (res.data.calculated_roi) {
        setCalculatedRoi(res.data.calculated_roi);
      }
    } catch (err: any) {
      console.error('AI consult failed:', err);
      setAiReport(`AI Advisory Consultation encountered an issue: ${err.response?.data?.detail || err.message}`);
    } finally {
      setAiLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="mt-8 bg-white p-6 rounded-2xl border border-slate-200 shadow-xs flex items-center justify-center gap-3 py-12 text-slate-500">
        <RefreshCw className="w-5 h-5 animate-spin text-[#1F3A8A]" />
        <span className="text-sm font-semibold">Analyzing telemetry and compiling Smart Motor ROI Intelligence...</span>
      </div>
    );
  }

  if (error || !roiData) {
    return (
      <div className="mt-8 bg-amber-50 p-6 rounded-2xl border border-amber-200 text-amber-800 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0" />
          <span className="text-sm font-medium">{error || 'Telemetry data insufficient for Smart ROI calculation.'}</span>
        </div>
        <button
          onClick={fetchSmartRoiContext}
          className="px-3 py-1.5 bg-amber-600 text-white rounded-lg text-xs font-semibold hover:bg-amber-700 cursor-pointer"
        >
          Retry
        </button>
      </div>
    );
  }

  const { device, telemetry_metrics, presets } = roiData;
  const isUnderloaded = (telemetry_metrics?.loading_pct || 100) < 45.0;

  return (
    <div className="mt-8 bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
      
      {/* ── SECTION HEADER ────────────────────────────────────────────────── */}
      <div className="p-6 bg-gradient-to-r from-[#0F172A] via-[#1E293B] to-[#1F3A8A] text-white">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="px-2.5 py-0.5 rounded-full text-[10px] font-extrabold uppercase tracking-wider bg-blue-500/30 text-blue-200 border border-blue-400/30">
                Automated Telemetry Intelligence
              </span>
              <span className="text-xs text-slate-300 font-medium">
                {device?.motor_make} • {device?.motor_rating_kw} kW Motor
              </span>
            </div>
            <h2 className="text-xl font-extrabold tracking-tight mt-1 text-white flex items-center gap-2">
              <Calculator className="w-5 h-5 text-blue-300" />
              Smart Motor ROI & Energy Optimization
            </h2>
            <p className="text-xs text-slate-300 mt-1 max-w-2xl">
              Calculates financial payback by automatically integrating measured telemetry (load factor, operating duty, power factor) and asking only for plant-subjective procurement costs.
            </p>
          </div>

          {/* Quick Refresh */}
          <button
            onClick={fetchSmartRoiContext}
            title="Refresh Telemetry Context"
            className="self-start md:self-auto flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/10 hover:bg-white/20 text-xs font-semibold text-white transition-colors cursor-pointer"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Reload Telemetry</span>
          </button>
        </div>

        {/* ── AUTOMATIC TELEMETRY BADGES (What the system already extracted) ─ */}
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-2.5 mt-5 pt-4 border-t border-white/10 text-xs">
          <div className="bg-white/5 rounded-xl p-2.5 border border-white/10">
            <span className="text-[11px] text-slate-400 block font-medium">Measured Power</span>
            <span className="text-sm font-bold text-white">{telemetry_metrics?.avg_kw} kW</span>
            <span className="text-[10px] text-slate-400 block">Peak: {telemetry_metrics?.max_kw} kW</span>
          </div>
          <div className="bg-white/5 rounded-xl p-2.5 border border-white/10">
            <span className="text-[11px] text-slate-400 block font-medium">Motor Loading</span>
            <span className={`text-sm font-bold ${isUnderloaded ? 'text-amber-300' : 'text-emerald-300'}`}>
              {telemetry_metrics?.loading_pct}%
            </span>
            <span className="text-[10px] text-slate-400 block">{telemetry_metrics?.loading_status === 'severely_underloaded' ? 'Underloaded' : 'Normal'}</span>
          </div>
          <div className="bg-white/5 rounded-xl p-2.5 border border-white/10">
            <span className="text-[11px] text-slate-400 block font-medium">Duty Cycle</span>
            <span className="text-sm font-bold text-white">{telemetry_metrics?.duty_pct}% Run</span>
            <span className="text-[10px] text-slate-400 block">~{telemetry_metrics?.projected_annual_loaded_hours?.toLocaleString()} hrs/yr</span>
          </div>
          <div className="bg-white/5 rounded-xl p-2.5 border border-white/10">
            <span className="text-[11px] text-slate-400 block font-medium">Power Factor</span>
            <span className="text-sm font-bold text-emerald-300">{telemetry_metrics?.weighted_pf}</span>
            <span className="text-[10px] text-slate-400 block">Weighted PF</span>
          </div>
          <div className="bg-white/5 rounded-xl p-2.5 border border-white/10">
            <span className="text-[11px] text-slate-400 block font-medium">Current Efficiency</span>
            <span className="text-sm font-bold text-white">{device?.rated_efficiency_pct}%</span>
            <span className="text-[10px] text-slate-400 block">IE2 Baseline</span>
          </div>
          <div className="bg-white/5 rounded-xl p-2.5 border border-white/10">
            <span className="text-[11px] text-slate-400 block font-medium">Application</span>
            <span className="text-sm font-bold text-white truncate block">{device?.machine_name || 'Air Compressor'}</span>
            <span className="text-[10px] text-slate-400 block truncate">{device?.location || 'Plant Floor'}</span>
          </div>
        </div>

        {/* Highlight Banner if Severely Underloaded */}
        {isUnderloaded && (
          <div className="mt-3 p-3 bg-amber-500/20 border border-amber-400/40 rounded-xl flex items-start gap-2 text-xs text-amber-200">
            <AlertTriangle className="w-4 h-4 text-amber-300 shrink-0 mt-0.5" />
            <div>
              <span className="font-bold text-amber-100">Right-Sizing Opportunity Detected: </span>
              {telemetry_metrics?.loading_note}
            </div>
          </div>
        )}
      </div>

      <div className="p-6 space-y-6">
        
        {/* ── STEP 1: ONE-CLICK UPGRADE PRESETS ──────────────────────────── */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <label className="text-xs font-bold uppercase tracking-wider text-slate-700 flex items-center gap-1.5">
              <span>1. Choose Proposed Upgrade Scenario</span>
              <span className="text-[11px] font-normal text-slate-500 normal-case">(Click any preset to auto-populate standard parameters)</span>
            </label>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {presets?.map((preset: any) => {
              const isSelected = selectedPresetId === preset.id;
              return (
                <div
                  key={preset.id}
                  onClick={() => handleSelectPreset(preset)}
                  className={`relative p-4 rounded-xl border-2 transition-all cursor-pointer ${
                    isSelected
                      ? 'border-[#1F3A8A] bg-blue-50/50 shadow-sm ring-1 ring-[#1F3A8A]'
                      : 'border-slate-200 hover:border-slate-300 bg-white hover:bg-slate-50/50'
                  }`}
                >
                  {preset.recommended && (
                    <span className="absolute -top-2.5 right-3 px-2 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-emerald-600 text-white shadow-xs">
                      ★ Recommended ROI
                    </span>
                  )}
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="font-bold text-sm text-slate-900">{preset.name}</span>
                    <span className="text-xs font-extrabold text-[#1F3A8A]">
                      {preset.candidate_efficiency_pct}% Eff
                    </span>
                  </div>
                  <p className="text-xs text-slate-500 mb-3 leading-relaxed">{preset.description}</p>
                  <div className="pt-2 border-t border-slate-200/80 flex items-center justify-between text-xs">
                    <span className="text-slate-500">Est. Investment:</span>
                    <span className="font-bold text-slate-800">₹{preset.estimated_investment?.toLocaleString()}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* ── STEP 2: SUBJECTIVE USER INPUTS ─────────────────────────────── */}
        <div className="bg-slate-50 p-4 rounded-xl border border-slate-200">
          <div className="flex items-center justify-between mb-3">
            <div>
              <span className="text-xs font-bold uppercase tracking-wider text-slate-700">
                2. Subjective Parameters (Customize for your Plant)
              </span>
              <p className="text-xs text-slate-500 mt-0.5">
                The values below are prefilled with telemetry projections and market standards. Adjust them if your quotation or contract differs:
              </p>
            </div>
            {calcLoading && (
              <span className="flex items-center gap-1 text-[11px] font-semibold text-blue-600">
                <RefreshCw className="w-3 h-3 animate-spin" /> Recalculating...
              </span>
            )}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3 text-xs">
            {/* 1. Motor Purchase Cost */}
            <div>
              <label className="block font-semibold text-slate-700 mb-1">
                Motor Investment (₹)
              </label>
              <input
                type="number"
                step="1000"
                value={motorInvestment}
                onChange={(e) => setMotorInvestment(Math.max(0, parseFloat(e.target.value) || 0))}
                className="w-full bg-white border border-slate-300 rounded-lg p-2 font-semibold text-slate-800 focus:border-[#1F3A8A] focus:outline-hidden"
              />
              <span className="text-[10px] text-slate-400 mt-0.5 block">Purchase quotation</span>
            </div>

            {/* 2. Installation & Retrofit Cost */}
            <div>
              <label className="block font-semibold text-slate-700 mb-1">
                Installation Cost (₹)
              </label>
              <input
                type="number"
                step="500"
                value={installationCost}
                onChange={(e) => setInstallationCost(Math.max(0, parseFloat(e.target.value) || 0))}
                className="w-full bg-white border border-slate-300 rounded-lg p-2 font-semibold text-slate-800 focus:border-[#1F3A8A] focus:outline-hidden"
              />
              <span className="text-[10px] text-slate-400 mt-0.5 block">Mounting, cabling, labor</span>
            </div>

            {/* 3. Electricity Tariff */}
            <div>
              <label className="block font-semibold text-slate-700 mb-1">
                Electricity Tariff (₹/kWh)
              </label>
              <input
                type="number"
                step="0.1"
                value={tariff}
                onChange={(e) => setTariff(Math.max(0, parseFloat(e.target.value) || 0))}
                className="w-full bg-white border border-slate-300 rounded-lg p-2 font-semibold text-slate-800 focus:border-[#1F3A8A] focus:outline-hidden"
              />
              <span className="text-[10px] text-slate-400 mt-0.5 block">HT Industrial tariff</span>
            </div>

            {/* 4. Annual Operating Hours */}
            <div>
              <label className="block font-semibold text-slate-700 mb-1">
                Operating Hours (hrs/yr)
              </label>
              <input
                type="number"
                step="100"
                value={annualHours}
                onChange={(e) => setAnnualHours(Math.max(0, parseFloat(e.target.value) || 0))}
                className="w-full bg-white border border-slate-300 rounded-lg p-2 font-semibold text-slate-800 focus:border-[#1F3A8A] focus:outline-hidden"
              />
              <span className="text-[10px] text-slate-400 mt-0.5 block">Extrapolated from duty</span>
            </div>

            {/* 5. Target Replacement Efficiency */}
            <div>
              <label className="block font-semibold text-slate-700 mb-1">
                Target Efficiency (%)
              </label>
              <input
                type="number"
                step="0.1"
                min="50"
                max="99"
                value={candidateEff}
                onChange={(e) => setCandidateEff(Math.min(99, Math.max(50, parseFloat(e.target.value) || 90)))}
                className="w-full bg-white border border-slate-300 rounded-lg p-2 font-semibold text-[#1F3A8A] focus:border-[#1F3A8A] focus:outline-hidden"
              />
              <span className="text-[10px] text-slate-400 mt-0.5 block">IE3 (~93%) or IE4 (~94.5%)</span>
            </div>
          </div>
        </div>

        {/* ── STEP 3: INSTANT LIVE FINANCIAL & ENERGY METRICS ────────────── */}
        <div>
          <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-3">
            3. Instant Financial & Energy Return Summary
          </label>

          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            
            {/* 1. Annual Savings */}
            <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl">
              <div className="flex items-center gap-1.5 text-emerald-800 text-xs font-semibold mb-1">
                <DollarSign className="w-4 h-4 text-emerald-600" />
                <span>Annual Savings</span>
              </div>
              <div className="text-xl font-extrabold text-emerald-700">
                ₹{calculatedRoi?.annual_saving_cost?.toLocaleString() || '0'}
              </div>
              <span className="text-[10px] text-emerald-600/90 font-medium">per year</span>
            </div>

            {/* 2. Simple Payback */}
            <div className="p-4 bg-blue-50 border border-blue-200 rounded-xl">
              <div className="flex items-center gap-1.5 text-blue-900 text-xs font-semibold mb-1">
                <Clock className="w-4 h-4 text-[#1F3A8A]" />
                <span>Simple Payback</span>
              </div>
              <div className="text-xl font-extrabold text-[#1F3A8A]">
                {calculatedRoi?.simple_payback_years ? `${calculatedRoi.simple_payback_years} Yrs` : '--'}
              </div>
              <span className="text-[10px] text-blue-600 font-medium">
                {calculatedRoi?.simple_payback_months ? `~${calculatedRoi.simple_payback_months} Months` : 'No saving'}
              </span>
            </div>

            {/* 3. Monthly Savings */}
            <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl">
              <div className="flex items-center gap-1.5 text-slate-700 text-xs font-semibold mb-1">
                <TrendingUp className="w-4 h-4 text-slate-500" />
                <span>Monthly Savings</span>
              </div>
              <div className="text-xl font-extrabold text-slate-800">
                ₹{calculatedRoi?.monthly_saving_cost?.toLocaleString() || '0'}
              </div>
              <span className="text-[10px] text-slate-500 font-medium">per month</span>
            </div>

            {/* 4. Energy Conserved */}
            <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl">
              <div className="flex items-center gap-1.5 text-slate-700 text-xs font-semibold mb-1">
                <Zap className="w-4 h-4 text-amber-500" />
                <span>Energy Saved</span>
              </div>
              <div className="text-xl font-extrabold text-slate-800">
                {calculatedRoi?.annual_saving_kwh?.toLocaleString() || '0'}
              </div>
              <span className="text-[10px] text-slate-500 font-medium">kWh / year</span>
            </div>

            {/* 5. 5-Year Net Benefit */}
            <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl">
              <div className="flex items-center gap-1.5 text-slate-700 text-xs font-semibold mb-1">
                <ShieldCheck className="w-4 h-4 text-indigo-500" />
                <span>5-Year Net Gain</span>
              </div>
              <div className={`text-xl font-extrabold ${calculatedRoi?.five_year_net_savings >= 0 ? 'text-indigo-700' : 'text-red-600'}`}>
                ₹{calculatedRoi?.five_year_net_savings?.toLocaleString() || '0'}
              </div>
              <span className="text-[10px] text-slate-500 font-medium">Net profit after Capex</span>
            </div>

            {/* 6. Carbon Emissions Avoided */}
            <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl">
              <div className="flex items-center gap-1.5 text-slate-700 text-xs font-semibold mb-1">
                <Leaf className="w-4 h-4 text-emerald-500" />
                <span>CO₂ Avoided</span>
              </div>
              <div className="text-xl font-extrabold text-emerald-700">
                {calculatedRoi?.co2_reduction_tons || '0'}
              </div>
              <span className="text-[10px] text-slate-500 font-medium">Tons CO₂ / year</span>
            </div>

          </div>
        </div>

        {/* ── STEP 4: AI CONSULTANT & WEB SEARCH MARKET INTELLIGENCE ──────── */}
        <div className="pt-6 border-t border-slate-200">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-3">
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-800 flex items-center gap-1.5">
                  <Sparkles className="w-4 h-4 text-amber-500" />
                  4. AI Executive Advisor with Live Market Web Search
                </span>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-800">
                  Web-Enabled LLM
                </span>
              </div>
              <p className="text-xs text-slate-500 mt-0.5">
                Leverages OpenAI reasoning and real-time Indian motor market pricing benchmarks (BEE subsidies, IE3/IE4 pricing) to synthesize an audit report.
              </p>
            </div>

            {/* Web search toggle */}
            <label className="flex items-center gap-2 text-xs font-semibold text-slate-700 cursor-pointer self-start sm:self-auto">
              <input
                type="checkbox"
                checked={includeWebSearch}
                onChange={(e) => setIncludeWebSearch(e.target.checked)}
                className="w-4 h-4 text-[#1F3A8A] rounded-sm focus:ring-[#1F3A8A]"
              />
              <span className="flex items-center gap-1">
                <Globe className="w-3.5 h-3.5 text-blue-600" />
                <span>Enable Web Search & Subsidies</span>
              </span>
            </label>
          </div>

          {/* Quick Query Input & Action Bar */}
          <div className="flex flex-col sm:flex-row gap-2">
            <input
              type="text"
              value={aiQuery}
              onChange={(e) => setAiQuery(e.target.value)}
              placeholder="e.g. Find current 22 kW IE4 motor prices in India and recommend right-sizing vs like-for-like..."
              className="flex-1 border border-slate-300 rounded-xl px-3.5 py-2.5 text-xs focus:border-[#1F3A8A] focus:outline-hidden"
            />
            <button
              onClick={() => handleRunAiConsult()}
              disabled={aiLoading}
              className="px-5 py-2.5 rounded-xl bg-[#1F3A8A] text-white font-bold text-xs shadow-xs hover:bg-[#1E3A8A] active:scale-98 disabled:opacity-50 flex items-center justify-center gap-2 transition-all cursor-pointer"
            >
              {aiLoading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4 text-amber-300" />}
              <span>{aiLoading ? 'Researching Market & Analyzing...' : 'Consult AI Advisor'}</span>
            </button>
          </div>

          {/* Suggested Quick Questions */}
          <div className="flex flex-wrap items-center gap-1.5 mt-2.5">
            <span className="text-[11px] font-semibold text-slate-400">Quick inquiries:</span>
            {[
              'Compare IE3 vs IE4 Payback for this motor',
              'Right-sizing 22 kW to 7.5 kW / 11 kW Analysis',
              'Tamil Nadu TEDA & BEE Energy Subsidies',
              'Does this compressor load profile justify a VFD?',
            ].map((qText) => (
              <button
                key={qText}
                onClick={() => {
                  setAiQuery(qText);
                  handleRunAiConsult(qText);
                }}
                className="px-2.5 py-1 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-[11px] font-medium transition-colors cursor-pointer"
              >
                {qText}
              </button>
            ))}
          </div>

          {/* Web Search Sources Chips (if any returned) */}
          {aiSources.length > 0 && (
            <div className="mt-3 p-3 bg-blue-50/60 rounded-xl border border-blue-200 text-xs">
              <span className="font-bold text-[#1F3A8A] block mb-1.5 flex items-center gap-1.5">
                <Globe className="w-3.5 h-3.5 text-blue-600" />
                <span>Live Market Sources Retrieved:</span>
              </span>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                {aiSources.map((src: any, idx: number) => (
                  <a
                    key={idx}
                    href={src.url}
                    target="_blank"
                    rel="noreferrer"
                    className="p-2 bg-white rounded-lg border border-blue-100 hover:border-blue-300 transition-colors flex items-start justify-between gap-2 group cursor-pointer"
                  >
                    <div>
                      <span className="font-bold text-slate-800 text-[11px] block group-hover:text-blue-600">
                        {src.title}
                      </span>
                      <p className="text-[10px] text-slate-500 line-clamp-2 mt-0.5">{src.snippet}</p>
                    </div>
                    <ExternalLink className="w-3.5 h-3.5 text-slate-400 shrink-0 mt-0.5" />
                  </a>
                ))}
              </div>
            </div>
          )}

          {/* AI Response Card */}
          {aiReport && (
            <div className="mt-4 p-5 bg-gradient-to-br from-slate-50 to-blue-50/40 rounded-xl border border-slate-200 text-xs text-slate-800 shadow-2xs leading-relaxed animate-in fade-in">
              <div className="flex items-center justify-between pb-3 mb-3 border-b border-slate-200">
                <span className="font-bold text-slate-900 flex items-center gap-1.5 text-sm">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                  <span>AI Executive Consultation & Engineering Appraisal</span>
                </span>
                <span className="text-[11px] font-semibold text-slate-400">
                  Model: {aiModelUsed} with Live Web Grounding
                </span>
              </div>
              <div className="prose prose-sm max-w-none prose-slate text-xs leading-relaxed space-y-2">
                <ReactMarkdown>{aiReport}</ReactMarkdown>
              </div>
            </div>
          )}
        </div>

      </div>
    </div>
  );
};
export default SmartRoiSection;
