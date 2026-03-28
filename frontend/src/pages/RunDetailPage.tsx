import { useParams, useNavigate } from 'react-router-dom';
import { useState, lazy, Suspense } from 'react';
import { useRun, useRunSummary, useRunMetrics, useDeleteRun } from '../api/client';
import MetricBrowser from '../components/Charts/MetricBrowser';
import JsonViewer from '../components/JsonViewer';

const MetricViewer = lazy(() => import('../components/Charts/MetricViewer'));

function isDarkMode() {
  return typeof document !== 'undefined' && document.documentElement.classList.contains('dark');
}

export default function RunDetailPage() {
  const { runId } = useParams<{ runId: string }>();
  const navigate = useNavigate();
  const [selectedTab, setSelectedTab] = useState<'overview' | 'metrics' | 'config'>('overview');
  const [selectedMetric, setSelectedMetric] = useState<string | null>(null);

  const { data: run, isLoading: runLoading } = useRun(parseInt(runId || '0'));
  const { data: summary, isLoading: summaryLoading } = useRunSummary(parseInt(runId || '0'));
  const { data: metricNames, isLoading: metricsLoading } = useRunMetrics(parseInt(runId || '0'));
  const deleteRunMutation = useDeleteRun();

  const handleDeleteRun = () => {
    if (!run) return;
    if (!confirm(`Delete run "${run.name}"? This cannot be undone.`)) return;
    deleteRunMutation.mutate(run.id, {
      onSuccess: () => navigate(`/projects/${run.project_id}/runs`),
    });
  };

  const isLoading = runLoading || summaryLoading || metricsLoading;

  if (isLoading) {
    return (
      <div className="p-8">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded w-1/4 mb-6"></div>
          <div className="space-y-4">
            <div className="h-32 bg-gray-200 rounded"></div>
            <div className="h-64 bg-gray-200 rounded"></div>
          </div>
        </div>
      </div>
    );
  }

  if (!run) {
    return (
      <div className="p-8">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
          <h3 className="font-semibold mb-1">Run not found</h3>
          <p className="text-sm">The requested run does not exist.</p>
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
            className="hover:text-primary-600 dark:hover:text-primary-400 transition-colors"
          >
            Projects
          </button>
          <span>/</span>
          <button
            onClick={() => navigate(`/projects/${run.project_id}/runs`)}
            className="hover:text-primary-600 dark:hover:text-primary-400 transition-colors"
          >
            Runs
          </button>
          <span>/</span>
          <span className="text-gray-900 dark:text-gray-100">{run.run_id}</span>
        </div>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">{run.name}</h1>
            <p className="text-gray-600 mt-1">
              <span className="font-mono text-primary-600">{run.run_id}</span>
              {run.group_name && (
                <span className="ml-3 text-gray-500">Group: {run.group_name}</span>
              )}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <span
              className={`inline-flex px-3 py-1 text-sm font-semibold rounded-full ${
                run.state === 'running'
                  ? 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-400'
                  : run.state === 'completed'
                  ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-400'
                  : 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-400'
              }`}
            >
              {run.state}
            </span>
            <button
              onClick={handleDeleteRun}
              disabled={deleteRunMutation.isPending}
              className="px-3 py-1 text-sm text-red-600 border border-red-300 rounded-md hover:bg-red-50 transition-colors disabled:opacity-50"
              title="Delete this run"
            >
              {deleteRunMutation.isPending ? 'Deleting…' : '🗑️ Delete Run'}
            </button>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="-mb-px flex space-x-8">
          {['overview', 'metrics', 'config'].map((tab) => (
            <button
              key={tab}
              onClick={() => setSelectedTab(tab as typeof selectedTab)}
              className={`${
                selectedTab === tab
                  ? 'border-primary-500 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm capitalize transition-colors`}
            >
              {tab}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      {selectedTab === 'overview' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Run Info */}
          <div className="card">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">Run Information</h3>
            <dl className="space-y-3">
              <div>
                <dt className="text-sm text-gray-500">Created</dt>
                <dd className="text-sm text-gray-900 dark:text-gray-100 mt-1">
                  {new Date(run.created_at).toLocaleString()}
                </dd>
              </div>
              <div>
                <dt className="text-sm text-gray-500">Updated</dt>
                <dd className="text-sm text-gray-900 dark:text-gray-100 mt-1">
                  {new Date(run.updated_at).toLocaleString()}
                </dd>
              </div>
              <div>
                <dt className="text-sm text-gray-500">State</dt>
                <dd className="text-sm text-gray-900 dark:text-gray-100 mt-1">{run.state}</dd>
              </div>
            </dl>
          </div>

          {/* Summary Stats */}
          {summary?.metrics && Object.keys(summary.metrics).length > 0 && (
            <div className="card lg:col-span-2">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">Summary Metrics</h3>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                {Object.entries(summary.metrics)
                  .filter(([_, value]) => {
                    // Only show primitive values (numbers, strings, booleans)
                    const isPrimitive = typeof value !== 'object' || value === null;
                    return isPrimitive;
                  })
                  .slice(0, 12)
                  .map(([key, value]) => {
                    // Format value based on type
                    let displayValue: string;
                    if (typeof value === 'number') {
                      // Check if it's an integer
                      if (Number.isInteger(value)) {
                        displayValue = value.toString();
                      } else {
                        displayValue = value.toFixed(4);
                      }
                    } else {
                      displayValue = String(value);
                    }

                    return (
                      <div key={key}>
                        <dt className="text-xs text-gray-500 truncate" title={key}>
                          {key}
                        </dt>
                        <dd className="text-lg font-semibold text-gray-900 dark:text-gray-100 mt-1">
                          {displayValue}
                        </dd>
                      </div>
                    );
                  })}
              </div>
            </div>
          )}
        </div>
      )}

      {selectedTab === 'metrics' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Metric Browser */}
          <div className="lg:col-span-1">
            <MetricBrowser
              metrics={metricNames || []}
              onMetricSelect={setSelectedMetric}
              selectedMetric={selectedMetric}
            />
          </div>

          {/* Metric Viewer */}
          <div className="lg:col-span-1">
            {selectedMetric ? (
              <Suspense fallback={<div className="card py-12 text-center">Loading chart...</div>}>
                <MetricViewer
                  runId={parseInt(runId || '0')}
                  metricPath={selectedMetric}
                  onClose={() => setSelectedMetric(null)}
                />
              </Suspense>
            ) : (
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
                <p className="text-gray-500 dark:text-gray-400 text-lg">Select a metric to visualize</p>
                <p className="text-gray-400 dark:text-gray-500 text-sm mt-2">
                  Browse the metric tree on the left and click on a metric to view its data
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {selectedTab === 'config' && (
        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">Configuration</h3>
          {(() => {
            const configData = summary?.config || {};

            return Object.keys(configData).length > 0 ? (
              <JsonViewer data={configData} dark={isDarkMode()} />
            ) : (
              <p className="text-gray-500 dark:text-gray-400 text-center py-8">No configuration data available</p>
            );
          })()}
        </div>
      )}
    </div>
  );
}
