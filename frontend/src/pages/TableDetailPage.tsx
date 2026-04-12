import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { useState, useCallback, useEffect } from 'react';
import { useTable, useTableData, useTableStats, useRun, useProject, useDeleteTable, useUpdateTableState } from '../api/client';
import type { ColumnFilter } from '../api/client';
import { Link2, ChevronLeft, ChevronRight, Trash2, Table2, FilterX } from 'lucide-react';
import ColumnHeader from '../components/DataTable/ColumnHeader';

function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState(value);
  useEffect(() => {
    const handler = setTimeout(() => setDebouncedValue(value), delay);
    return () => clearTimeout(handler);
  }, [value, delay]);
  return debouncedValue;
}

export default function TableDetailPage() {
  const { tableId } = useParams<{ tableId: string }>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const tableIdNum = parseInt(tableId || '0');
  const projectId = searchParams.get('project');

  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(50);
  const [sortBy, setSortBy] = useState<string | null>(null);
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');
  const [filters, setFilters] = useState<ColumnFilter[]>([]);

  const debouncedFilters = useDebounce(filters, 400);

  const { data: table, isLoading: tableLoading } = useTable(tableIdNum);
  const { data: tableData, isLoading: dataLoading } = useTableData(tableIdNum, {
    limit: pageSize,
    offset: page * pageSize,
    sort_by: sortBy || undefined,
    sort_order: sortOrder,
    filters: filters.length > 0 ? filters : undefined,
  });
  const { data: tableStats } = useTableStats(tableIdNum, {
    filters: debouncedFilters.length > 0 ? debouncedFilters : undefined,
  });
  const deleteTableMutation = useDeleteTable();
  const updateTableStateMutation = useUpdateTableState();

  const { data: linkedRun } = useRun(table?.run_id || 0);
  const { data: project } = useProject(table?.project_id || 0);

  const totalPages = Math.ceil((tableData?.total || 0) / pageSize);
  const activeFilterCount = filters.length;

  const handleSort = (column: string) => {
    if (sortBy === column) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(column);
      setSortOrder('asc');
    }
    setPage(0);
  };

  const handleColumnFilter = useCallback((filter: ColumnFilter | undefined, columnName?: string) => {
    setFilters((prev) => {
      const col = filter?.column ?? columnName ?? '';
      const without = prev.filter((f) => f.column !== col);
      if (filter) {
        return [...without, filter];
      }
      return without;
    });
    setPage(0);
  }, []);

  const clearAllFilters = () => {
    setFilters([]);
    setPage(0);
  };

  const getColumnFilter = (colName: string): ColumnFilter | undefined => {
    return filters.find((f) => f.column === colName);
  };

  const renderCellValue = (value: unknown, type: string): React.ReactNode => {
    if (value === null || value === undefined) return <span style={{ color: 'var(--text-tertiary)' }}>-</span>;
    if (type === 'list' || type === 'dict') {
      try {
        return (
          <span className="mono text-xs px-1.5 py-0.5 rounded" style={{ backgroundColor: 'var(--bg-elevated)', color: 'var(--text-secondary)' }}>
            {JSON.stringify(value)}
          </span>
        );
      } catch {
        return String(value);
      }
    }
    if (type === 'date') {
      return new Date(String(value)).toLocaleString();
    }
    if (type === 'int' || type === 'float') {
      return <span className="mono">{String(value)}</span>;
    }
    return String(value);
  };

  const handleDelete = async () => {
    if (confirm('Delete this table? This cannot be undone.')) {
      await deleteTableMutation.mutateAsync(tableIdNum);
      navigate(`/projects/${projectId}/tables`);
    }
  };

  const handleLinkedRunClick = () => {
    if (linkedRun) {
      navigate(`/runs/${linkedRun.id}?project=${projectId}`);
    }
  };

  if (tableLoading) {
    return (
      <div className="p-8 page-enter">
        <div className="mb-6">
          <div className="skeleton h-8 w-48 rounded-md mb-2"></div>
          <div className="skeleton h-4 w-32 rounded"></div>
        </div>
        <div className="space-y-4">
          <div className="skeleton h-32 rounded-lg"></div>
          <div className="skeleton h-64 rounded-lg"></div>
        </div>
      </div>
    );
  }

  if (!table) {
    return (
      <div className="p-8 page-enter">
        <div className="card p-6" style={{ backgroundColor: 'rgba(239, 68, 68, 0.08)', borderColor: 'rgba(239, 68, 68, 0.2)' }}>
          <h3 className="font-semibold mb-1" style={{ color: 'var(--badge-failed)' }}>Table not found</h3>
          <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>The requested table does not exist.</p>
        </div>
      </div>
    );
  }

  const columns = tableData?.column_schema || [];

  return (
    <div className="p-8 page-enter">
      <div className="mb-6">
        <div className="flex items-center gap-2 text-sm mb-3" style={{ color: 'var(--text-tertiary)' }}>
          <button
            onClick={() => navigate('/projects')}
            className="hover:text-[var(--accent)] transition-colors"
          >
            Projects
          </button>
          <span>/</span>
          <button
            onClick={() => navigate(`/projects/${table.project_id}/tables`)}
            className="hover:text-[var(--accent)] transition-colors"
          >
            {project?.name}
          </button>
          <span>/</span>
          <span style={{ color: 'var(--text-primary)' }}>{table.table_id}</span>
        </div>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="heading-display">{table.name || table.table_id}</h1>
            <p className="mt-1">
              <span className="mono text-sm" style={{ color: 'var(--accent-hover)' }}>{table.table_id}</span>
              {table.name && (
                <span className="ml-3 text-sm" style={{ color: 'var(--text-secondary)' }}>{table.name}</span>
              )}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => {
                const newState = table.state === 'active' ? 'finished' : 'active';
                updateTableStateMutation.mutate({ tableId: table.id, state: newState });
              }}
              disabled={updateTableStateMutation.isPending}
              className={`badge cursor-pointer transition-opacity hover:opacity-80 ${
                table.state === 'active'
                  ? 'badge-running'
                  : 'badge-completed'
              }`}
              title={`Click to mark as ${table.state === 'active' ? 'finished' : 'active'}`}
            >
              {table.state === 'active' && <span className="pulse-dot" />}
              {table.state.charAt(0).toUpperCase() + table.state.slice(1)}
            </button>
            <button
              onClick={handleDelete}
              disabled={deleteTableMutation.isPending}
              className="btn-secondary text-sm"
              style={{ color: '#ef4444' }}
              title="Delete this table"
            >
              {deleteTableMutation.isPending ? 'Deleting…' : (
                <>
                  <Trash2 size={14} />
                  Delete
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 mb-6 card-stagger">
        <div className="card card-appear">
          <dt className="text-small">Log Mode</dt>
          <dd className="mt-1">
            <span className={`badge text-xs ${
              table.log_mode === 'IMMUTABLE'
                ? 'badge-completed'
                : table.log_mode === 'MUTABLE'
                ? 'badge-running'
                : 'badge-failed'
            }`}>
              {table.log_mode}
            </span>
          </dd>
        </div>
        <div className="card card-appear">
          <dt className="text-small">Version</dt>
          <dd className="text-lg font-semibold mt-1" style={{ color: 'var(--text-primary)' }}>{table.version}</dd>
        </div>
        <div className="card card-appear">
          <dt className="text-small">Rows</dt>
          <dd className="text-lg font-semibold mt-1" style={{ color: 'var(--text-primary)' }}>{(tableData?.total ?? table.row_count).toLocaleString()}</dd>
        </div>
        <div className="card card-appear">
          <dt className="text-small">Created</dt>
          <dd className="text-sm mt-1" style={{ color: 'var(--text-primary)' }}>{new Date(table.created_at).toLocaleString()}</dd>
        </div>
      </div>

      {linkedRun && (
        <div className="mb-6">
          <button
            onClick={handleLinkedRunClick}
            className="card flex items-center gap-3 hover:shadow-md transition-shadow cursor-pointer"
            style={{ padding: '12px 16px' }}
          >
            <Link2 size={16} style={{ color: 'var(--accent)' }} />
            <span className="text-sm" style={{ color: 'var(--text-secondary)' }}>Linked Run:</span>
            <span className="mono text-sm font-medium" style={{ color: 'var(--accent-hover)' }}>{linkedRun.run_id}</span>
            <span className="text-sm" style={{ color: 'var(--text-secondary)' }}>{linkedRun.name || 'unnamed'}</span>
          </button>
        </div>
      )}

      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        <div className="flex items-center justify-between px-4 py-3 border-b" style={{ borderColor: 'var(--border)' }}>
          <div className="flex items-center gap-2">
            <Table2 size={16} style={{ color: 'var(--text-tertiary)' }} />
            <span className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>Data</span>
            <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
              {tableData?.total ?? 0} rows
            </span>
            {activeFilterCount > 0 && (
              <span className="text-xs px-1.5 py-0.5 rounded" style={{ backgroundColor: 'var(--accent-muted)', color: 'var(--accent)' }}>
                {activeFilterCount} filter{activeFilterCount > 1 ? 's' : ''}
              </span>
            )}
          </div>
          <div className="flex items-center gap-4">
            {activeFilterCount > 0 && (
              <button
                onClick={clearAllFilters}
                className="flex items-center gap-1 text-xs px-2 py-1 rounded border transition-colors"
                style={{ borderColor: 'var(--border)', color: 'var(--text-secondary)' }}
                onMouseEnter={(e) => e.currentTarget.style.borderColor = 'var(--accent)'}
                onMouseLeave={(e) => e.currentTarget.style.borderColor = 'var(--border)'}
              >
                <FilterX size={11} />
                Clear
              </button>
            )}
            <div className="flex items-center gap-2">
              <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>Per page:</span>
              <select
                value={pageSize}
                onChange={(e) => {
                  setPageSize(Number(e.target.value));
                  setPage(0);
                }}
                className="text-xs px-2 py-1 rounded border"
                style={{ backgroundColor: 'var(--bg-surface)', borderColor: 'var(--border)', color: 'var(--text-primary)' }}
              >
                <option value={25}>25</option>
                <option value={50}>50</option>
                <option value={100}>100</option>
              </select>
            </div>
            <div className="flex items-center gap-1">
              <button
                onClick={() => setPage(p => Math.max(0, p - 1))}
                disabled={page === 0}
                className="p-1 rounded hover:bg-[var(--bg-elevated)] disabled:opacity-30 transition-colors"
                style={{ color: 'var(--text-secondary)' }}
              >
                <ChevronLeft size={16} />
              </button>
              <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                {page + 1} / {totalPages || 1}
              </span>
              <button
                onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
                disabled={page >= totalPages - 1}
                className="p-1 rounded hover:bg-[var(--bg-elevated)] disabled:opacity-30 transition-colors"
                style={{ color: 'var(--text-secondary)' }}
              >
                <ChevronRight size={16} />
              </button>
            </div>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full min-w-[600px]">
            <thead>
              <tr>
                {columns.map((col) => (
                  <ColumnHeader
                    key={col.name}
                    column={col}
                    stats={tableStats?.columns[col.name]}
                    sortBy={sortBy}
                    sortOrder={sortOrder}
                    filter={getColumnFilter(col.name)}
                    onSort={handleSort}
                    onFilter={handleColumnFilter}
                  />
                ))}
              </tr>
            </thead>
            <tbody>
              {dataLoading ? (
                <tr>
                  <td colSpan={columns.length} className="px-4 py-16 text-center">
                    <div className="text-body">Loading data...</div>
                  </td>
                </tr>
              ) : (tableData?.rows.length ?? 0) === 0 ? (
                <tr>
                  <td colSpan={columns.length} className="px-4 py-16 text-center">
                    <Table2 size={32} className="mx-auto mb-3" style={{ color: 'var(--text-tertiary)' }} />
                    <p className="text-body">
                      {activeFilterCount > 0 ? 'No rows match filters' : 'No data in this table'}
                    </p>
                    {activeFilterCount > 0 && (
                      <button
                        onClick={clearAllFilters}
                        className="mt-2 text-sm underline"
                        style={{ color: 'var(--accent)' }}
                      >
                        Clear all filters
                      </button>
                    )}
                  </td>
                </tr>
              ) : (
                tableData?.rows.map((row, idx) => (
                  <tr key={idx} className="table-row">
                    {columns.map((col) => (
                      <td key={col.name} className="px-4 py-2.5 text-sm" style={{ color: 'var(--text-primary)' }}>
                        {renderCellValue(row[col.name], col.type)}
                      </td>
                    ))}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
