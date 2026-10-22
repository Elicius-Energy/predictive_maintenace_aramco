import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useDevice } from '../contexts/DeviceContext';
import {
  Activity, Zap, Gauge, Flame, Clock, RefreshCw, AlertTriangle,
  CheckCircle2, WifiOff, AlertCircle
} from 'lucide-react';
import {
  ResponsiveContainer, LineChart, Line, BarChart, Bar,
  XAxis, YAxis, Tooltip, CartesianGrid, ReferenceArea,
  PieChart, Pie, Cell
} from 'recharts';

export const Dashboard: React.FC = () => {
  const { devices, selectedDevice, selectedDeviceId, getStatusColor } = useDevice();
  
  // Live cards data
  const [liveData, setLiveData] = useState<any>(null);

  const getIstDateAndTime = (d: Date) => {
    const formatter = new Intl.DateTimeFormat('en-CA', {
      timeZone: 'Asia/Kolkata',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    });
    const parts = formatter.formatToParts(d);
    const getPart = (type: string) => parts.find(p => p.type === type)?.value || '';
    return {
      date: `${getPart('year')}-${getPart('month')}-${getPart('day')}`,
      time: `${getPart('hour')}:${getPart('minute')}`,
    };
  };

  const toIsoUtc = (dateStr: string, timeStr: string) => {
    // Treat dateStr ('YYYY-MM-DD') and timeStr ('HH:mm') strictly as IST (UTC+5:30)
    const d = new Date(`${dateStr}T${timeStr}:00+05:30`);
    return isNaN(d.getTime()) ? new Date().toISOString() : d.toISOString();
  };

  // Adaptive IST Time / Date Formatter for X-Axis
  const formatTimeTick = (iso: string) => {
    if (!iso) return '';
    try {
      const d = new Date(iso);
      if (analysisPreset === '7d') {
        return d.toLocaleDateString('en-IN', {
          timeZone: 'Asia/Kolkata',
          day: 'numeric',
          month: 'short',
        });
      }
      if (analysisPreset === '24h') {
        return d.toLocaleDateString('en-IN', {
          timeZone: 'Asia/Kolkata',
          day: 'numeric',
          month: 'short',
        }) + ' ' + d.toLocaleTimeString('en-IN', {
          timeZone: 'Asia/Kolkata',
          hour: '2-digit',
          minute: '2-digit',
          hour12: false,
        });
      }
      return d.toLocaleTimeString('en-IN', {
        timeZone: 'Asia/Kolkata',
        hour: '2-digit',
        minute: '2-digit',
        hour12: false,
      });
    } catch {
      return '';
    }
  };

  // Full IST Date-Time (e.g. 15 Oct, 17:42:10 IST)
  const formatIstDateTime = (iso: string) => {
    if (!iso) return '';
    try {
      const d = new Date(iso);
      return d.toLocaleString('en-IN', {
        timeZone: 'Asia/Kolkata',
        day: '2-digit',
        month: 'short',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false,
      }) + ' IST';
    } catch {
      return iso;
    }
  };

  // Short IST Time only (e.g. 17:42 IST)
  const formatIstTimeOnly = (iso: string) => {
    if (!iso) return '';
    try {
      const d = new Date(iso);
      return d.toLocaleTimeString('en-IN', {
        timeZone: 'Asia/Kolkata',
        hour: '2-digit',
        minute: '2-digit',
        hour12: false,
      }) + ' IST';
    } catch {
      return iso;
    }
  };

  // Trend chart filters
  const [analysisPreset, setAnalysisPreset] = useState<'1h' | '8h' | '24h' | '7d' | 'custom'>('1h');
  const [startDate, setStartDate] = useState(() => getIstDateAndTime(new Date(Date.now() - 1 * 3600 * 1000)).date);
  const [startTime, setStartTime] = useState(() => getIstDateAndTime(new Date(Date.now() - 1 * 3600 * 1000)).time);
  const [endDate, setEndDate] = useState(() => getIstDateAndTime(new Date()).date);
  const [endTime, setEndTime] = useState(() => getIstDateAndTime(new Date()).time);

  const [interval, setIntervalVal] = useState<'1-minute' | '5-minute' | '1-hour'>('1-minute');
  // Default active trend charts: open Current, Active Power, and Voltage by default
  const [activeParams, setActiveParams] = useState<Record<string, boolean>>({
    kw: true,
    current: true,
    voltage: true,
    kwh: false,
    pf: false,
    freq: false,
  });

  // Query results
  const [summary, setSummary] = useState<any>(null);
  const [trends, setTrends] = useState<any[]>([]);
  const [alertWindows, setAlertWindows] = useState<any[]>([]);
  const [chartHint, setChartHint] = useState<string | null>(null);
  const [trendsLoading, setTrendsLoading] = useState(false);

  // 1. Polling for Live Cards (every 5 seconds)
  const fetchLive = async () => {
    if (!selectedDeviceId) return;
    try {
      const res = await axios.get(`/api/devices/${selectedDeviceId}/live`, { withCredentials: true });
      setLiveData(res.data);
    } catch (err) {
      console.error('Error fetching live data:', err);
    }
  };

  useEffect(() => {
    fetchLive();
    const timer = setInterval(fetchLive, 5000);
    return () => clearInterval(timer);
  }, [selectedDeviceId]);

  // 2. Compute date window from presets
  const handlePresetChange = (preset: '1h' | '8h' | '24h' | '7d') => {
    setAnalysisPreset(preset);
    const now = new Date();
    const hours = preset === '1h' ? 1 : preset === '8h' ? 8 : preset === '24h' ? 24 : 168;
    const start = new Date(now.getTime() - hours * 3600 * 1000);

    const sFmt = getIstDateAndTime(start);
    const eFmt = getIstDateAndTime(now);

    setStartDate(sFmt.date);
    setStartTime(sFmt.time);
    setEndDate(eFmt.date);
    setEndTime(eFmt.time);

    // Choose appropriate default interval
    if (preset === '1h') setIntervalVal('1-minute');
    else if (preset === '8h' || preset === '24h') setIntervalVal('5-minute');
    else setIntervalVal('1-hour');
  };

  // 3. Fetch Trend Charts & Summary without screen blinking
  const fetchTrendsAndSummary = async (isBackground = false) => {
    if (!selectedDeviceId) return;
    if (!isBackground && trends.length === 0) {
      setTrendsLoading(true);
    }
    setChartHint(null);

    const startIso = toIsoUtc(startDate, startTime);
    const endIso = toIsoUtc(endDate, endTime);

    try {
      const [sumRes, trRes] = await Promise.all([
        axios.get(`/api/devices/${selectedDeviceId}/summary?start_time=${startIso}&end_time=${endIso}`, { withCredentials: true }),
        axios.get(`/api/devices/${selectedDeviceId}/trends?start_time=${startIso}&end_time=${endIso}&interval=${interval}`, { withCredentials: true }),
      ]);

      setSummary(sumRes.data);
      if (trRes.data.hint) {
        setChartHint(trRes.data.hint);
        setTrends([]);
      } else {
        setTrends(trRes.data.points || []);
        setAlertWindows(trRes.data.alert_windows || []);
      }
    } catch (err) {
      console.error('Error fetching trends:', err);
    } finally {
      setTrendsLoading(false);
    }
  };

  useEffect(() => {
    fetchTrendsAndSummary(false);
    // Silent periodic refresh every 10 seconds: keeps trend points live without full page flicker
    const timer = setInterval(() => fetchTrendsAndSummary(true), 10000);
    return () => clearInterval(timer);
  }, [selectedDeviceId, startDate, startTime, endDate, endTime, interval]);

  const toggleParam = (key: string) => {
    setActiveParams((prev: Record<string, boolean>) => ({ ...prev, [key]: !prev[key] }));
  };

  const handleAcknowledge = async (alertId: number) => {
    try {
      await axios.post(`/api/devices/${selectedDeviceId}/alerts/${alertId}/acknowledge`, {}, { withCredentials: true });
      fetchLive();
    } catch (err) {
      console.error('Error acknowledging alert:', err);
    }
  };

  const overallStatus = liveData?.status || selectedDevice?.status || 'Normal';
  const statusTheme = getStatusColor(overallStatus);

  if (devices.length === 0) {
    return (
      <div className="max-w-4xl mx-auto py-16 px-4 text-center">
        <div className="bg-white rounded-2xl border border-slate-200 p-10 shadow-xs max-w-lg mx-auto">
          <div className="w-16 h-16 rounded-2xl bg-blue-50 text-[#1F3A8A] flex items-center justify-center mx-auto mb-4">
            <Zap className="w-8 h-8" />
          </div>
          <h2 className="text-xl font-bold text-slate-800">No Devices Registered</h2>
          <p className="text-sm text-slate-500 mt-2 mb-6">
            Register your IoT energy meter hardware ID in Configuration to start receiving live telemetry, tracking power parameters, and generating reports.
          </p>
          <a
            href="/configuration"
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-[#1F3A8A] text-white font-semibold text-sm hover:bg-[#1E3A8A] transition-colors"
          >
            Go to Configuration
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="dashboard-page max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8 space-y-6">

      {/* ── 1. STATUS BANNER ────────────────────────────────────────────── */}
      <div className={`dashboard-status p-4 sm:p-5 rounded-2xl border ${statusTheme.border} ${statusTheme.bg} shadow-xs transition-all`}>
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          
          <div className="flex items-center gap-3.5">
            <div className={`w-12 h-12 rounded-xl flex items-center justify-center shrink-0 ${
              overallStatus === 'Normal' ? 'bg-emerald-600 text-white' :
              overallStatus === 'Warning' ? 'bg-amber-500 text-white' : 'bg-red-600 text-white'
            }`}>
              {overallStatus === 'Normal' && <CheckCircle2 className="w-7 h-7" />}
              {overallStatus === 'Warning' && <AlertTriangle className="w-7 h-7" />}
              {(overallStatus === 'Incorrect connection' || overallStatus === 'Disconnected') && <AlertCircle className="w-7 h-7" />}
              {overallStatus === 'Communication failure' && <WifiOff className="w-7 h-7" />}
            </div>

            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Overall Status</span>
                <span className={`text-base font-extrabold ${statusTheme.text}`}>{overallStatus}</span>
              </div>
              <div className="text-xs text-slate-500 font-medium mt-0.5">
                Last data received: <span className="font-semibold text-slate-700">{liveData?.last_seen_str || 'connecting...'}</span>
              </div>
            </div>
          </div>

          {/* Per-Phase Diagnostic Chips */}
          <div className="flex flex-wrap items-center gap-2">
            {[
              { id: 'ct_l1', label: 'CT L1' },
              { id: 'ct_l2', label: 'CT L2' },
              { id: 'ct_l3', label: 'CT L3' },
              { id: 'vclip_l1', label: 'Clip L1' },
              { id: 'vclip_l2', label: 'Clip L2' },
              { id: 'vclip_l3', label: 'Clip L3' }
            ].map((chip) => {
              const chipStatus = liveData?.status_detail?.[chip.id] || 'Normal';
              const chipDetail = liveData?.status_detail?.[`${chip.id}_detail`];
              const chipColor = getStatusColor(chipStatus);
              return (
                <div
                  key={chip.id}
                  title={chipDetail || `${chip.label}: ${chipStatus}`}
                  className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg border ${chipColor.border} bg-white text-xs font-semibold shadow-2xs`}
                >
                  <span className={`w-2 h-2 rounded-full ${chipColor.dot}`} />
                  <span className="text-slate-700">{chip.label}:</span>
                  <span className={chipColor.text}>{chipStatus}</span>
                </div>
              );
            })}
          </div>

        </div>

        {/* Compact Open Alerts List with Acknowledge Button */}
        {liveData?.open_alerts && liveData.open_alerts.length > 0 && (
          <div className="mt-4 pt-4 border-t border-slate-200/60 space-y-2">
            {liveData.open_alerts.map((alt: any) => (
              <div
                key={alt.id}
                className={`flex items-center justify-between p-2.5 bg-white/90 rounded-xl border text-xs ${
                  alt.severity === 'Warning' ? 'border-amber-200 text-amber-900' : 'border-red-200 text-red-900'
                }`}
              >
                <div className="flex items-center gap-2">
                  {alt.severity === 'Warning' ? (
                    <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
                  ) : (
                    <AlertCircle className="w-4 h-4 text-red-600 shrink-0" />
                  )}
                  <span className="font-bold">{alt.phase ? `[${alt.phase}] ` : ''}{alt.type.replace(/_/g, ' ').toUpperCase()}:</span>
                  <span className="text-slate-700">{alt.details?.reason || alt.details?.message || alt.severity}</span>
                  <span className="text-[11px] text-slate-400">({formatIstTimeOnly(alt.started_at)})</span>
                </div>
                <button
                  onClick={() => handleAcknowledge(alt.id)}
                  className={`px-2.5 py-1 text-white font-medium rounded-md text-[11px] transition-colors cursor-pointer ${
                    alt.severity === 'Warning' ? 'bg-amber-600 hover:bg-amber-700' : 'bg-red-600 hover:bg-red-700'
                  }`}
                >
                  Acknowledge
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ── 2. SIX LIVE CARDS ───────────────────────────────────────────── */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 sm:gap-4">
        
        {/* Card 1: Line-to-Line Voltage */}
        <div className="metric-card metric-voltage bg-white p-4 rounded-2xl border border-slate-200 shadow-xs hover:border-[#1F3A8A] transition-colors">
          <div className="flex items-center justify-between text-slate-500 mb-1">
            <span className="text-xs font-bold uppercase tracking-wider">Voltage (Line-Line)</span>
            <Activity className="w-4 h-4 text-[#1F3A8A]" />
          </div>
          <div className="flex items-baseline gap-1">
            <span className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
              {liveData?.voltage?.vll_avg ?? liveData?.voltage?.avg ?? '--'}
            </span>
            <span className="text-xs font-semibold text-slate-500">V</span>
          </div>
          <div className="mt-2 pt-2 border-t border-slate-100 flex justify-between text-[11px] text-slate-500 font-medium">
            <span>V12: <strong className="text-slate-700">{liveData?.voltage?.v12 ?? '-'}</strong></span>
            <span>V23: <strong className="text-slate-700">{liveData?.voltage?.v23 ?? '-'}</strong></span>
            <span>V31: <strong className="text-slate-700">{liveData?.voltage?.v31 ?? '-'}</strong></span>
          </div>
        </div>

        {/* Card 2: Current */}
        <div className="metric-card metric-current bg-white p-4 rounded-2xl border border-slate-200 shadow-xs hover:border-[#1F3A8A] transition-colors">
          <div className="flex items-center justify-between text-slate-500 mb-1">
            <span className="text-xs font-bold uppercase tracking-wider">Current</span>
            <Zap className="w-4 h-4 text-[#1F3A8A]" />
          </div>
          <div className="flex items-baseline gap-1">
            <span className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
              {liveData?.current?.avg ?? '--'}
            </span>
            <span className="text-xs font-semibold text-slate-500">A</span>
          </div>
          <div className="mt-2 pt-2 border-t border-slate-100 flex justify-between text-[11px] text-slate-500 font-medium">
            <span>I1: {liveData?.current?.i1 ?? '-'}</span>
            <span>I2: {liveData?.current?.i2 ?? '-'}</span>
            <span>I3: {liveData?.current?.i3 ?? '-'}</span>
          </div>
        </div>

        {/* Card 3: Power */}
        <div className="metric-card metric-power bg-white p-4 rounded-2xl border border-slate-200 shadow-xs hover:border-[#1F3A8A] transition-colors">
          <div className="flex items-center justify-between text-slate-500 mb-1">
            <span className="text-xs font-bold uppercase tracking-wider">Active Power</span>
            <Flame className="w-4 h-4 text-orange-500" />
          </div>
          <div className="flex items-baseline gap-1">
            <span className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
              {liveData?.power?.total ?? '--'}
            </span>
            <span className="text-xs font-semibold text-slate-500">kW</span>
          </div>
          <div className="mt-2 pt-2 border-t border-slate-100 flex justify-between text-[11px] text-slate-500 font-medium">
            <span>P1: {liveData?.power?.kw1 ?? '-'}</span>
            <span>P2: {liveData?.power?.kw2 ?? '-'}</span>
            <span>P3: {liveData?.power?.kw3 ?? '-'}</span>
          </div>
        </div>

        {/* Card 4: Energy */}
        <div className="metric-card metric-energy bg-white p-4 rounded-2xl border border-slate-200 shadow-xs hover:border-[#1F3A8A] transition-colors">
          <div className="flex items-center justify-between text-slate-500 mb-1">
            <span className="text-xs font-bold uppercase tracking-wider">Energy Consumed</span>
            <Clock className="w-4 h-4 text-emerald-600" />
          </div>
          <div className="flex items-baseline gap-1">
            <span className="text-2xl sm:text-3xl font-extrabold text-emerald-700 tracking-tight">
              {liveData?.energy?.today_kwh ?? '--'}
            </span>
            <span className="text-xs font-semibold text-slate-500">kWh</span>
          </div>
          <div className="mt-2 pt-2 border-t border-slate-100 flex justify-between text-[11px] text-slate-500 font-medium">
            <span>Today's Energy</span>
            <span className="font-semibold text-slate-700">{liveData?.energy?.lifetime_kwh ?? 0} total</span>
          </div>
        </div>

        {/* Card 5: Power Factor */}
        <div className="metric-card metric-factor bg-white p-4 rounded-2xl border border-slate-200 shadow-xs hover:border-[#1F3A8A] transition-colors">
          <div className="flex items-center justify-between text-slate-500 mb-1">
            <span className="text-xs font-bold uppercase tracking-wider">Power Factor</span>
            <Gauge className="w-4 h-4 text-[#1F3A8A]" />
          </div>
          <div className="flex items-baseline gap-1">
            <span className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
              {liveData?.power_factor?.avg ?? '--'}
            </span>
            <span className="text-xs font-semibold text-slate-500">PF</span>
          </div>
          <div className="mt-2 pt-2 border-t border-slate-100 flex justify-between text-[11px] text-slate-500 font-medium">
            <span>PF1: {liveData?.power_factor?.pf1 ?? '-'}</span>
            <span>PF2: {liveData?.power_factor?.pf2 ?? '-'}</span>
            <span>PF3: {liveData?.power_factor?.pf3 ?? '-'}</span>
          </div>
        </div>

        {/* Card 6: Frequency */}
        <div className="metric-card metric-frequency bg-white p-4 rounded-2xl border border-slate-200 shadow-xs hover:border-[#1F3A8A] transition-colors">
          <div className="flex items-center justify-between text-slate-500 mb-1">
            <span className="text-xs font-bold uppercase tracking-wider">Frequency</span>
            <Activity className="w-4 h-4 text-[#1F3A8A]" />
          </div>
          <div className="flex items-baseline gap-1">
            <span className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
              {liveData?.frequency?.freq ?? '50.0'}
            </span>
            <span className="text-xs font-semibold text-slate-500">Hz</span>
          </div>
          <div className="mt-2 pt-2 border-t border-slate-100 flex justify-between text-[11px] text-slate-500 font-medium">
            <span>Grid Standard</span>
            <span className="text-emerald-600 font-semibold">50.0 Hz</span>
          </div>
        </div>

      </div>

      {/* ── 3. TREND SELECTION BAR & PERIOD SUMMARY STRIP ───────────────── */}
      <div className="dashboard-panel bg-white p-4 rounded-2xl border border-slate-200 shadow-xs space-y-4">
        
        {/* Controls Bar */}
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-4 border-b border-slate-100">
          
          {/* Quick Presets */}
          <div className="flex items-center gap-1.5 flex-wrap">
            <span className="text-xs font-bold text-slate-600 uppercase tracking-wider mr-1">Period:</span>
            {(['1h', '8h', '24h', '7d'] as const).map((p) => (
              <button
                key={p}
                onClick={() => handlePresetChange(p)}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors cursor-pointer ${
                  analysisPreset === p
                    ? 'bg-[#1F3A8A] text-white shadow-2xs'
                    : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                }`}
              >
                Last {p}
              </button>
            ))}
          </div>

          {/* Date & Time Pickers */}
          <div className="flex items-center gap-2 flex-wrap text-xs">
            <div className="flex items-center gap-1 bg-slate-50 border border-slate-300 rounded-lg px-2 py-1">
              <span className="text-slate-400 font-medium">From:</span>
              <input
                type="date"
                value={startDate}
                onChange={(e) => { setStartDate(e.target.value); setAnalysisPreset('custom'); }}
                className="bg-transparent font-medium text-slate-700 focus:outline-hidden"
              />
              <input
                type="time"
                value={startTime}
                onChange={(e) => { setStartTime(e.target.value); setAnalysisPreset('custom'); }}
                className="bg-transparent font-medium text-slate-700 focus:outline-hidden"
              />
            </div>

            <div className="flex items-center gap-1 bg-slate-50 border border-slate-300 rounded-lg px-2 py-1">
              <span className="text-slate-400 font-medium">To:</span>
              <input
                type="date"
                value={endDate}
                onChange={(e) => { setEndDate(e.target.value); setAnalysisPreset('custom'); }}
                className="bg-transparent font-medium text-slate-700 focus:outline-hidden"
              />
              <input
                type="time"
                value={endTime}
                onChange={(e) => { setEndTime(e.target.value); setAnalysisPreset('custom'); }}
                className="bg-transparent font-medium text-slate-700 focus:outline-hidden"
              />
            </div>

            {/* Interval Selector */}
            <div className="flex items-center gap-1 bg-slate-50 border border-slate-300 rounded-lg px-2 py-1">
              <span className="text-slate-400 font-medium">Interval:</span>
              <select
                value={interval}
                onChange={(e) => setIntervalVal(e.target.value as any)}
                className="bg-transparent font-semibold text-slate-700 focus:outline-hidden cursor-pointer"
              >
                <option value="1-minute">1-minute</option>
                <option value="5-minute">5-minute</option>
                <option value="1-hour">1-hour</option>
              </select>
            </div>
          </div>

        </div>

        {/* Parameter Chips */}
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs font-bold text-slate-600 uppercase tracking-wider mr-1">Parameters:</span>
          {[
            { id: 'current', label: 'Current (A)' },
            { id: 'kw', label: 'Power (kW)' },
            { id: 'kwh', label: 'Energy (kWh)' },
            { id: 'voltage', label: 'Voltage L-L (V)' },
            { id: 'pf', label: 'Power Factor' },
            { id: 'freq', label: 'Frequency (Hz)' }
          ].map((param) => (
            <button
              key={param.id}
              onClick={() => toggleParam(param.id)}
              className={`px-3 py-1 rounded-full text-xs font-semibold transition-colors cursor-pointer border ${
                  activeParams[param.id]
                  ? 'bg-gradient-to-r from-sky-100 via-indigo-50 to-violet-100 border-indigo-300 text-indigo-900 shadow-2xs'
                  : 'bg-white border-slate-200 text-slate-400 hover:border-slate-300'
              }`}
            >
              {param.label}
            </button>
          ))}
        </div>

        {/* Period Summary & Run Time vs Idle Time Doughnut */}
        {summary && (() => {
          const durationHrs = summary.duration_hours || 0.001;
          const idleHrs = summary.idle_hours ?? 0;
          const runningHrs = summary.running_hours ?? Math.max(0, durationHrs - idleHrs);
          const runningPct = summary.running_pct ?? (durationHrs > 0 ? Math.max(0, Math.min(100, Math.round(((durationHrs - idleHrs) / durationHrs) * 1000) / 10)) : 100);
          const idlePct = summary.idle_pct ?? Math.max(0, Math.round((100 - runningPct) * 10) / 10);

          const dutyData = [
            { name: 'Run Time', value: Number(runningHrs.toFixed(2)) || (idleHrs === 0 ? 1 : 0), color: '#10B981' },
            { name: 'Idle Time', value: Number(idleHrs.toFixed(2)), color: '#F59E0B' },
          ];

          return (
            <div className="summary-grid bg-slate-50 border border-slate-200 rounded-2xl p-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              
              {/* Doughnut Chart: Operating Duty (Run vs Idle) */}
            <div className="bg-white p-3.5 rounded-xl border border-emerald-100 shadow-2xs flex items-center justify-between gap-3">
                <div className="relative w-24 h-24 shrink-0 flex items-center justify-center">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={dutyData}
                        dataKey="value"
                        nameKey="name"
                        cx="50%"
                        cy="50%"
                        innerRadius={28}
                        outerRadius={44}
                        paddingAngle={3}
                        isAnimationActive={false}
                      >
                        {dutyData.map((entry, idx) => (
                          <Cell key={`duty-${idx}`} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip formatter={(val: any, name: any) => [`${val} hrs`, name]} />
                    </PieChart>
                  </ResponsiveContainer>
                  <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                    <span className="text-sm font-extrabold text-emerald-700 leading-none">{runningPct}%</span>
                    <span className="text-[9px] text-slate-400 font-bold uppercase tracking-wider mt-0.5">Run</span>
                  </div>
                </div>

                <div className="flex-1 space-y-1.5 text-xs">
                  <div className="text-[11px] font-bold uppercase tracking-wider text-slate-500">Operating Duty</div>
                  <div className="flex items-center justify-between text-slate-700">
                    <div className="flex items-center gap-1.5">
                      <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 shrink-0" />
                      <span className="font-medium text-[11px]">Run:</span>
                    </div>
                    <span className="font-extrabold text-emerald-700 text-[11px]">
                      {summary.running_time_str ? summary.running_time_str : `${runningHrs}h (${runningPct}%)`}
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-slate-700">
                    <div className="flex items-center gap-1.5">
                      <span className="w-2.5 h-2.5 rounded-full bg-amber-500 shrink-0" />
                      <span className="font-medium text-[11px]">Idle:</span>
                    </div>
                    <span className="font-extrabold text-amber-700 text-[11px]">
                      {summary.idle_time_str ? summary.idle_time_str : `${idleHrs}h (${idlePct}%)`}
                    </span>
                  </div>
                </div>
              </div>

              {/* Time Window (IST) */}
              <div className="bg-white p-3.5 rounded-xl border border-sky-100 shadow-2xs space-y-2 flex flex-col justify-center">
                <div>
                  <span className="block text-[10px] uppercase font-bold text-slate-400 tracking-wider">Start Time (IST)</span>
                  <span className="font-bold text-slate-800 text-xs">{formatIstDateTime(summary.start_time)}</span>
                </div>
                <div>
                  <span className="block text-[10px] uppercase font-bold text-slate-400 tracking-wider">End Time (IST)</span>
                  <span className="font-bold text-slate-800 text-xs">{formatIstDateTime(summary.end_time)}</span>
                </div>
              </div>

              {/* Energy & Power */}
              <div className="bg-white p-3.5 rounded-xl border border-orange-100 shadow-2xs space-y-1.5 flex flex-col justify-center text-xs">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Analysis Period</span>
                  <span className="font-extrabold text-slate-800">{summary.duration_str}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Energy Consumed</span>
                  <span className="font-extrabold text-[#1F3A8A] text-sm">{summary.energy_kwh} kWh</span>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-500 font-medium">Avg Active Power:</span>
                  <span className="font-bold text-slate-800">{summary.avg_kw} kW</span>
                </div>
              </div>

              {/* Diagnostics & Voltage */}
              <div className="bg-white p-3.5 rounded-xl border border-violet-100 shadow-2xs space-y-1.5 flex flex-col justify-center text-xs">
                <div className="flex items-center justify-between">
                  <span className="text-slate-500 font-medium">Avg Voltage (L-L):</span>
                  <span className="font-extrabold text-slate-800">{summary.avg_voltage ?? 415.0} V</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-500 font-medium">Weighted PF:</span>
                  <span className="font-extrabold text-emerald-700">{summary.weighted_pf}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-500 font-medium">Voltage Unbalance:</span>
                  <span className={`font-bold ${summary.voltage_unbalance_pct > 2.0 ? 'text-red-600' : 'text-slate-700'}`}>
                    {summary.voltage_unbalance_pct}%
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-500 font-medium">Data Completeness:</span>
                  <span className="font-semibold text-slate-700">{summary.data_completeness_pct}%</span>
                </div>
              </div>

            </div>
          );
        })()}

      </div>

      {/* ── 4. TREND CHARTS SECTION (2-Column Grid) ────────────────────── */}
      {chartHint && (
        <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl text-amber-800 text-xs font-medium flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-amber-600 shrink-0" />
          <span>{chartHint}</span>
        </div>
      )}

      {trendsLoading && trends.length === 0 ? (
        <div className="py-16 text-center text-slate-400 text-sm">
          <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-[#1F3A8A]" />
          Rendering trend charts...
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

          {/* Empty state: charts are collapsed until a parameter is clicked */}
          {!Object.values(activeParams).some(Boolean) && (
            <div className="lg:col-span-2 bg-white border border-dashed border-slate-300 rounded-2xl py-16 px-6 text-center">
              <Activity className="w-8 h-8 text-slate-300 mx-auto mb-3" />
              <p className="text-sm font-semibold text-slate-600">No parameters selected</p>
              <p className="text-xs text-slate-400 mt-1">
                Click a parameter tab above to open its trend chart.
              </p>
            </div>
          )}

          {/* Chart 1: Current Trend (3 Phases) */}
          {activeParams.current && (
            <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs">
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-700">Current Trend (3 Phases)</span>
                <div className="flex items-center gap-3 text-xs font-semibold">
                  <span className="text-red-500">• I1</span>
                  <span className="text-amber-500">• I2</span>
                  <span className="text-blue-500">• I3</span>
                </div>
              </div>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={trends}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E2E8F0" />
                    <XAxis dataKey="ts" tickFormatter={formatTimeTick} stroke="#94A3B8" fontSize={11} />
                    <YAxis stroke="#94A3B8" fontSize={11} unit=" A" />
                    <Tooltip
                      labelFormatter={(lbl) => formatIstDateTime(lbl)}
                      formatter={(val: any, name: any) => [`${val} A`, name]}
                    />
                    <Line isAnimationActive={false} type="monotone" dataKey="i1" name="I L1" stroke="#EF4444" strokeWidth={1.5} dot={false} connectNulls={true} />
                    <Line isAnimationActive={false} type="monotone" dataKey="i2" name="I L2" stroke="#F59E0B" strokeWidth={1.5} dot={false} connectNulls={true} />
                    <Line isAnimationActive={false} type="monotone" dataKey="i3" name="I L3" stroke="#3B82F6" strokeWidth={1.5} dot={false} connectNulls={true} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          {/* Chart 2: Active Power (kW) Trend */}
          {activeParams.kw && (
            <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs">
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-700">Active Power (kW)</span>
                <span className="text-xs font-semibold text-slate-500">Avg: {summary?.avg_kw ?? 0} kW</span>
              </div>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={trends}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E2E8F0" />
                    <XAxis dataKey="ts" tickFormatter={formatTimeTick} stroke="#94A3B8" fontSize={11} />
                    <YAxis stroke="#94A3B8" fontSize={11} unit=" kW" />
                    <Tooltip
                      labelFormatter={(lbl) => formatIstDateTime(lbl)}
                      formatter={(val: any) => [`${val} kW`, 'Power']}
                    />
                    {alertWindows.map((aw: any, i: number) => (
                      <ReferenceArea key={i} x1={aw.start} x2={aw.end} fill="#FEE2E2" fillOpacity={0.4} />
                    ))}
                    <Line isAnimationActive={false} type="monotone" dataKey="kw" stroke="#1F3A8A" strokeWidth={2} dot={false} connectNulls={true} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          {/* Chart 3: Interval Energy (kWh) Trend */}
          {activeParams.kwh && (
            <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs">
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-700">Interval Energy (kWh)</span>
                <span className="text-xs font-semibold text-[#1F3A8A]">Total: {summary?.energy_kwh ?? 0} kWh</span>
              </div>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={trends}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E2E8F0" />
                    <XAxis dataKey="ts" tickFormatter={formatTimeTick} stroke="#94A3B8" fontSize={11} />
                    <YAxis stroke="#94A3B8" fontSize={11} unit=" kWh" />
                    <Tooltip
                      labelFormatter={(lbl) => formatIstDateTime(lbl)}
                      formatter={(val: any) => [`${val} kWh`, 'Energy']}
                    />
                    <Bar isAnimationActive={false} dataKey="kwh" fill="#1F3A8A" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          {/* Chart 4: Line-to-Line Voltage Trend */}
          {activeParams.voltage && (
            <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs">
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-700">Line-to-Line Voltage Trend</span>
                <div className="flex items-center gap-3 text-xs font-semibold">
                  <span className="text-red-500">• V12 (L1-L2)</span>
                  <span className="text-amber-500">• V23 (L2-L3)</span>
                  <span className="text-blue-500">• V31 (L3-L1)</span>
                </div>
              </div>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={trends}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E2E8F0" />
                    <XAxis dataKey="ts" tickFormatter={formatTimeTick} stroke="#94A3B8" fontSize={11} />
                    <YAxis domain={['auto', 'auto']} stroke="#94A3B8" fontSize={11} unit=" V" />
                    <Tooltip
                      labelFormatter={(lbl) => formatIstDateTime(lbl)}
                      formatter={(val: any, name: any) => [`${val} V`, name]}
                    />
                    <Line isAnimationActive={false} type="monotone" dataKey="v12" name="V12 (L1-L2)" stroke="#EF4444" strokeWidth={1.5} dot={false} connectNulls={true} />
                    <Line isAnimationActive={false} type="monotone" dataKey="v23" name="V23 (L2-L3)" stroke="#F59E0B" strokeWidth={1.5} dot={false} connectNulls={true} />
                    <Line isAnimationActive={false} type="monotone" dataKey="v31" name="V31 (L3-L1)" stroke="#3B82F6" strokeWidth={1.5} dot={false} connectNulls={true} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          {/* Chart 5: Power Factor Trend */}
          {activeParams.pf && (
            <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs">
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-700">Power Factor Trend</span>
                <span className="text-xs font-semibold text-emerald-600">Weighted: {summary?.weighted_pf ?? 1.0}</span>
              </div>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={trends}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E2E8F0" />
                    <XAxis dataKey="ts" tickFormatter={formatTimeTick} stroke="#94A3B8" fontSize={11} />
                    <YAxis domain={[0, 1.0]} stroke="#94A3B8" fontSize={11} />
                    <Tooltip
                      labelFormatter={(lbl) => formatIstDateTime(lbl)}
                      formatter={(val: any) => [val, 'Power Factor']}
                    />
                    <Line isAnimationActive={false} type="monotone" dataKey="pf_avg" name="Power Factor" stroke="#10B981" strokeWidth={2} dot={false} connectNulls={true} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          {/* Chart 6: Frequency Trend */}
          {activeParams.freq && (
            <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs">
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-700">Frequency (Hz)</span>
                <span className="text-xs font-semibold text-slate-500">Nominal: 50.0 Hz</span>
              </div>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={trends}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E2E8F0" />
                    <XAxis dataKey="ts" tickFormatter={formatTimeTick} stroke="#94A3B8" fontSize={11} />
                    <YAxis domain={[49.0, 51.0]} stroke="#94A3B8" fontSize={11} unit=" Hz" />
                    <Tooltip
                      labelFormatter={(lbl) => formatIstDateTime(lbl)}
                      formatter={(val: any) => [`${val} Hz`, 'Frequency']}
                    />
                    <Line isAnimationActive={false} type="monotone" dataKey="freq" name="Frequency" stroke="#8B5CF6" strokeWidth={1.5} dot={false} connectNulls={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

        </div>
      )}

    </div>
  );
};
export default Dashboard;
