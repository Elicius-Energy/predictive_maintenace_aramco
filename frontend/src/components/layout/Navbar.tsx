import React, { useState } from 'react';
import { NavLink } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { useDevice } from '../../contexts/DeviceContext';
import { LogOut, Sliders, LayoutDashboard, FileSpreadsheet, ChevronDown, Users } from 'lucide-react';

export const Navbar: React.FC = () => {
  const { logout, user } = useAuth();
  const { devices, selectedDevice, selectedDeviceId, setSelectedDeviceId, getStatusColor } = useDevice();
  const [logoError, setLogoError] = useState(false);

  const statusStyle = selectedDevice
    ? getStatusColor(selectedDevice.status)
    : { dot: 'bg-slate-400', bg: 'bg-slate-50', text: 'text-slate-700', border: 'border-slate-200' };

  return (
    <header className="sticky top-0 z-40 surface-nav border-b border-slate-200/80 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          
          {/* Brand Logo & Name */}
          <div className="flex items-center gap-3">
            {!logoError ? (
              <img
                src="/Elicius_Logo.png"
                alt="Elicius Energy Logo"
                className="h-9 w-auto object-contain"
                onError={() => setLogoError(true)}
              />
            ) : (
              <div className="flex items-center justify-center h-9 px-2.5 rounded-sm bg-[#1F3A8A] text-white font-bold text-sm tracking-wider">
                Elicius
              </div>
            )}
            <div className="hidden sm:block border-l border-slate-300 pl-3">
              <div className="text-xs font-bold text-[#1F3A8A] tracking-wider uppercase leading-none">
                Elicius Energy
              </div>
              <div className="text-[11px] font-medium text-slate-500 tracking-tight leading-none mt-1">
                IoT Energy Monitoring
              </div>
            </div>
          </div>

          {/* Exactly Three Navigation Tabs */}
          <nav className="flex items-center space-x-1 sm:space-x-2">
            <NavLink
              to="/config"
              className={({ isActive }) =>
                `flex items-center gap-2 px-3 sm:px-4 py-2 rounded-md text-sm font-semibold transition-colors ${
                  isActive
                    ? 'bg-[#1F3A8A] text-white shadow-xs'
                    : 'text-slate-600 hover:text-[#1F3A8A] hover:bg-slate-100'
                }`
              }
            >
              <Sliders className="w-4 h-4" />
              <span>Configuration</span>
            </NavLink>
            {user?.role.toLowerCase() === 'admin' && <NavLink to="/users" className={({ isActive }) => `flex items-center gap-2 px-3 sm:px-4 py-2 rounded-md text-sm font-semibold transition-colors ${isActive ? 'bg-[#1F3A8A] text-white shadow-xs' : 'text-slate-600 hover:text-[#1F3A8A] hover:bg-slate-100'}`}>
              <Users className="w-4 h-4" /><span>Users</span>
            </NavLink>}

            <NavLink
              to="/dashboard"
              className={({ isActive }) =>
                `flex items-center gap-2 px-3 sm:px-4 py-2 rounded-md text-sm font-semibold transition-colors ${
                  isActive
                    ? 'bg-[#1F3A8A] text-white shadow-xs'
                    : 'text-slate-600 hover:text-[#1F3A8A] hover:bg-slate-100'
                }`
              }
            >
              <LayoutDashboard className="w-4 h-4" />
              <span>Dashboard</span>
            </NavLink>

            <NavLink
              to="/reports"
              className={({ isActive }) =>
                `flex items-center gap-2 px-3 sm:px-4 py-2 rounded-md text-sm font-semibold transition-colors ${
                  isActive
                    ? 'bg-[#1F3A8A] text-white shadow-xs'
                    : 'text-slate-600 hover:text-[#1F3A8A] hover:bg-slate-100'
                }`
              }
            >
              <FileSpreadsheet className="w-4 h-4" />
              <span>Reports & Downloads</span>
            </NavLink>
          </nav>

          {/* Right Controls: Device Selector & Logout */}
          <div className="flex items-center gap-3">
            
            {/* Multi-Device Selector */}
            <div className="relative flex items-center">
              <div className="flex items-center gap-2 surface-control border border-slate-300/80 rounded-lg px-2.5 py-1.5 shadow-2xs hover:border-[#1F3A8A] transition-colors">
                <span className={`w-2.5 h-2.5 rounded-full ${statusStyle.dot} ring-2 ring-white shrink-0`} />
                <select
                  value={selectedDeviceId}
                  onChange={(e) => setSelectedDeviceId(e.target.value)}
                  className="bg-transparent text-xs font-semibold text-slate-800 pr-5 appearance-none focus:outline-hidden cursor-pointer"
                  title="Select Energy Meter Device"
                >
                  {devices.map((d) => (
                    <option key={d.device_id} value={d.device_id}>
                      {d.alias || 'Device'} · {d.device_id.slice(0, 6)}…{d.device_id.slice(-6)} ({d.status})
                    </option>
                  ))}
                  {devices.length === 0 && <option value="">No devices registered</option>}
                </select>
                <ChevronDown className="w-3.5 h-3.5 text-slate-400 absolute right-2 pointer-events-none" />
              </div>
            </div>

            {/* User & Logout */}
            <button
              onClick={logout}
              title="Sign Out"
              className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs font-medium text-slate-600 hover:text-red-700 hover:bg-red-50 border border-slate-200 hover:border-red-200 transition-colors cursor-pointer"
            >
              <LogOut className="w-3.5 h-3.5" />
              <span className="hidden md:inline">Logout</span>
            </button>
          </div>

        </div>
      </div>
    </header>
  );
};
