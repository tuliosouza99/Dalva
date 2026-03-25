import { useVirtualizer } from '@tanstack/react-virtual';
import { useNavigate } from 'react-router-dom';
import { useRef, useEffect, useState, useMemo } from 'react';
import type { Run } from '../../api/client';
import { api } from '../../api/client';

interface Column {
  key: string;
  label: string;
  width: string;
  render: (run: Run, metricValues?: Record<number, Record<string, number | null>>) => React.ReactNode;
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
  projectId,
}: VirtualRunsTableProps) {
  const navigate = useNavigate();
  const parentRef = useRef<HTMLDivElement>(null);
  const [metricValues, setMetricValues] = useState<Record<number, Record<string, number | null>>>({});

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
        const aValue = metricValues[a.id]?.[metricPath];
        const bValue = metricValues[b.id]?.[metricPath];

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
      const value = metricVals?.[run.id]?.[metricPath];
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
            <input
              type="checkbox"
              checked={selectedRunIds.includes(run.id)}
              onChange={(e) => {
                e.stopPropagation();
                handleToggleSelection(run.id);
              }}
              onClick={(e) => e.stopPropagation()}
              className="w-4 h-4 text-primary-600 rounded border-gray-300 focus:ring-primary-500"
            />
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
          className="text-sm font-medium text-primary-600 font-mono hover:text-primary-800 hover:underline cursor-pointer"
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
        <span className="text-sm text-gray-900 dark:text-gray-100 truncate block" title={run.name}>
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
                className="inline-flex px-2 py-0.5 text-xs font-medium rounded bg-gray-100 dark:bg-gray-700 dark:text-gray-300 whitespace-nowrap"
                title={tag}
              >
                {tag}
              </span>
            ))
          ) : (
            <span className="text-sm text-gray-400 dark:text-gray-500">-</span>
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
        <span
          className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
            run.state === 'running'
              ? 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-400'
              : run.state === 'completed'
              ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-400'
              : 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-400'
          }`}
        >
          {run.state}
        </span>
      ),
    },
    {
      key: 'created_at',
      label: 'Created',
      width: '180px',
      render: (run) => (
        <span className="text-sm text-gray-600 dark:text-gray-400">
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
              className="text-sm font-medium text-primary-600 font-mono hover:text-primary-800 hover:underline cursor-pointer"
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
            <span className="text-sm text-gray-900 dark:text-gray-100 truncate block" title={run.name}>
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
                    className="inline-flex px-2 py-0.5 text-xs font-medium rounded bg-gray-100 dark:bg-gray-700 dark:text-gray-300 whitespace-nowrap"
                    title={tag}
                  >
                    {tag}
                  </span>
                ))
              ) : (
                <span className="text-sm text-gray-400 dark:text-gray-500">-</span>
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
            <span
              className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                run.state === 'running'
                  ? 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-400'
                  : run.state === 'completed'
                  ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-400'
                  : 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-400'
              }`}
            >
              {run.state}
            </span>
          ),
        },
        {
          key: 'created_at',
          label: 'Created',
          width: '180px',
          render: (run) => (
            <span className="text-sm text-gray-600 dark:text-gray-400">
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
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-8">
        <div className="animate-pulse space-y-3">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="h-12 bg-gray-200 dark:bg-gray-700 rounded"></div>
          ))}
        </div>
      </div>
    );
  }

  if (sortedRuns.length === 0) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-12 text-center">
        <p className="text-gray-500 dark:text-gray-400 text-lg">No runs found</p>
        <p className="text-gray-400 dark:text-gray-500 text-sm mt-2">
          Try adjusting your filters or start a new experiment
        </p>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
      {/* Table Header */}
      <div className="bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700 flex items-center" style={{ minWidth: '900px' }}>
        {columns.map((column) => (
          <div
            key={column.key}
            className={`px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider flex items-center gap-1 ${
              onSort && column.key !== 'select' ? 'cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800' : ''
            }`}
            style={{ width: column.width, minWidth: column.width }}
            onClick={() => column.key !== 'select' && handleHeaderClick(column.key)}
          >
            {column.key === 'select' ? (
              <input
                type="checkbox"
                checked={sortedRuns.length > 0 && selectedRunIds.length === sortedRuns.length}
                onChange={handleToggleAll}
                className="w-4 h-4 text-primary-600 rounded border-gray-300 focus:ring-primary-500"
              />
            ) : (
              <>
                <span>{column.label}</span>
                {sortBy === column.key && (
                  <span className="text-primary-600">
                    {sortOrder === 'asc' ? '↑' : '↓'}
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
                className={`absolute top-0 left-0 w-full flex items-center ${
                  !isLoaderRow
                    ? 'hover:bg-gray-50 dark:hover:bg-gray-700/50 border-b border-gray-200 dark:border-gray-700'
                    : ''
                }`}
                style={{
                  height: `${virtualRow.size}px`,
                  transform: `translateY(${virtualRow.start}px)`,
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
                        className="px-6 py-3"
                        style={{ width: column.width, minWidth: column.width }}
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
      <div className="bg-gray-50 dark:bg-gray-900 border-t border-gray-200 dark:border-gray-700 px-6 py-3 text-sm text-gray-600 dark:text-gray-400">
        Showing {sortedRuns.length} {sortedRuns.length === 1 ? 'run' : 'runs'}
        {hasMore && ' (scroll for more)'}
      </div>
    </div>
  );
}
