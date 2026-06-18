import { memo } from 'react';
import type { FC } from 'react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

interface GaugeChartProps {
  value: number;
  min: number;
  max: number;
  unit: string;
  label: string;
  thresholds?: { warning: number; critical: number };
}

const GaugeChart: FC<GaugeChartProps> = ({ value, min, max, unit, label, thresholds }) => {
  const percentage = Math.min(100, Math.max(0, ((value - min) / (max - min)) * 100));
  
  let colorClass = "text-primary";
  let strokeColor = "#0891b2";

  if (thresholds) {
    if (value >= thresholds.critical) {
      colorClass = "text-accent-red";
      strokeColor = "#dc2626";
    } else if (value >= thresholds.warning) {
      colorClass = "text-accent-amber";
      strokeColor = "#d97706";
    }
  }

  const radius = 40;
  const circumference = 2 * Math.PI * radius;
  const span = 240;
  const offset = circumference - (percentage / 100) * (span / 360) * circumference;
  const rotation = 150;

  return (
    <div className="flex flex-col items-center justify-center p-2 relative group">
      <svg className="w-36 h-36" viewBox="0 0 100 100">
        {/* Background track */}
        <circle
          cx="50"
          cy="50"
          r={radius}
          fill="transparent"
          stroke="#e2e8f0"
          strokeWidth="7"
          strokeDasharray={`${(span / 360) * circumference} ${circumference}`}
          strokeDashoffset="0"
          strokeLinecap="round"
          style={{ transform: `rotate(${rotation}deg)`, transformOrigin: '50% 50%' }}
        />
        {/* Progress Fill */}
        <circle
          cx="50"
          cy="50"
          r={radius}
          fill="transparent"
          stroke={strokeColor}
          strokeWidth="7"
          strokeDasharray={`${(span / 360) * circumference} ${circumference}`}
          strokeDashoffset={offset}
          strokeLinecap="round"
          className="transition-all duration-1000 ease-out"
          style={{ transform: `rotate(${rotation}deg)`, transformOrigin: '50% 50%' }}
        />
      </svg>
      
      <div className="absolute inset-0 flex flex-col items-center justify-center pt-2">
        <span className={cn("text-2xl font-extrabold scada-number leading-none", colorClass)}>
          {value.toFixed(value < 10 ? 2 : 1)}
        </span>
        <span className="text-[10px] text-text-muted uppercase font-bold tracking-tight">{unit}</span>
      </div>
      
      <div className="mt-[-8px] text-xs font-bold text-text-secondary text-center uppercase tracking-wider">{label}</div>
    </div>
  );
};

export default memo(GaugeChart);
