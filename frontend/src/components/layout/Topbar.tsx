import { useState, useEffect } from 'react';
import type { FC } from 'react';
import { useMachine } from '../../contexts/MachineContext';
import { useMotorDetails } from '../../contexts/MotorDetailsContext';
import { useSensorData } from '../../hooks/useSensorData';
import { 
  Bell, 
  MapPin, 
  Clock, 
  ChevronDown,
  CheckCircle2,
  XCircle,
  Download,
  FileText,
  Calendar
} from 'lucide-react';
import { format } from 'date-fns';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { useReportGenerator } from '../../hooks/useReportGenerator';
import api from '../../utils/api';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

const Topbar: FC = () => {
  const { activeMachine, machines, setActiveMachine, timeRange, setTimeRange, isAutoUpdate, setIsAutoUpdate } = useMachine();
  const { motorDetails } = useMotorDetails();
  const { isConnected, activeAlerts, latestHealth } = useSensorData();
  const [time, setTime] = useState(new Date());
  const [csvResolution, setCsvResolution] = useState('10m');
  
  const { isGenerating, generateReport } = useReportGenerator();

  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  const healthStatus = activeMachine?.status || 'offline';
  const healthScore = latestHealth?.health_score || activeMachine?.health_score || 0;

  return (
    <header className="glass-topbar z-40">
      <div className="flex items-center justify-between px-4 lg:px-6 py-2 gap-4 overflow-x-auto overflow-y-hidden whitespace-nowrap scrollbar-hide">
        {/* ── Left Side: Identity & Time Selection ── */}
        <div className="flex items-center gap-3 shrink-0">
          {/* Site / Location Badge */}
          <div className="flex items-center gap-1.5 px-2.5 py-1 glass-badge rounded-lg shrink-0">
            <MapPin size={13} className="text-primary" />
            <span className="text-xs font-medium text-text-secondary whitespace-nowrap">
              {motorDetails?.location || 'Unassigned Location'}
            </span>
          </div>

          <div className="h-5 w-px bg-white/10 hidden sm:block shrink-0" />

          {/* Device selector */}
          <div className="relative group min-w-[120px] shrink-0">
            <select 
              value={activeMachine?.machine_id || ''} 
              onChange={(e) => {
                const m = machines.find(m => m.machine_id === e.target.value);
                if (m) setActiveMachine(m);
              }}
              className="w-full appearance-none bg-transparent text-white font-bold text-sm pr-6 focus:outline-none cursor-pointer"
            >
              {machines.map(m => (
                <option key={m.machine_id} value={m.machine_id} className="bg-surface-alt text-white">
                  {m.name}
                </option>
              ))}
            </select>
            <ChevronDown size={14} className="absolute right-0 top-1/2 -translate-y-1/2 pointer-events-none text-primary" />
          </div>

          <div className="h-5 w-px bg-white/10 hidden sm:block shrink-0" />

          {/* Date Range Selector */}
          <div className="flex items-center gap-2 glass-badge p-1.5 rounded-lg shrink-0">
            <Calendar size={13} className="text-primary shrink-0" />
            
            <div className="flex items-center gap-1">
              <span className="text-[10px] text-text-muted font-bold uppercase tracking-wider hidden sm:inline">Start</span>
              <input 
                type="datetime-local" 
                value={timeRange.start}
                onChange={(e) => setTimeRange({ ...timeRange, start: e.target.value })}
                className="glass-input text-xs font-mono font-bold text-white [color-scheme:dark] px-2 py-1 rounded-lg disabled:opacity-50"
                disabled={isAutoUpdate}
              />
            </div>

            <div className="w-px h-4 bg-white/10" />

            <div className="flex items-center gap-1">
              <span className="text-[10px] text-text-muted font-bold uppercase tracking-wider hidden sm:inline">End</span>
              <input 
                type="datetime-local" 
                value={timeRange.end}
                onChange={(e) => setTimeRange({ ...timeRange, end: e.target.value })}
                className="glass-input text-xs font-mono font-bold text-white [color-scheme:dark] px-2 py-1 rounded-lg disabled:opacity-50"
                disabled={isAutoUpdate}
              />
            </div>

            <div className="w-px h-4 bg-white/10" />

            <label className="flex items-center gap-1.5 cursor-pointer px-1.5">
              <input
                type="checkbox"
                checked={isAutoUpdate}
                onChange={(e) => setIsAutoUpdate(e.target.checked)}
                className="w-3.5 h-3.5 text-primary rounded border-text-muted focus:ring-primary/50"
              />
              <span className="text-[10px] text-primary font-bold uppercase tracking-wider">Auto</span>
            </label>
          </div>
        </div>

        {/* ── Right Side: Status, Actions & Branding ── */}
        <div className="flex items-center gap-3 lg:gap-4 shrink-0">
          {/* Actions: CSV + Report */}
          <div className="flex items-center gap-2 shrink-0">
            <div className="flex items-center gap-1.5 glass-badge px-1.5 py-1 rounded-lg">
              <select
                value={csvResolution}
                onChange={(e) => setCsvResolution(e.target.value)}
                className="glass-input text-[11px] font-mono font-bold text-white px-2 py-1 rounded-lg focus:outline-none"
              >
                <option value="1m" className="bg-surface-alt text-white">1 Min</option>
                <option value="5m" className="bg-surface-alt text-white">5 Min</option>
                <option value="10m" className="bg-surface-alt text-white">10 Min</option>
                <option value="15m" className="bg-surface-alt text-white">15 Min</option>
                <option value="1h" className="bg-surface-alt text-white">1 Hour</option>
              </select>
              <button 
                onClick={async () => {
                  if (activeMachine) {
                    try {
                      const startUtc = new Date(timeRange.start).toISOString();
                      const endUtc = new Date(timeRange.end).toISOString();
                      const url = `/api/data/download_csv?machine_id=${activeMachine.machine_id}&start_time=${startUtc}&end_time=${endUtc}&resolution=${csvResolution}`;
                      const response = await api.get(url, { responseType: 'blob' });
                      const blobUrl = window.URL.createObjectURL(new Blob([response.data]));
                      const link = document.createElement('a');
                      link.href = blobUrl;
                      link.setAttribute('download', `export_${activeMachine.machine_id}.csv`);
                      document.body.appendChild(link);
                      link.click();
                      link.parentNode?.removeChild(link);
                    } catch (e) {
                      console.error('CSV download error:', e);
                      alert('Failed to download CSV');
                    }
                  }
                }}
                className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-primary/10 hover:bg-primary/20 transition-colors border border-primary/20 hover:border-primary/30 text-primary"
                title="Download CSV"
              >
                <Download size={13} />
                <span className="text-[10px] font-bold uppercase tracking-wider hidden sm:inline">CSV</span>
              </button>
            </div>
            
            <button 
              onClick={generateReport}
              disabled={isGenerating}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-primary/10 hover:bg-primary/20 transition-colors border border-primary/20 hover:border-primary/30 text-primary disabled:opacity-50"
              title="Download Report PDF"
            >
              <FileText size={13} />
              <span className="text-[10px] font-bold uppercase tracking-wider hidden xl:inline">
                {isGenerating ? 'Generating...' : 'Report PDF'}
              </span>
            </button>
          </div>

          <div className="h-5 w-px bg-white/10 hidden sm:block shrink-0" />

          {/* Connection Status */}
          <div className="flex items-center gap-1.5 shrink-0">
            {isConnected ? (
              <CheckCircle2 size={14} className="text-accent-green" />
            ) : (
              <XCircle size={14} className="text-accent-red animate-pulse" />
            )}
            <span className="text-[10px] font-semibold tracking-wide text-text-secondary uppercase">
              {isConnected ? 'Live' : 'Offline'}
            </span>
          </div>

          {/* Health */}
          <div className="flex items-center gap-2 px-3 py-1 glass-badge rounded-full shrink-0">
            <span className="text-[10px] text-text-muted uppercase font-bold tracking-tight hidden sm:inline">Health</span>
            <div className={cn(
              "text-sm font-bold scada-number",
              healthStatus === 'healthy' ? "text-accent-green" : 
              healthStatus === 'warning' ? "text-accent-amber" : "text-accent-red"
            )}>
              {healthScore.toFixed(1)}%
            </div>
            <div className={cn(
              "w-2.5 h-2.5 rounded-full",
              healthStatus === 'healthy' ? "bg-accent-green shadow-[0_0_6px_rgba(52,211,153,0.5)]" : 
              healthStatus === 'warning' ? "bg-accent-amber shadow-[0_0_6px_rgba(251,191,36,0.5)]" : "bg-accent-red shadow-[0_0_6px_rgba(248,113,113,0.5)]"
            )} />
          </div>

          {/* Notifications */}
          <div className="relative cursor-pointer group shrink-0">
            <div className="hover:bg-white/5 p-1.5 rounded-full transition-colors relative">
              <Bell size={18} className={cn("text-text-secondary", activeAlerts.length > 0 && "animate-pulse text-accent-amber")} />
              {activeAlerts.length > 0 && (
                <span className="absolute -top-0.5 -right-0.5 w-4 h-4 bg-accent-red text-white text-[9px] flex items-center justify-center rounded-full font-bold shadow-lg shadow-red-500/25">
                  {activeAlerts.length}
                </span>
              )}
            </div>
            
            {/* Notifications Dropdown */}
            <div className="absolute right-0 mt-2 w-80 industrial-card opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-50 overflow-hidden">
              <div className="p-3 border-b border-white/8 bg-white/3">
                <h3 className="text-sm font-bold text-text-primary">Recent Alerts</h3>
              </div>
              <div className="max-h-64 overflow-y-auto">
                {activeAlerts.length > 0 ? (
                  activeAlerts.slice(0, 5).map((alert, idx) => (
                    <div key={idx} className="p-3 border-b border-white/8 hover:bg-white/5 transition-colors">
                      <div className="flex justify-between items-start mb-1">
                        <span className={cn(
                          "text-[10px] font-bold uppercase px-2 py-0.5 rounded-full",
                          alert.severity === 'critical' ? "bg-accent-red/15 text-accent-red" : "bg-accent-amber/15 text-accent-amber"
                        )}>
                          {alert.severity}
                        </span>
                        <span className="text-[10px] text-text-muted">{format(new Date((alert.timestamp.endsWith('Z') || alert.timestamp.includes('+')) ? alert.timestamp : alert.timestamp + 'Z'), 'HH:mm:ss')}</span>
                      </div>
                      <p className="text-xs text-text-secondary font-medium">{alert.message}</p>
                      {alert.value !== undefined && alert.threshold !== undefined && (
                        <p className="text-[10px] text-text-muted mt-1">Value: {alert.value.toFixed(2)} / Threshold: {alert.threshold.toFixed(2)}</p>
                      )}
                    </div>
                  ))
                ) : (
                  <div className="p-4 text-center text-sm text-text-muted">
                    No active alerts.
                  </div>
                )}
              </div>
            </div>
          </div>

          <div className="h-5 w-px bg-white/10 hidden sm:block shrink-0" />

          {/* Clock */}
          <div className="flex flex-col items-end shrink-0">
            <div className="flex items-center gap-1.5 text-white font-mono text-xs font-bold">
              <Clock size={12} className="text-primary" />
              {format(time, 'HH:mm:ss')}
            </div>
            <div className="text-[10px] text-text-muted font-mono">
              {format(time, 'dd MMM yyyy')}
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};

export default Topbar;
