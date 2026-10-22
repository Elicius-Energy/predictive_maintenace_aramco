import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useDevice } from '../contexts/DeviceContext';
import {
  FileSpreadsheet, Download, RefreshCw, AlertCircle, Eye
} from 'lucide-react';

export const Reports: React.FC = () => {
  const { devices, selectedDevice, selectedDeviceId } = useDevice();

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

  const formatIstDateTime = (iso: string) => {
    if (!iso) return '';
    try {
      const d = new Date(iso);
      return d.toLocaleString('en-IN', {
        timeZone: 'Asia/Kolkata',
        day: '2-digit',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        hour12: false,
      }) + ' IST';
    } catch {
      return iso;
    }
  };

  // Study Form State (with sensible defaults)
  const [preset, setPreset] = useState<'1h' | '8h' | '24h' | '7d'>('8h');
  const [startDate, setStartDate] = useState(() => getIstDateAndTime(new Date(Date.now() - 8 * 3600 * 1000)).date);
  const [startTime, setStartTime] = useState(() => getIstDateAndTime(new Date(Date.now() - 8 * 3600 * 1000)).time);
  const [endDate, setEndDate] = useState(() => getIstDateAndTime(new Date()).date);
  const [endTime, setEndTime] = useState(() => getIstDateAndTime(new Date()).time);
  const [interval, setIntervalVal] = useState<'1-minute' | '5-minute' | '1-hour'>('1-minute');

  const [title, setTitle] = useState('');
  const [remarks, setRemarks] = useState('');

  // Energy Saving & ROI is part of the required report template.
  const includeRoi = true;
  const [includeAiSummary, setIncludeAiSummary] = useState(false);
  const [beforeStart, setBeforeStart] = useState(() => getIstDateAndTime(new Date(Date.now() - 48 * 3600 * 1000)).date);
  const [beforeEnd, setBeforeEnd] = useState(() => getIstDateAndTime(new Date(Date.now() - 24 * 3600 * 1000)).date);
  const [tariff, setTariff] = useState<number | ''>('');
  const [operatingHours, setOperatingHours] = useState<number | ''>('');
  const [motorInvestment, setMotorInvestment] = useState<number>(0);
  const [installationCost, setInstallationCost] = useState<number>(0);
  const [manualBeforeKwhHr, setManualBeforeKwhHr] = useState<string>('');
  const [manualAfterKwhHr, setManualAfterKwhHr] = useState<string>('');

  // Live Preview State
  const [preview, setPreview] = useState<any>(null);
  const [previewLoading, setPreviewLoading] = useState(false);

  // Download & History State
  const [generating, setGenerating] = useState(false);
  const [generationElapsedSeconds, setGenerationElapsedSeconds] = useState(0);
  const [downloadingRaw, setDownloadingRaw] = useState(false);
  const [history, setHistory] = useState<any[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    if (!generating) {
      setGenerationElapsedSeconds(0);
      return;
    }
    const timer = window.setInterval(() => setGenerationElapsedSeconds((seconds) => seconds + 1), 1000);
    return () => window.clearInterval(timer);
  }, [generating]);

  // Compute duration in plain English
  const getDurationStr = () => {
    try {
      const s = new Date(toIsoUtc(startDate, startTime)).getTime();
      const e = new Date(toIsoUtc(endDate, endTime)).getTime();
      const diffHrs = Math.max(0, (e - s) / (1000 * 3600));
      const hrs = Math.floor(diffHrs);
      const mins = Math.round((diffHrs - hrs) * 60);
      return `${hrs} h ${mins} min`;
    } catch {
      return '--';
    }
  };

  // Quick preset button handler
  const handlePreset = (p: '1h' | '8h' | '24h' | '7d') => {
    setPreset(p);
    const now = new Date();
    const hours = p === '1h' ? 1 : p === '8h' ? 8 : p === '24h' ? 24 : 168;
    const start = new Date(now.getTime() - hours * 3600 * 1000);

    const sFmt = getIstDateAndTime(start);
    const eFmt = getIstDateAndTime(now);

    setStartDate(sFmt.date);
    setStartTime(sFmt.time);
    setEndDate(eFmt.date);
    setEndTime(eFmt.time);

    if (p === '1h') setIntervalVal('1-minute');
    else if (p === '8h' || p === '24h') setIntervalVal('5-minute');
    else setIntervalVal('1-hour');
  };

  // Pre-fill tariff and operating hours from device profile
  useEffect(() => {
    if (!selectedDeviceId) return;
    const loadProfileDefaults = async () => {
      try {
        const res = await axios.get(`/api/devices/${selectedDeviceId}/profile`, { withCredentials: true });
        if (res.data) {
          setTariff(res.data.electricity_tariff ?? '');
          setOperatingHours(res.data.annual_operating_hours ?? '');
          setMotorInvestment(res.data.motor_investment ?? 0);
          setInstallationCost(res.data.installation_cost ?? 0);
        }
      } catch (err) {
        console.error('Error loading profile for report:', err);
      }
    };
    loadProfileDefaults();
  }, [selectedDeviceId]);

  // Fetch Live Preview as form inputs change
  useEffect(() => {
    if (!selectedDeviceId) return;
    const fetchPreview = async () => {
      setPreviewLoading(true);
      setErrorMsg(null);
      const startIso = toIsoUtc(startDate, startTime);
      const endIso = toIsoUtc(endDate, endTime);

      try {
        const res = await axios.post(
          '/api/reports/preview',
          {
            device_id: selectedDeviceId,
            start_time: startIso,
            end_time: endIso,
            interval,
          },
          { withCredentials: true }
        );
        setPreview(res.data);
      } catch (err: any) {
        setPreview(null);
      } finally {
        setPreviewLoading(false);
      }
    };

    const timer = setTimeout(fetchPreview, 400);
    return () => clearTimeout(timer);
  }, [selectedDeviceId, startDate, startTime, endDate, endTime, interval]);

  // Fetch Report History
  const fetchHistory = async () => {
    if (!selectedDeviceId) return;
    setHistoryLoading(true);
    try {
      const res = await axios.get(`/api/reports/history/${selectedDeviceId}`, { withCredentials: true });
      setHistory(res.data || []);
    } catch (err) {
      console.error('Error fetching report history:', err);
    } finally {
      setHistoryLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, [selectedDeviceId]);

  // Generate Excel Report
  const handleGenerateReport = async () => {
    if (!selectedDeviceId) return;
    setGenerating(true);
    setErrorMsg(null);

    const startIso = toIsoUtc(startDate, startTime);
    const endIso = toIsoUtc(endDate, endTime);

    try {
      const resp = await axios.post(
        '/api/reports/generate',
        {
          device_id: selectedDeviceId,
          start_time: startIso,
          end_time: endIso,
          interval,
          title,
          remarks,
          include_roi: includeRoi,
          include_ai_summary: includeAiSummary,
          roi_params: {
            electricity_tariff: tariff === '' ? undefined : tariff,
            annual_operating_hours: operatingHours === '' ? undefined : operatingHours,
            motor_investment: motorInvestment,
            installation_cost: installationCost,
            before_start: toIsoUtc(beforeStart, '00:00'),
            before_end: toIsoUtc(beforeEnd, '23:59'),
            before_kwh_hr_manual: manualBeforeKwhHr ? parseFloat(manualBeforeKwhHr) : undefined,
            after_kwh_hr_manual: manualAfterKwhHr ? parseFloat(manualAfterKwhHr) : undefined,
          },
        },
        {
          responseType: 'blob',
          withCredentials: true,
          timeout: 180000,
        }
      );

      // Trigger browser download
      const blob = new Blob([resp.data], {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `Motor_Energy_Report_${selectedDeviceId.slice(-6)}_${startDate}.xlsx`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      a.remove();

      fetchHistory();
    } catch (err: any) {
      let message = err.message || 'Unknown report generation error.';
      const responseData = err.response?.data;
      if (responseData instanceof Blob) {
        try {
          const body = JSON.parse(await responseData.text());
          message = body.detail || body.message || message;
        } catch {
          // Keep the transport error when the server returned a non-JSON blob.
        }
      } else if (responseData?.detail) {
        message = responseData.detail;
      }
      setErrorMsg(`Report generation failed: ${message}`);
    } finally {
      setGenerating(false);
    }
  };

  // Download Raw Data (.csv)
  const handleDownloadRaw = async (format: 'csv' | 'xlsx' = 'csv') => {
    if (!selectedDeviceId) return;
    setDownloadingRaw(true);
    const startIso = toIsoUtc(startDate, startTime);
    const endIso = toIsoUtc(endDate, endTime);

    try {
      const resp = await axios.get(
        `/api/reports/raw-data?device_id=${selectedDeviceId}&start_time=${startIso}&end_time=${endIso}&format=${format}`,
        {
          responseType: 'blob',
          withCredentials: true,
        }
      );

      const blob = new Blob([resp.data], { type: format === 'csv' ? 'text/csv' : 'application/octet-stream' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `Raw_Energy_Data_${selectedDeviceId.slice(-6)}_${startDate}.${format}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      a.remove();
    } catch (err) {
      setErrorMsg('Failed to download raw telemetry data.');
    } finally {
      setDownloadingRaw(false);
    }
  };

  if (devices.length === 0) {
    return (
      <div className="max-w-4xl mx-auto py-16 px-4 text-center">
        <div className="bg-white rounded-2xl border border-slate-200 p-10 shadow-xs max-w-lg mx-auto">
          <div className="w-16 h-16 rounded-2xl bg-blue-50 text-[#1F3A8A] flex items-center justify-center mx-auto mb-4">
            <Download className="w-8 h-8" />
          </div>
          <h2 className="text-xl font-bold text-slate-800">No Devices Registered</h2>
          <p className="text-sm text-slate-500 mt-2 mb-6">
            Please register an IoT energy meter in Configuration before generating reports or downloading telemetry data.
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
    <div className="max-w-5xl mx-auto py-8 px-4 sm:px-6 lg:px-8 space-y-8">
      
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
          Reports & Data Downloads
        </h1>
        <p className="text-xs sm:text-sm text-slate-500 mt-1">
          Generate the official Motor Energy Reading Report (.xlsx) with embedded formulas, analysis, and native Excel charts.
        </p>
      </div>

      {errorMsg && (
        <div className="p-4 rounded-xl bg-red-50 border border-red-200 flex items-center gap-2.5 text-xs text-red-700">
          <AlertCircle className="w-4 h-4 text-red-600 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* ── REPORT CONFIGURATION FORM ───────────────────────────────────── */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-6">
        
        {/* Presets & Timing */}
        <div>
          <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
            Study Window & Duration
          </label>
          <div className="flex flex-wrap items-center gap-2 mb-3">
            {(['1h', '8h', '24h', '7d'] as const).map((p) => (
              <button
                key={p}
                type="button"
                onClick={() => handlePreset(p)}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors cursor-pointer ${
                  preset === p
                    ? 'bg-[#1F3A8A] text-white shadow-2xs'
                    : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                }`}
              >
                Last {p}
              </button>
            ))}
            <span className="text-xs font-semibold text-slate-500 ml-2">
              Duration: <span className="text-[#1F3A8A] font-bold">{getDurationStr()}</span>
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 text-xs">
            <div className="bg-slate-50 border border-slate-300 rounded-lg p-2.5">
            <label className="block text-slate-500 font-semibold mb-1">Start Date & Time (IST)</label>
              <div className="flex gap-1.5">
                <input
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  className="bg-white border border-slate-200 rounded-md p-1.5 w-full font-medium text-slate-800"
                />
                <input
                  type="time"
                  value={startTime}
                  onChange={(e) => setStartTime(e.target.value)}
                  className="bg-white border border-slate-200 rounded-md p-1.5 font-medium text-slate-800"
                />
              </div>
            </div>

            <div className="bg-slate-50 border border-slate-300 rounded-lg p-2.5">
            <label className="block text-slate-500 font-semibold mb-1">End Date & Time (IST)</label>
              <div className="flex gap-1.5">
                <input
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  className="bg-white border border-slate-200 rounded-md p-1.5 w-full font-medium text-slate-800"
                />
                <input
                  type="time"
                  value={endTime}
                  onChange={(e) => setEndTime(e.target.value)}
                  className="bg-white border border-slate-200 rounded-md p-1.5 font-medium text-slate-800"
                />
              </div>
            </div>

            <div className="bg-slate-50 border border-slate-300 rounded-lg p-2.5">
              <label className="block text-slate-500 font-semibold mb-1">Data Bucketing Interval</label>
              <select
                value={interval}
                onChange={(e) => setIntervalVal(e.target.value as any)}
                className="bg-white border border-slate-200 rounded-md p-1.5 w-full font-semibold text-slate-800 cursor-pointer"
              >
                <option value="1-minute">1-minute resolution</option>
                <option value="5-minute">5-minute resolution</option>
                <option value="1-hour">1-hour resolution</option>
              </select>
            </div>
          </div>
        </div>

        {/* Title & Remarks */}
        <div className="grid grid-cols-1 gap-3 text-xs">
          <div>
            <label className="block font-semibold text-slate-700 mb-1">Study Title / Header (Optional)</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Ring Frame 14 - Motor Energy & Loading Study"
              className="w-full border border-slate-300 rounded-lg p-2.5 focus:border-[#1F3A8A] focus:outline-hidden"
            />
          </div>

          <div>
            <label className="block font-semibold text-slate-700 mb-1">
              Observations & Recommendations (Appears in Section 6 of Report)
            </label>
            <textarea
              rows={3}
              value={remarks}
              onChange={(e) => setRemarks(e.target.value)}
              placeholder="Enter audit observations (e.g. Motor running smooth; recommended VFD speed reduction during night shift)..."
              className="w-full border border-slate-300 rounded-lg p-2.5 focus:border-[#1F3A8A] focus:outline-hidden text-xs"
            />
          </div>
        </div>

        {/* ── REQUIRED: Energy Saving & ROI ───────────────────────────────── */}
        <div className="pt-4 border-t border-slate-200 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <span className="text-sm font-bold text-slate-800">Energy Saving & ROI</span>
              <p className="text-xs text-slate-500">
                Included in every report. Savings are calculated only when a measured or manually supplied before value is available.
              </p>
            </div>
          </div>

          {
            <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-3 text-xs animate-in fade-in">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                <div>
                  <label className="block font-semibold text-slate-600 mb-1">Electricity Tariff (Rs/kWh)</label>
                  <input
                    type="number"
                    step="0.01"
                    value={tariff}
                    onChange={(e) => setTariff(e.target.value === '' ? '' : parseFloat(e.target.value))}
                    className="w-full bg-white border border-slate-300 rounded-lg p-2 font-medium"
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-600 mb-1">Annual Operating Hours</label>
                  <input
                    type="number"
                    step="1"
                    value={operatingHours}
                    onChange={(e) => setOperatingHours(e.target.value === '' ? '' : parseFloat(e.target.value))}
                    className="w-full bg-white border border-slate-300 rounded-lg p-2 font-medium"
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-600 mb-1">Motor Investment (Rs)</label>
                  <input
                    type="number"
                    step="100"
                    value={motorInvestment}
                    onChange={(e) => setMotorInvestment(e.target.value === '' ? 0 : parseFloat(e.target.value))}
                    className="w-full bg-white border border-slate-300 rounded-lg p-2 font-medium"
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-600 mb-1">Installation / Retrofit Cost (Rs)</label>
                  <input
                    type="number"
                    step="100"
                    value={installationCost}
                    onChange={(e) => setInstallationCost(e.target.value === '' ? 0 : parseFloat(e.target.value))}
                    className="w-full bg-white border border-slate-300 rounded-lg p-2 font-medium"
                  />
                </div>
              </div>

              {/* Before Window & Manual Overrides */}
              <div className="pt-2 border-t border-slate-200 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            <div>
              <label className="block font-semibold text-slate-600 mb-1">Before Window Start</label>
              <input
                type="date"
                value={beforeStart}
                onChange={(e) => setBeforeStart(e.target.value)}
                className="w-full bg-white border border-slate-300 rounded-lg p-2 font-medium"
              />
            </div>
            <div>
              <label className="block font-semibold text-slate-600 mb-1">Before Window End</label>
              <input
                type="date"
                value={beforeEnd}
                onChange={(e) => setBeforeEnd(e.target.value)}
                className="w-full bg-white border border-slate-300 rounded-lg p-2 font-medium"
              />
            </div>
                <div>
                  <label className="block font-semibold text-slate-600 mb-1">Before kWh/hr (Manual Override)</label>
                  <input
                    type="number"
                    step="0.01"
                    placeholder="Auto from DB"
                    value={manualBeforeKwhHr}
                    onChange={(e) => setManualBeforeKwhHr(e.target.value)}
                    className="w-full bg-white border border-slate-300 rounded-lg p-2 font-medium"
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-600 mb-1">After kWh/hr (Manual Override)</label>
                  <input
                    type="number"
                    step="0.01"
                    placeholder="Auto from study"
                    value={manualAfterKwhHr}
                    onChange={(e) => setManualAfterKwhHr(e.target.value)}
                    className="w-full bg-white border border-slate-300 rounded-lg p-2 font-medium"
                  />
                </div>
              </div>
            </div>
          }
        </div>

        <div className="pt-4 border-t border-slate-200 flex items-start justify-between gap-4">
          <div>
            <label htmlFor="include-ai-summary" className="text-sm font-bold text-slate-800">AI generated data summary</label>
            <p className="text-xs text-slate-500 mt-1">Requests OpenAI power-study insights from measured loading and running time. Configure the candidate motor rating and efficiency to calculate replacement savings; the existing motor’s rated efficiency is required.</p>
          </div>
          <input
            id="include-ai-summary"
            type="checkbox"
            checked={includeAiSummary}
            onChange={(e) => setIncludeAiSummary(e.target.checked)}
            className="mt-1 w-4 h-4 text-[#1F3A8A] rounded-sm focus:ring-[#1F3A8A] cursor-pointer"
          />
        </div>

        {generating && (
          <div
            role="status"
            aria-live="polite"
            className="rounded-xl border border-blue-300 bg-blue-50 p-4 text-sm text-blue-950 shadow-sm"
          >
            <div className="flex items-center gap-3">
              <RefreshCw className="h-5 w-5 shrink-0 animate-spin text-blue-700" />
              <div className="min-w-0 flex-1">
                <div className="font-bold">
                  {includeAiSummary ? 'Waiting for AI insights and building your report' : 'Building your report'}
                </div>
                <div className="mt-1 text-xs text-blue-800">
                  {includeAiSummary
                    ? `The OpenAI model is analyzing the summarized telemetry. Elapsed: ${generationElapsedSeconds}s. Keep this page open until the download begins.`
                    : `Preparing the workbook. Elapsed: ${generationElapsedSeconds}s.`}
                </div>
              </div>
              <span className="shrink-0 font-mono text-xs font-semibold">{generationElapsedSeconds}s</span>
            </div>
            <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-blue-100">
              <div className="h-full w-1/3 animate-pulse rounded-full bg-blue-600" />
            </div>
          </div>
        )}

        {/* ── LIVE PREVIEW CARD ─────────────────────────────────────────── */}
        <div className="p-4 bg-blue-50/70 border border-blue-200 rounded-xl space-y-2 text-xs">
          <div className="flex items-center justify-between font-bold text-[#1F3A8A]">
            <div className="flex items-center gap-1.5">
              <Eye className="w-4 h-4 text-[#1F3A8A]" />
              <span>Live Study Preview (Calculated from Stored Telemetry)</span>
            </div>
            {previewLoading && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 pt-2">
            <div>
              <span className="block text-slate-500 font-medium">Energy Consumption</span>
              <span className="text-base font-extrabold text-[#1F3A8A]">
                {preview ? `${preview.energy_kwh} kWh` : '--'}
              </span>
            </div>
            <div>
              <span className="block text-slate-500 font-medium">Average Power</span>
              <span className="text-base font-extrabold text-slate-800">
                {preview ? `${preview.avg_kw} kW` : '--'}
              </span>
            </div>
            <div>
              <span className="block text-slate-500 font-medium">Weighted Power Factor</span>
              <span className="text-base font-extrabold text-emerald-700">
                {preview ? `${preview.avg_pf}` : '--'}
              </span>
            </div>
            <div>
              <span className="block text-slate-500 font-medium">Idle Time</span>
              <span className="text-base font-extrabold text-amber-700">
                {preview ? preview.idle_time_str : '--'}
              </span>
            </div>
            <div>
              <span className="block text-slate-500 font-medium">Data Completeness</span>
              <span className="text-base font-extrabold text-slate-800">
                {preview ? `${preview.data_completeness_pct}%` : '--'}
              </span>
            </div>
          </div>
        </div>

        {/* ── ACTION BUTTONS ────────────────────────────────────────────── */}
        <div className="flex flex-col sm:flex-row items-center gap-3 pt-3">
          <button
            onClick={handleGenerateReport}
            disabled={generating}
            className="w-full sm:w-auto flex-1 inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl bg-[#1F3A8A] text-white font-bold text-sm shadow-md hover:bg-[#1E3A8A] active:scale-98 disabled:opacity-50 transition-all cursor-pointer"
          >
            {generating ? <RefreshCw className="w-4 h-4 animate-spin" /> : <FileSpreadsheet className="w-4 h-4" />}
            <span>{generating ? (includeAiSummary ? 'Generating AI insights & report...' : 'Compiling Official Report...') : 'Generate Excel Report (.xlsx)'}</span>
          </button>

          <button
            onClick={() => handleDownloadRaw('csv')}
            disabled={downloadingRaw}
            className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-5 py-3 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-800 font-semibold text-sm border border-slate-300 transition-colors cursor-pointer"
          >
            <Download className="w-4 h-4 text-slate-600" />
            <span>{downloadingRaw ? 'Exporting...' : 'Download Raw Data (.csv)'}</span>
          </button>
        </div>

      </div>

      {/* ── PREVIOUSLY GENERATED REPORTS (History Archive) ──────────────── */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-base font-bold text-slate-800">Previously Generated Reports</h3>
            <p className="text-xs text-slate-500">
              Access and re-download archived audit workbooks for <span className="font-semibold text-slate-700">{selectedDevice?.alias || selectedDeviceId}</span>.
            </p>
          </div>
          <button
            onClick={fetchHistory}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors"
            title="Refresh History"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>

        {historyLoading ? (
          <div className="py-8 text-center text-xs text-slate-400">Loading archived reports...</div>
        ) : history.length === 0 ? (
          <div className="py-8 text-center bg-slate-50 rounded-xl border border-slate-100 text-xs text-slate-500">
            No previously generated reports found for this device. Click "Generate Excel Report" above to create one.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead className="bg-slate-50 border-y border-slate-200 text-slate-600 font-semibold uppercase tracking-wider">
                <tr>
                  <th className="py-2.5 px-3">Report Number</th>
                  <th className="py-2.5 px-3">Generated Date</th>
                  <th className="py-2.5 px-3">Study Period</th>
                  <th className="py-2.5 px-3">Total Energy</th>
                  <th className="py-2.5 px-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700">
                {history.map((rep) => (
                  <tr key={rep.id} className="hover:bg-slate-50 transition-colors">
                    <td className="py-3 px-3 font-mono font-bold text-[#1F3A8A]">
                      {rep.report_no}
                    </td>
                    <td className="py-3 px-3">
                      {formatIstDateTime(rep.created_at)}
                    </td>
                    <td className="py-3 px-3 font-medium">
                      {formatIstDateTime(rep.start_time)} to {formatIstDateTime(rep.end_time)}
                    </td>
                    <td className="py-3 px-3 font-semibold text-emerald-700">
                      {rep.energy_kwh} kWh
                    </td>
                    <td className="py-3 px-3 text-right">
                      <a
                        href={`/api/reports/download/${rep.id}`}
                        download
                        className="inline-flex items-center gap-1.5 px-3 py-1 bg-blue-50 hover:bg-blue-100 text-[#1F3A8A] font-semibold rounded-md transition-colors"
                      >
                        <Download className="w-3.5 h-3.5" />
                        <span>Download</span>
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

    </div>
  );
};
export default Reports;
