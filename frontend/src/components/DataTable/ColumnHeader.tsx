import { useState, useRef, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { Filter } from 'lucide-react';
import { SortIcon } from '../Icons';
import type { ColumnSchema, ColumnStats, ColumnFilter } from '../../api/client';
import MiniHistogram from './MiniHistogram';
import MiniCategoryBar from './MiniCategoryBar';
import ColumnFilterPopover from './ColumnFilter';

interface ColumnHeaderProps {
  column: ColumnSchema;
  stats: ColumnStats | undefined;
  sortBy: string | null;
  sortOrder: string;
  filter: ColumnFilter | undefined;
  onSort: (column: string) => void;
  onFilter: (filter: ColumnFilter | undefined, columnName?: string) => void;
}

export default function ColumnHeader({
  column,
  stats,
  sortBy,
  sortOrder,
  filter,
  onSort,
  onFilter,
}: ColumnHeaderProps) {
  const [showFilter, setShowFilter] = useState(false);
  const [popoverPos, setPopoverPos] = useState({ left: 0, top: 0 });
  const filterBtnRef = useRef<HTMLButtonElement>(null);
  const colType = column.type;

  useEffect(() => {
    if (showFilter && filterBtnRef.current) {
      const rect = filterBtnRef.current.getBoundingClientRect();
      setPopoverPos({ left: rect.left, top: rect.bottom + 4 });
    }
  }, [showFilter]);

  useEffect(() => {
    if (!showFilter) return;
    function handleClick(e: MouseEvent) {
      const target = e.target as Node;
      if (filterBtnRef.current?.contains(target)) return;
      const popover = document.getElementById('column-filter-portal');
      if (popover?.contains(target)) return;
      setShowFilter(false);
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [showFilter]);

  const renderVisualization = () => {
    if (!stats) return null;
    if (colType === 'int' || colType === 'float') {
      if (stats.type !== 'numeric') return null;
      return (
        <MiniHistogram
          bins={stats.bins}
          filterMin={filter?.op === 'between' ? filter.min as number : undefined}
          filterMax={filter?.op === 'between' ? filter.max as number : undefined}
        />
      );
    }
    if (colType === 'bool' && stats.type === 'bool') {
      return <MiniCategoryBar stats={stats} />;
    }
    if (colType === 'str' && stats.type === 'string') {
      return <MiniCategoryBar stats={stats} />;
    }
    return null;
  };

  const typeLabel = (t: string) => {
    switch (t) {
      case 'int': return '123';
      case 'float': return '#.#';
      case 'bool': return 'T/F';
      case 'str': return 'Aa';
      case 'date': return '📅';
      case 'list': return '[]';
      case 'dict': return '{}';
      default: return t;
    }
  };

  const canFilter = colType === 'int' || colType === 'float' || colType === 'bool' || colType === 'str';

  return (
    <th className="column-header-cell">
      <div className="column-header-top">
        <button onClick={() => onSort(column.name)} className="column-header-sort">
          <span className="column-header-name">{column.name}</span>
          <SortIcon column={column.name} sortBy={sortBy} sortOrder={sortOrder} />
        </button>
        <div className="flex items-center gap-1">
          <span className="column-type-badge">{typeLabel(colType)}</span>
          {canFilter && (
            <button
              ref={filterBtnRef}
              onClick={(e) => {
                e.stopPropagation();
                setShowFilter(!showFilter);
              }}
              className={`column-filter-btn ${filter ? 'column-filter-btn-active' : ''}`}
            >
              <Filter size={11} />
            </button>
          )}
        </div>
      </div>
      <div className="column-header-viz">
        {renderVisualization()}
      </div>
      {showFilter && canFilter && createPortal(
        <div
          id="column-filter-portal"
          className="column-filter-popover"
          style={{
            position: 'fixed',
            left: popoverPos.left,
            top: popoverPos.top,
          }}
        >
          <ColumnFilterPopover
            column={column}
            stats={stats}
            filter={filter}
            onApply={(f) => {
              onFilter(f, column.name);
              setShowFilter(false);
            }}
            onClose={() => setShowFilter(false)}
          />
        </div>,
        document.body,
      )}
    </th>
  );
}
