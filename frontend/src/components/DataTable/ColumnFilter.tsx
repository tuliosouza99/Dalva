import { useState, useMemo, useCallback } from 'react';
import { X } from 'lucide-react';
import type { ColumnFilter, ColumnSchema, ColumnStats } from '../../api/client';

interface ColumnFilterProps {
  column: ColumnSchema;
  stats: ColumnStats | undefined;
  filter: ColumnFilter | undefined;
  onApply: (filter: ColumnFilter | undefined) => void;
  onClose: () => void;
}

function getInitialValues(filter: ColumnFilter | undefined) {
  if (filter) {
    if (filter.op === 'between') {
      return {
        minVal: filter.min !== undefined ? String(filter.min) : '',
        maxVal: filter.max !== undefined ? String(filter.max) : '',
        strVal: '',
        boolVal: 'all' as const,
      };
    }
    if (filter.op === 'contains') {
      return {
        minVal: '',
        maxVal: '',
        strVal: String(filter.value ?? ''),
        boolVal: 'all' as const,
      };
    }
    if (filter.op === 'eq') {
      return {
        minVal: '',
        maxVal: '',
        strVal: '',
        boolVal: filter.value === true ? 'true' as const : filter.value === false ? 'false' as const : 'all' as const,
      };
    }
  }
  return { minVal: '', maxVal: '', strVal: '', boolVal: 'all' as const };
}

export default function ColumnFilterPopover({
  column,
  stats,
  filter,
  onApply,
  onClose,
}: ColumnFilterProps) {
  const colType = column.type;
  const initial = useMemo(() => getInitialValues(filter), [filter]);

  const [minVal, setMinVal] = useState(initial.minVal);
  const [maxVal, setMaxVal] = useState(initial.maxVal);
  const [strVal, setStrVal] = useState(initial.strVal);
  const [boolVal, setBoolVal] = useState<'all' | 'true' | 'false'>(initial.boolVal);

  const numericMin = stats?.type === 'numeric' ? stats.min : null;
  const numericMax = stats?.type === 'numeric' ? stats.max : null;

  const isOutOfRange = useCallback((val: string, bound: 'min' | 'max'): boolean => {
    if (val === '') return false;
    const num = Number(val);
    if (Number.isNaN(num)) return true;
    if (bound === 'min' && numericMin !== null && num < numericMin) return true;
    if (bound === 'max' && numericMax !== null && num > numericMax) return true;
    return false;
  }, [numericMin, numericMax]);

  const clampOnBlur = useCallback((val: string, bound: 'min' | 'max'): string => {
    if (val === '') return '';
    const num = Number(val);
    if (Number.isNaN(num)) return val;
    if (bound === 'min' && numericMin !== null && num < numericMin) return String(numericMin);
    if (bound === 'max' && numericMax !== null && num > numericMax) return String(numericMax);
    return val;
  }, [numericMin, numericMax]);

  const handleApply = () => {
    if (colType === 'int' || colType === 'float') {
      const clampedMin = clampOnBlur(minVal, 'min');
      const clampedMax = clampOnBlur(maxVal, 'max');
      setMinVal(clampedMin);
      setMaxVal(clampedMax);

      const rawMin = clampedMin !== '' ? Number(clampedMin) : undefined;
      const rawMax = clampedMax !== '' ? Number(clampedMax) : undefined;

      if (rawMin !== undefined && rawMax !== undefined && rawMin > rawMax) {
        return;
      }
      if (rawMin !== undefined || rawMax !== undefined) {
        onApply({ column: column.name, op: 'between', min: rawMin, max: rawMax });
      } else {
        onApply(undefined);
      }
    } else if (colType === 'str') {
      if (strVal.trim()) {
        onApply({ column: column.name, op: 'contains', value: strVal.trim() });
      } else {
        onApply(undefined);
      }
    } else if (colType === 'bool') {
      if (boolVal === 'all') {
        onApply(undefined);
      } else {
        onApply({ column: column.name, op: 'eq', value: boolVal === 'true' });
      }
    }
    onClose();
  };

  const handleReset = () => {
    setMinVal('');
    setMaxVal('');
    setStrVal('');
    setBoolVal('all');
    onApply(undefined);
    onClose();
  };

  const inputMin = numericMin !== null ? String(numericMin) : '';
  const inputMax = numericMax !== null ? String(numericMax) : '';

  const minOutOfRange = isOutOfRange(minVal, 'min');
  const maxOutOfRange = isOutOfRange(maxVal, 'max');

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-semibold" style={{ color: 'var(--text-primary)' }}>
          Filter: {column.name}
        </span>
        <button onClick={onClose} className="p-0.5 rounded hover:bg-[var(--bg-elevated)]" style={{ color: 'var(--text-tertiary)' }}>
          <X size={12} />
        </button>
      </div>

      {(colType === 'int' || colType === 'float') && (
        <div className="space-y-2">
          <div className="flex gap-2">
            <div className="flex-1">
              <label className="text-[10px] uppercase tracking-wide" style={{ color: 'var(--text-tertiary)' }}>Min</label>
              <input
                type="number"
                value={minVal}
                onChange={(e) => setMinVal(e.target.value)}
                onBlur={() => setMinVal(clampOnBlur(minVal, 'min'))}
                placeholder={inputMin}
                className={`filter-input ${minOutOfRange ? 'filter-input-error' : ''}`}
                step={colType === 'float' ? '0.1' : '1'}
              />
            </div>
            <div className="flex-1">
              <label className="text-[10px] uppercase tracking-wide" style={{ color: 'var(--text-tertiary)' }}>Max</label>
              <input
                type="number"
                value={maxVal}
                onChange={(e) => setMaxVal(e.target.value)}
                onBlur={() => setMaxVal(clampOnBlur(maxVal, 'max'))}
                placeholder={inputMax}
                className={`filter-input ${maxOutOfRange ? 'filter-input-error' : ''}`}
                step={colType === 'float' ? '0.1' : '1'}
              />
            </div>
          </div>
          {numericMin !== null && numericMax !== null && (
            <div className="text-[10px]" style={{ color: 'var(--text-tertiary)' }}>
              Range: {numericMin} – {numericMax}
            </div>
          )}
        </div>
      )}

      {colType === 'str' && (
        <div>
          <label className="text-[10px] uppercase tracking-wide" style={{ color: 'var(--text-tertiary)' }}>Contains</label>
          <input
            type="text"
            value={strVal}
            onChange={(e) => setStrVal(e.target.value)}
            placeholder="Search..."
            className="filter-input"
            onKeyDown={(e) => e.key === 'Enter' && handleApply()}
          />
        </div>
      )}

      {colType === 'bool' && (
        <div className="flex gap-1">
          {(['all', 'true', 'false'] as const).map((val) => (
            <button
              key={val}
              onClick={() => setBoolVal(val)}
              className={`bool-filter-btn ${boolVal === val ? 'bool-filter-btn-active' : ''}`}
            >
              {val.charAt(0).toUpperCase() + val.slice(1)}
            </button>
          ))}
        </div>
      )}

      <div className="flex gap-2 mt-3">
        <button onClick={handleApply} className="filter-apply-btn">Apply</button>
        {filter && (
          <button onClick={handleReset} className="filter-reset-btn">Reset</button>
        )}
      </div>
    </div>
  );
}
