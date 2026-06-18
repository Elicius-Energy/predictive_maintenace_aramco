import { memo } from 'react';
import type { FC } from 'react';

interface PhasorDiagramProps {
  v1: number;
  v2: number;
  v3: number;
  i1?: number;
  i2?: number;
  i3?: number;
}

const PHASE_COLORS = {
  L1: '#ef4444',
  L1_light: '#fca5a5',
  L2: '#f59e0b',
  L2_light: '#fcd34d',
  L3: '#3b82f6',
  L3_light: '#93c5fd',
};

const PhasorDiagram: FC<PhasorDiagramProps> = ({ v1, v2, v3, i1 = 0, i2 = 0, i3 = 0 }) => {
  const cx = 120;
  const cy = 120;

  const vMax = Math.max(v1, v2, v3, 1); // avoid /0
  const vScale = 75 / vMax;

  const iMax = Math.max(i1, i2, i3, 1);
  const iScale = 45 / iMax;

  // Standard 3-phase angles (degrees) — L1 at top, 120° apart
  const vAngles = { L1: -90, L2: 150, L3: 30 };
  // Current vectors lag by ~25° (typical inductive load)
  const iAngles = { L1: -65, L2: 175, L3: 55 };

  const endpoint = (mag: number, angleDeg: number) => {
    const r = (angleDeg * Math.PI) / 180;
    return { x: cx + mag * Math.cos(r), y: cy + mag * Math.sin(r) };
  };

  const vp1 = endpoint(v1 * vScale, vAngles.L1);
  const vp2 = endpoint(v2 * vScale, vAngles.L2);
  const vp3 = endpoint(v3 * vScale, vAngles.L3);

  const ip1 = endpoint(i1 * iScale, iAngles.L1);
  const ip2 = endpoint(i2 * iScale, iAngles.L2);
  const ip3 = endpoint(i3 * iScale, iAngles.L3);

  const renderVector = (
    id: string,
    from: { x: number; y: number },
    to: { x: number; y: number },
    color: string,
    width: number,
    dashed?: boolean
  ) => (
    <line
      key={id}
      x1={from.x}
      y1={from.y}
      x2={to.x}
      y2={to.y}
      stroke={color}
      strokeWidth={width}
      strokeDasharray={dashed ? '5 3' : undefined}
      markerEnd={`url(#arrow-${id})`}
      style={{ transition: 'all 0.8s cubic-bezier(.4,0,.2,1)' }}
    />
  );

  const renderArrowDef = (id: string, color: string) => (
    <marker
      key={`marker-${id}`}
      id={`arrow-${id}`}
      markerWidth="8"
      markerHeight="8"
      refX="7"
      refY="4"
      orient="auto"
    >
      <path d="M0,0 L8,4 L0,8 Z" fill={color} />
    </marker>
  );

  const origin = { x: cx, y: cy };

  return (
    <div className="flex flex-col items-center justify-center w-full h-full min-h-[250px] relative">
      <svg viewBox="0 0 240 240" className="w-full h-full max-w-[260px]">
        <defs>
          {renderArrowDef('vL1', PHASE_COLORS.L1)}
          {renderArrowDef('vL2', PHASE_COLORS.L2)}
          {renderArrowDef('vL3', PHASE_COLORS.L3)}
          {renderArrowDef('iL1', PHASE_COLORS.L1_light)}
          {renderArrowDef('iL2', PHASE_COLORS.L2_light)}
          {renderArrowDef('iL3', PHASE_COLORS.L3_light)}
          {/* Glow filters */}
          <filter id="glowL1" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feFlood floodColor={PHASE_COLORS.L1} floodOpacity="0.4" />
            <feComposite in2="blur" operator="in" />
            <feMerge><feMergeNode /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
          <filter id="glowL2" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feFlood floodColor={PHASE_COLORS.L2} floodOpacity="0.4" />
            <feComposite in2="blur" operator="in" />
            <feMerge><feMergeNode /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
          <filter id="glowL3" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feFlood floodColor={PHASE_COLORS.L3} floodOpacity="0.4" />
            <feComposite in2="blur" operator="in" />
            <feMerge><feMergeNode /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
          <radialGradient id="centerGlow">
            <stop offset="0%" stopColor="#64748b" stopOpacity="0.3" />
            <stop offset="100%" stopColor="#64748b" stopOpacity="0" />
          </radialGradient>
        </defs>

        {/* Background rings */}
        <circle cx={cx} cy={cy} r="90" fill="none" stroke="#e2e8f0" strokeWidth="0.5" opacity="0.6" />
        <circle cx={cx} cy={cy} r="60" fill="none" stroke="#e2e8f0" strokeWidth="0.5" opacity="0.4" />
        <circle cx={cx} cy={cy} r="30" fill="none" stroke="#e2e8f0" strokeWidth="0.5" opacity="0.3" />

        {/* Axis cross-hairs */}
        <line x1={cx} y1="25" x2={cx} y2="215" stroke="#f1f5f9" strokeWidth="0.5" />
        <line x1="25" y1={cy} x2="215" y2={cy} stroke="#f1f5f9" strokeWidth="0.5" />

        {/* Center glow */}
        <circle cx={cx} cy={cy} r="15" fill="url(#centerGlow)" />

        {/* Voltage Vectors (solid, thick, glowing) */}
        <g filter="url(#glowL1)">{renderVector('vL1', origin, vp1, PHASE_COLORS.L1, 3)}</g>
        <g filter="url(#glowL2)">{renderVector('vL2', origin, vp2, PHASE_COLORS.L2, 3)}</g>
        <g filter="url(#glowL3)">{renderVector('vL3', origin, vp3, PHASE_COLORS.L3, 3)}</g>

        {/* Current Vectors (dashed, thinner) */}
        {i1 > 0 && renderVector('iL1', origin, ip1, PHASE_COLORS.L1_light, 2, true)}
        {i2 > 0 && renderVector('iL2', origin, ip2, PHASE_COLORS.L2_light, 2, true)}
        {i3 > 0 && renderVector('iL3', origin, ip3, PHASE_COLORS.L3_light, 2, true)}

        {/* Voltage labels */}
        <text x={vp1.x} y={vp1.y - 8} fill={PHASE_COLORS.L1} fontSize="11" fontWeight="800" textAnchor="middle" dominantBaseline="auto">
          L1
        </text>
        <text x={vp1.x} y={vp1.y - 19} fill={PHASE_COLORS.L1} fontSize="8" fontWeight="600" textAnchor="middle" opacity="0.8">
          {v1.toFixed(0)}V
        </text>

        <text x={vp2.x + 12} y={vp2.y + 5} fill={PHASE_COLORS.L2} fontSize="11" fontWeight="800" textAnchor="start">
          L2
        </text>
        <text x={vp2.x + 12} y={vp2.y + 16} fill={PHASE_COLORS.L2} fontSize="8" fontWeight="600" textAnchor="start" opacity="0.8">
          {v2.toFixed(0)}V
        </text>

        <text x={vp3.x - 12} y={vp3.y + 5} fill={PHASE_COLORS.L3} fontSize="11" fontWeight="800" textAnchor="end">
          L3
        </text>
        <text x={vp3.x - 12} y={vp3.y + 16} fill={PHASE_COLORS.L3} fontSize="8" fontWeight="600" textAnchor="end" opacity="0.8">
          {v3.toFixed(0)}V
        </text>

        {/* Center dot */}
        <circle cx={cx} cy={cy} r="4" fill="#475569" />
        <circle cx={cx} cy={cy} r="2" fill="#f8fafc" />
      </svg>

      {/* Legend */}
      <div className="flex gap-4 mt-1 text-[10px] font-semibold text-text-secondary">
        <span className="flex items-center gap-1">
          <span className="w-4 h-[2px] bg-[#ef4444] inline-block rounded"></span>
          V (solid)
        </span>
        <span className="flex items-center gap-1">
          <span className="w-4 h-[2px] border-t-2 border-dashed border-[#fca5a5] inline-block"></span>
          I (dashed)
        </span>
      </div>
    </div>
  );
};

export default memo(PhasorDiagram);
