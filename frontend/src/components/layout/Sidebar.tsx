import { useState } from 'react';
import type { FC } from 'react';
import { NavLink } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import MotorDetailsForm from '../../pages/MotorDetailsForm';
import {
  LayoutDashboard,
  Activity,
  LogOut,
  ChevronLeft,
  ChevronRight,
  Settings2
} from 'lucide-react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

const navItems = [
  { path: '/machines', name: 'Asset Selector', icon: LayoutDashboard },
  { path: '/dashboard', name: 'Dashboard Overview', icon: Activity },
];

const Sidebar: FC = () => {
  const { logout } = useAuth();
  const [isExpanded, setIsExpanded] = useState(true);
  const [showMotorConfig, setShowMotorConfig] = useState(false);

  return (
    <>
      <aside
        className={cn(
          "h-full flex flex-col relative z-50 glass-sidebar transition-all duration-300",
          isExpanded ? "w-72" : "w-[88px]"
        )}
      >
      {/* Toggle Button */}
      <button 
        onClick={() => {
          setIsExpanded(!isExpanded);
          // Force Recharts to remeasure its container after the 300ms CSS transition finishes
          setTimeout(() => window.dispatchEvent(new Event('resize')), 350);
        }}
        className="absolute -right-3 top-6 bg-surface-alt/80 backdrop-blur-md border border-white/10 rounded-full p-1 shadow-lg text-text-muted hover:text-primary z-50 transition-all hover:scale-110"
      >
        {isExpanded ? <ChevronLeft size={16} /> : <ChevronRight size={16} />}
      </button>

      {/* Branding */}
      <div className={cn("flex flex-col items-center justify-center py-6 transition-all", isExpanded ? "px-6" : "px-2")}>
        <div className={cn(
          "bg-white rounded-xl shadow-[0_4px_12px_rgba(0,0,0,0.15)] flex items-center justify-center transition-all duration-300",
          isExpanded ? "px-4 py-2 gap-4" : "px-2 py-3 flex-col gap-3"
        )}>
          <img 
            src="/Elicius_Logo.png" 
            alt="Elicius Energy" 
            className={cn("object-contain transition-all duration-300", isExpanded ? "h-10" : "h-5")} 
          />
          <div className={cn("bg-gray-200 transition-all duration-300", isExpanded ? "w-[1px] h-8" : "h-[1px] w-6")} />
          <img 
            src="/ledl.png" 
            alt="LEDL" 
            className={cn("object-contain transition-all duration-300", isExpanded ? "h-10" : "h-5")} 
          />
        </div>
        
        {isExpanded && (
          <p className="text-[11px] text-primary font-semibold tracking-[0.2em] uppercase whitespace-nowrap overflow-hidden mt-1">
            PdM Dashboard
          </p>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-6 px-3 space-y-2 overflow-y-auto overflow-x-hidden">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            title={!isExpanded ? item.name : undefined}
            className={({ isActive }) => cn(
              "flex items-center rounded-xl transition-all duration-200 group",
              isExpanded ? "gap-3 px-4 py-3.5" : "justify-center py-3 px-0",
              isActive
                ? "bg-primary/15 text-primary font-semibold shadow-sm border border-primary/25 backdrop-blur-sm"
                : "text-text-secondary hover:text-text-primary hover:bg-white/5"
            )}
            end
          >
            <item.icon size={isExpanded ? 22 : 24} className={cn("transition-colors flex-shrink-0", "group-hover:text-primary")} />
            {isExpanded && <span className="text-sm font-extrabold whitespace-nowrap tracking-wide">{item.name}</span>}
          </NavLink>
        ))}
      </nav>

      {/* Status Bar Section */}
      <div className={cn("p-4 border-t border-white/10 space-y-4", !isExpanded && "items-center flex flex-col px-2")}>
        {isExpanded ? (
          <div className="bg-white/5 backdrop-blur-sm p-4 rounded-xl border border-white/8">
            <div className="flex justify-between items-center mb-2">
              <span className="text-[11px] text-text-muted uppercase tracking-wider font-extrabold">System Status</span>
              <div className="w-2.5 h-2.5 rounded-full bg-accent-green animate-pulse shadow-lg shadow-emerald-500/30" />
            </div>
            <p className="text-xs text-text-secondary font-mono font-bold">MQTT: CONNECTED</p>
            <p className="text-xs text-text-secondary font-mono font-bold">SAMPLING: 1Hz</p>
          </div>
        ) : (
          <div className="w-3 h-3 rounded-full bg-accent-green animate-pulse shadow-lg shadow-emerald-500/30 mt-2" title="System Status: Connected" />
        )}

        <button
          onClick={() => setShowMotorConfig(true)}
          title={!isExpanded ? "Motor Configuration" : undefined}
          className={cn(
            "flex items-center justify-center text-text-muted hover:text-primary hover:bg-white/5 rounded-xl transition-all",
            isExpanded ? "w-full gap-2 px-4 py-2.5" : "w-10 h-10 p-0"
          )}
        >
          <Settings2 size={isExpanded ? 16 : 20} className="flex-shrink-0" />
          {isExpanded && <span className="text-xs font-extrabold whitespace-nowrap tracking-wide">Motor Config</span>}
        </button>

        <button
          onClick={() => {
            logout();
            window.location.href = '/login';
          }}
          title={!isExpanded ? "Sign Out" : undefined}
          className={cn(
            "flex items-center justify-center text-text-muted hover:text-accent-red hover:bg-accent-red/10 rounded-xl transition-all",
            isExpanded ? "w-full gap-2 px-4 py-2.5" : "w-10 h-10 p-0"
          )}
        >
          <LogOut size={isExpanded ? 16 : 20} className="flex-shrink-0" />
          {isExpanded && <span className="text-xs font-extrabold whitespace-nowrap tracking-wide">Sign Out</span>}
        </button>
      </div>
    </aside>
      {showMotorConfig && <MotorDetailsForm onClose={() => setShowMotorConfig(false)} />}
    </>
  );
};

export default Sidebar;
