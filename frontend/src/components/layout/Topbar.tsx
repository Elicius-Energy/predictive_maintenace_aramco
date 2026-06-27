import { useState, useEffect } from 'react';
import type { FC } from 'react';
import { useMachine } from '../../contexts/MachineContext';
import { useSensorData } from '../../hooks/useSensorData';
import { 
  Bell, 
  MapPin, 
  Clock, 
  ChevronDown,
  CheckCircle2,
  XCircle
} from 'lucide-react';
import { format } from 'date-fns';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

const Topbar: FC = () => {
  const { activeMachine, machines, setActiveMachine, timeRange, setTimeRange } = useMachine();
  const { isConnected, activeAlerts, latestHealth } = useSensorData();
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  const healthStatus = activeMachine?.status || 'offline';
  const healthScore = latestHealth?.health_score || activeMachine?.health_score || 0;

  return (
    <header className="min-h-[4rem] py-2 border-b border-border bg-surface flex flex-wrap items-center justify-between px-4 lg:px-6 z-40 shadow-sm gap-y-3">
      {/* breadcrumbs / machine selector */}
      <div className="flex items-center gap-3 lg:gap-6 flex-wrap">
        <div className="flex items-center gap-2 px-3 py-1.5 bg-surface-muted rounded-lg border border-border shrink-0">
          <MapPin size={14} className="text-secondary" />
          <span className="text-sm font-medium text-text-secondary">
            {activeMachine ? `${activeMachine.plant} / ${activeMachine.unit}` : 'Select Plant'}
          </span>
        </div>

        <div className="h-6 w-px bg-border hidden sm:block" />

        <div className="relative group min-w-[140px] md:min-w-[180px] shrink-0">
          <select 
            value={activeMachine?.machine_id || ''} 
            onChange={(e) => {
              const m = machines.find(m => m.machine_id === e.target.value);
              if (m) setActiveMachine(m);
            }}
            className="w-full appearance-none bg-transparent text-text-primary font-bold text-base pr-6 focus:outline-none cursor-pointer"
          >
            {machines.map(m => (
              <option key={m.machine_id} value={m.machine_id} className="bg-surface text-text-primary">
                {m.name}
              </option>
            ))}
          </select>
          <ChevronDown size={14} className="absolute right-0 top-1/2 -translate-y-1/2 pointer-events-none text-primary" />
        </div>

        <div className="h-6 w-px bg-border hidden sm:block" />

        {/* Datetime Range Selector */}
        <div className="flex items-center gap-2 lg:gap-3 bg-surface-muted p-1.5 rounded-lg border border-border shrink-0">
          <div className="flex items-center gap-1.5">
            <span className="text-[10px] text-text-muted font-bold uppercase tracking-wider hidden sm:inline">Start</span>
            <input 
              type="datetime-local" 
              value={timeRange.start}
              onChange={(e) => setTimeRange({ ...timeRange, start: e.target.value })}
              className="bg-surface text-xs font-mono font-bold text-text-primary px-2 py-1 rounded border border-border focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary/30 transition-all"
            />
          </div>
          <div className="w-px h-4 bg-border" />
          <div className="flex items-center gap-1.5">
            <span className="text-[10px] text-text-muted font-bold uppercase tracking-wider hidden sm:inline">End</span>
            <input 
              type="datetime-local" 
              value={timeRange.end}
              onChange={(e) => setTimeRange({ ...timeRange, end: e.target.value })}
              className="bg-surface text-xs font-mono font-bold text-text-primary px-2 py-1 rounded border border-border focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary/30 transition-all"
            />
          </div>
        </div>
      </div>

      {/* Global Status indicators */}
      <div className="flex items-center gap-4 lg:gap-8 flex-wrap shrink-0">
        {/* Connection Status */}
        <div className="flex items-center gap-2">
          {isConnected ? (
            <CheckCircle2 size={16} className="text-accent-green" />
          ) : (
            <XCircle size={16} className="text-accent-red animate-pulse" />
          )}
          <span className="text-xs font-semibold tracking-wide text-text-secondary">
            {isConnected ? 'LIVE FEED ACTIVE' : 'DISCONNECTED'}
          </span>
        </div>

        {/* Health Indicator */}
        <div className="flex items-center gap-3 px-4 py-2 bg-surface-muted rounded-full border border-border">
          <span className="text-xs text-text-muted uppercase font-bold tracking-tight">Health</span>
          <div className={cn(
            "text-base font-bold scada-number",
            healthStatus === 'healthy' ? "text-accent-green" : 
            healthStatus === 'warning' ? "text-accent-amber" : "text-accent-red"
          )}>
            {healthScore.toFixed(1)}%
          </div>
          <div className={cn(
            "w-3 h-3 rounded-full",
            healthStatus === 'healthy' ? "bg-accent-green shadow-[0_0_6px_#059669]" : 
            healthStatus === 'warning' ? "bg-accent-amber shadow-[0_0_6px_#d97706]" : "bg-accent-red shadow-[0_0_6px_#dc2626]"
          )} />
        </div>

        {/* Notifications */}
        <div className="relative cursor-pointer group">
          <div className="hover:bg-surface-muted p-2 rounded-full transition-colors relative">
            <Bell size={20} className={cn("text-text-muted", activeAlerts.length > 0 && "animate-pulse text-accent-amber")} />
            {activeAlerts.length > 0 && (
              <span className="absolute top-0 right-0 w-4 h-4 bg-accent-red text-white text-[10px] flex items-center justify-center rounded-full font-bold">
                {activeAlerts.length}
              </span>
            )}
          </div>
          
          {/* Notifications Dropdown */}
          <div className="absolute right-0 mt-2 w-80 bg-surface border border-border rounded-xl shadow-xl opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-50">
            <div className="p-3 border-b border-border bg-surface-muted rounded-t-xl">
              <h3 className="text-sm font-bold text-text-primary">Recent Alerts</h3>
            </div>
            <div className="max-h-64 overflow-y-auto">
              {activeAlerts.length > 0 ? (
                activeAlerts.slice(0, 5).map((alert, idx) => (
                  <div key={idx} className="p-3 border-b border-border hover:bg-surface-muted transition-colors">
                    <div className="flex justify-between items-start mb-1">
                      <span className={cn(
                        "text-[10px] font-bold uppercase px-2 py-0.5 rounded-full",
                        alert.severity === 'critical' ? "bg-accent-red/20 text-accent-red" : "bg-accent-amber/20 text-accent-amber"
                      )}>
                        {alert.severity}
                      </span>
                      <span className="text-[10px] text-text-muted">{format(new Date(alert.timestamp.endsWith('Z') ? alert.timestamp : alert.timestamp + 'Z'), 'HH:mm:ss')}</span>
                    </div>
                    <p className="text-xs text-text-primary font-medium">{alert.message}</p>
                    {alert.value !== undefined && alert.threshold !== undefined && (
                      <p className="text-[10px] text-text-secondary mt-1">Value: {alert.value.toFixed(2)} / Threshold: {alert.threshold.toFixed(2)}</p>
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

        <div className="flex flex-col items-end border-l border-border pl-6">
          <div className="flex items-center gap-2 text-text-primary font-mono text-sm font-bold">
            <Clock size={14} className="text-primary" />
            {format(time, 'HH:mm:ss')}
          </div>
          <div className="text-xs text-text-muted font-mono">
            {format(time, 'dd MMM yyyy')}
          </div>
        </div>
      </div>
    </header>
  );
};

export default Topbar;
