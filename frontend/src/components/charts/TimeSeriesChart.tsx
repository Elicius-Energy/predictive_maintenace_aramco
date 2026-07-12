import { useMemo } from 'react';
import type { FC } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  ReferenceLine
} from 'recharts';

interface DataPoint {
  timestamp: string;
  [key: string]: any;
}

interface TimeSeriesChartProps {
  data: DataPoint[];
  lines: { key: string; color: string; name: string; dashed?: boolean }[];
  yDomain?: [number | string, number | string];
  title?: string;
  threshold?: { value: number; label: string; color: string };
}

const TimeSeriesChart: FC<TimeSeriesChartProps> = ({ data, lines, yDomain, title, threshold }) => {
  // Memoize the expensive map + sort so it only re-computes when data changes
  const processedData = useMemo(() => {
    return data.map(d => {
      let timeValue;
      if (d.dTS && d.dTS > 0) {
        // Device sends "epoch time IST", meaning the epoch is offset by +5.5 hours.
        // We subtract the IST offset (19800 seconds) so it becomes a standard UTC epoch.
        // Then formatting it to 'Asia/Kolkata' will correctly display the time.
        timeValue = (d.dTS - 19800) * 1000;
      } else {
        timeValue = new Date(d.timestamp.endsWith('Z') ? d.timestamp : d.timestamp + 'Z').getTime();
      }
      return {
        ...d,
        timeValue
      };
    }).sort((a, b) => a.timeValue - b.timeValue);
  }, [data]);

  return (
    <div className="w-full h-full flex flex-col">
      <div className="flex justify-between items-center mb-3">
        {title && <h3 className="text-xs uppercase font-bold tracking-wider text-text-muted">{title}</h3>}
        <span className="text-[10px] text-primary glass-badge px-2 py-0.5 rounded-lg font-mono">
          {data.length} pts
        </span>
      </div>
      <div className="flex-1 min-h-0">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={processedData} margin={{ top: 5, right: 20, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.2)" vertical={false} />
            <XAxis 
              dataKey="timeValue" 
              type="number"
              domain={['dataMin', 'dataMax']}
              stroke="#94a3b8"
              fontSize={10}
              tickLine={false}
              axisLine={false}
              minTickGap={50}
              tickFormatter={(unix) => {
                try {
                  // We formatted all timestamps to standard UTC epoch, 
                  // so we can reliably use Asia/Kolkata here.
                  return new Date(unix).toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata', hour: '2-digit', minute: '2-digit', hour12: false });
                } catch {
                  return '';
                }
              }}
            />
            <YAxis 
              stroke="#94a3b8" 
              fontSize={11} 
              tickLine={false} 
              axisLine={false}
              domain={yDomain || ['auto', 'auto']}
              allowDataOverflow={false}
            />
            <Tooltip 
              contentStyle={{ 
                background: 'rgba(255, 255, 255, 0.75)', 
                backdropFilter: 'blur(12px)',
                WebkitBackdropFilter: 'blur(12px)',
                border: '1px solid rgba(255, 255, 255, 0.5)', 
                borderRadius: '12px', 
                fontSize: '12px', 
                boxShadow: '0 8px 32px -4px rgba(0,0,0,0.1)' 
              }}
              itemStyle={{ padding: '2px 0' }}
              labelFormatter={(unix) => new Date(unix).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata', hour: '2-digit', minute: '2-digit', hour12: false })}
            />
            <Legend iconType="circle" wrapperStyle={{ fontSize: '12px', paddingTop: '10px' }} />
            {lines.map((line) => (
              <Line
                key={line.key}
                type="monotone"
                dataKey={line.key}
                stroke={line.color}
                name={line.name}
                dot={false}
                strokeWidth={2}
                connectNulls={true}
                isAnimationActive={false}
                animationDuration={0}
                strokeDasharray={line.dashed ? '5 5' : undefined}
              />
            ))}
            {threshold && (
              <ReferenceLine
                y={threshold.value}
                label={{ position: 'top', value: threshold.label, fill: threshold.color, fontSize: 10, fontWeight: 'bold' }}
                stroke={threshold.color}
                strokeDasharray="3 3"
                strokeWidth={2}
              />
            )}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default TimeSeriesChart;
