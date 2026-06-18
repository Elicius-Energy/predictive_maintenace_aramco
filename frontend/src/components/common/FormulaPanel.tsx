import type { FC } from 'react';
import type { FormulaEntry } from '../../data/formulas';

interface FormulaPanelProps {
  items: FormulaEntry[];
  className?: string;
}

const FormulaPanel: FC<FormulaPanelProps> = ({ items, className = '' }) => {
  if (!items.length) return null;

  return (
    <div className={`mt-4 rounded-xl border border-border bg-surface-muted/60 p-4 ${className}`}>
      <p className="text-[10px] font-bold uppercase tracking-[0.24em] text-text-muted">Formula Reference</p>
      <div className="mt-3 space-y-3">
        {items.map((item) => (
          <div key={item.name} className="space-y-1">
            <p className="text-xs font-semibold text-text-primary">{item.name}</p>
            <code className="block rounded-lg bg-surface px-3 py-2 text-[11px] text-primary">{item.expression}</code>
            <p className="text-xs leading-relaxed text-text-secondary">{item.explanation}</p>
          </div>
        ))}
      </div>
    </div>
  );
};

export default FormulaPanel;
