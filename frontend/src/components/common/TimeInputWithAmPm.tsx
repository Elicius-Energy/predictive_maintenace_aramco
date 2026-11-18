import React, { useState, useEffect } from 'react';

export interface TimeInputWithAmPmProps {
  value: string; // 24-hour format "HH:mm" (e.g. "07:10", "15:30", "00:00")
  onChange: (val24: string) => void;
  disabled?: boolean;
  className?: string;
}

export function parse24To12(val24: string): { hh: string; mm: string; period: 'AM' | 'PM' } {
  if (!val24 || typeof val24 !== 'string' || !val24.includes(':')) {
    return { hh: '12', mm: '00', period: 'AM' };
  }
  const [hStr, mStr] = val24.split(':');
  let h = parseInt(hStr, 10);
  let m = parseInt(mStr, 10);
  if (isNaN(h)) h = 0;
  if (isNaN(m)) m = 0;

  const period: 'AM' | 'PM' = h >= 12 ? 'PM' : 'AM';
  let h12 = h % 12;
  if (h12 === 0) h12 = 12;

  return {
    hh: String(h12).padStart(2, '0'),
    mm: String(m).padStart(2, '0'),
    period,
  };
}

export function format12To24(hh: number | string, mm: number | string, period: 'AM' | 'PM'): string {
  let h = typeof hh === 'string' ? parseInt(hh, 10) : hh;
  let m = typeof mm === 'string' ? parseInt(mm, 10) : mm;
  if (isNaN(h)) h = 12;
  if (isNaN(m)) m = 0;

  h = Math.min(12, Math.max(1, h));
  m = Math.min(59, Math.max(0, m));

  let h24 = h % 12;
  if (period === 'PM') {
    h24 += 12;
  }

  return `${String(h24).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
}

export const TimeInputWithAmPm: React.FC<TimeInputWithAmPmProps> = ({
  value,
  onChange,
  disabled = false,
  className = '',
}) => {
  const parsed = parse24To12(value);
  const [displayTime, setDisplayTime] = useState(`${parsed.hh}:${parsed.mm}`);
  const [period, setPeriod] = useState<'AM' | 'PM'>(parsed.period);

  // Synchronize when value changes externally (e.g. Presets or Parent state updates)
  useEffect(() => {
    const p = parse24To12(value);
    setDisplayTime(`${p.hh}:${p.mm}`);
    setPeriod(p.period);
  }, [value]);

  const commitTime = (rawStr: string, currentPeriod: 'AM' | 'PM') => {
    // Clean string to digits and colon
    const cleaned = rawStr.trim();
    let h = 12;
    let m = 0;
    let newPeriod = currentPeriod;

    if (cleaned.includes(':')) {
      const [hPart, mPart] = cleaned.split(':');
      h = parseInt(hPart, 10);
      m = parseInt(mPart, 10);
    } else if (cleaned.length >= 3) {
      // e.g. 730 or 1530
      h = parseInt(cleaned.slice(0, cleaned.length - 2), 10);
      m = parseInt(cleaned.slice(cleaned.length - 2), 10);
    } else if (cleaned.length > 0) {
      h = parseInt(cleaned, 10);
      m = 0;
    }

    if (isNaN(h)) h = 12;
    if (isNaN(m)) m = 0;

    // Handle user entering 24h format directly (e.g. 15:30 or 00:15)
    if (h >= 13 && h <= 23) {
      newPeriod = 'PM';
      h = h - 12;
    } else if (h === 0) {
      newPeriod = 'AM';
      h = 12;
    }

    h = Math.min(12, Math.max(1, h));
    m = Math.min(59, Math.max(0, m));

    const formattedDisplay = `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
    setDisplayTime(formattedDisplay);
    setPeriod(newPeriod);

    const val24 = format12To24(h, m, newPeriod);
    if (val24 !== value) {
      onChange(val24);
    }
  };

  const handlePeriodChange = (newPeriod: 'AM' | 'PM') => {
    if (disabled || newPeriod === period) return;
    setPeriod(newPeriod);
    const [hStr, mStr] = displayTime.split(':');
    const val24 = format12To24(hStr || '12', mStr || '00', newPeriod);
    onChange(val24);
  };

  const handleTextChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    // Allow numbers and colon, up to 5 chars (HH:MM)
    const val = e.target.value.replace(/[^0-9:]/g, '').slice(0, 5);
    setDisplayTime(val);
  };

  const handleBlur = () => {
    commitTime(displayTime, period);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      commitTime(displayTime, period);
      (e.target as HTMLInputElement).blur();
    } else if (e.key === 'ArrowUp' || e.key === 'ArrowDown') {
      e.preventDefault();
      const [hStr, mStr] = displayTime.split(':');
      let h = parseInt(hStr || '12', 10);
      let m = parseInt(mStr || '0', 10);
      const step = e.shiftKey ? 15 : 1;
      if (e.key === 'ArrowUp') {
        m += step;
        if (m >= 60) {
          m = m % 60;
          h = (h % 12) + 1;
        }
      } else {
        m -= step;
        if (m < 0) {
          m = (m + 60) % 60;
          h = h === 1 ? 12 : h - 1;
        }
      }
      const newDisplay = `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
      setDisplayTime(newDisplay);
      const val24 = format12To24(h, m, period);
      onChange(val24);
    }
  };

  return (
    <div className={`inline-flex items-center gap-1.5 ${className}`}>
      {/* Time Text Input */}
      <input
        type="text"
        value={displayTime}
        disabled={disabled}
        onChange={handleTextChange}
        onBlur={handleBlur}
        onKeyDown={handleKeyDown}
        placeholder="hh:mm"
        maxLength={5}
        title="Enter time in 12-hour format (hh:mm). Use arrow keys to adjust minutes."
        className="w-16 h-[32px] text-center bg-white border border-slate-300 rounded-md py-1 px-1 font-semibold text-slate-800 text-xs focus:border-[#1F3A8A] focus:ring-1 focus:ring-[#1F3A8A] focus:outline-hidden disabled:bg-slate-100 disabled:text-slate-400 transition-all shadow-2xs"
      />

      {/* AM / PM Segmented Switch */}
      <div className="inline-flex h-[32px] items-center rounded-md border border-slate-300 bg-slate-100 p-0.5 text-xs font-bold shrink-0 shadow-2xs">
        <button
          type="button"
          disabled={disabled}
          onClick={() => handlePeriodChange('AM')}
          className={`h-full px-2.5 rounded flex items-center justify-center text-[11px] font-bold transition-all cursor-pointer ${
            period === 'AM'
              ? 'bg-[#1F3A8A] text-white shadow-xs'
              : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200'
          } ${disabled ? 'cursor-not-allowed opacity-50' : ''}`}
        >
          AM
        </button>
        <button
          type="button"
          disabled={disabled}
          onClick={() => handlePeriodChange('PM')}
          className={`h-full px-2.5 rounded flex items-center justify-center text-[11px] font-bold transition-all cursor-pointer ${
            period === 'PM'
              ? 'bg-[#1F3A8A] text-white shadow-xs'
              : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200'
          } ${disabled ? 'cursor-not-allowed opacity-50' : ''}`}
        >
          PM
        </button>
      </div>
    </div>
  );
};
