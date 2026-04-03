import { useSearchParams, useNavigate } from 'react-router-dom';
import { useState, useMemo, lazy, Suspense } from 'react';
import { useRun, useRunSummary, useRunMetrics, useMetricValues } from '../api/client';

const MultiMetricChart = lazy(() => import('../components/Charts/MultiMetricChart'));

function ChevronRightIcon({ className = '' }: { className?: string }) {
  return (
    <svg className={className} width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="9 18 15 12 9 6"/>
    </svg>
  );
}

function ChartIcon({ className = '' }: { className?: string }) {
  return (
    <svg className={className} width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="18" y1="20" x2="18" y2="10"/>
      <line x1="12" y1="20" x2="12" y2="4"/>
      <line x1="6" y1="20" x2="6" y2="14"/>
    </svg>
  );
}

export default function CompareRunsPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [expandedMetrics, setExpandedMetrics] = useState<Set<string>>(new Set());

  // Get run IDs from query params (e.g., ?runs=1,2,3)
  const runIds = useMemo(() => {
    const runsParam = searchParams.get('runs');
    if (!runsParam) return [];
    return runsParam.split(',').map((id) => parseInt(id.trim())).filter((id) => !isNaN(id));
  }, [searchParams]);

  // Fetch data for each run
  const runsData = runIds.map((runId) => ({
    runId,
    // eslint-disable-next-line react-hooks/rules-of-hooks
    run: useRun(runId),
    // eslint-disable-next-line react-hooks/rules-of-hooks
    summary: useRunSummary(runId),
    // eslint-disable-next-line react-hooks/rules-of-hooks
    metricNames: useRunMetrics(runId),
  }));

  const isLoading = runsData.some((r) => r.run.isLoading || r.summary.isLoading);
  const error = runsData.find((r) => r.run.error || r.summary.error);

  // Get all unique metric names across all runs
  const allMetricNames = useMemo(() => {
    const namesSet = new Set<string>();
    runsData.forEach((r) => {
      if (r.metricNames.data) {
        r.metricNames.data.forEach((name: string) => namesSet.add(name));
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

  if (runIds.length === 0) {
    return (
      <div className="p-8 page-enter">
        <div className="card text-center py-16">
          <ChartIcon className="mx-auto mb-4" style={{ color: 'var(--text-tertiary)' }} />
          <h3 className="heading-md mb-2">No runs selected</h3>
          <p className="text-body mb-6 max-w-md mx-auto">
            Select runs from the runs table and click "Compare" to view them side-by-side
          </p>
          <button
            onClick={() => navigate(-1)}
            className="btn-secondary"
          >
            Go Back
          </button>
        </div>
      </div>
    );
  }

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
          <button onClick={() => navigate(-1)} className="btn-secondary text-sm">
            Back
          </button>
        </div>
      </div>

      {/* Run Info Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6 card-stagger">
        {runsData.map(({ runId, run, metricNames }) => (
          <div key={runId} className="card card-appear">
            <div className="flex items-start justify-between mb-2">
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
          {/* Header with Expand/Collapse All */}
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

          {/* Metrics List */}
          <div className="space-y-2">
            {allMetricNames.map((metricPath) => {
              const isExpanded = expandedMetrics.has(metricPath);
              
              return (
                <div key={metricPath} className="card p-0 overflow-hidden">
                  {/* Collapsed Header */}
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

                  {/* Expanded Content - Only render when expanded */}
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

// Component that loads metric data and decides what to show
interface MetricComparisonViewerProps {
  metricPath: string;
  runIds: number[];
  runNames: string[];
}

function MetricComparisonViewer({ metricPath, runIds, runNames }: MetricComparisonViewerProps) {
  // Fetch metric data for all runs
  const metricsData = runIds.map((runId) => ({
    runId,
    // eslint-disable-next-line react-hooks/rules-of-hooks
    data: useMetricValues(runId, metricPath),
  }));

  const isLoading = metricsData.some((m) => m.data.isLoading);
  const error = metricsData.find((m) => m.data.error);

  // Analyze the metric type using first run's data
  const metricAnalysis = useMemo(() => {
    const firstData = metricsData[0]?.data.data?.data;
    
    if (!firstData || firstData.length === 0) {
      return { type: 'empty' };
    }

    const numericValues = firstData.filter((v: unknown) => typeof v.value === 'number');

    // Single value
    if (firstData.length === 1) {
      return { type: 'single' };
    }

    // Multiple numeric values - chartable!
    if (numericValues.length > 1) {
      return { type: 'chart' };
    }

    // Multiple non-numeric values
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
    // Extract single values from all runs
    const values = metricsData.map((m) => {
      const metricData = m.data.data?.data;
      if (metricData && metricData.length > 0) {
        return metricData[0].value;
      }
      return null;
    });

    // Find min/max for highlighting (only for numeric values)
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
                
                // Apply color coding for numeric values
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
    return (
      <div className="card p-4 text-center">
        <p className="text-body text-sm">This metric contains non-numeric values and cannot be charted</p>
      </div>
    );
  }

  // metricAnalysis.type === 'chart'
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
