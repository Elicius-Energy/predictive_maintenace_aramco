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
  size?: 'sm' | 'md';
  color?: string;
}

const GaugeChart: FC<GaugeChartProps> = ({ value, min, max, unit, label, thresholds, size = 'md', color }) => {
  const percentage = Math.min(100, Math.max(0, ((value - min) / (max - min)) * 100));
  
  let colorClass = "text-primary";
  let strokeColor = color || "#22d3ee";

  if (thresholds) {
    if (value >= thresholds.critical) {
      colorClass = "text-accent-red";
      strokeColor = "#ef4444";
    } else if (value >= thresholds.warning) {
      colorClass = "text-accent-amber";
      strokeColor = "#f59e0b";
    }
  }

  const radius = 40;
  const circumference = 2 * Math.PI * radius;
  const span = 240;
  const offset = circumference - (percentage / 100) * (span / 360) * circumference;
  const rotation = 150;

  const isSmall = size === 'sm';

  return (
    <div className={cn("flex flex-col items-center justify-center relative group", isSmall ? "p-1" : "p-2")}>
      <svg className={isSmall ? "w-24 h-24" : "w-36 h-36"} viewBox="0 0 100 100">
        {/* Background track */}
        <circle
          cx="50"
          cy="50"
          r={radius}
          fill="transparent"
          stroke="rgba(255, 255, 255, 0.1)"
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
          style={{ 
            transform: `rotate(${rotation}deg)`, 
            transformOrigin: '50% 50%',
            filter: `drop-shadow(0 0 6px ${strokeColor}40)`
          }}
        />
      </svg>
      
      <div className="absolute inset-0 flex flex-col items-center justify-center pt-2">
        <span 
          className={cn("font-extrabold scada-number leading-none", !color && colorClass, isSmall ? "text-xl" : "text-2xl")}
          style={color && !thresholds ? { color: strokeColor } : undefined}
        >
          {value.toFixed(value < 10 ? 2 : 1)}
        </span>
        <span className={cn("text-gray-400 uppercase font-bold tracking-tight", isSmall ? "text-[8px]" : "text-[10px]")}>{unit}</span>
      </div>
      
      <div className={cn("mt-[-8px] font-bold text-gray-300 text-center uppercase tracking-wider", isSmall ? "text-[9px]" : "text-xs")}>{label}</div>
    </div>
  );
};

export default memo(GaugeChart);
