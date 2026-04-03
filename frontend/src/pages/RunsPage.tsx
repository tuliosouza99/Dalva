import { useParams, useNavigate } from 'react-router-dom';
import { useState, useMemo, useRef, useEffect } from 'react';
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
import { useComparison } from '../contexts/ComparisonContext';

export default function RunsPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const { selectedRunIds, setSelectedRunIds, clearSelection, isAtMax, maxSelections } = useComparison();
  const selectedRunIdsRef = useRef(selectedRunIds);

  // Keep ref updated with latest selectedRunIds
  useEffect(() => {
    selectedRunIdsRef.current = selectedRunIds;
  }, [selectedRunIds]);

  const handleSelectionChange = (ids: number[]) => {
    if (isAtMax() && ids.length > selectedRunIds.length) {
      return;
    }
    setSelectedRunIds(ids);
  };
  const [filters, setFilters] = useState<RunFilters>({
    project_id: parseInt(projectId || '0'),
  });
  const [sortBy, setSortBy] = useState<string>('created_at');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [selectedMetricColumns, setSelectedMetricColumns] = useState<string[]>([]);
  const [showSaveViewModal, setShowSaveViewModal] = useState(false);
  const [newViewName, setNewViewName] = useState('');
  const [currentView, setCurrentView] = useState<CustomView | null>(null);
  const [originalViewState, setOriginalViewState] = useState<{
    filters: RunFilters;
    tags: string[];
    columns: string[];
    sortBy: string;
    sortOrder: 'asc' | 'desc';
  } | null>(null);
  const viewsDropdownRef = useRef<HTMLDetailsElement>(null);
  const [openDropdown, setOpenDropdown] = useState<string | null>(null);

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
    await Promise.all(selectedRunIds.map((id) => deleteRunMutation.mutateAsync(id)));
    clearSelection();
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

  // Close dropdown when clicking outside
  const dropdownRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setOpenDropdown(null);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

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
      let newFilters = { ...filters };
      let newTags: string[] = [];
      let newColumns: string[] = [];
      let newSortBy = 'created_at';
      let newSortOrder: 'asc' | 'desc' = 'desc';

      if (view.filters) {
        const parsedFilters = JSON.parse(view.filters);
        newFilters = {
          ...filters,
          state: parsedFilters.state,
          search: parsedFilters.search,
        };
        newTags = parsedFilters.tags || [];
        setFilters(newFilters);
        setSelectedTags(newTags);
      }

      // Load columns
      if (view.columns) {
        newColumns = JSON.parse(view.columns);
        setSelectedMetricColumns(newColumns);
      }

      // Load sort
      if (view.sort_by) {
        const parsedSort = JSON.parse(view.sort_by);
        newSortBy = parsedSort.sort_by;
        newSortOrder = parsedSort.sort_order;
        setSortBy(newSortBy);
        setSortOrder(newSortOrder);
      }

      // Set as current view and save original state
      setCurrentView(view);
      setOriginalViewState({
        filters: newFilters,
        tags: newTags,
        columns: newColumns,
        sortBy: newSortBy,
        sortOrder: newSortOrder,
      });

      // Close the dropdown
      if (viewsDropdownRef.current) {
        viewsDropdownRef.current.open = false;
      }
    } catch (err) {
      console.error('Failed to load view:', err);
    }
  };

  // Check if current state differs from original view state
  const hasViewChanges = useMemo(() => {
    if (!currentView || !originalViewState) return false;

    const filtersChanged = JSON.stringify(filters) !== JSON.stringify(originalViewState.filters);
    const tagsChanged = JSON.stringify(selectedTags) !== JSON.stringify(originalViewState.tags);
    const columnsChanged = JSON.stringify(selectedMetricColumns) !== JSON.stringify(originalViewState.columns);
    const sortChanged = sortBy !== originalViewState.sortBy || sortOrder !== originalViewState.sortOrder;

    return filtersChanged || tagsChanged || columnsChanged || sortChanged;
  }, [currentView, originalViewState, filters, selectedTags, selectedMetricColumns, sortBy, sortOrder]);

  const handleDiscardChanges = () => {
    if (!originalViewState) return;
    
    setFilters(originalViewState.filters);
    setSelectedTags(originalViewState.tags);
    setSelectedMetricColumns(originalViewState.columns);
    setSortBy(originalViewState.sortBy);
    setSortOrder(originalViewState.sortOrder);
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
    setOriginalViewState(null);
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
      <div className="p-8 page-enter">
        <div className="card p-6" style={{ backgroundColor: 'rgba(239, 68, 68, 0.08)', borderColor: 'rgba(239, 68, 68, 0.2)' }}>
          <h3 className="font-semibold mb-1" style={{ color: 'var(--badge-failed)' }}>Error loading runs</h3>
          <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>{error.message}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8 page-enter">
      {/* Header */}
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
        <h1 className="heading-display">{project?.name}</h1>
        <p className="text-body mt-1">
          {total} {total === 1 ? 'run' : 'runs'}
        </p>
      </div>

      {/* Custom Views */}
      <div className="mb-4 flex gap-3 items-center flex-wrap">
        {/* Current View Indicator */}
        {currentView && (
          <div 
            className="px-3 py-1.5 rounded-md text-sm flex items-center gap-2"
            style={{ backgroundColor: 'var(--accent-muted)', color: 'var(--accent-hover)' }}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M9 11H3v10h6V11z"/><path d="M15 3H9v10h6V3z"/><path d="M21 6h-6v12h6V6z"/>
            </svg>
            <span>{currentView.name}</span>
            <button
              onClick={handleClearView}
              className="ml-1 hover:opacity-70 transition-opacity"
              title="Clear view and reset all filters"
            >
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
                <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
              </svg>
            </button>
          </div>
        )}

        {/* View Selector */}
        {customViews && customViews.length > 0 && (
          <div className="relative">
            <button
              onClick={() => setOpenDropdown(openDropdown === 'views' ? null : 'views')}
              className="input list-none cursor-pointer flex items-center gap-2"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M9 11H3v10h6V11z"/><path d="M15 3H9v10h6V3z"/><path d="M21 6h-6v12h6V6z"/>
              </svg>
              <span>Views</span>
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="ml-auto transition-transform" style={{ transform: openDropdown === 'views' ? 'rotate(180deg)' : 'rotate(0deg)' }}>
                <polyline points="6 9 12 15 18 9"/>
              </svg>
            </button>
            {openDropdown === 'views' && (
              <div 
                className="absolute z-10 mt-1 rounded-md shadow-lg min-w-[250px]"
                style={{ backgroundColor: 'var(--bg-surface)', border: '1px solid var(--border)' }}
              >
                {customViews.map((view) => (
                  <div
                    key={view.id}
                    className="flex items-center justify-between px-4 py-2 transition-colors"
                    style={{ color: 'var(--text-primary)' }}
                    onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
                    onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
                  >
                    <button
                      onClick={() => {
                        handleLoadView(view.id);
                        setOpenDropdown(null);
                      }}
                      className="flex-1 text-left text-sm"
                    >
                      {view.name}
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeleteView(view.id);
                      }}
                      className="ml-2 transition-colors"
                      style={{ color: 'var(--text-tertiary)' }}
                      onMouseEnter={(e) => (e.currentTarget.style.color = '#ef4444')}
                      onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--text-tertiary)')}
                      title="Delete view"
                    >
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <polyline points="3 6 5 6 21 6"/>
                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                      </svg>
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Save/Update/Discard View Buttons */}
        {currentView ? (
          <>
            <button
              onClick={() => handleOpenSaveModal(true)}
              className="btn-secondary text-sm"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>
                <polyline points="17 21 17 13 7 13 7 21"/>
                <polyline points="7 3 7 8 15 8"/>
              </svg>
              Update "{currentView.name}"
            </button>
            {hasViewChanges && (
              <button
                onClick={handleDiscardChanges}
                className="btn-secondary text-sm"
                style={{ color: 'var(--text-secondary)' }}
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="3 6 5 6 21 6"/>
                  <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                </svg>
                Discard Changes
              </button>
            )}
          </>
        ) : (
          <button
            onClick={() => handleOpenSaveModal(false)}
            className="btn-secondary text-sm"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>
              <polyline points="17 21 17 13 7 13 7 21"/>
              <polyline points="7 3 7 8 15 8"/>
            </svg>
            Save as New View
          </button>
        )}
      </div>

      {/* Filters */}
      <div className="mb-6 flex gap-3 items-center justify-between flex-wrap" ref={dropdownRef}>
        <div className="flex gap-3 flex-wrap">
          <input
            type="text"
            placeholder="Search runs..."
            className="input w-48"
            onChange={(e) =>
              setFilters({ ...filters, search: e.target.value || undefined })
            }
          />
          {/* State Filter */}
          <div className="relative">
            <button
              onClick={() => setOpenDropdown(openDropdown === 'state' ? null : 'state')}
              className="input list-none cursor-pointer flex items-center gap-2"
              style={{ width: '140px' }}
            >
              <span>
                {filters.state
                  ? filters.state.charAt(0).toUpperCase() + filters.state.slice(1)
                  : 'All States'}
              </span>
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="ml-auto transition-transform" style={{ transform: openDropdown === 'state' ? 'rotate(180deg)' : 'rotate(0deg)' }}>
                <polyline points="6 9 12 15 18 9"/>
              </svg>
            </button>
            {openDropdown === 'state' && (
              <div 
                className="absolute z-10 mt-1 rounded-md shadow-lg min-w-[140px]"
                style={{ backgroundColor: 'var(--bg-surface)', border: '1px solid var(--border)' }}
              >
                {[
                  { value: '', label: 'All States' },
                  { value: 'running', label: 'Running' },
                  { value: 'completed', label: 'Completed' },
                  { value: 'failed', label: 'Failed' },
                ].map((option) => (
                  <button
                    key={option.value}
                    onClick={() => {
                      setFilters({ ...filters, state: option.value || undefined });
                      setOpenDropdown(null);
                    }}
                    className="w-full text-left px-4 py-2 text-sm transition-colors"
                    style={{ 
                      color: filters.state === option.value ? 'var(--accent)' : 'var(--text-primary)',
                      backgroundColor: filters.state === option.value ? 'var(--accent-muted)' : 'transparent'
                    }}
                    onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
                    onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = filters.state === option.value ? 'var(--accent-muted)' : 'transparent')}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Tag Filter */}
          {availableTags && availableTags.length > 0 && (
            <div className="relative">
              <button
                onClick={() => setOpenDropdown(openDropdown === 'tags' ? null : 'tags')}
                className="input list-none cursor-pointer flex items-center gap-2"
              >
                <span>
                  {selectedTags.length === 0
                    ? 'Filter by tags'
                    : `${selectedTags.length} tag${selectedTags.length > 1 ? 's' : ''} selected`}
                </span>
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="ml-auto transition-transform" style={{ transform: openDropdown === 'tags' ? 'rotate(180deg)' : 'rotate(0deg)' }}>
                  <polyline points="6 9 12 15 18 9"/>
                </svg>
              </button>
              {openDropdown === 'tags' && (
                <div 
                  className="absolute z-10 mt-1 rounded-md shadow-lg max-h-60 overflow-auto min-w-[200px]"
                  style={{ backgroundColor: 'var(--bg-surface)', border: '1px solid var(--border)' }}
                >
                  {availableTags.map((tag) => (
                    <label
                      key={tag}
                      className="flex items-center gap-2 px-4 py-2 cursor-pointer transition-colors"
                      style={{ color: 'var(--text-primary)' }}
                      onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
                      onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
                    >
                      <input
                        type="checkbox"
                        checked={selectedTags.includes(tag)}
                        onChange={() => handleTagToggle(tag)}
                        className="w-4 h-4 rounded"
                        style={{ accentColor: 'var(--accent)' }}
                      />
                      <span className="text-sm">{tag}</span>
                    </label>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Column Selector */}
          {availableColumns && availableColumns.length > 0 && (
            <div className="relative">
              <button
                onClick={() => setOpenDropdown(openDropdown === 'columns' ? null : 'columns')}
                className="input list-none cursor-pointer flex items-center gap-2"
              >
                <span>
                  {selectedMetricColumns.length === 0
                    ? 'Add columns'
                    : `${selectedMetricColumns.length} metric${selectedMetricColumns.length > 1 ? 's' : ''}`}
                </span>
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="ml-auto transition-transform" style={{ transform: openDropdown === 'columns' ? 'rotate(180deg)' : 'rotate(0deg)' }}>
                  <polyline points="6 9 12 15 18 9"/>
                </svg>
              </button>
              {openDropdown === 'columns' && (
                <div 
                  className="absolute z-10 mt-1 rounded-md shadow-lg max-h-60 overflow-auto min-w-[250px]"
                  style={{ backgroundColor: 'var(--bg-surface)', border: '1px solid var(--border)' }}
                >
                  {availableColumns.map((column) => (
                    <label
                      key={column}
                      className="flex items-center gap-2 px-4 py-2 cursor-pointer transition-colors"
                      style={{ color: 'var(--text-primary)' }}
                      onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
                      onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
                    >
                      <input
                        type="checkbox"
                        checked={selectedMetricColumns.includes(column)}
                        onChange={() => handleMetricColumnToggle(column)}
                        className="w-4 h-4 rounded"
                        style={{ accentColor: 'var(--accent)' }}
                      />
                      <span className="text-sm mono">{column}</span>
                    </label>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {selectedRunIds.length > 0 && (
          <div className="flex gap-3 items-center">
            <span className="text-sm" style={{ color: 'var(--text-secondary)' }}>
              {selectedRunIds.length === maxSelections ? (
                <>Selected {selectedRunIds.length}/{maxSelections} (max)</>
              ) : (
                <>{selectedRunIds.length} selected</>
              )}
            </span>
            <button
              onClick={() => navigate(`/compare?project=${projectId}&runs=${selectedRunIdsRef.current.join(',')}`)}
              className="btn-primary text-sm"
              disabled={selectedRunIds.length < 2}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="18" cy="18" r="3"/><circle cx="6" cy="6" r="3"/>
                <path d="M6 21V9a9 9 0 0 0 9 9"/>
              </svg>
              Compare Runs
            </button>
            <button
              onClick={() => {
                const runIds = selectedRunIdsRef.current.join(', ');
                if (confirm(`Delete runs ${runIds}? This cannot be undone.`)) {
                  handleDeleteSelectedRuns();
                }
              }}
              disabled={deleteRunMutation.isPending}
              className="btn-secondary text-sm"
              style={{ color: '#ef4444' }}
            >
              {deleteRunMutation.isPending ? 'Deleting…' : (
                <>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <polyline points="3 6 5 6 21 6"/>
                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                  </svg>
                  Delete
                </>
              )}
            </button>
            <button
              onClick={clearSelection}
              className="text-sm transition-colors"
              style={{ color: 'var(--text-tertiary)' }}
              onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--text-primary)')}
              onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--text-tertiary)')}
            >
              Clear
            </button>
          </div>
        )}
      </div>

      {/* Save View Modal */}
      {showSaveViewModal && (
        <div 
          className="fixed inset-0 flex items-center justify-center z-50"
          style={{ backgroundColor: 'rgba(0, 0, 0, 0.5)' }}
        >
          <div className="card max-w-md w-full mx-4 animate-in" style={{ animation: 'fadeSlideIn 0.2s ease-out' }}>
            <h3 className="heading-lg mb-4">
              {currentView ? `Update View "${currentView.name}"` : 'Save New Custom View'}
            </h3>
            <input
              type="text"
              placeholder="View name..."
              value={newViewName}
              onChange={(e) => setNewViewName(e.target.value)}
              className="input mb-4"
              autoFocus
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleSaveView();
                if (e.key === 'Escape') handleCloseModal();
              }}
            />
            <div className="text-body text-sm mb-6">
              <p>{currentView ? 'This will update the view with:' : 'This will save:'}</p>
              <ul className="list-disc list-inside mt-2 space-y-1">
                <li>Current filters (state, search, tags: {selectedTags.length})</li>
                <li>Selected metric columns ({selectedMetricColumns.length})</li>
                <li>Sort settings ({sortBy} {sortOrder})</li>
              </ul>
            </div>
            <div className="flex gap-3 justify-end">
              <button
                onClick={handleCloseModal}
                className="btn-secondary"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveView}
                disabled={!newViewName.trim() || createViewMutation.isPending || updateViewMutation.isPending}
                className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
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
        onSelectionChange={handleSelectionChange}
        metricColumns={selectedMetricColumns}
        projectId={parseInt(projectId || '0')}
        selectionDisabled={isAtMax()}
      />
    </div>
  );
}
