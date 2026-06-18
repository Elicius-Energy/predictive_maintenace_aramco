import { memo } from 'react';
import type { FC } from 'react';

interface PowerTriangleProps {
  kw: number;
  kvar: number;
  kva: number;
}

const PowerTriangle: FC<PowerTriangleProps> = ({ kw, kvar, kva }) => {
  const allZero = kw === 0 && kvar === 0 && kva === 0;

  // Use reference values when load is zero so we still draw a shape
  const rKw = allZero ? 4 : kw;
  const rKvar = allZero ? 3 : kvar;

  // Calculate the angle to draw the triangle proportionally
  const angle = Math.atan2(rKvar, rKw);
  
  // Enforce a minimum display angle so the triangle doesn't collapse into a single line
  const minAngle = 0.15; // about 8.5 degrees
  const displayAngle = (!allZero && angle < minAngle) ? minAngle : angle;

  // Define a fixed hypotenuse length for the visual representation
  // This ensures the triangle is always a good size and labels don't overlap
  const visualHypotenuse = 220; 
  
  const tw = visualHypotenuse * Math.cos(displayAngle);
  const th = visualHypotenuse * Math.sin(displayAngle);

  // Center the triangle in the SVG
  const svgWidth = 500;
  const svgHeight = 350;
  
  // Anchor: bottom-left corner (the right-angle vertex)
  const A = { x: (svgWidth - tw) / 2, y: (svgHeight + th) / 2 + 20 }; // bottom-left
  const B = { x: A.x + tw, y: A.y };                                  // bottom-right (kW)
  const C = { x: A.x, y: A.y - th };                                  // top-left (kVAR)

  return (
    <div className="flex flex-col items-center justify-center w-full h-full min-h-[300px] relative">
      <svg viewBox={`0 0 ${svgWidth} ${svgHeight}`} className="w-full h-full max-w-[500px]" preserveAspectRatio="xMidYMid meet">
        <defs>
          <linearGradient id="ptGrad" x1="0%" y1="100%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#10b981" stopOpacity="0.15" />
            <stop offset="100%" stopColor="#8b5cf6" stopOpacity="0.15" />
          </linearGradient>
          <filter id="gG"><feGaussianBlur stdDeviation="2" result="b"/><feFlood floodColor="#10b981" floodOpacity="0.4"/><feComposite in2="b" operator="in"/><feMerge><feMergeNode/><feMergeNode in="SourceGraphic"/></feMerge></filter>
          <filter id="gA"><feGaussianBlur stdDeviation="2" result="b"/><feFlood floodColor="#f59e0b" floodOpacity="0.4"/><feComposite in2="b" operator="in"/><feMerge><feMergeNode/><feMergeNode in="SourceGraphic"/></feMerge></filter>
          <filter id="gV"><feGaussianBlur stdDeviation="2" result="b"/><feFlood floodColor="#8b5cf6" floodOpacity="0.4"/><feComposite in2="b" operator="in"/><feMerge><feMergeNode/><feMergeNode in="SourceGraphic"/></feMerge></filter>
        </defs>

        {/* Filled area */}
        <polygon
          points={`${A.x},${A.y} ${B.x},${B.y} ${C.x},${C.y}`}
          fill="url(#ptGrad)"
          style={{ transition: 'all 0.8s ease' }}
        />

        {/* Right-angle marker at A */}
        <polyline
          points={`${A.x + 15},${A.y} ${A.x + 15},${A.y - 15} ${A.x},${A.y - 15}`}
          fill="none" stroke="#94a3b8" strokeWidth="1.5"
        />

        {/* P (kW) — bottom edge A→B — green */}
        <g filter="url(#gG)">
          <line x1={A.x} y1={A.y} x2={B.x} y2={B.y}
            stroke="#10b981" strokeWidth="4" strokeLinecap="round"
            style={{ transition: 'all 0.8s ease' }} />
        </g>

        {/* Q (kVAR) — left edge A→C — amber */}
        <g filter="url(#gA)">
          <line x1={A.x} y1={A.y} x2={C.x} y2={C.y}
            stroke="#f59e0b" strokeWidth="4" strokeLinecap="round"
            style={{ transition: 'all 0.8s ease' }} />
        </g>

        {/* S (kVA) — hypotenuse B→C — violet */}
        <g filter="url(#gV)">
          <line x1={B.x} y1={B.y} x2={C.x} y2={C.y}
            stroke="#8b5cf6" strokeWidth="4" strokeLinecap="round"
            style={{ transition: 'all 0.8s ease' }} />
        </g>

        {/* Corner dots */}
        <circle cx={A.x} cy={A.y} r="5" fill="#475569" />
        <circle cx={B.x} cy={B.y} r="5" fill="#10b981" />
        <circle cx={C.x} cy={C.y} r="5" fill="#f59e0b" />

        {/* ── Labels positioned OUTSIDE the triangle ── */}

        {/* P (kW) label — below the bottom edge */}
        <text x={(A.x + B.x) / 2} y={A.y + 30} textAnchor="middle" fontSize="14" fontWeight="800" fill="#10b981">
          P (kW)
        </text>
        <text x={(A.x + B.x) / 2} y={A.y + 48} textAnchor="middle" fontSize="14" fontWeight="700" fill="#64748b" fontFamily="monospace">
          {kw.toFixed(2)}
        </text>

        {/* Q (kVAR) label — to the left of the vertical edge */}
        <text x={A.x - 20} y={(A.y + C.y) / 2 - 8} textAnchor="end" fontSize="14" fontWeight="800" fill="#f59e0b" dominantBaseline="middle">
          Q (kVAR)
        </text>
        <text x={A.x - 20} y={(A.y + C.y) / 2 + 12} textAnchor="end" fontSize="14" fontWeight="700" fill="#64748b" fontFamily="monospace" dominantBaseline="middle">
          {kvar.toFixed(2)}
        </text>

        {/* S (kVA) label — to the right of the hypotenuse */}
        <text x={(B.x + C.x) / 2 + 10} y={(B.y + C.y) / 2 - 25} textAnchor="start" fontSize="14" fontWeight="800" fill="#8b5cf6">
          S (kVA)
        </text>
        <text x={(B.x + C.x) / 2 + 10} y={(B.y + C.y) / 2 - 5} textAnchor="start" fontSize="14" fontWeight="700" fill="#64748b" fontFamily="monospace">
          {kva.toFixed(2)}
        </text>

        {/* φ angle arc at vertex B (bottom-right) */}
        {!allZero && kva > 0 && (
          (() => {
            const phi = Math.acos(Math.min(kw / kva, 1));
            const phiDeg = phi * (180 / Math.PI);
            if (phiDeg < 0.5) return null;
            const r = 30;
            const startX = B.x - r;
            const startY = B.y;
            const endX = B.x - r * Math.cos(phi);
            const endY = B.y - r * Math.sin(phi);
            return (
              <>
                <path
                  d={`M${startX},${startY} A${r},${r} 0 0,1 ${endX},${endY}`}
                  fill="none" stroke="#8b5cf6" strokeWidth="2" strokeDasharray="4 3" opacity="0.8"
                />
                <text x={B.x + 10} y={B.y - 8} fontSize="12" fill="#8b5cf6" fontWeight="700" textAnchor="start">
                  φ={phiDeg.toFixed(1)}°
                </text>
              </>
            );
          })()
        )}

        {allZero && (
          <text x={svgWidth / 2} y="20" textAnchor="middle" fontSize="12" fill="#94a3b8" fontWeight="600" fontStyle="italic">
            No load — reference shape
          </text>
        )}
      </svg>
    </div>
  );
};

export default memo(PowerTriangle);
