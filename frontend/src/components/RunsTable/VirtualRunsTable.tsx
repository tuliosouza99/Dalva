import { useVirtualizer } from '@tanstack/react-virtual';
import { useNavigate } from 'react-router-dom';
import { useRef, useEffect, useState, useMemo } from 'react';
import type { Run } from '../../api/client';
import { api } from '../../api/client';

function CheckIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="20 6 9 17 4 12"/>
    </svg>
  );
}

function ChevronUpIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="18 15 12 9 6 15"/>
    </svg>
  );
}

function ChevronDownIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="6 9 12 15 18 9"/>
    </svg>
  );
}

interface Column {
  key: string;
  label: string;
  width: string;
  render: (run: Run, metricValues?: Record<string, Record<string, number | null>>) => React.ReactNode;
}

interface VirtualRunsTableProps {
  runs: Run[];
  isLoading?: boolean;
  hasMore?: boolean;
  fetchNextPage?: () => void;
  isFetchingNextPage?: boolean;
  onSort?: (key: string) => void;
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
  selectable?: boolean;
  selectedRunIds?: number[];
  onSelectionChange?: (selectedIds: number[]) => void;
  metricColumns?: string[];
  projectId?: number;
}

export default function VirtualRunsTable({
  runs,
  isLoading,
  hasMore,
  fetchNextPage,
  isFetchingNextPage,
  onSort,
  sortBy,
  sortOrder,
  selectable = false,
  selectedRunIds = [],
  onSelectionChange,
  metricColumns = [],
}: VirtualRunsTableProps) {
  const navigate = useNavigate();
  const parentRef = useRef<HTMLDivElement>(null);
  const [metricValues, setMetricValues] = useState<Record<string, Record<string, number | null>>>({});

  // Fetch metric values when runs or metricColumns change
  useEffect(() => {
    if (metricColumns.length === 0 || runs.length === 0) {
      setMetricValues({});
      return;
    }

    const runIds = runs.map(r => r.id);
    api.getSummaryMetrics(runIds, metricColumns)
      .then(data => setMetricValues(data))
      .catch(err => console.error('Failed to fetch metric values:', err));
  }, [runs, metricColumns]);

  // Sort runs by metric column if needed
  const sortedRuns = useMemo(() => {
    // If sorting by a metric column, sort on the client side
    if (sortBy && sortBy.startsWith('metric:')) {
      const metricPath = sortBy.replace('metric:', '');

      return [...runs].sort((a, b) => {
        const aValue = metricValues[String(a.id)]?.[metricPath];
        const bValue = metricValues[String(b.id)]?.[metricPath];

        // Handle null/undefined values - put them at the end
        if (aValue === null || aValue === undefined) return 1;
        if (bValue === null || bValue === undefined) return -1;

        const comparison = aValue - bValue;
        return sortOrder === 'asc' ? comparison : -comparison;
      });
    }

    // Otherwise, use the runs as-is (already sorted by backend)
    return runs;
  }, [runs, sortBy, sortOrder, metricValues]);

  const handleToggleSelection = (runId: number) => {
    if (!onSelectionChange) return;

    if (selectedRunIds.includes(runId)) {
      onSelectionChange(selectedRunIds.filter((id) => id !== runId));
    } else {
      onSelectionChange([...selectedRunIds, runId]);
    }
  };

  const handleToggleAll = () => {
    if (!onSelectionChange) return;

    if (selectedRunIds.length === sortedRuns.length) {
      onSelectionChange([]);
    } else {
      onSelectionChange(sortedRuns.map((r) => r.id));
    }
  };

  // Create dynamic metric columns
  const metricColumnDefs: Column[] = metricColumns.map(metricPath => ({
    key: `metric:${metricPath}`,
    label: metricPath.split('/').pop() || metricPath, // Use last part of path as label
    width: '120px',
    render: (run, metricVals) => {
      const value = metricVals?.[String(run.id)]?.[metricPath];
      if (value === null || value === undefined) {
        return <span className="text-sm text-gray-400 dark:text-gray-500">-</span>;
      }
      return (
        <span className="text-sm text-gray-900 dark:text-gray-100 font-mono">
          {typeof value === 'number' ? value.toFixed(4) : value}
        </span>
      );
    },
  }));

  const columns: Column[] = selectable
    ? [
        {
          key: 'select',
          label: '',
          width: '50px',
          render: (run) => (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <div 
                className="flex items-center justify-center cursor-pointer"
                style={{
                  width: '16px',
                  height: '16px',
                  borderRadius: '3px',
                  border: `2px solid ${selectedRunIds.includes(run.id) ? 'var(--accent)' : 'var(--border)'}`,
                  backgroundColor: selectedRunIds.includes(run.id) ? 'var(--accent)' : 'transparent',
                  transition: 'all 0.15s ease',
                  flexShrink: 0,
                }}
                onClick={(e) => {
                  e.stopPropagation();
                  handleToggleSelection(run.id);
                }}
                onMouseEnter={(e) => {
                  if (!selectedRunIds.includes(run.id)) {
                    e.currentTarget.style.borderColor = 'var(--accent)';
                    e.currentTarget.style.backgroundColor = 'var(--accent-muted)';
                  }
                }}
                onMouseLeave={(e) => {
                  if (!selectedRunIds.includes(run.id)) {
                    e.currentTarget.style.borderColor = 'var(--border)';
                    e.currentTarget.style.backgroundColor = 'transparent';
                  }
                }}
              >
                {selectedRunIds.includes(run.id) && (
                  <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="20 6 9 17 4 12"/>
                  </svg>
                )}
              </div>
            </div>
          ),
        },
        {
          key: 'run_id',
          label: 'Run ID',
          width: '150px',
          render: (run) => (
            <button
              onClick={(e) => {
                e.stopPropagation();
                navigate(`/runs/${run.id}`);
              }}
              className="mono text-sm cursor-pointer transition-colors"
              style={{ color: 'var(--accent-hover)' }}
              onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--accent)')}
              onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--accent-hover)')}
            >
              {run.run_id}
            </button>
          ),
        },
        {
          key: 'name',
          label: 'Name',
          width: '250px',
          render: (run) => (
            <span className="text-sm truncate block" style={{ color: 'var(--text-primary)' }} title={run.name}>
              {run.name}
            </span>
          ),
        },
        {
          key: 'tags',
          label: 'Tags',
          width: '200px',
          render: (run) => (
            <div className="flex flex-nowrap gap-1 overflow-x-auto">
              {run.tags ? (
                run.tags.split(',').map((tag, idx) => (
                  <span
                    key={idx}
                    className="inline-flex px-2 py-0.5 text-xs font-medium rounded-md whitespace-nowrap"
                    style={{ backgroundColor: 'var(--bg-elevated)', color: 'var(--text-secondary)' }}
                    title={tag}
                  >
                    {tag}
                  </span>
                ))
              ) : (
                <span className="text-sm" style={{ color: 'var(--text-tertiary)' }}>-</span>
              )}
            </div>
          ),
        },
        ...metricColumnDefs,
        {
          key: 'state',
          label: 'State',
          width: '120px',
          render: (run) => (
            <span className={`badge ${
              run.state === 'running'
                ? 'badge-running'
                : run.state === 'completed'
                ? 'badge-completed'
                : 'badge-failed'
            }`}>
              {run.state === 'running' && <span className="pulse-dot" />}
              {run.state}
            </span>
          ),
        },
        {
          key: 'created_at',
          label: 'Created',
          width: '180px',
          render: (run) => (
            <span className="text-sm" style={{ color: 'var(--text-secondary)' }}>
              {new Date(run.created_at).toLocaleString()}
            </span>
          ),
        },
      ]
    : [
        {
          key: 'run_id',
          label: 'Run ID',
          width: '150px',
          render: (run) => (
            <button
              onClick={(e) => {
                e.stopPropagation();
                navigate(`/runs/${run.id}`);
              }}
              className="mono text-sm cursor-pointer transition-colors"
              style={{ color: 'var(--accent-hover)' }}
              onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--accent)')}
              onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--accent-hover)')}
            >
              {run.run_id}
            </button>
          ),
        },
        {
          key: 'name',
          label: 'Name',
          width: '250px',
          render: (run) => (
            <span className="text-sm truncate block" style={{ color: 'var(--text-primary)' }} title={run.name}>
              {run.name}
            </span>
          ),
        },
        {
          key: 'tags',
          label: 'Tags',
          width: '200px',
          render: (run) => (
            <div className="flex flex-nowrap gap-1 overflow-x-auto">
              {run.tags ? (
                run.tags.split(',').map((tag, idx) => (
                  <span
                    key={idx}
                    className="inline-flex px-2 py-0.5 text-xs font-medium rounded-md whitespace-nowrap"
                    style={{ backgroundColor: 'var(--bg-elevated)', color: 'var(--text-secondary)' }}
                    title={tag}
                  >
                    {tag}
                  </span>
                ))
              ) : (
                <span className="text-sm" style={{ color: 'var(--text-tertiary)' }}>-</span>
              )}
            </div>
          ),
        },
        ...metricColumnDefs,
        {
          key: 'state',
          label: 'State',
          width: '120px',
          render: (run) => (
            <span className={`badge ${
              run.state === 'running'
                ? 'badge-running'
                : run.state === 'completed'
                ? 'badge-completed'
                : 'badge-failed'
            }`}>
              {run.state === 'running' && <span className="pulse-dot" />}
              {run.state}
            </span>
          ),
        },
        {
          key: 'created_at',
          label: 'Created',
          width: '180px',
          render: (run) => (
            <span className="text-sm" style={{ color: 'var(--text-secondary)' }}>
              {new Date(run.created_at).toLocaleString()}
            </span>
          ),
        },
      ];

  const rowVirtualizer = useVirtualizer({
    count: hasMore ? sortedRuns.length + 1 : sortedRuns.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 52, // Height of each row in pixels
    overscan: 5, // Number of rows to render outside viewport
  });

  const virtualItems = rowVirtualizer.getVirtualItems();

  // Infinite scroll: fetch more when scrolling near the end
  useEffect(() => {
    const [lastItem] = [...virtualItems].reverse();

    if (!lastItem) {
      return;
    }

    if (
      lastItem.index >= sortedRuns.length - 1 &&
      hasMore &&
      !isFetchingNextPage
    ) {
      fetchNextPage?.();
    }
  }, [
    hasMore,
    fetchNextPage,
    sortedRuns.length,
    isFetchingNextPage,
    virtualItems,
  ]);

  const handleHeaderClick = (key: string) => {
    if (onSort) {
      onSort(key);
    }
  };

  if (isLoading && sortedRuns.length === 0) {
    return (
      <div className="card p-8">
        <div className="space-y-3">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="skeleton h-12 rounded-md"></div>
          ))}
        </div>
      </div>
    );
  }

  if (sortedRuns.length === 0) {
    return (
      <div className="card p-12 text-center">
        <svg className="mx-auto mb-4" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" style={{ color: 'var(--text-tertiary)' }}>
          <path d="M4 20h16a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.93a2 2 0 0 1-1.66-.9l-.82-1.2A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13c0 1.1.9 2 2 2Z"/>
        </svg>
        <p className="heading-md mb-1">No runs found</p>
        <p className="text-body">Try adjusting your filters or start a new experiment</p>
      </div>
    );
  }

  return (
    <div className="card p-0 overflow-hidden">
      {/* Table Header */}
      <div className="table-header flex items-center" style={{ minWidth: '900px' }}>
        {columns.map((column) => (
          <div
            key={column.key}
            className={`px-6 py-3 text-left flex items-center gap-1 flex-shrink-0 ${
              onSort && column.key !== 'select' ? 'cursor-pointer' : ''
            }`}
            style={{ width: column.width, minWidth: column.width, flex: '0 0 auto' }}
            onClick={() => column.key !== 'select' && handleHeaderClick(column.key)}
          >
            {column.key === 'select' ? (
              <div
                className="flex items-center justify-center cursor-pointer"
                style={{
                  width: '16px',
                  height: '16px',
                  borderRadius: '3px',
                  border: `2px solid ${
                    sortedRuns.length > 0 && selectedRunIds.length === sortedRuns.length
                      ? 'var(--accent)'
                      : 'var(--border)'
                  }`,
                  backgroundColor: sortedRuns.length > 0 && selectedRunIds.length === sortedRuns.length ? 'var(--accent)' : 'transparent',
                  transition: 'all 0.15s ease',
                  flexShrink: 0,
                }}
                onClick={(e) => {
                  e.stopPropagation();
                  handleToggleAll();
                }}
                onMouseEnter={(e) => {
                  if (!(sortedRuns.length > 0 && selectedRunIds.length === sortedRuns.length)) {
                    e.currentTarget.style.borderColor = 'var(--accent)';
                    e.currentTarget.style.backgroundColor = 'var(--accent-muted)';
                  }
                }}
                onMouseLeave={(e) => {
                  if (!(sortedRuns.length > 0 && selectedRunIds.length === sortedRuns.length)) {
                    e.currentTarget.style.borderColor = 'var(--border)';
                    e.currentTarget.style.backgroundColor = 'transparent';
                  }
                }}
              >
                {sortedRuns.length > 0 && selectedRunIds.length === sortedRuns.length && (
                  <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="20 6 9 17 4 12"/>
                  </svg>
                )}
              </div>
            ) : (
              <>
                <span>{column.label}</span>
                {sortBy === column.key && (
                  <span style={{ color: 'var(--accent)' }}>
                    {sortOrder === 'asc' ? <ChevronUpIcon /> : <ChevronDownIcon />}
                  </span>
                )}
              </>
            )}
          </div>
        ))}
      </div>

      {/* Virtual Scrolling Container */}
      <div
        ref={parentRef}
        className="overflow-auto"
        style={{ height: '600px', minWidth: '900px' }}
      >
        <div
          style={{
            height: `${rowVirtualizer.getTotalSize()}px`,
            width: '100%',
            position: 'relative',
          }}
        >
          {virtualItems.map((virtualRow) => {
            const isLoaderRow = virtualRow.index > sortedRuns.length - 1;
            const run = sortedRuns[virtualRow.index];

            return (
              <div
                key={virtualRow.index}
                className={`absolute top-0 left-0 w-full items-center table-row ${
                  !isLoaderRow ? '' : ''
                }`}
                style={{
                  height: `${virtualRow.size}px`,
                  transform: `translateY(${virtualRow.start}px)`,
                  display: 'flex',
                  flexDirection: 'row',
                }}
              >
                {isLoaderRow ? (
                  <div className="w-full px-6 py-4 text-center text-sm text-gray-500">
                    {isFetchingNextPage ? 'Loading more...' : 'Load more'}
                  </div>
                ) : (
                  <>
                    {columns.map((column) => (
                      <div
                        key={column.key}
                        className="px-6 py-3 flex-shrink-0"
                        style={{ width: column.width, minWidth: column.width, flex: '0 0 auto' }}
                      >
                        {column.render(run, metricValues)}
                      </div>
                    ))}
                  </>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Footer with count */}
      <div 
        className="border-t px-6 py-3 text-sm"
        style={{ backgroundColor: 'var(--bg-primary)', borderColor: 'var(--border)', color: 'var(--text-secondary)' }}
      >
        Showing {sortedRuns.length} {sortedRuns.length === 1 ? 'run' : 'runs'}
        {hasMore && ' (scroll for more)'}
      </div>
    </div>
  );
}
