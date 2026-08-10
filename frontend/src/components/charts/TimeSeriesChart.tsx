import { useMemo, useState, useRef, useEffect } from 'react';
import type { FC } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
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
  const containerRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ width: 0, height: 0 });

  useEffect(() => {
    if (!containerRef.current) return;
    const observer = new ResizeObserver((entries) => {
      for (let entry of entries) {
        setSize({
          width: entry.contentRect.width,
          height: entry.contentRect.height
        });
      }
    });
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);

  // Memoize the expensive map + sort so it only re-computes when data changes
  const processedData = useMemo(() => {
    return data.map(d => {
      let timeValue;
      if (d.dTS && d.dTS > 0) {
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
      <div className="flex-1 min-h-0 min-w-0 w-full" ref={containerRef}>
        {size.width > 0 && size.height > 0 && (
          <LineChart width={size.width} height={size.height} data={processedData} margin={{ top: 5, right: 20, left: -20, bottom: 0 }}>
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
                  const date = new Date(unix);
                  const spanHours = processedData.length > 0 ? (processedData[processedData.length - 1].timeValue - processedData[0].timeValue) / (1000 * 60 * 60) : 0;
                  if (spanHours > 24) {
                    return date.toLocaleString('en-IN', { timeZone: 'Asia/Kolkata', day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false });
                  }
                  return date.toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata', hour: '2-digit', minute: '2-digit', hour12: false });
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
                background: 'rgba(15, 23, 42, 0.85)', 
                backdropFilter: 'blur(12px)',
                WebkitBackdropFilter: 'blur(12px)',
                border: '1px solid rgba(255, 255, 255, 0.1)', 
                borderRadius: '12px', 
                fontSize: '12px', 
                boxShadow: '0 8px 32px -4px rgba(0,0,0,0.5)' 
              }}
              itemStyle={{ padding: '2px 0', color: '#f8fafc' }}
              labelStyle={{ color: '#94a3b8', marginBottom: '4px' }}
              labelFormatter={(unix) => new Date(unix).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata', day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false })}
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
        )}
      </div>
    </div>
  );
};

export default TimeSeriesChart;
