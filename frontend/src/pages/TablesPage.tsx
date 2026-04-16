import { useParams, useNavigate } from 'react-router-dom';
import { useState, useMemo } from 'react';
import { useTables, useProject, useDeleteTable } from '../api/client';
import type { TableFilters } from '../api/client';
import { Search, X, Trash2, Table2 } from 'lucide-react';
import { SortIcon } from '../components/Icons';

export default function TablesPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const projectIdNum = parseInt(projectId || '0');

  const [filters] = useState<TableFilters>({
    project_id: projectIdNum,
  });
  const [sortBy, setSortBy] = useState<string>('created_at');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [search, setSearch] = useState('');

  const { data: project, isLoading: projectLoading } = useProject(projectIdNum);
  const { data, isLoading: tablesLoading } = useTables({
    ...filters,
    sort_by: sortBy,
    sort_order: sortOrder,
  });
  const deleteTableMutation = useDeleteTable();

  const total = data?.total ?? 0;

  const filteredTables = useMemo(() => {
    if (!search) return data?.tables ?? [];
    return (data?.tables ?? []).filter(t =>
      t.table_id.toLowerCase().includes(search.toLowerCase()) ||
      (t.name && t.name.toLowerCase().includes(search.toLowerCase()))
    );
  }, [data?.tables, search]);

  const handleSort = (column: string) => {
    if (sortBy === column) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(column);
      setSortOrder('asc');
    }
  };

  const handleDeleteTable = async (tableId: number, e: React.MouseEvent) => {
    e.stopPropagation();
    if (confirm('Delete this table?')) {
      await deleteTableMutation.mutateAsync(tableId);
    }
  };

  const handleRowClick = (tableId: number) => {
    navigate(`/tables/${tableId}?project=${projectIdNum}`);
  };

  if (projectLoading || tablesLoading) {
    return (
      <div className="p-8 page-enter">
        <div className="mb-6">
          <div className="skeleton h-8 w-48 rounded-md mb-2"></div>
          <div className="skeleton h-4 w-32 rounded"></div>
        </div>
        <div className="skeleton h-64 rounded-lg"></div>
      </div>
    );
  }

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
          <span style={{ color: 'var(--text-primary)' }}>{project?.name}</span>
        </div>
        <h1 className="heading-display">Tables</h1>
        <p className="text-body mt-1">
          {total} {total === 1 ? 'table' : 'tables'}
        </p>
      </div>

      <div className="mb-6 flex gap-3 items-center">
        <div className="relative flex-1 max-w-xs">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: 'var(--text-tertiary)' }} />
          <input
            type="text"
            placeholder="Search tables..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="input pl-10 pr-10"
          />
          {search && (
            <button
              onClick={() => setSearch('')}
              className="absolute right-3 top-1/2 -translate-y-1/2 hover:text-[var(--text-primary)] transition-colors"
              style={{ color: 'var(--text-tertiary)' }}
            >
              <X size={16} />
            </button>
          )}
        </div>
      </div>

      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        <table className="w-full">
          <thead>
            <tr className="table-header">
              <th
                className="px-4 py-3 text-left cursor-pointer hover:text-[var(--text-primary)] transition-colors"
                onClick={() => handleSort('table_id')}
              >
                <div className="flex items-center gap-2">
                  ID
                  <SortIcon column="table_id" sortBy={sortBy} sortOrder={sortOrder} />
                </div>
              </th>
              <th
                className="px-4 py-3 text-left cursor-pointer hover:text-[var(--text-primary)] transition-colors"
                onClick={() => handleSort('name')}
              >
                <div className="flex items-center gap-2">
                  Name
                  <SortIcon column="name" sortBy={sortBy} sortOrder={sortOrder} />
                </div>
              </th>
              <th
                className="px-4 py-3 text-left cursor-pointer hover:text-[var(--text-primary)] transition-colors"
                onClick={() => handleSort('row_count')}
              >
                <div className="flex items-center gap-2">
                  Rows
                  <SortIcon column="row_count" sortBy={sortBy} sortOrder={sortOrder} />
                </div>
              </th>
              <th
                className="px-4 py-3 text-left cursor-pointer hover:text-[var(--text-primary)] transition-colors"
                onClick={() => handleSort('state')}
              >
                <div className="flex items-center gap-2">
                  State
                  <SortIcon column="state" sortBy={sortBy} sortOrder={sortOrder} />
                </div>
              </th>
              <th
                className="px-4 py-3 text-left cursor-pointer hover:text-[var(--text-primary)] transition-colors"
                onClick={() => handleSort('created_at')}
              >
                <div className="flex items-center gap-2">
                  Created
                  <SortIcon column="created_at" sortBy={sortBy} sortOrder={sortOrder} />
                </div>
              </th>
              <th className="px-4 py-3 text-right"></th>
            </tr>
          </thead>
          <tbody>
            {filteredTables.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-16 text-center">
                  <Table2 size={32} className="mx-auto mb-3" style={{ color: 'var(--text-tertiary)' }} />
                  <p className="text-body">No tables found</p>
                </td>
              </tr>
            ) : (
              filteredTables.map((table) => (
                <tr
                  key={table.id}
                  className="table-row cursor-pointer"
                  onClick={() => handleRowClick(table.id)}
                >
                  <td className="px-4 py-3">
                    <span className="mono text-sm" style={{ color: 'var(--accent-hover)' }}>{table.table_id}</span>
                  </td>
                  <td className="px-4 py-3 text-sm" style={{ color: 'var(--text-primary)' }}>
                    {table.name || '-'}
                  </td>
                  <td className="px-4 py-3 text-sm mono" style={{ color: 'var(--text-primary)' }}>
                    {table.row_count.toLocaleString()}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`badge ${
                      table.state === 'active'
                        ? 'badge-running'
                        : 'badge-completed'
                    }`}>
                      {table.state === 'active' && <span className="pulse-dot" />}
                      {table.state.charAt(0).toUpperCase() + table.state.slice(1)}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm" style={{ color: 'var(--text-secondary)' }}>
                    {new Date(table.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={(e) => handleDeleteTable(table.id, e)}
                      className="p-1.5 rounded-md transition-colors hover:bg-[rgba(239,68,68,0.1)]"
                      style={{ color: 'var(--text-tertiary)' }}
                      onMouseEnter={(e) => (e.currentTarget.style.color = '#ef4444')}
                      onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--text-tertiary)')}
                    >
                      <Trash2 size={14} />
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {filteredTables.length > 0 && (
        <div className="mt-4 text-sm" style={{ color: 'var(--text-tertiary)' }}>
          Showing {filteredTables.length} of {total} tables
        </div>
      )}
    </div>
  );
}
