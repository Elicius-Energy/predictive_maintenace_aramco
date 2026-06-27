import { useState } from 'react';
import type { FC } from 'react';
import { NavLink } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import {
  LayoutDashboard,
  Activity,
  Zap,
  Settings2,
  BrainCircuit,
  LogOut,
  ChevronLeft,
  ChevronRight
} from 'lucide-react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

const navItems = [
  { path: '/machines', name: 'Asset Selector', icon: LayoutDashboard },
  { path: '/dashboard/mechanical', name: 'Mechanical Params', icon: Activity },
  { path: '/dashboard/electrical', name: 'Electrical Params', icon: Zap },
  { path: '/dashboard/other', name: 'Auxiliary Metrics', icon: Settings2 },
  { path: '/dashboard/ai-analysis', name: 'AI Analysis & RAG', icon: BrainCircuit },
];

const Sidebar: FC = () => {
  const { logout } = useAuth();
  const [isExpanded, setIsExpanded] = useState(true);

  return (
    <aside
      className={cn(
        "h-full flex flex-col relative z-50 shadow-lg border-r border-gray-100 transition-all duration-300",
        isExpanded ? "w-72" : "w-[88px]"
      )}
      style={{ background: '#ffffff' }}
    >
      {/* Toggle Button */}
      <button 
        onClick={() => setIsExpanded(!isExpanded)}
        className="absolute -right-3 top-6 bg-white border border-gray-200 rounded-full p-1 shadow-sm text-gray-500 hover:text-cyan-600 z-50 transition-colors"
      >
        {isExpanded ? <ChevronLeft size={16} /> : <ChevronRight size={16} />}
      </button>

      {/* Branding — Elicius Logo */}
      <div className={cn("py-7 border-b border-gray-100 flex flex-col items-center transition-all", isExpanded ? "px-6" : "px-2")}>
        <img
          src="/Elicius_Logo.png"
          alt="Elicius"
          className={cn("w-auto object-contain mb-2 transition-all", isExpanded ? "h-16" : "h-8")}
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
                ? "bg-cyan-50 text-cyan-700 font-semibold shadow-sm border border-cyan-100"
                : "text-gray-500 hover:text-gray-800 hover:bg-gray-50"
            )}
          >
            <item.icon size={isExpanded ? 22 : 24} className={cn("transition-colors flex-shrink-0", "group-hover:text-cyan-600")} />
            {isExpanded && <span className="text-sm font-medium whitespace-nowrap">{item.name}</span>}
          </NavLink>
        ))}
      </nav>

      {/* Status Bar Section */}
      <div className={cn("p-4 border-t border-gray-100 space-y-4", !isExpanded && "items-center flex flex-col px-2")}>
        {isExpanded ? (
          <div className="bg-gray-50 p-4 rounded-xl border border-gray-100">
            <div className="flex justify-between items-center mb-2">
              <span className="text-[11px] text-gray-400 uppercase tracking-wider font-semibold">System Status</span>
              <div className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
            </div>
            <p className="text-xs text-gray-600 font-mono">MQTT: CONNECTED</p>
            <p className="text-xs text-gray-600 font-mono">SAMPLING: 1Hz</p>
          </div>
        ) : (
          <div className="w-3 h-3 rounded-full bg-emerald-500 animate-pulse mt-2" title="System Status: Connected" />
        )}

        <button
          onClick={() => {
            logout();
            window.location.href = '/login';
          }}
          title={!isExpanded ? "Sign Out" : undefined}
          className={cn(
            "flex items-center justify-center text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-xl transition-all",
            isExpanded ? "w-full gap-2 px-4 py-2.5" : "w-10 h-10 p-0"
          )}
        >
          <LogOut size={isExpanded ? 16 : 20} className="flex-shrink-0" />
          {isExpanded && <span className="text-xs font-medium whitespace-nowrap">Sign Out</span>}
        </button>
      </div>
    </aside>
  );
};

export default Sidebar;
