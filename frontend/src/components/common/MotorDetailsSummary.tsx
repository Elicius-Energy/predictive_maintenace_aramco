import { useState } from 'react';
import type { FC } from 'react';
import { useMotorDetails } from '../../contexts/MotorDetailsContext';
import { ChevronDown, ChevronUp, Cpu, Zap, MapPin } from 'lucide-react';

const MotorDetailsSummary: FC = () => {
  const { motorDetails, isMotorConfigured } = useMotorDetails();
  const [isExpanded, setIsExpanded] = useState(false);

  if (!isMotorConfigured || !motorDetails) return null;

  return (
    <div className="industrial-card border-l-4 border-l-primary overflow-hidden transition-all duration-300">
      {/* Collapsed header — always visible */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between px-5 py-3 hover:bg-surface-muted transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center">
            <Cpu size={16} className="text-primary" />
          </div>
          <div className="text-left">
            <p className="text-sm font-bold text-text-primary">{motorDetails.motorName}</p>
            <p className="text-[10px] text-text-muted font-medium">
              {motorDetails.motorType} · {motorDetails.ratedPower} kW · η {motorDetails.ratedEfficiency}%
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-[10px] text-primary font-bold uppercase tracking-wider bg-primary/10 px-2 py-0.5 rounded">
            Configured
          </span>
          {isExpanded ? (
            <ChevronUp size={16} className="text-text-muted" />
          ) : (
            <ChevronDown size={16} className="text-text-muted" />
          )}
        </div>
      </button>

      {/* Expanded details */}
      {isExpanded && (
        <div className="px-5 pb-4 pt-2 border-t border-border bg-surface-muted/50 space-y-3">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="p-3 rounded-lg bg-surface border border-border">
              <p className="text-[9px] font-bold text-text-muted uppercase tracking-wider">Motor Type</p>
              <p className="text-sm font-bold text-text-primary mt-0.5">{motorDetails.motorType}</p>
            </div>
            <div className="p-3 rounded-lg bg-surface border border-border">
              <p className="text-[9px] font-bold text-text-muted uppercase tracking-wider">Rated Power</p>
              <p className="text-sm font-mono font-bold text-text-primary mt-0.5">{motorDetails.ratedPower} kW</p>
            </div>
            <div className="p-3 rounded-lg bg-surface border border-border">
              <p className="text-[9px] font-bold text-text-muted uppercase tracking-wider">Rated η</p>
              <p className="text-sm font-mono font-bold text-primary mt-0.5">{motorDetails.ratedEfficiency}%</p>
            </div>
            <div className="p-3 rounded-lg bg-surface border border-border">
              <p className="text-[9px] font-bold text-text-muted uppercase tracking-wider">Motor Price</p>
              <p className="text-sm font-mono font-bold text-text-primary mt-0.5">₹{motorDetails.motorPrice.toLocaleString()}</p>
            </div>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {motorDetails.location && (
              <div className="p-3 rounded-lg bg-surface border border-border">
                <p className="text-[9px] font-bold text-text-muted uppercase tracking-wider flex items-center gap-1">
                  <MapPin size={9} /> Location
                </p>
                <p className="text-sm font-medium text-text-primary mt-0.5">{motorDetails.location}</p>
              </div>
            )}
            {motorDetails.connectedLoad && (
              <div className="p-3 rounded-lg bg-surface border border-border">
                <p className="text-[9px] font-bold text-text-muted uppercase tracking-wider">Connected Load</p>
                <p className="text-sm font-medium text-text-primary mt-0.5">{motorDetails.connectedLoad}</p>
              </div>
            )}
            {motorDetails.manufacturer && (
              <div className="p-3 rounded-lg bg-surface border border-border">
                <p className="text-[9px] font-bold text-text-muted uppercase tracking-wider">Manufacturer</p>
                <p className="text-sm font-medium text-text-primary mt-0.5">{motorDetails.manufacturer}</p>
              </div>
            )}
            {motorDetails.electricityCost > 0 && (
              <div className="p-3 rounded-lg bg-surface border border-border">
                <p className="text-[9px] font-bold text-text-muted uppercase tracking-wider flex items-center gap-1">
                  <Zap size={9} /> Elec. Cost
                </p>
                <p className="text-sm font-mono font-bold text-text-primary mt-0.5">₹{motorDetails.electricityCost}/kWh</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default MotorDetailsSummary;
