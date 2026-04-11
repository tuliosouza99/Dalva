import { useNavigate, useSearchParams } from 'react-router-dom';
import { useState, useMemo, useEffect, lazy, Suspense } from 'react';
import { useQueries } from '@tanstack/react-query';
import { api, useMetricValues } from '../api/client';
import { useComparison } from '../contexts/ComparisonContext';
import CategoryAreaChart from '../components/Charts/CategoryAreaChart';

const MultiMetricChart = lazy(() => import('../components/Charts/MultiMetricChart'));

function ChevronRightIcon({ className = '', style }: { className?: string; style?: React.CSSProperties }) {
  return (
    <svg className={className} style={style} width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="9 18 15 12 9 6"/>
    </svg>
  );
}

function ChartIcon({ className = '', style }: { className?: string; style?: React.CSSProperties }) {
  return (
    <svg className={className} style={style} width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="18" y1="20" x2="18" y2="10"/>
      <line x1="12" y1="20" x2="12" y2="4"/>
      <line x1="6" y1="20" x2="6" y2="14"/>
    </svg>
  );
}

function EmptyState({ onNavigate }: { onNavigate: () => void }) {
  return (
    <div className="p-8 page-enter">
      <div className="card text-center py-16">
        <ChartIcon className="mx-auto mb-4" style={{ color: 'var(--text-tertiary)' }} />
        <h3 className="heading-md mb-2">No runs selected</h3>
        <p className="text-body mb-6 max-w-md mx-auto">
          Select runs from the runs table and click "Compare" to view them side-by-side
        </p>
        <button onClick={onNavigate} className="btn-secondary">
          Go Back
        </button>
      </div>
    </div>
  );
}

