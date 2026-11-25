import React, { useState, useRef, useEffect } from 'react';
import { ChevronDown, Trash2, Check } from 'lucide-react';

export interface PowerStudyOption {
  id: number;
  study_code: string;
  customer_name?: string;
  display_label?: string;
  device_id?: string;
  status?: string;
  started_at?: string;
  stopped_at?: string | null;
  updated_at?: string;
  duration_str?: string;
  kwh_per_running_hour?: number | null;
}

interface PowerStudyDropdownProps {
  id?: string;
  ariaLabel?: string;
  studies: PowerStudyOption[];
  value: string;
  placeholder: string;
  onChange: (studyId: string) => void;
  canDelete?: boolean;
  onDelete?: (study: PowerStudyOption) => Promise<void> | void;
  formatMeta?: (study: PowerStudyOption) => string;
  buttonClassName?: string;
}

export const PowerStudyDropdown: React.FC<PowerStudyDropdownProps> = ({
  id,
  ariaLabel,
  studies,
  value,
  placeholder,
  onChange,
  canDelete = false,
  onDelete,
  formatMeta,
  buttonClassName = 'w-full bg-white border border-slate-300 rounded-lg px-2.5 py-2 font-medium text-slate-800',
}) => {
  const [open, setOpen] = useState(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    if (open) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [open]);

  const selectedStudy = studies.find((s) => String(s.id) === value) || null;

  const formatPrimary = (s: PowerStudyOption) =>
    `${s.study_code} — ${(s.customer_name || '').trim() || 'No Customer'}`;

  const handleDeleteClick = async (e: React.MouseEvent, study: PowerStudyOption) => {
    e.stopPropagation();
    e.preventDefault();
    if (!onDelete || deletingId === study.id) return;
    setDeletingId(study.id);
    try {
      await onDelete(study);
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div ref={containerRef} className="relative">
      <button
        id={id}
        type="button"
        aria-label={ariaLabel}
        aria-haspopup="listbox"
        aria-expanded={open}
        onClick={() => setOpen((prev) => !prev)}
        className={`flex items-center justify-between gap-2 text-left text-xs transition-colors cursor-pointer focus:border-[#1F3A8A] focus:outline-hidden ${buttonClassName}`}
      >
        <span className="truncate">
          {selectedStudy ? (
            <>
              <span className="font-semibold text-slate-800">{formatPrimary(selectedStudy)}</span>
              {formatMeta && formatMeta(selectedStudy) ? (
                <span className="text-slate-500 ml-1">({formatMeta(selectedStudy)})</span>
              ) : null}
            </>
          ) : (
            <span className="text-slate-500">{placeholder}</span>
          )}
        </span>
        <ChevronDown className={`w-3.5 h-3.5 text-slate-400 shrink-0 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>

      {open && (
        <div
          role="listbox"
          className="absolute z-50 mt-1 w-full min-w-[280px] max-h-64 overflow-y-auto rounded-xl border border-slate-200 bg-white shadow-lg py-1 text-xs"
        >
          {value && (
            <button
              type="button"
              onClick={() => {
                onChange('');
                setOpen(false);
              }}
              className="w-full px-3 py-2 text-left text-slate-500 hover:bg-slate-50 border-b border-slate-100 cursor-pointer"
            >
              -- Clear selection --
            </button>
          )}

          {studies.length === 0 ? (
            <div className="px-3 py-3 text-slate-400 text-center">No recorded power studies yet</div>
          ) : (
            studies.map((s) => {
              const isSelected = String(s.id) === value;
              const meta = formatMeta ? formatMeta(s) : '';
              return (
                <div
                  key={s.id}
                  role="option"
                  aria-selected={isSelected}
                  className={`flex items-center justify-between gap-2 px-2.5 py-1.5 transition-colors ${
                    isSelected ? 'bg-blue-50/90 text-[#1F3A8A]' : 'hover:bg-slate-50 text-slate-800'
                  }`}
                >
                  <button
                    type="button"
                    onClick={() => {
                      onChange(String(s.id));
                      setOpen(false);
                    }}
                    className="flex-1 min-w-0 flex items-center gap-2 text-left cursor-pointer py-0.5"
                  >
                    <Check className={`w-3.5 h-3.5 shrink-0 ${isSelected ? 'text-[#1F3A8A] opacity-100' : 'opacity-0'}`} />
                    <div className="min-w-0 flex-1">
                      <div className="font-semibold truncate">{formatPrimary(s)}</div>
                      {meta && <div className="text-[10px] text-slate-500 truncate">{meta}</div>}
                    </div>
                  </button>

                  {canDelete && onDelete && (
                    <button
                      type="button"
                      aria-label={`Delete study ${s.study_code}`}
                      title={`Delete study ${s.study_code} (archived in backend recovery DB)`}
                      disabled={deletingId === s.id}
                      onClick={(e) => handleDeleteClick(e, s)}
                      className="p-1.5 rounded-md text-rose-500 hover:text-rose-700 hover:bg-rose-50 disabled:opacity-40 transition-colors cursor-pointer shrink-0"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>
              );
            })
          )}
        </div>
      )}
    </div>
  );
};

export default PowerStudyDropdown;
