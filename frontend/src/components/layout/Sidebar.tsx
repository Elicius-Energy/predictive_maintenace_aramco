import type { FC } from 'react';
import { NavLink } from 'react-router-dom';
import { 
  LayoutDashboard, 
  Activity, 
  Zap, 
  Settings2,
  BrainCircuit,
  LogOut
} from 'lucide-react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

const navItems = [
  { path: '/', name: 'Asset Selector', icon: LayoutDashboard },
  { path: '/dashboard/mechanical', name: 'Mechanical Params', icon: Activity },
  { path: '/dashboard/electrical', name: 'Electrical Params', icon: Zap },
  { path: '/dashboard/other', name: 'Auxiliary Metrics', icon: Settings2 },
  { path: '/dashboard/ai-analysis', name: 'AI Analysis & RAG', icon: BrainCircuit },
];

const Sidebar: FC = () => {
  return (
    <aside
      className="w-72 h-full flex flex-col relative z-50 shadow-lg border-r border-gray-100"
      style={{ background: '#ffffff' }}
    >
      {/* Branding — Elicius Logo (Centered & Large) */}
      <div className="py-7 px-6 border-b border-gray-100 flex flex-col items-center">
        <img 
          src="/Elicius_Logo.png" 
          alt="Elicius" 
          className="h-16 w-auto object-contain mb-2"
        />
        <p className="text-[11px] text-cyan-600 font-semibold tracking-[0.2em] uppercase">
          Saudi Aramco PdM
        </p>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-6 px-4 space-y-1">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) => cn(
              "flex items-center gap-3 px-4 py-3.5 rounded-xl transition-all duration-200 group",
              isActive 
                ? "bg-cyan-50 text-cyan-700 font-semibold shadow-sm border border-cyan-100" 
                : "text-gray-500 hover:text-gray-800 hover:bg-gray-50"
            )}
          >
            <item.icon size={22} className={cn("transition-colors", "group-hover:text-cyan-600")} />
            <span className="text-sm font-medium">{item.name}</span>
          </NavLink>
        ))}
      </nav>

      {/* Status Bar Section */}
      <div className="p-5 border-t border-gray-100 space-y-4">
        <div className="bg-gray-50 p-4 rounded-xl border border-gray-100">
          <div className="flex justify-between items-center mb-2">
            <span className="text-[11px] text-gray-400 uppercase tracking-wider font-semibold">System Status</span>
            <div className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
          </div>
          <p className="text-xs text-gray-600 font-mono">MQTT: CONNECTED</p>
          <p className="text-xs text-gray-600 font-mono">SAMPLING: 1Hz</p>
        </div>

        <button 
          onClick={() => {
            sessionStorage.removeItem('isAuthenticated');
            window.location.href = '/login';
          }}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-xl transition-all"
        >
          <LogOut size={16} />
          <span className="text-xs font-medium">Sign Out</span>
        </button>
      </div>
    </aside>
  );
};

export default Sidebar;
