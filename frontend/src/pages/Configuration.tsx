import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useDevice } from '../contexts/DeviceContext';
import {
  Save, CheckCircle2, AlertCircle, ChevronDown, ChevronUp,
  Cpu, Building, Zap, Cog, Activity, UserCheck, ShieldCheck,
  IndianRupee, Sliders, Plus, Trash2
} from 'lucide-react';

export const Configuration: React.FC = () => {
  const { selectedDeviceId, refreshDevices } = useDevice();
  const [profile, setProfile] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [baselineSuccess, setBaselineSuccess] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [showRegister, setShowRegister] = useState(false);
  const [regDeviceId, setRegDeviceId] = useState('');
  const [regAlias, setRegAlias] = useState('');
  const [registering, setRegistering] = useState(false);

  // Collapsible section states (first two open by default)
  const [openSections, setOpenSections] = useState<Record<string, boolean>>({
    device: true,
    customer: true,
    motor: false,
    machine: false,
    inverter: false,
    representative: false,
    signatory: false,
    commercial: false,
    advanced: false,
  });

  const toggleSection = (sec: string) => {
    setOpenSections((prev) => ({ ...prev, [sec]: !prev[sec] }));
  };

  const fetchProfile = async () => {
    if (!selectedDeviceId) {
      setLoading(false);
      setProfile(null);
      setShowRegister(true);
      return;
    }
    setLoading(true);
    setErrorMessage(null);
    try {
      const res = await axios.get(`/api/devices/${selectedDeviceId}/profile`, { withCredentials: true });
      setProfile(res.data);
    } catch (err: any) {
      setErrorMessage(err.response?.data?.detail || 'Failed to load device profile');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProfile();
  }, [selectedDeviceId]);

  const handleInputChange = (field: string, value: any) => {
    setProfile((prev: any) => ({ ...prev, [field]: value }));
  };

  const handleThresholdChange = (key: string, value: any) => {
    setProfile((prev: any) => ({
      ...prev,
      thresholds: { ...(prev?.thresholds || {}), [key]: value },
    }));
  };

  const handleSave = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!selectedDeviceId || !profile) return;
    if (!profile.rated_efficiency_pct || profile.rated_efficiency_pct <= 0 || profile.rated_efficiency_pct > 100) {
      setErrorMessage('Rated motor efficiency from the nameplate is required (greater than 0 and up to 100%).');
      setOpenSections((prev) => ({ ...prev, motor: true }));
      return;
    }
    setSaving(true);
    setSaveSuccess(false);
    setErrorMessage(null);

    try {
      await axios.put(`/api/devices/${selectedDeviceId}/profile`, profile, { withCredentials: true });
      setSaveSuccess(true);
      refreshDevices();
      setTimeout(() => setSaveSuccess(false), 4000);
    } catch (err: any) {
      setErrorMessage(err.response?.data?.detail || 'Failed to save configuration');
    } finally {
      setSaving(false);
    }
  };

  const handleMarkBaseline = async () => {
    if (!selectedDeviceId) return;
    setBaselineSuccess(null);
    setErrorMessage(null);

    try {
      const res = await axios.post(`/api/devices/${selectedDeviceId}/mark-baseline`, {}, { withCredentials: true });
      setBaselineSuccess(res.data.message || 'Installation baseline established successfully');
      setTimeout(() => setBaselineSuccess(null), 5000);
    } catch (err: any) {
      setErrorMessage(err.response?.data?.detail || 'Could not establish baseline. Ensure motor is energized.');
    }
  };

  const handleRegisterDevice = async () => {
    if (!regDeviceId.trim() || !regAlias.trim()) {
      setErrorMessage('Please enter both Device ID and Device Name.');
      return;
    }
    setRegistering(true);
    setErrorMessage(null);
    try {
      await axios.post('/api/devices/register', {
        device_id: regDeviceId.trim(),
        alias: regAlias.trim()
      }, { withCredentials: true });
      setSaveSuccess(true);
      setRegDeviceId('');
      setRegAlias('');
      setShowRegister(false);
      refreshDevices();
      setTimeout(() => setSaveSuccess(false), 4000);
    } catch (err: any) {
      setErrorMessage(err.response?.data?.detail || 'Failed to register device');
    } finally {
      setRegistering(false);
    }
  };

  const handleDeleteDevice = async () => {
    if (!selectedDeviceId) return;
    const alias = profile?.alias || selectedDeviceId;
    if (!confirm(`Are you sure you want to delete device "${alias}"? All readings and configuration will be permanently removed.`)) return;
    setErrorMessage(null);
    try {
      await axios.delete(`/api/devices/${selectedDeviceId}`, { withCredentials: true });
      refreshDevices();
    } catch (err: any) {
      setErrorMessage(err.response?.data?.detail || 'Failed to delete device');
    }
  };

  if (loading) {
    return (
      <div className="max-w-5xl mx-auto py-12 px-4 text-center">
        <div className="inline-block animate-spin w-8 h-8 border-4 border-[#1F3A8A] border-t-transparent rounded-full" />
        <p className="mt-3 text-sm text-slate-500 font-medium">Loading configuration profile...</p>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto py-8 px-4 sm:px-6 lg:px-8 pb-28">
      
      {/* Page Header with Sticky Save Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-6 border-b border-slate-200 gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
            Device & Audit Configuration
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 mt-1">
            Parameters for <span className="font-semibold text-[#1F3A8A]">{profile?.alias || selectedDeviceId}</span> are automatically used for reports and fault detection.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {selectedDeviceId && (
            <button
              onClick={handleDeleteDevice}
              type="button"
              className="inline-flex items-center justify-center gap-1.5 px-3 py-2.5 rounded-lg border border-red-200 bg-red-50 text-red-600 font-semibold text-xs hover:bg-red-100 transition-all cursor-pointer"
              title="Delete this device"
            >
              <Trash2 className="w-3.5 h-3.5" />
              <span>Delete Device</span>
            </button>
          )}
          <button
            onClick={() => handleSave()}
            disabled={saving || !selectedDeviceId}
            className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-lg bg-[#1F3A8A] text-white font-semibold text-sm shadow-md hover:bg-[#1E3A8A] active:scale-95 disabled:opacity-50 transition-all cursor-pointer"
          >
            <Save className="w-4 h-4" />
            <span>{saving ? 'Saving...' : 'Save Configuration'}</span>
          </button>
        </div>
      </div>

      {/* Register New Device Panel */}
      <div className="mt-4">
        {!showRegister ? (
          <button
            onClick={() => setShowRegister(true)}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border-2 border-dashed border-slate-300 text-sm font-semibold text-slate-600 hover:border-[#1F3A8A] hover:text-[#1F3A8A] hover:bg-blue-50 transition-colors cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            <span>Register New Device</span>
          </button>
        ) : (
          <div className="bg-blue-50 rounded-xl border border-blue-200 p-5">
            <h3 className="text-sm font-bold text-[#1F3A8A] mb-3">Register a New Energy Meter</h3>
            <p className="text-xs text-slate-500 mb-4">
              Enter the device hardware ID (dID printed on the meter) and a friendly name. Once registered, MQTT telemetry from this device will be accepted and displayed.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Device ID (Hardware dID) *</label>
                <input
                  type="text"
                  value={regDeviceId}
                  onChange={(e) => setRegDeviceId(e.target.value)}
                  placeholder="e.g. 002D00203335471332323632"
                  className="w-full border border-slate-300 rounded-lg p-2.5 text-xs font-mono focus:border-[#1F3A8A] focus:outline-hidden"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Device Name *</label>
                <input
                  type="text"
                  value={regAlias}
                  onChange={(e) => setRegAlias(e.target.value)}
                  placeholder="e.g. Ring Frame 14 - Main Motor"
                  className="w-full border border-slate-300 rounded-lg p-2.5 text-xs focus:border-[#1F3A8A] focus:outline-hidden"
                />
              </div>
              <div className="flex items-end gap-2">
                <button
                  type="button"
                  onClick={handleRegisterDevice}
                  disabled={registering}
                  className="inline-flex items-center gap-1.5 px-4 py-2.5 rounded-lg bg-[#1F3A8A] text-white font-semibold text-xs hover:bg-[#1E3A8A] disabled:opacity-50 transition-colors cursor-pointer"
                >
                  <Plus className="w-3.5 h-3.5" />
                  {registering ? 'Registering...' : 'Register'}
                </button>
                <button
                  type="button"
                  onClick={() => { setShowRegister(false); setRegDeviceId(''); setRegAlias(''); }}
                  className="px-3 py-2.5 rounded-lg border border-slate-300 text-xs font-medium text-slate-600 hover:bg-slate-100 transition-colors cursor-pointer"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Confirmation Banner */}
      {saveSuccess && (
        <div className="mt-4 p-4 rounded-xl bg-emerald-50 border border-emerald-200 flex items-center gap-3 text-sm text-emerald-800 animate-in fade-in">
          <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
          <span className="font-medium">Configuration successfully saved and stored in database.</span>
        </div>
      )}

      {baselineSuccess && (
        <div className="mt-4 p-4 rounded-xl bg-blue-50 border border-blue-200 flex items-center gap-3 text-sm text-blue-800 animate-in fade-in">
          <CheckCircle2 className="w-5 h-5 text-blue-600 shrink-0" />
          <span className="font-medium">{baselineSuccess}</span>
        </div>
      )}

      {errorMessage && (
        <div className="mt-4 p-4 rounded-xl bg-red-50 border border-red-200 flex items-center gap-3 text-sm text-red-800 animate-in fade-in">
          <AlertCircle className="w-5 h-5 text-red-600 shrink-0" />
          <span className="font-medium">{errorMessage}</span>
        </div>
      )}

      <form onSubmit={handleSave} className="mt-6 space-y-4">

        {/* ── SECTION 1: Device ────────────────────────────────────────── */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-2xs overflow-hidden">
          <button
            type="button"
            onClick={() => toggleSection('device')}
            className="w-full px-5 py-4 flex items-center justify-between bg-slate-50 hover:bg-slate-100 transition-colors cursor-pointer text-left"
          >
            <div className="flex items-center gap-2.5 font-bold text-slate-800 text-sm">
              <Cpu className="w-4 h-4 text-[#1F3A8A]" />
              <span>1. Device Identity & Installation Status</span>
            </div>
            {openSections.device ? <ChevronUp className="w-4 h-4 text-slate-500" /> : <ChevronDown className="w-4 h-4 text-slate-500" />}
          </button>

          {openSections.device && (
            <div className="p-5 border-t border-slate-200 grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
              <div>
                <label className="block font-semibold text-slate-600 mb-1">Device ID (Hardware dID)</label>
                <input
                  type="text"
                  readOnly
                  value={profile?.device_id || ''}
                  className="w-full bg-slate-100 text-slate-600 border border-slate-200 rounded-lg p-2.5 font-mono cursor-not-allowed"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Device Alias (Name) *</label>
                <input
                  type="text"
                  required
                  value={profile?.alias || ''}
                  onChange={(e) => handleInputChange('alias', e.target.value)}
                  placeholder="e.g. Ring Frame 14 - Main Drive"
                  className="w-full border border-slate-300 rounded-lg p-2.5 focus:border-[#1F3A8A] focus:outline-hidden"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-600 mb-1">Firmware Version</label>
                <input
                  type="text"
                  readOnly
                  value={profile?.fw_ver || '13.4'}
                  className="w-full bg-slate-100 text-slate-600 border border-slate-200 rounded-lg p-2.5 font-mono cursor-not-allowed"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Nominal Voltage (V)</label>
                <input
                  type="number"
                  step="any"
                  value={profile?.nominal_voltage ?? 240.0}
                  onChange={(e) => handleInputChange('nominal_voltage', parseFloat(e.target.value))}
                  className="w-full border border-slate-300 rounded-lg p-2.5 focus:border-[#1F3A8A] focus:outline-hidden"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">CT Rated Current (A)</label>
                <input
                  type="number"
                  step="any"
                  value={profile?.ct_rated_current ?? 100.0}
                  onChange={(e) => handleInputChange('ct_rated_current', parseFloat(e.target.value))}
                  className="w-full border border-slate-300 rounded-lg p-2.5 focus:border-[#1F3A8A] focus:outline-hidden"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Installation Baseline</label>
                <button
                  type="button"
                  onClick={handleMarkBaseline}
                  className="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-semibold py-2.5 px-3 rounded-lg text-xs shadow-xs transition-colors cursor-pointer flex items-center justify-center gap-1.5"
                >
                  <ShieldCheck className="w-4 h-4" />
                  <span>Mark Installation OK</span>
                </button>
              </div>
            </div>
          )}
        </div>

        {/* ── SECTION 2: Customer Information ──────────────────────────── */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-2xs overflow-hidden">
          <button
            type="button"
            onClick={() => toggleSection('customer')}
            className="w-full px-5 py-4 flex items-center justify-between bg-slate-50 hover:bg-slate-100 transition-colors cursor-pointer text-left"
          >
            <div className="flex items-center gap-2.5 font-bold text-slate-800 text-sm">
              <Building className="w-4 h-4 text-[#1F3A8A]" />
              <span>2. Customer Information</span>
            </div>
            {openSections.customer ? <ChevronUp className="w-4 h-4 text-slate-500" /> : <ChevronDown className="w-4 h-4 text-slate-500" />}
          </button>

          {openSections.customer && (
            <div className="p-5 border-t border-slate-200 grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">Customer Name *</label>
                <input
                  type="text"
                  required
                  value={profile?.customer_name || ''}
                  onChange={(e) => handleInputChange('customer_name', e.target.value)}
                  className="w-full border border-slate-300 rounded-lg p-2.5 focus:border-[#1F3A8A] focus:outline-hidden"
                />
              </div>
              <div>
                <label className="block font-semibold text-slate-700 mb-1">Location *</label>
                <input
                  type="text"
                  required
                  value={profile?.location || ''}
                  onChange={(e) => handleInputChange('location', e.target.value)}
                  className="w-full border border-slate-300 rounded-lg p-2.5 focus:border-[#1F3A8A] focus:outline-hidden"
                />
              </div>
              <div>
                <label className="block font-semibold text-slate-700 mb-1">Department</label>
                <input
                  type="text"
                  value={profile?.department || ''}
                  onChange={(e) => handleInputChange('department', e.target.value)}
                  className="w-full border border-slate-300 rounded-lg p-2.5 focus:border-[#1F3A8A] focus:outline-hidden"
                />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Contact Person</label>
                  <input
                    type="text"
                    value={profile?.contact_person || ''}
                    onChange={(e) => handleInputChange('contact_person', e.target.value)}
                    className="w-full border border-slate-300 rounded-lg p-2.5 focus:border-[#1F3A8A] focus:outline-hidden"
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Contact Number</label>
                  <input
                    type="text"
                    value={profile?.contact_number || ''}
                    onChange={(e) => handleInputChange('contact_number', e.target.value)}
                    className="w-full border border-slate-300 rounded-lg p-2.5 focus:border-[#1F3A8A] focus:outline-hidden"
                  />
                </div>
              </div>
            </div>
          )}
        </div>

        {/* ── SECTION 3: Motor Name Plate Details ───────────────────────── */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-2xs overflow-hidden">
          <button
            type="button"
            onClick={() => toggleSection('motor')}
            className="w-full px-5 py-4 flex items-center justify-between bg-slate-50 hover:bg-slate-100 transition-colors cursor-pointer text-left"
          >
            <div className="flex items-center gap-2.5 font-bold text-slate-800 text-sm">
              <Zap className="w-4 h-4 text-[#1F3A8A]" />
              <span>3. Motor Name Plate Details</span>
            </div>
            {openSections.motor ? <ChevronUp className="w-4 h-4 text-slate-500" /> : <ChevronDown className="w-4 h-4 text-slate-500" />}
          </button>

          {openSections.motor && (
            <div className="p-5 border-t border-slate-200 grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">Motor Make</label>
                <input
                  type="text"
                  value={profile?.motor_make || ''}
                  onChange={(e) => handleInputChange('motor_make', e.target.value)}
                  className="w-full border border-slate-300 rounded-lg p-2.5 focus:border-[#1F3A8A] focus:outline-hidden"
                />
              </div>
              <div>
                <label className="block font-semibold text-slate-700 mb-1">Motor Rating (kW) *</label>
                <input
                  type="number"
                  step="any"
                  required
                  value={profile?.motor_rating_kw ?? ''}
                  onChange={(e) => handleInputChange('motor_rating_kw', parseFloat(e.target.value))}
                  className="w-full border border-slate-300 rounded-lg p-2.5 focus:border-[#1F3A8A] focus:outline-hidden"
                />
              </div>
              <div>
                <label className="block font-semibold text-slate-700 mb-1">Frame Size</label>
                <input
                  type="text"
                  value={profile?.frame_size || ''}
                  onChange={(e) => handleInputChange('frame_size', e.target.value)}
                  className="w-full border border-slate-300 rounded-lg p-2.5 focus:border-[#1F3A8A] focus:outline-hidden"
                />
              </div>
              <div>
                <label className="block font-semibold text-slate-700 mb-1">Rated Current (Amps)</label>
                <input
                  type="number"
                  step="any"
                  value={profile?.rated_current_amps ?? ''}
                  onChange={(e) => handleInputChange('rated_current_amps', parseFloat(e.target.value))}
                  className="w-full border border-slate-300 rounded-lg p-2.5 focus:border-[#1F3A8A] focus:outline-hidden"
                />
              </div>
              <div>
                <label className="block font-semibold text-slate-700 mb-1">Rated Speed (RPM)</label>
                <input
                  type="number"
                  step="any"
                  value={profile?.rated_speed_rpm ?? ''}
                  onChange={(e) => handleInputChange('rated_speed_rpm', parseFloat(e.target.value))}
                  className="w-full border border-slate-300 rounded-lg p-2.5 focus:border-[#1F3A8A] focus:outline-hidden"
                />
              </div>
              <div>
                <label className="block font-semibold text-slate-700 mb-1">Rated Voltage (V)</label>
                <input
                  type="number"
                  step="any"
                  value={profile?.rated_voltage ?? ''}
                  onChange={(e) => handleInputChange('rated_voltage', parseFloat(e.target.value))}
                  className="w-full border border-slate-300 rounded-lg p-2.5 focus:border-[#1F3A8A] focus:outline-hidden"
                />
              </div>
              <div>
                <label className="block font-semibold text-slate-700 mb-1">Rated Efficiency (%) *</label>
                <input
                  type="number"
                  step="0.01"
                  min="0.01"
                  max="100"
                  required
                  value={profile?.rated_efficiency_pct ?? ''}
                  onChange={(e) => handleInputChange('rated_efficiency_pct', e.target.value === '' ? null : parseFloat(e.target.value))}
                  className="w-full border border-slate-300 rounded-lg p-2.5 focus:border-[#1F3A8A] focus:outline-hidden"
                />
                <p className="text-[11px] text-slate-500 mt-1">Enter the efficiency (%) printed on the current motor nameplate.</p>
              </div>
              <div>
                <label className="block font-semibold text-slate-700 mb-1">Connection</label>
                <select
                  value={profile?.motor_connection || ''}
                  onChange={(e) => handleInputChange('motor_connection', e.target.value)}
                  className="w-full border border-slate-300 rounded-lg p-2.5 bg-white focus:border-[#1F3A8A] focus:outline-hidden"
                >
                  <option value="">Select connection</option>
                  <option value="Delta">Delta</option>
                  <option value="Star">Star</option>
                </select>
              </div>
              <div>
                <label className="block font-semibold text-slate-700 mb-1">Duty</label>
                <input
                  type="text"
                  value={profile?.motor_duty || ''}
                  onChange={(e) => handleInputChange('motor_duty', e.target.value)}
                  className="w-full border border-slate-300 rounded-lg p-2.5 focus:border-[#1F3A8A] focus:outline-hidden"
                />
              </div>
              <div>
                <label className="block font-semibold text-slate-700 mb-1">Motor Type</label>
                <input
                  type="text"
                  value={profile?.motor_type || 'IE3 Premium Efficiency'}
                  onChange={(e) => handleInputChange('motor_type', e.target.value)}
                  className="w-full border border-slate-300 rounded-lg p-2.5 focus:border-[#1F3A8A] focus:outline-hidden"
                />
              </div>
            </div>
          )}
        </div>

        {/* ── SECTION 4: Machine Details ───────────────────────────────── */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-2xs overflow-hidden">
          <button
            type="button"
            onClick={() => toggleSection('machine')}
            className="w-full px-5 py-4 flex items-center justify-between bg-slate-50 hover:bg-slate-100 transition-colors cursor-pointer text-left"
          >
            <div className="flex items-center gap-2.5 font-bold text-slate-800 text-sm">
              <Cog className="w-4 h-4 text-[#1F3A8A]" />
              <span>4. Machine Details</span>
            </div>
            {openSections.machine ? <ChevronUp className="w-4 h-4 text-slate-500" /> : <ChevronDown className="w-4 h-4 text-slate-500" />}
          </button>

          {openSections.machine && (
            <div className="p-5 border-t border-slate-200 grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">Machine Name</label>
                <input
                  type="text"
                  value={profile?.machine_name || 'Ring Frame 14'}
                  onChange={(e) => handleInputChange('machine_name', e.target.value)}
                  className="w-full border border-slate-300 rounded-lg p-2.5 focus:border-[#1F3A8A] focus:outline-hidden"
                />
              </div>
              <div>
                <label className="block font-semibold text-slate-700 mb-1">Make & Model</label>
                <input
                  type="text"
                  value={profile?.machine_model_no || 'LMW LR9/AXL'}
                  onChange={(e) => handleInputChange('machine_model_no', e.target.value)}
                  className="w-full border border-slate-300 rounded-lg p-2.5 focus:border-[#1F3A8A] focus:outline-hidden"
                />
              </div>
              <div>
                <label className="block font-semibold text-slate-700 mb-1">No. of Spindles</label>
                <input
                  type="number"
                  value={profile?.no_of_spindles ?? 1200}
                  onChange={(e) => handleInputChange('no_of_spindles', parseInt(e.target.value) || 0)}
                  className="w-full border border-slate-300 rounded-lg p-2.5 focus:border-[#1F3A8A] focus:outline-hidden"
                />
              </div>
            </div>
          )}
        </div>

        {/* ── SECTION 5: Inverter Details ──────────────────────────────── */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-2xs overflow-hidden">
          <button
            type="button"
            onClick={() => toggleSection('inverter')}
            className="w-full px-5 py-4 flex items-center justify-between bg-slate-50 hover:bg-slate-100 transition-colors cursor-pointer text-left"
          >
            <div className="flex items-center gap-2.5 font-bold text-slate-800 text-sm">
              <Activity className="w-4 h-4 text-[#1F3A8A]" />
              <span>5. Inverter (VFD) Details</span>
            </div>
            {openSections.inverter ? <ChevronUp className="w-4 h-4 text-slate-500" /> : <ChevronDown className="w-4 h-4 text-slate-500" />}
          </button>

          {openSections.inverter && (
            <div className="p-5 border-t border-slate-200 grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">Inverter Make</label>
                <input
                  type="text"
                  value={profile?.inverter_make || 'Danfoss'}
                  onChange={(e) => handleInputChange('inverter_make', e.target.value)}
                  className="w-full border border-slate-300 rounded-lg p-2.5 focus:border-[#1F3A8A] focus:outline-hidden"
                />
              </div>
              <div>
                <label className="block font-semibold text-slate-700 mb-1">Inverter Model</label>
                <input
                  type="text"
                  value={profile?.inverter_model || 'VLT AutomationDrive'}
                  onChange={(e) => handleInputChange('inverter_model', e.target.value)}
                  className="w-full border border-slate-300 rounded-lg p-2.5 focus:border-[#1F3A8A] focus:outline-hidden"
                />
              </div>
            </div>
          )}
        </div>

        {/* ── SECTION 6 & 7: Personnel & Signatories ───────────────────── */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-2xs overflow-hidden">
          <button
            type="button"
            onClick={() => toggleSection('representative')}
            className="w-full px-5 py-4 flex items-center justify-between bg-slate-50 hover:bg-slate-100 transition-colors cursor-pointer text-left"
          >
            <div className="flex items-center gap-2.5 font-bold text-slate-800 text-sm">
              <UserCheck className="w-4 h-4 text-[#1F3A8A]" />
              <span>6. Elicius Representative & Customer Signatory</span>
            </div>
            {openSections.representative ? <ChevronUp className="w-4 h-4 text-slate-500" /> : <ChevronDown className="w-4 h-4 text-slate-500" />}
          </button>

          {openSections.representative && (
            <div className="p-5 border-t border-slate-200 grid grid-cols-1 md:grid-cols-2 gap-6 text-xs">
              <div className="space-y-3">
                <h4 className="font-bold text-[#1F3A8A] text-xs uppercase tracking-wider">Elicius Service Personnel</h4>
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Name</label>
                  <input
                    type="text"
                    value={profile?.rep_name || 'K. Senthil Kumar'}
                    onChange={(e) => handleInputChange('rep_name', e.target.value)}
                    className="w-full border border-slate-300 rounded-lg p-2.5 focus:border-[#1F3A8A] focus:outline-hidden"
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Designation</label>
                  <input
                    type="text"
                    value={profile?.rep_designation || 'Sr. Energy Audit Engineer'}
                    onChange={(e) => handleInputChange('rep_designation', e.target.value)}
                    className="w-full border border-slate-300 rounded-lg p-2.5 focus:border-[#1F3A8A] focus:outline-hidden"
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Contact Number</label>
                  <input
                    type="text"
                    value={profile?.rep_contact_number || '+91 98422 12345'}
                    onChange={(e) => handleInputChange('rep_contact_number', e.target.value)}
                    className="w-full border border-slate-300 rounded-lg p-2.5 focus:border-[#1F3A8A] focus:outline-hidden"
                  />
                </div>
              </div>

              <div className="space-y-3">
                <h4 className="font-bold text-[#1F3A8A] text-xs uppercase tracking-wider">Customer Signatory</h4>
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Customer Signatory Name</label>
                  <input
                    type="text"
                    value={profile?.signatory_customer_name || 'M. Natarajan'}
                    onChange={(e) => handleInputChange('signatory_customer_name', e.target.value)}
                    className="w-full border border-slate-300 rounded-lg p-2.5 focus:border-[#1F3A8A] focus:outline-hidden"
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Designation</label>
                  <input
                    type="text"
                    value={profile?.signatory_designation || 'General Manager - Operations'}
                    onChange={(e) => handleInputChange('signatory_designation', e.target.value)}
                    className="w-full border border-slate-300 rounded-lg p-2.5 focus:border-[#1F3A8A] focus:outline-hidden"
                  />
                </div>
              </div>
            </div>
          )}
        </div>

        {/* ── SECTION 8: Commercial Inputs (Used for ROI) ─────────────── */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-2xs overflow-hidden">
          <button
            type="button"
            onClick={() => toggleSection('commercial')}
            className="w-full px-5 py-4 flex items-center justify-between bg-slate-50 hover:bg-slate-100 transition-colors cursor-pointer text-left"
          >
            <div className="flex items-center gap-2.5 font-bold text-slate-800 text-sm">
              <IndianRupee className="w-4 h-4 text-[#1F3A8A]" />
              <span>8. Commercial Inputs (Used for Energy Savings & ROI)</span>
            </div>
            {openSections.commercial ? <ChevronUp className="w-4 h-4 text-slate-500" /> : <ChevronDown className="w-4 h-4 text-slate-500" />}
          </button>

          {openSections.commercial && (
            <div className="p-5 border-t border-slate-200 grid grid-cols-1 md:grid-cols-4 gap-4 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">Electricity Tariff (Rs/kWh)</label>
                <input
                  type="number"
                  step="0.01"
                  value={profile?.electricity_tariff ?? ''}
                  onChange={(e) => handleInputChange('electricity_tariff', e.target.value === '' ? null : parseFloat(e.target.value))}
                  className="w-full border border-slate-300 rounded-lg p-2.5 focus:border-[#1F3A8A] focus:outline-hidden"
                />
              </div>
              <div>
                <label className="block font-semibold text-slate-700 mb-1">Annual Operating Hours</label>
                <input
                  type="number"
                  step="1"
                  value={profile?.annual_operating_hours ?? ''}
                  onChange={(e) => handleInputChange('annual_operating_hours', e.target.value === '' ? null : parseFloat(e.target.value))}
                  className="w-full border border-slate-300 rounded-lg p-2.5 focus:border-[#1F3A8A] focus:outline-hidden"
                />
              </div>
              <div>
                <label className="block font-semibold text-slate-700 mb-1">Motor Investment (Rs)</label>
                <input
                  type="number"
                  step="100"
                  value={profile?.motor_investment ?? 0}
                  onChange={(e) => handleInputChange('motor_investment', parseFloat(e.target.value))}
                  className="w-full border border-slate-300 rounded-lg p-2.5 focus:border-[#1F3A8A] focus:outline-hidden"
                />
              </div>
              <div>
                <label className="block font-semibold text-slate-700 mb-1">Installation / Retrofit Cost (Rs)</label>
                <input
                  type="number"
                  step="100"
                  value={profile?.installation_cost ?? 0}
                  onChange={(e) => handleInputChange('installation_cost', parseFloat(e.target.value))}
                  className="w-full border border-slate-300 rounded-lg p-2.5 focus:border-[#1F3A8A] focus:outline-hidden"
                />
              </div>
            </div>
          )}
        </div>

        <div className="bg-white rounded-xl border border-slate-200 shadow-2xs overflow-hidden">
          <div className="px-5 py-4 bg-slate-50 border-b border-slate-200">
            <div className="font-bold text-slate-800 text-sm">Replacement Motor Comparison (Optional)</div>
            <p className="text-xs text-slate-500 mt-1">Provide a candidate motor nameplate to calculate savings using measured loading and operating hours.</p>
          </div>
          <div className="p-5 grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
            <div>
              <label className="block font-semibold text-slate-700 mb-1">Candidate Motor Rating (kW)</label>
              <input type="number" min="0" step="any" value={profile?.replacement_motor_rating_kw ?? ''} onChange={(e) => handleInputChange('replacement_motor_rating_kw', e.target.value === '' ? null : parseFloat(e.target.value))} className="w-full border border-slate-300 rounded-lg p-2.5" />
            </div>
            <div>
              <label className="block font-semibold text-slate-700 mb-1">Candidate Motor Efficiency (%)</label>
              <input type="number" min="0.01" max="100" step="0.01" value={profile?.replacement_motor_efficiency_pct ?? ''} onChange={(e) => handleInputChange('replacement_motor_efficiency_pct', e.target.value === '' ? null : parseFloat(e.target.value))} className="w-full border border-slate-300 rounded-lg p-2.5" />
            </div>
          </div>
        </div>

        {/* ── SECTION 9: Advanced & Alert Thresholds (Collapsed by default) */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-2xs overflow-hidden">
          <button
            type="button"
            onClick={() => toggleSection('advanced')}
            className="w-full px-5 py-4 flex items-center justify-between bg-slate-50 hover:bg-slate-100 transition-colors cursor-pointer text-left"
          >
            <div className="flex items-center gap-2.5 font-bold text-slate-800 text-sm">
              <Sliders className="w-4 h-4 text-[#1F3A8A]" />
              <span>9. Advanced Thresholds & Alarm Engine (Engineering Settings)</span>
            </div>
            {openSections.advanced ? <ChevronUp className="w-4 h-4 text-slate-500" /> : <ChevronDown className="w-4 h-4 text-slate-500" />}
          </button>

          {openSections.advanced && (
            <div className="p-5 border-t border-slate-200 space-y-4 text-xs">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Idle Power Threshold (kW)</label>
                  <input
                    type="number"
                    step="0.01"
                    placeholder={`Default: ${(profile?.motor_rating_kw ? profile.motor_rating_kw * 0.05 : 0.2).toFixed(2)} kW (5%)`}
                    value={profile?.idle_threshold_kw ?? ''}
                    onChange={(e) => handleInputChange('idle_threshold_kw', e.target.value === '' ? null : parseFloat(e.target.value))}
                    className="w-full border border-slate-300 rounded-lg p-2.5 focus:border-[#1F3A8A] focus:outline-hidden"
                  />
                  <p className="text-[11px] text-slate-400 mt-1">Slices below this power are counted as Idle Time.</p>
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Active Current Threshold (A)</label>
                  <input
                    type="number"
                    step="0.1"
                    value={profile?.thresholds?.active_current_a ?? 1.0}
                    onChange={(e) => handleThresholdChange('active_current_a', parseFloat(e.target.value))}
                    className="w-full border border-slate-300 rounded-lg p-2.5 focus:border-[#1F3A8A] focus:outline-hidden"
                  />
                  <p className="text-[11px] text-slate-400 mt-1">Minimum current to evaluate phase polarity.</p>
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Debounce Sample Count</label>
                  <input
                    type="number"
                    step="1"
                    value={profile?.thresholds?.debounce_raise_count ?? 3}
                    onChange={(e) => handleThresholdChange('debounce_raise_count', parseInt(e.target.value))}
                    className="w-full border border-slate-300 rounded-lg p-2.5 focus:border-[#1F3A8A] focus:outline-hidden"
                  />
                  <p className="text-[11px] text-slate-400 mt-1">Consecutive bad packets required to raise alarm.</p>
                </div>
              </div>

              <div className="pt-3 border-t border-slate-100 flex items-center justify-between">
                <div>
                  <div className="font-semibold text-slate-800 text-xs">Email Notifications</div>
                  <div className="text-[11px] text-slate-500">Dispatch alerts via SMTP when wiring fault is detected.</div>
                </div>
                <input
                  type="checkbox"
                  checked={profile?.email_alerts_enabled || false}
                  onChange={(e) => handleInputChange('email_alerts_enabled', e.target.checked)}
                  className="w-4 h-4 text-[#1F3A8A] rounded-sm focus:ring-[#1F3A8A]"
                />
              </div>
            </div>
          )}
        </div>

        {/* Sticky Save Footer */}
        <div className="fixed bottom-0 left-0 right-0 z-30 bg-white/95 backdrop-blur-md border-t border-slate-200 py-3.5 px-4 shadow-lg flex items-center justify-between max-w-5xl mx-auto rounded-t-xl">
          <div className="text-xs text-slate-500 font-medium">
            Changes apply to <span className="font-semibold text-slate-700">{profile?.alias || selectedDeviceId}</span>
          </div>
          <button
            type="submit"
            disabled={saving}
            className="inline-flex items-center gap-2 px-6 py-2 rounded-lg bg-[#1F3A8A] text-white font-semibold text-sm shadow-md hover:bg-[#1E3A8A] active:scale-95 disabled:opacity-50 transition-all cursor-pointer"
          >
            <Save className="w-4 h-4" />
            <span>{saving ? 'Saving...' : 'Save All Settings'}</span>
          </button>
        </div>

      </form>
    </div>
  );
};
export default Configuration;