function CompareRunsContent({ runIds, onRemove, onClear }: { runIds: number[]; onRemove: (id: number) => void; onClear: () => void }) {
  const navigate = useNavigate();
  const [expandedMetrics, setExpandedMetrics] = useState<Set<string>>(new Set());

  const queryResults = useQueries({
    queries: runIds.map((runId) => ({
      queryKey: ['runs', runId],
      queryFn: () => api.getRun(runId),
      enabled: true,
    })),
  });

  const summaryResults = useQueries({
    queries: runIds.map((runId) => ({
      queryKey: ['runs', runId, 'summary'],
      queryFn: () => api.getRunSummary(runId),
      enabled: true,
    })),
  });

  const metricsResults = useQueries({
    queries: runIds.map((runId) => ({
      queryKey: ['runs', runId, 'metrics'],
      queryFn: () => api.getRunMetrics(runId),
      enabled: true,
    })),
  });

  const runsData = runIds.map((runId, idx) => ({
    runId,
    run: queryResults[idx],
    summary: summaryResults[idx],
    metricNames: metricsResults[idx],
  }));

  const isLoading = runsData.some((r) => r.run.isLoading || r.summary.isLoading);
  const error = runsData.find((r) => r.run.error || r.summary.error);

  const allMetricNames = useMemo(() => {
    const namesSet = new Set<string>();
    runsData.forEach((r) => {
      if (r.metricNames.data) {
        r.metricNames.data.forEach((m: { path: string }) => namesSet.add(m.path));
      }
    });
    return Array.from(namesSet).sort();
  }, [runsData]);

  const toggleMetric = (metricPath: string) => {
    setExpandedMetrics((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(metricPath)) {
        newSet.delete(metricPath);
      } else {
        newSet.add(metricPath);
      }
      return newSet;
    });
  };

  const expandAll = () => {
    setExpandedMetrics(new Set(allMetricNames));
  };

  const collapseAll = () => {
    setExpandedMetrics(new Set());
  };

  const allExpanded = expandedMetrics.size === allMetricNames.length && allMetricNames.length > 0;

  if (isLoading) {
    return (
      <div className="p-8 page-enter">
        <div className="mb-6">
          <div className="skeleton h-8 w-48 rounded-md mb-2"></div>
          <div className="skeleton h-4 w-24 rounded"></div>
        </div>
        <div className="card p-4">
          <div className="space-y-3">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="skeleton h-12 rounded-md"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8 page-enter">
        <div className="card p-6" style={{ backgroundColor: 'rgba(239, 68, 68, 0.08)', borderColor: 'rgba(239, 68, 68, 0.2)' }}>
          <h3 className="font-semibold mb-1" style={{ color: 'var(--badge-failed)' }}>Error loading runs</h3>
          <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>{error.run?.error?.message || error.summary?.error?.message}</p>
        </div>
      </div>
    );
  }

  const runNames = runsData.map((r) => r.run.data?.run_id || `Run ${r.runId}`);

  return (
    <div className="p-8 page-enter">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="heading-display">Compare Runs</h1>
            <p className="text-body mt-1">
              Comparing {runIds.length} {runIds.length === 1 ? 'run' : 'runs'}
            </p>
          </div>
          <div className="flex gap-3">
            <button onClick={onClear} className="btn-secondary text-sm">
              Clear All
            </button>
            <button onClick={() => navigate(-1)} className="btn-secondary text-sm">
              Back
            </button>
          </div>
        </div>
      </div>

      {/* Run Info Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6 card-stagger">
        {runsData.map(({ runId, run, metricNames }) => (
          <div key={runId} className="card card-appear relative">
            <button
              onClick={() => onRemove(runId)}
              className="absolute top-3 right-3 p-1 rounded-md transition-colors"
              style={{ color: 'var(--text-tertiary)' }}
              onMouseEnter={(e) => { e.currentTarget.style.color = 'var(--badge-failed)'; e.currentTarget.style.backgroundColor = 'rgba(239, 68, 68, 0.1)'; }}
              onMouseLeave={(e) => { e.currentTarget.style.color = 'var(--text-tertiary)'; e.currentTarget.style.backgroundColor = 'transparent'; }}
              title="Remove from comparison"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
              </svg>
            </button>
            <div className="flex items-start justify-between mb-2 pr-8">
              <h3 className="heading-md truncate" style={{ color: 'var(--text-primary)' }}>
                {run.data?.name}
              </h3>
              <span className={`badge ${
                run.data?.state === 'running'
                  ? 'badge-running'
                  : run.data?.state === 'completed'
                  ? 'badge-completed'
                  : 'badge-failed'
              }`}>
                {run.data?.state === 'running' && <span className="pulse-dot" />}
                {run.data?.state}
              </span>
            </div>
            <p className="mono text-sm mb-2" style={{ color: 'var(--accent-hover)' }}>{run.data?.run_id}</p>
            {run.data?.group_name && (
              <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Group: {run.data.group_name}</p>
            )}
            <p className="text-xs mt-2" style={{ color: 'var(--text-tertiary)' }}>
              {metricNames.data?.length || 0} metrics
            </p>
          </div>
        ))}
      </div>

      {/* Metrics Comparison */}
      {allMetricNames.length === 0 ? (
        <div className="card text-center py-16">
          <ChartIcon className="mx-auto mb-4" style={{ color: 'var(--text-tertiary)' }} />
          <h3 className="heading-md mb-2">No metrics found</h3>
          <p className="text-body">These runs don't have any logged metrics yet.</p>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <p className="text-small">
              {allMetricNames.length} metric{allMetricNames.length !== 1 ? 's' : ''} available
            </p>
            <button
              onClick={allExpanded ? collapseAll : expandAll}
              className="btn-secondary text-sm"
            >
              {allExpanded ? 'Collapse All' : 'Expand All'}
            </button>
          </div>

          <div className="space-y-2">
            {allMetricNames.map((metricPath) => {
              const isExpanded = expandedMetrics.has(metricPath);
              
              return (
                <div key={metricPath} className="card p-0 overflow-hidden">
                  <button
                    onClick={() => toggleMetric(metricPath)}
                    className="w-full px-6 py-4 flex items-center justify-between transition-colors"
                    style={{ backgroundColor: 'var(--bg-surface)' }}
                    onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
                    onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'var(--bg-surface)')}
                  >
                    <div className="flex items-center gap-3">
                      <ChevronRightIcon 
                        className="transition-transform" 
                        style={{ 
                          color: 'var(--text-tertiary)',
                          transform: isExpanded ? 'rotate(90deg)' : 'rotate(0deg)'
                        }} 
                      />
                      <span className="text-sm mono" style={{ color: 'var(--text-primary)' }}>{metricPath}</span>
                    </div>
                    {isExpanded && (
                      <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>Click to collapse</span>
                    )}
                  </button>

                  {isExpanded && (
                    <div 
                      className="px-6 py-4"
                      style={{ backgroundColor: 'var(--bg-primary)', borderTop: '1px solid var(--border)' }}
                    >
                      <MetricComparisonViewer
                        metricPath={metricPath}
                        runIds={runIds}
                        runNames={runNames}
                      />
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

interface MetricComparisonViewerProps {
  metricPath: string;
  runIds: number[];
  runNames: string[];
}

function MetricComparisonViewer({ metricPath, runIds, runNames }: MetricComparisonViewerProps) {
  const metricsData = runIds.map((runId) => ({
    runId,
    // eslint-disable-next-line react-hooks/rules-of-hooks
    data: useMetricValues(runId, metricPath),
  }));

  const isLoading = metricsData.some((m) => m.data.isLoading);
  const error = metricsData.find((m) => m.data.error);

  const metricAnalysis = useMemo(() => {
    const allData = metricsData.map((m) => m.data.data);
    const firstWithData = allData.find((d) => d && d.data.length > 0);
    
    if (!firstWithData) {
      return { type: 'empty' };
    }

    const attributeType = firstWithData.attribute_type;
    const isCategorical = attributeType === 'bool_series' || attributeType === 'string_series';

    if (isCategorical) {
      return { type: 'category', attributeType };
    }

    const firstValues = firstWithData.data;
    const numericValues = firstValues.filter((v) => typeof (v as { value?: unknown }).value === 'number');

    if (firstValues.length === 1) {
      return { type: 'single' };
    }

    if (numericValues.length > 1) {
      return { type: 'chart' };
    }

    return { type: 'list' };
  }, [metricsData]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="text-center">
          <div className="skeleton w-8 h-8 rounded-full mx-auto mb-2"></div>
          <p className="text-small">Loading metric data...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card p-4" style={{ backgroundColor: 'rgba(239, 68, 68, 0.08)', borderColor: 'rgba(239, 68, 68, 0.2)' }}>
        <p className="text-sm" style={{ color: 'var(--badge-failed)' }}>Error loading metric: {error.data.error?.message}</p>
      </div>
    );
  }

  if (metricAnalysis.type === 'empty') {
    return (
      <div className="card p-4 text-center">
        <p className="text-body text-sm">No data available for this metric</p>
      </div>
    );
  }

  if (metricAnalysis.type === 'single') {
    const values = metricsData.map((m) => {
      const metricData = m.data.data?.data;
      if (metricData && metricData.length > 0) {
        return metricData[0].value;
      }
      return null;
    });

    const numericValues = values.filter((v) => typeof v === 'number') as number[];
    let minValue: number | null = null;
    let maxValue: number | null = null;
    
    if (numericValues.length > 1) {
      minValue = Math.min(...numericValues);
      maxValue = Math.max(...numericValues);
    }

    return (
      <div className="card p-0 overflow-hidden">
        <table className="min-w-full">
          <thead style={{ backgroundColor: 'var(--bg-primary)' }}>
            <tr>
              {runNames.map((name, idx) => (
                <th
                  key={idx}
                  className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider"
                  style={{ color: 'var(--text-tertiary)' }}
                >
                  {name}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            <tr>
              {values.map((value, idx) => {
                let bgColor = '';
                
                if (minValue !== null && maxValue !== null && typeof value === 'number' && minValue !== maxValue) {
                  if (value === maxValue) {
                    bgColor = 'rgba(34, 197, 94, 0.12)';
                  } else if (value === minValue) {
                    bgColor = 'rgba(239, 68, 68, 0.1)';
                  }
                }
                
                return (
                  <td
                    key={idx}
                    className="px-4 py-4 text-sm font-semibold"
                    style={{ 
                      color: 'var(--text-primary)',
                      backgroundColor: bgColor || 'transparent'
                    }}
                  >
                    {value === null || value === undefined
                      ? '-'
                      : typeof value === 'number'
                      ? value.toFixed(6)
                      : String(value)}
                  </td>
                );
              })}
            </tr>
          </tbody>
        </table>
      </div>
    );
  }

  if (metricAnalysis.type === 'list') {
    const values = metricsData.map((m) => {
      const metricData = m.data.data?.data;
      if (metricData && metricData.length > 0) {
        return metricData[0].value;
      }
      return null;
    });

    return (
      <div className="card p-0 overflow-hidden">
        <table className="min-w-full">
          <thead style={{ backgroundColor: 'var(--bg-primary)' }}>
            <tr>
              {runNames.map((name, idx) => (
                <th
                  key={idx}
                  className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider"
                  style={{ color: 'var(--text-tertiary)' }}
                >
                  {name}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            <tr>
              {values.map((value, idx) => (
                <td
                  key={idx}
                  className="px-4 py-4 text-sm font-semibold"
                  style={{ color: 'var(--text-primary)' }}
                >
                  {value === null || value === undefined
                    ? '-'
                    : String(value)}
                </td>
              ))}
            </tr>
          </tbody>
        </table>
      </div>
    );
  }

  if (metricAnalysis.type === 'category') {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {metricsData.map((m, idx) => {
          const metricValues = m.data.data?.data;
          if (!metricValues || metricValues.length === 0) return null;
          return (
            <div key={m.runId} className="rounded-lg border p-4" style={{ borderColor: 'var(--border)' }}>
              <p className="text-xs mb-2 font-medium" style={{ color: 'var(--text-tertiary)' }}>
                {runNames[idx]}
              </p>
              <CategoryAreaChart
                values={metricValues}
                attributeType={metricAnalysis.attributeType!}
                metricPath={runNames[idx]}
                height={300}
              />
            </div>
          );
        })}
      </div>
    );
  }

  return (
    <div className="card p-0" style={{ backgroundColor: 'var(--bg-surface)' }}>
      <Suspense fallback={<div className="p-4 text-center text-body">Loading chart...</div>}>
        <MultiMetricChart
          metrics={runIds.map((runId, idx) => ({
            runId,
            metricPath,
            name: runNames[idx],
          }))}
          title=""
          height={400}
        />
      </Suspense>
    </div>
  );
}

export default function CompareRunsPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { selectedRunIds, setSelectedRunIds, clearSelection } = useComparison();

  const runIdsFromUrl = searchParams.get('runs');
  const projectId = searchParams.get('project');

  useEffect(() => {
    if (runIdsFromUrl) {
      const parsed = runIdsFromUrl.split(',').map(Number).filter((n) => !isNaN(n));
      if (parsed.length > 0) {
        setSelectedRunIds(parsed);
      }
    }
  }, [runIdsFromUrl, setSelectedRunIds]);

  const handleRemoveRun = (runId: number) => {
    const newRunIds = selectedRunIds.filter(id => id !== runId);
    setSelectedRunIds(newRunIds);
  };

  const handleClearAll = () => {
    clearSelection();
  };

  if (selectedRunIds.length === 0) {
    return <EmptyState onNavigate={() => navigate(projectId ? `/projects/${projectId}/runs` : '/projects')} />;
  }

  return (
    <CompareRunsContent 
      runIds={selectedRunIds} 
      onRemove={handleRemoveRun} 
      onClear={handleClearAll} 
    />
  );
}
