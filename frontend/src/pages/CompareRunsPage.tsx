import { useSearchParams, useNavigate } from 'react-router-dom';
import { useState, useMemo, lazy, Suspense } from 'react';
import { useRun, useRunSummary, useRunMetrics, useMetricValues } from '../api/client';

const MultiMetricChart = lazy(() => import('../components/Charts/MultiMetricChart'));

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
      <div className="p-8">
        <div className="card text-center py-12">
          <p className="text-gray-500 text-lg">No runs selected for comparison</p>
          <p className="text-gray-400 text-sm mt-2">
            Select runs from the runs table and click "Compare" to view them side-by-side
          </p>
          <button
            onClick={() => navigate(-1)}
            className="mt-4 btn-secondary"
          >
            Go Back
          </button>
        </div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="p-8">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded w-1/4 mb-6"></div>
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <div className="space-y-3">
              {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="h-12 bg-gray-200 rounded"></div>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
          <h3 className="font-semibold mb-1">Error loading runs</h3>
          <p className="text-sm">{error.run?.error?.message || error.summary?.error?.message}</p>
        </div>
      </div>
    );
  }

  const runNames = runsData.map((r) => r.run.data?.run_id || `Run ${r.runId}`);

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">Compare Runs</h1>
            <p className="text-gray-600 dark:text-gray-400 mt-1">
              Comparing {runIds.length} {runIds.length === 1 ? 'run' : 'runs'}
            </p>
          </div>
          <button onClick={() => navigate(-1)} className="btn-secondary text-sm">
            Back
          </button>
        </div>
      </div>

      {/* Run Info Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
        {runsData.map(({ runId, run, metricNames }) => (
          <div key={runId} className="card">
            <div className="flex items-start justify-between mb-2">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 truncate">
                {run.data?.name}
              </h3>
              <span
                className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                  run.data?.state === 'running'
                    ? 'bg-green-100 dark:bg-green-900/30 dark:text-green-400 text-green-800'
                    : run.data?.state === 'completed'
                    ? 'bg-blue-100 dark:bg-blue-900/30 dark:text-blue-400 text-blue-800'
                    : 'bg-red-100 dark:bg-red-900/30 dark:text-red-400 text-red-800'
                }`}
              >
                {run.data?.state}
              </span>
            </div>
            <p className="text-sm font-mono text-primary-600 mb-2">{run.data?.run_id}</p>
            {run.data?.group_name && (
              <p className="text-sm text-gray-600 dark:text-gray-400">Group: {run.data.group_name}</p>
            )}
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
              {metricNames.data?.length || 0} metrics
            </p>
          </div>
        ))}
      </div>

      {/* Metrics Comparison */}
      {allMetricNames.length === 0 ? (
        <div className="card text-center py-12">
          <svg
            className="w-16 h-16 text-gray-300 dark:text-gray-600 mx-auto mb-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
            />
          </svg>
          <p className="text-gray-500 dark:text-gray-400 text-lg">No metrics found</p>
        </div>
      ) : (
        <div className="space-y-4">
          {/* Header with Expand/Collapse All */}
          <div className="flex justify-between items-center">
            <p className="text-sm text-gray-600 dark:text-gray-400">
              {allMetricNames.length} metric{allMetricNames.length !== 1 ? 's' : ''} available
            </p>
            <button
              onClick={allExpanded ? collapseAll : expandAll}
              className="px-4 py-2 text-sm bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600 rounded-md hover:bg-gray-200 transition-colors"
            >
              {allExpanded ? 'Collapse All' : 'Expand All'}
            </button>
          </div>

          {/* Metrics List */}
          <div className="space-y-2">
            {allMetricNames.map((metricPath) => {
              const isExpanded = expandedMetrics.has(metricPath);
              
              return (
                <div key={metricPath} className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
                  {/* Collapsed Header */}
                  <button
                    onClick={() => toggleMetric(metricPath)}
                    className="w-full px-6 py-4 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors flex items-center justify-between"
                  >
                    <div className="flex items-center gap-3">
                      <svg
                        className={`w-5 h-5 text-gray-500 dark:text-gray-400 transition-transform ${
                          isExpanded ? 'rotate-90' : ''
                        }`}
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                      </svg>
                      <span className="text-sm font-mono text-gray-900 dark:text-gray-100">{metricPath}</span>
                    </div>
                    {isExpanded && (
                      <span className="text-xs text-gray-500 dark:text-gray-400">Click to collapse</span>
                    )}
                  </button>

                  {/* Expanded Content - Only render when expanded */}
                  {isExpanded && (
                    <div className="px-6 py-4 bg-gray-50 dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700">
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

    const numericValues = firstData.filter((v: any) => typeof v.value === 'number');

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
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
          <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">Loading metric data...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 rounded-lg border border-red-200 p-4">
        <p className="text-red-700 text-sm">Error loading metric: {error.data.error?.message}</p>
      </div>
    );
  }

  if (metricAnalysis.type === 'empty') {
    return (
      <div className="bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4 text-center">
        <p className="text-gray-600 dark:text-gray-400 text-sm">No data available for this metric</p>
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
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
        <table className="min-w-full">
          <thead className="bg-gray-50 dark:bg-gray-700">
            <tr>
              {runNames.map((name, idx) => (
                <th
                  key={idx}
                  className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider"
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
                    bgColor = 'bg-green-100 dark:bg-green-900/30';
                  } else if (value === minValue) {
                    bgColor = 'bg-red-100 dark:bg-red-900/30';
                  }
                }
                
                return (
                  <td
                    key={idx}
                    className={`px-4 py-4 text-sm font-semibold text-gray-900 dark:text-gray-100 ${bgColor}`}
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
      <div className="bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4 text-center">
        <p className="text-gray-600 dark:text-gray-400 text-sm">This metric contains non-numeric values and cannot be charted</p>
      </div>
    );
  }

  // metricAnalysis.type === 'chart'
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg">
      <Suspense fallback={<div className="p-4 text-center">Loading chart...</div>}>
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
