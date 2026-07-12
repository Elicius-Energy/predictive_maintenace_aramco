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
        onClick={() => setIsExpanded(!isExpanded)}
        className="absolute -right-3 top-6 bg-white/70 backdrop-blur-md border border-white/50 rounded-full p-1 shadow-lg text-gray-500 hover:text-cyan-600 z-50 transition-all hover:scale-110"
      >
        {isExpanded ? <ChevronLeft size={16} /> : <ChevronRight size={16} />}
      </button>

      {/* Branding — Elicius Logo */}
      <div className={cn("py-7 border-b border-white/30 flex flex-col items-center transition-all", isExpanded ? "px-6" : "px-2")}>
        <img
          src="/Elicius_Logo.png"
          alt="Elicius"
          className={cn("w-auto object-contain mb-2 transition-all drop-shadow-sm", isExpanded ? "h-16" : "h-8")}
        />
        {isExpanded && (
          <p className="text-[11px] text-cyan-600 font-semibold tracking-[0.2em] uppercase whitespace-nowrap overflow-hidden">
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
                ? "bg-cyan-500/15 text-cyan-700 font-semibold shadow-sm border border-cyan-200/40 backdrop-blur-sm"
                : "text-gray-600 hover:text-gray-800 hover:bg-white/40"
            )}
            end
          >
            <item.icon size={isExpanded ? 22 : 24} className={cn("transition-colors flex-shrink-0", "group-hover:text-cyan-600")} />
            {isExpanded && <span className="text-sm font-medium whitespace-nowrap">{item.name}</span>}
          </NavLink>
        ))}
      </nav>

      {/* Status Bar Section */}
      <div className={cn("p-4 border-t border-white/30 space-y-4", !isExpanded && "items-center flex flex-col px-2")}>
        {isExpanded ? (
          <div className="bg-white/30 backdrop-blur-sm p-4 rounded-xl border border-white/40">
            <div className="flex justify-between items-center mb-2">
              <span className="text-[11px] text-gray-500 uppercase tracking-wider font-semibold">System Status</span>
              <div className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse shadow-lg shadow-emerald-500/40" />
            </div>
            <p className="text-xs text-gray-600 font-mono">MQTT: CONNECTED</p>
            <p className="text-xs text-gray-600 font-mono">SAMPLING: 1Hz</p>
          </div>
        ) : (
          <div className="w-3 h-3 rounded-full bg-emerald-500 animate-pulse shadow-lg shadow-emerald-500/40 mt-2" title="System Status: Connected" />
        )}

        <button
          onClick={() => setShowMotorConfig(true)}
          title={!isExpanded ? "Motor Configuration" : undefined}
          className={cn(
            "flex items-center justify-center text-gray-500 hover:text-cyan-600 hover:bg-white/40 rounded-xl transition-all",
            isExpanded ? "w-full gap-2 px-4 py-2.5" : "w-10 h-10 p-0"
          )}
        >
          <Settings2 size={isExpanded ? 16 : 20} className="flex-shrink-0" />
          {isExpanded && <span className="text-xs font-medium whitespace-nowrap">Motor Config</span>}
        </button>

        <button
          onClick={() => {
            logout();
            window.location.href = '/login';
          }}
          title={!isExpanded ? "Sign Out" : undefined}
          className={cn(
            "flex items-center justify-center text-gray-400 hover:text-red-500 hover:bg-red-50/40 rounded-xl transition-all",
            isExpanded ? "w-full gap-2 px-4 py-2.5" : "w-10 h-10 p-0"
          )}
        >
          <LogOut size={isExpanded ? 16 : 20} className="flex-shrink-0" />
          {isExpanded && <span className="text-xs font-medium whitespace-nowrap">Sign Out</span>}
        </button>
      </div>
    </aside>
      {showMotorConfig && <MotorDetailsForm onClose={() => setShowMotorConfig(false)} />}
    </>
  );
};

export default Sidebar;
