import { useState } from 'react';
import type { FC } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMotorDetails } from '../contexts/MotorDetailsContext';
import type { MotorDetails } from '../contexts/MotorDetailsContext';
import { useMachine } from '../contexts/MachineContext';
import {
  Cpu,
  MapPin,
  Settings2,
  Zap,
  DollarSign,
  Upload,
  Image as ImageIcon,
  ChevronRight,
  X,
  Info,
  RotateCcw
} from 'lucide-react';

interface MotorDetailsFormProps {
  onClose?: () => void;
  onSuccess?: () => void;
}

const MotorDetailsForm: FC<MotorDetailsFormProps> = ({ onClose, onSuccess }) => {
  const navigate = useNavigate();
  const { activeMachine } = useMachine();
  const { motorDetails, saveMotorDetails, resetMotorDetails, isMotorConfigured } = useMotorDetails();

  const [form, setForm] = useState<MotorDetails>(motorDetails || {
    motorName: '',
    location: '',
    connectedLoad: '',
    motorType: 'Induction Motor',
    manufacturer: '',
    ratedPower: 0,
    ratedSpeed: 0,
    ratedEfficiency: 0,
    motorPrice: 0,
    electricityCost: 0,
    nameplateImage: null,
  });

  const [imagePreview, setImagePreview] = useState<string | null>(form.nameplateImage);
  const [dragActive, setDragActive] = useState(false);

  const handleChange = (field: keyof MotorDetails, value: string | number) => {
    setForm(prev => ({ ...prev, [field]: value }));
  };

  const handleImageUpload = (file: File) => {
    if (!file.type.startsWith('image/')) return;
    const reader = new FileReader();
    reader.onload = () => {
      const dataUrl = reader.result as string;
      setImagePreview(dataUrl);
      setForm(prev => ({ ...prev, nameplateImage: dataUrl }));
    };
    reader.readAsDataURL(file);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(false);
    if (e.dataTransfer.files?.[0]) {
      handleImageUpload(e.dataTransfer.files[0]);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await saveMotorDetails(form);
      if (onSuccess) onSuccess();
      else navigate('/dashboard/mechanical');
    } catch (err) {
      alert("Failed to save motor configuration.");
    }
  };

  const handleReset = async () => {
    if (window.confirm("Are you sure you want to clear the saved motor configuration? This will reset efficiency and ROI calculations.")) {
      try {
        await resetMotorDetails();
        setForm({
          motorName: '',
          location: '',
          connectedLoad: '',
          motorType: 'Induction Motor',
          manufacturer: '',
          ratedPower: 0,
          ratedSpeed: 0,
          ratedEfficiency: 0,
          motorPrice: 0,
          electricityCost: 0,
          nameplateImage: null,
        });
        setImagePreview(null);
      } catch (err) {
        alert("Failed to reset configuration.");
      }
    }
  };

  const isValid = form.motorName.trim() !== '' && form.ratedPower > 0 && form.ratedSpeed > 0 && form.ratedEfficiency > 0;

  return (
    <div className="fixed inset-0 z-[100] bg-surface/95 backdrop-blur-sm overflow-y-auto font-sans py-10 px-4">
      <div className="w-full max-w-5xl mx-auto bg-surface-muted rounded-2xl shadow-2xl overflow-hidden border border-border relative">
        {/* Hero header */}
        <div className="bg-gradient-to-br from-primary-dark via-primary to-cyan-400 text-white relative">
          {onClose && (
            <button onClick={onClose} className="absolute top-4 right-4 p-2 bg-white/10 hover:bg-white/20 rounded-full transition-colors">
              <X size={20} className="text-white" />
            </button>
          )}
          <div className="px-8 py-10">
            <div className="flex items-center gap-4 mb-4">
              <div className="w-14 h-14 rounded-2xl bg-white/15 backdrop-blur-sm flex items-center justify-center border border-white/20">
                <Cpu size={28} className="text-white" />
              </div>
              <div>
                <h1 className="text-3xl font-extrabold tracking-tight">Motor Configuration</h1>
                <p className="text-cyan-100 text-sm font-medium mt-1">
                  Enter motor nameplate data to enable efficiency analysis & ROI calculations
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2 mt-6">
              <div className="flex items-center gap-2 px-3 py-1.5 bg-white/10 rounded-full text-xs font-bold">
                <div className="w-2 h-2 rounded-full bg-cyan-300 animate-pulse" />
                Asset: {activeMachine?.name || activeMachine?.machine_id || 'Unknown'}
              </div>
              <span className="text-cyan-200 text-xs">•</span>
              <span className="text-cyan-200 text-xs font-medium">Motor Setup</span>
            </div>
          </div>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="max-w-5xl mx-auto px-8 py-10 space-y-8">

          {/* ── Motor Identity ── */}
          <div className="industrial-card p-6 space-y-5">
            <div className="flex items-center gap-2 mb-1">
              <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center">
                <Settings2 size={16} className="text-primary" />
              </div>
              <h2 className="text-sm font-extrabold uppercase tracking-wider text-text-primary">Motor Identity</h2>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              {/* Motor Name */}
              <div>
                <label className="block text-xs font-bold text-text-secondary uppercase tracking-wide mb-1.5">
                  Motor Name <span className="text-accent-red">*</span>
                </label>
                <input
                  type="text"
                  value={form.motorName}
                  onChange={(e) => handleChange('motorName', e.target.value)}
                  placeholder="e.g. P-105 Centrifugal Pump Motor"
                  className="w-full px-4 py-3 rounded-xl border border-border bg-surface focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary text-sm font-medium text-text-primary placeholder-text-muted transition-all"
                  required
                />
              </div>
              {/* Location */}
              <div>
                <label className="block text-xs font-bold text-text-secondary uppercase tracking-wide mb-1.5">
                  Location / Plant Area
                </label>
                <div className="relative">
                  <MapPin size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
                  <input
                    type="text"
                    value={form.location}
                    onChange={(e) => handleChange('location', e.target.value)}
                    placeholder="e.g. Processing Unit 3"
                    className="w-full pl-9 pr-4 py-3 rounded-xl border border-border bg-surface focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary text-sm font-medium text-text-primary placeholder-text-muted transition-all"
                  />
                </div>
              </div>
              {/* Connected Load */}
              <div>
                <label className="block text-xs font-bold text-text-secondary uppercase tracking-wide mb-1.5">
                  Connected Load / Machine
                </label>
                <input
                  type="text"
                  value={form.connectedLoad}
                  onChange={(e) => handleChange('connectedLoad', e.target.value)}
                  placeholder="e.g. Centrifugal Pump"
                  className="w-full px-4 py-3 rounded-xl border border-border bg-surface focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary text-sm font-medium text-text-primary placeholder-text-muted transition-all"
                />
              </div>
              {/* Motor Type */}
              <div>
                <label className="block text-xs font-bold text-text-secondary uppercase tracking-wide mb-1.5">
                  Type of Motor
                </label>
                <select
                  value={form.motorType}
                  onChange={(e) => handleChange('motorType', e.target.value)}
                  className="w-full px-4 py-3 rounded-xl border border-border bg-surface focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary text-sm font-medium text-text-primary transition-all appearance-none cursor-pointer"
                >
                  <option value="Induction Motor">Induction Motor</option>
                  <option value="SynRM">SynRM</option>
                </select>
              </div>
              {/* Manufacturer */}
              <div className="md:col-span-2">
                <label className="block text-xs font-bold text-text-secondary uppercase tracking-wide mb-1.5">
                  Manufacturer
                </label>
                <input
                  type="text"
                  value={form.manufacturer}
                  onChange={(e) => handleChange('manufacturer', e.target.value)}
                  placeholder="e.g. ABB, Siemens, WEG"
                  className="w-full px-4 py-3 rounded-xl border border-border bg-surface focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary text-sm font-medium text-text-primary placeholder-text-muted transition-all"
                />
              </div>
            </div>
          </div>

          {/* ── Nameplate Electrical & Performance Data ── */}
          <div className="industrial-card p-6 space-y-5">
            <div className="flex items-center gap-2 mb-1">
              <div className="w-8 h-8 rounded-lg bg-cyan-500/10 flex items-center justify-center">
                <Zap size={16} className="text-cyan-600" />
              </div>
              <h2 className="text-sm font-extrabold uppercase tracking-wider text-text-primary">Nameplate Electrical & Performance</h2>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              {/* Rated Power */}
              <div>
                <label className="block text-xs font-bold text-text-secondary uppercase tracking-wide mb-1.5">
                  Rated Power (kW) <span className="text-accent-red">*</span>
                </label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  value={form.ratedPower || ''}
                  onChange={(e) => handleChange('ratedPower', parseFloat(e.target.value) || 0)}
                  placeholder="e.g. 7.5"
                  className="w-full px-4 py-3 rounded-xl border border-border bg-surface focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary text-sm font-mono font-bold text-text-primary placeholder-text-muted transition-all"
                  required
                />
              </div>
              {/* Rated Efficiency */}
              <div>
                <label className="block text-xs font-bold text-text-secondary uppercase tracking-wide mb-1.5">
                  Rated Efficiency (%) <span className="text-accent-red">*</span>
                </label>
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  max="100"
                  value={form.ratedEfficiency || ''}
                  onChange={(e) => handleChange('ratedEfficiency', parseFloat(e.target.value) || 0)}
                  placeholder="e.g. 91.5"
                  className="w-full px-4 py-3 rounded-xl border border-border bg-surface focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary text-sm font-mono font-bold text-text-primary placeholder-text-muted transition-all"
                  required
                />
              </div>
              {/* Rated Speed */}
              <div>
                <label className="block text-xs font-bold text-text-secondary uppercase tracking-wide mb-1.5">
                  Rated Speed (RPM) <span className="text-accent-red">*</span>
                </label>
                <input
                  type="number"
                  step="1"
                  min="0"
                  value={form.ratedSpeed || ''}
                  onChange={(e) => handleChange('ratedSpeed', parseInt(e.target.value) || 0)}
                  placeholder="e.g. 1475"
                  className="w-full px-4 py-3 rounded-xl border border-border bg-surface focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary text-sm font-mono font-bold text-text-primary placeholder-text-muted transition-all"
                  required
                />
              </div>
              {/* Motor Price */}
              <div>
                <label className="block text-xs font-bold text-text-secondary uppercase tracking-wide mb-1.5">
                  Motor Price (₹)
                </label>
                <div className="relative">
                  <DollarSign size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
                  <input
                    type="number"
                    step="1"
                    min="0"
                    value={form.motorPrice || ''}
                    onChange={(e) => handleChange('motorPrice', parseFloat(e.target.value) || 0)}
                    placeholder="e.g. 150000"
                    className="w-full pl-9 pr-4 py-3 rounded-xl border border-border bg-surface focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary text-sm font-mono font-bold text-text-primary placeholder-text-muted transition-all"
                  />
                </div>
              </div>
              {/* Unit Cost of Electricity */}
              <div>
                <label className="block text-xs font-bold text-text-secondary uppercase tracking-wide mb-1.5">
                  Unit Cost of Electricity (₹/kWh)
                </label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  value={form.electricityCost || ''}
                  onChange={(e) => handleChange('electricityCost', parseFloat(e.target.value) || 0)}
                  placeholder="e.g. 8.5"
                  className="w-full px-4 py-3 rounded-xl border border-border bg-surface focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary text-sm font-mono font-bold text-text-primary placeholder-text-muted transition-all"
                />
              </div>
            </div>
          </div>

          {/* ── Nameplate Image Upload ── */}
          <div className="industrial-card p-6 space-y-5">
            <div className="flex items-center gap-2 mb-1">
              <div className="w-8 h-8 rounded-lg bg-violet-500/10 flex items-center justify-center">
                <ImageIcon size={16} className="text-violet-600" />
              </div>
              <h2 className="text-sm font-extrabold uppercase tracking-wider text-text-primary">Nameplate Image</h2>
            </div>

            {imagePreview ? (
              <div className="relative rounded-xl overflow-hidden border border-border bg-surface-muted">
                <img src={imagePreview} alt="Nameplate" className="w-full max-h-80 object-contain p-4" />
                <button
                  type="button"
                  onClick={() => { setImagePreview(null); setForm(prev => ({ ...prev, nameplateImage: null })); }}
                  className="absolute top-3 right-3 w-8 h-8 bg-white/90 rounded-full flex items-center justify-center shadow-md hover:bg-white transition-colors"
                >
                  <X size={16} className="text-text-secondary" />
                </button>
              </div>
            ) : (
              <div
                onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
                onDragLeave={() => setDragActive(false)}
                onDrop={handleDrop}
                className={`
                border-2 border-dashed rounded-xl p-10 flex flex-col items-center justify-center gap-3 transition-all cursor-pointer
                ${dragActive
                    ? 'border-primary bg-primary/5'
                    : 'border-border bg-surface-muted hover:border-primary/40 hover:bg-surface'}
              `}
                onClick={() => document.getElementById('nameplate-upload')?.click()}
              >
                <div className="w-14 h-14 rounded-xl bg-surface flex items-center justify-center border border-border">
                  <Upload size={24} className="text-text-muted" />
                </div>
                <p className="text-sm font-bold text-text-secondary">
                  Drop nameplate image here or <span className="text-primary">browse</span>
                </p>
                <p className="text-xs text-text-muted">Supports JPG, PNG, WEBP up to 5MB</p>
                <input
                  id="nameplate-upload"
                  type="file"
                  accept="image/*"
                  className="hidden"
                  onChange={(e) => {
                    if (e.target.files?.[0]) handleImageUpload(e.target.files[0]);
                  }}
                />
              </div>
            )}
          </div>

          {/* ── Info notice ── */}
          <div className="flex items-start gap-3 p-4 bg-cyan-50 rounded-xl border border-cyan-200">
            <Info size={18} className="text-primary flex-shrink-0 mt-0.5" />
            <p className="text-xs text-primary font-medium leading-relaxed">
              Motor nameplate data is used for efficiency calculations on the dashboard. Ensure rated power and
              efficiency match the manufacturer's specifications. Data is saved locally in your browser.
            </p>
          </div>

          {/* ── Form Actions ── */}
          <div className="flex justify-between items-center border-t border-border pt-6">
            <div>
              {isMotorConfigured && (
                <button
                  type="button"
                  onClick={handleReset}
                  className="px-6 py-3.5 rounded-xl text-sm font-bold text-accent-red bg-accent-red-light border border-red-200 hover:bg-red-100 transition-all flex items-center gap-2"
                >
                  <RotateCcw size={16} />
                  Reset Configuration
                </button>
              )}
            </div>
            <div className="flex gap-4">
              <button
                type="button"
                onClick={() => {
                  if (onClose) onClose();
                  else navigate('/machines');
                }}
                className="px-8 py-3.5 rounded-xl text-sm font-bold text-text-secondary bg-surface border border-border hover:bg-surface-muted transition-all"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={!isValid}
                className="px-10 py-3.5 rounded-xl text-sm font-extrabold text-white bg-gradient-to-r from-primary to-cyan-500 hover:from-primary-dark hover:to-primary shadow-lg shadow-primary/20 hover:shadow-primary/40 transition-all disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-2"
              >
                Save & Continue
                <ChevronRight size={16} />
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
};

export default MotorDetailsForm;
