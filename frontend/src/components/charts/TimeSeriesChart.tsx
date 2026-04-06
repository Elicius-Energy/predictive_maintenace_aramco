import type { FC } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend
} from 'recharts';

interface DataPoint {
  timestamp: string;
  [key: string]: any;
}

interface TimeSeriesChartProps {
  data: DataPoint[];
  lines: { key: string; color: string; name: string }[];
  yDomain?: [number | string, number | string];
  title?: string;
}

const TimeSeriesChart: FC<TimeSeriesChartProps> = ({ data, lines, yDomain, title }) => {
  // Convert timestamps to numbers for a proper time scale
  const processedData = data.map(d => ({
    ...d,
    timeValue: new Date(d.timestamp.endsWith('Z') ? d.timestamp : d.timestamp + 'Z').getTime()
  })).sort((a, b) => a.timeValue - b.timeValue);

  return (
    <div className="w-full h-full flex flex-col">
      <div className="flex justify-between items-center mb-3">
        {title && <h3 className="text-xs uppercase font-bold tracking-wider text-text-muted">{title}</h3>}
        <span className="text-[10px] text-primary bg-primary/10 px-2 py-0.5 rounded font-mono">
          {data.length} pts
        </span>
      </div>
      <div className="flex-1 min-h-0">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={processedData} margin={{ top: 5, right: 20, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" opacity={0.6} vertical={false} />
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
                  return new Date(unix).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
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
              contentStyle={{ backgroundColor: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '8px', fontSize: '12px', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)' }}
              itemStyle={{ padding: '2px 0' }}
              labelFormatter={(unix) => new Date(unix).toLocaleString()}
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
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default TimeSeriesChart;
