import type { FC } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell
} from 'recharts';

interface FFTChartProps {
  magnitudes: number[];
  frequencies: number[];
}

const FFTChart: FC<FFTChartProps> = ({ magnitudes, frequencies }) => {
  const data = magnitudes.slice(0, 100).map((mag, i) => ({
    freq: frequencies[i]?.toFixed(1) || i,
    mag: mag,
  }));

  return (
    <div className="w-full h-full flex flex-col">
      <h3 className="text-xs uppercase font-bold tracking-wider text-text-muted mb-3">Frequency Spectrum (FFT)</h3>
      <div className="flex-1 min-h-0">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" opacity={0.4} vertical={false} />
            <XAxis dataKey="freq" hide />
            <YAxis stroke="#94a3b8" fontSize={11} tickLine={false} axisLine={false} />
            <Tooltip 
              contentStyle={{ backgroundColor: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '8px', fontSize: '12px', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)' }}
              labelFormatter={(val) => `${val} Hz`}
            />
            <Bar dataKey="mag" fill="#0891b2" isAnimationActive={false} radius={[3, 3, 0, 0]}>
               {data.map((entry, index) => (
                 <Cell key={`cell-${index}`} fill={entry.mag > 0.5 ? '#d97706' : '#0891b2'} />
               ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default FFTChart;
