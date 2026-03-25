import { useParams, useNavigate } from 'react-router-dom';
import { useState, useMemo, useRef } from 'react';
import {
  useProject,
  useInfiniteRuns,
  useProjectTags,
  useAvailableColumns,
  useCustomViews,
  useCreateCustomView,
  useUpdateCustomView,
  useDeleteCustomView,
  useDeleteRun,
} from '../api/client';
import type { RunFilters, CustomView } from '../api/client';
import VirtualRunsTable from '../components/RunsTable/VirtualRunsTable';

export default function RunsPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const [filters, setFilters] = useState<RunFilters>({
    project_id: parseInt(projectId || '0'),
  });
  const [sortBy, setSortBy] = useState<string>('created_at');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [selectedRunIds, setSelectedRunIds] = useState<number[]>([]);
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [selectedMetricColumns, setSelectedMetricColumns] = useState<string[]>([]);
  const [showSaveViewModal, setShowSaveViewModal] = useState(false);
  const [newViewName, setNewViewName] = useState('');
  const [currentView, setCurrentView] = useState<CustomView | null>(null);
  const viewsDropdownRef = useRef<HTMLDetailsElement>(null);

  const projectIdNum = parseInt(projectId || '0');
  const { data: project, isLoading: projectLoading } = useProject(projectIdNum);
  const { data: availableTags } = useProjectTags(projectIdNum);
  const { data: availableColumns } = useAvailableColumns(projectIdNum);
  const { data: customViews } = useCustomViews(projectIdNum);
  const createViewMutation = useCreateCustomView(projectIdNum);
  const updateViewMutation = useUpdateCustomView(projectIdNum);
  const deleteViewMutation = useDeleteCustomView(projectIdNum);
  const deleteRunMutation = useDeleteRun();

  const handleDeleteSelectedRuns = async () => {
    if (selectedRunIds.length === 0) return;
    if (!confirm(`Delete ${selectedRunIds.length} selected run(s)? This cannot be undone.`)) return;
    await Promise.all(selectedRunIds.map((id) => deleteRunMutation.mutateAsync(id)));
    setSelectedRunIds([]);
  };
  const isMetricSort = sortBy.startsWith('metric:');

  const {
    data,
    isLoading: runsLoading,
    error,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = useInfiniteRuns({
    ...filters,
    tags: selectedTags.length > 0 ? selectedTags.join(',') : undefined,
    // Only use backend sorting for non-metric columns
    sort_by: isMetricSort ? 'created_at' : sortBy,
    sort_order: isMetricSort ? 'desc' : sortOrder,
  });

  // Flatten all pages into a single array of runs
  const runs = useMemo(() => {
    return data?.pages.flatMap((page) => page.runs) ?? [];
  }, [data]);

  const total = data?.pages[0]?.total ?? 0;

  const isLoading = projectLoading || runsLoading;

  const handleSort = (key: string) => {
    if (sortBy === key) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(key);
      setSortOrder('asc');
    }
  };

  const handleTagToggle = (tag: string) => {
    setSelectedTags(prev =>
      prev.includes(tag)
        ? prev.filter(t => t !== tag)
        : [...prev, tag]
    );
  };

  const handleMetricColumnToggle = (metricPath: string) => {
    setSelectedMetricColumns(prev =>
      prev.includes(metricPath)
        ? prev.filter(m => m !== metricPath)
        : [...prev, metricPath]
    );
  };

  const handleSaveView = () => {
    if (!newViewName.trim()) return;

    const viewData = {
      name: newViewName,
      filters: JSON.stringify({
        state: filters.state,
        search: filters.search,
        tags: selectedTags,
      }),
      columns: JSON.stringify(selectedMetricColumns),
      sort_by: JSON.stringify({ sort_by: sortBy, sort_order: sortOrder }),
    };

    if (currentView) {
      // Update existing view
      updateViewMutation.mutate(
        { viewId: currentView.id, view: viewData },
        {
          onSuccess: (updatedView) => {
            setShowSaveViewModal(false);
            setNewViewName('');
            setCurrentView(updatedView);
          },
        }
      );
    } else {
      // Create new view
      createViewMutation.mutate(viewData, {
        onSuccess: (newView) => {
          setShowSaveViewModal(false);
          setNewViewName('');
          setCurrentView(newView);
        },
      });
    }
  };

  const handleCloseModal = () => {
    setShowSaveViewModal(false);
    setNewViewName('');
    // Don't clear currentView here - keep it loaded
  };

  const handleLoadView = (viewId: number) => {
    const view = customViews?.find(v => v.id === viewId);
    if (!view) return;

    try {
      // Load filters
      if (view.filters) {
        const parsedFilters = JSON.parse(view.filters);
        setFilters({
          ...filters,
          state: parsedFilters.state,
          search: parsedFilters.search,
        });
        setSelectedTags(parsedFilters.tags || []);
      }

      // Load columns
      if (view.columns) {
        const parsedColumns = JSON.parse(view.columns);
        setSelectedMetricColumns(parsedColumns);
      }

      // Load sort
      if (view.sort_by) {
        const parsedSort = JSON.parse(view.sort_by);
        setSortBy(parsedSort.sort_by);
        setSortOrder(parsedSort.sort_order);
      }

      // Set as current view
      setCurrentView(view);

      // Close the dropdown
      if (viewsDropdownRef.current) {
        viewsDropdownRef.current.open = false;
      }
    } catch (err) {
      console.error('Failed to load view:', err);
    }
  };

  const handleOpenSaveModal = (editMode = false) => {
    if (editMode && currentView) {
      setNewViewName(currentView.name);
    } else {
      setNewViewName('');
      setCurrentView(null);
    }
    setShowSaveViewModal(true);
  };

  const handleClearView = () => {
    // Reset all filters and settings to defaults
    setCurrentView(null);
    setFilters({
      project_id: projectIdNum,
    });
    setSelectedTags([]);
    setSelectedMetricColumns([]);
    setSortBy('created_at');
    setSortOrder('desc');
  };

  const handleDeleteView = (viewId: number) => {
    if (confirm('Are you sure you want to delete this view?')) {
      deleteViewMutation.mutate(viewId, {
        onSuccess: () => {
          // Clear current view if it was the deleted one
          if (currentView?.id === viewId) {
            handleClearView();
          }
        },
      });
    }
  };

  if (error) {
    return (
      <div className="p-8">
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 text-red-700 dark:text-red-400">
          <h3 className="font-semibold mb-1">Error loading runs</h3>
          <p className="text-sm">{error.message}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400 mb-2">
          <button
            onClick={() => navigate('/projects')}
            className="hover:text-primary-600 transition-colors"
          >
            Projects
          </button>
          <span>/</span>
          <span className="text-gray-900 dark:text-gray-100">{project?.name}</span>
        </div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">{project?.name}</h1>
        <p className="text-gray-600 dark:text-gray-400 mt-1">
          {total} {total === 1 ? 'run' : 'runs'}
        </p>
      </div>

      {/* Custom Views */}
      <div className="mb-4 flex gap-3 items-center flex-wrap">
        {/* Current View Indicator */}
        {currentView && (
          <div className="px-3 py-1 bg-primary-50 dark:bg-primary-900/20 border border-primary-200 dark:border-primary-800 rounded-md text-sm text-primary-700 dark:text-primary-400 flex items-center gap-2">
            <span>📋 {currentView.name}</span>
            <button
              onClick={handleClearView}
              className="text-primary-600 dark:text-primary-400 hover:text-primary-800 dark:hover:text-primary-300"
              title="Clear view and reset all filters"
            >
              ✕
            </button>
          </div>
        )}

        {/* View Selector */}
        {customViews && customViews.length > 0 && (
          <div className="relative">
            <details ref={viewsDropdownRef} className="group">
              <summary className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md cursor-pointer focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent bg-white dark:bg-gray-800 list-none flex items-center gap-2 text-gray-900 dark:text-gray-100">
                <span>📋 Views</span>
                <span className="text-xs">▼</span>
              </summary>
              <div className="absolute z-10 mt-1 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-md shadow-lg min-w-[250px]">
                {customViews.map((view) => (
                  <div
                    key={view.id}
                    className={`flex items-center justify-between px-4 py-2 hover:bg-gray-50 dark:hover:bg-gray-700 ${
                      currentView?.id === view.id ? 'bg-primary-50 dark:bg-primary-900/20' : ''
                    }`}
                  >
                    <button
                      onClick={() => handleLoadView(view.id)}
                      className="flex-1 text-left text-sm text-gray-900 dark:text-gray-100"
                    >
                      {view.name}
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeleteView(view.id);
                      }}
                      className="ml-2 text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-300"
                      title="Delete view"
                    >
                      🗑️
                    </button>
                  </div>
                ))}
              </div>
            </details>
          </div>
        )}

        {/* Save/Update View Buttons */}
        {currentView ? (
          <button
            onClick={() => handleOpenSaveModal(true)}
            className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 transition-colors text-sm"
          >
            💾 Update "{currentView.name}"
          </button>
        ) : (
          <button
            onClick={() => handleOpenSaveModal(false)}
            className="px-4 py-2 border border-primary-600 text-primary-600 dark:text-primary-400 rounded-md hover:bg-primary-50 dark:hover:bg-primary-900/20 transition-colors text-sm"
          >
            💾 Save as New View
          </button>
        )}
      </div>

      {/* Filters */}
      <div className="mb-4 flex gap-3 items-center justify-between">
        <div className="flex gap-3 flex-wrap">
          <input
            type="text"
            placeholder="Search runs..."
            className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500"
            onChange={(e) =>
              setFilters({ ...filters, search: e.target.value || undefined })
            }
          />
          <select
            className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
            onChange={(e) =>
              setFilters({ ...filters, state: e.target.value || undefined })
            }
          >
            <option value="">All States</option>
            <option value="running">Running</option>
            <option value="completed">Completed</option>
            <option value="failed">Failed</option>
          </select>

          {/* Tag Filter */}
          {availableTags && availableTags.length > 0 && (
            <div className="relative">
              <details className="group">
                <summary className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md cursor-pointer focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent bg-white dark:bg-gray-800 list-none flex items-center gap-2 text-gray-900 dark:text-gray-100">
                  <span>
                    {selectedTags.length === 0
                      ? 'Filter by tags'
                      : `${selectedTags.length} tag${selectedTags.length > 1 ? 's' : ''} selected`}
                  </span>
                  <span className="text-xs">▼</span>
                </summary>
                <div className="absolute z-10 mt-1 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-md shadow-lg max-h-60 overflow-auto min-w-[200px]">
                  {availableTags.map((tag) => (
                    <label
                      key={tag}
                      className="flex items-center gap-2 px-4 py-2 hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer"
                    >
                      <input
                        type="checkbox"
                        checked={selectedTags.includes(tag)}
                        onChange={() => handleTagToggle(tag)}
                        className="w-4 h-4 text-primary-600 rounded border-gray-300 dark:border-gray-600 focus:ring-primary-500"
                      />
                      <span className="text-sm text-gray-900 dark:text-gray-100">{tag}</span>
                    </label>
                  ))}
                </div>
              </details>
            </div>
          )}

          {/* Column Selector */}
          {availableColumns && availableColumns.length > 0 && (
            <div className="relative">
              <details className="group">
                <summary className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md cursor-pointer focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent bg-white dark:bg-gray-800 list-none flex items-center gap-2 text-gray-900 dark:text-gray-100">
                  <span>
                    {selectedMetricColumns.length === 0
                      ? 'Add columns'
                      : `${selectedMetricColumns.length} metric${selectedMetricColumns.length > 1 ? 's' : ''}`}
                  </span>
                  <span className="text-xs">▼</span>
                </summary>
                <div className="absolute z-10 mt-1 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-md shadow-lg max-h-60 overflow-auto min-w-[250px]">
                  {availableColumns.map((column) => (
                    <label
                      key={column}
                      className="flex items-center gap-2 px-4 py-2 hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer"
                    >
                      <input
                        type="checkbox"
                        checked={selectedMetricColumns.includes(column)}
                        onChange={() => handleMetricColumnToggle(column)}
                        className="w-4 h-4 text-primary-600 rounded border-gray-300 dark:border-gray-600 focus:ring-primary-500"
                      />
                      <span className="text-sm font-mono text-xs text-gray-900 dark:text-gray-100">{column}</span>
                    </label>
                  ))}
                </div>
              </details>
            </div>
          )}
        </div>

        {selectedRunIds.length > 0 && (
          <div className="flex gap-2 items-center">
            <span className="text-sm text-gray-600 dark:text-gray-400">
              {selectedRunIds.length} selected
            </span>
            <button
              onClick={() => navigate(`/compare?runs=${selectedRunIds.join(',')}`)}
              className="btn-primary text-sm"
              disabled={selectedRunIds.length < 2}
            >
              Compare Runs
            </button>
            <button
              onClick={handleDeleteSelectedRuns}
              disabled={deleteRunMutation.isPending}
              className="px-3 py-2 text-sm text-red-600 dark:text-red-400 border border-red-300 dark:border-red-700 rounded-md hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors disabled:opacity-50"
            >
              {deleteRunMutation.isPending ? 'Deleting…' : '🗑️ Delete Selected'}
            </button>
            <button
              onClick={() => setSelectedRunIds([])}
              className="text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 transition-colors"
            >
              Clear
            </button>
          </div>
        )}
      </div>

      {/* Save View Modal */}
      {showSaveViewModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 dark:bg-opacity-70 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-gray-100">
              {currentView ? `Update View "${currentView.name}"` : 'Save New Custom View'}
            </h3>
            <input
              type="text"
              placeholder="View name..."
              value={newViewName}
              onChange={(e) => setNewViewName(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent mb-4 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500"
              autoFocus
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleSaveView();
                if (e.key === 'Escape') handleCloseModal();
              }}
            />
            <div className="text-sm text-gray-600 dark:text-gray-400 mb-4">
              <p>{currentView ? 'This will update the view with:' : 'This will save:'}</p>
              <ul className="list-disc list-inside mt-2">
                <li>Current filters (state, search, tags: {selectedTags.length})</li>
                <li>Selected metric columns ({selectedMetricColumns.length})</li>
                <li>Sort settings ({sortBy} {sortOrder})</li>
              </ul>
            </div>
            <div className="flex gap-2 justify-end">
              <button
                onClick={handleCloseModal}
                className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors text-gray-700 dark:text-gray-200"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveView}
                disabled={!newViewName.trim() || createViewMutation.isPending || updateViewMutation.isPending}
                className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {createViewMutation.isPending || updateViewMutation.isPending
                  ? 'Saving...'
                  : currentView
                  ? 'Update'
                  : 'Save'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Virtual Runs Table */}
      <VirtualRunsTable
        runs={runs}
        isLoading={isLoading}
        hasMore={hasNextPage}
        fetchNextPage={fetchNextPage}
        isFetchingNextPage={isFetchingNextPage}
        onSort={handleSort}
        sortBy={sortBy}
        sortOrder={sortOrder}
        selectable={true}
        selectedRunIds={selectedRunIds}
        onSelectionChange={setSelectedRunIds}
        metricColumns={selectedMetricColumns}
        projectId={parseInt(projectId || '0')}
      />
    </div>
  );
}
