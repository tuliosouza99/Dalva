import { useParams, useNavigate } from 'react-router-dom';
import { useState, lazy, Suspense } from 'react';
import { useRun, useRunSummary, useRunMetrics, useDeleteRun } from '../api/client';
import MetricBrowser from '../components/Charts/MetricBrowser';
import JsonViewer from '../components/JsonViewer';

const MetricViewer = lazy(() => import('../components/Charts/MetricViewer'));

function isDarkMode() {
  return typeof document !== 'undefined' && document.documentElement.classList.contains('dark');
}

function ChartIcon({ className = '', style }: { className?: string; style?: React.CSSProperties }) {
  return (
    <svg className={className} width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" style={style}>
      <line x1="18" y1="20" x2="18" y2="10"/>
      <line x1="12" y1="20" x2="12" y2="4"/>
      <line x1="6" y1="20" x2="6" y2="14"/>
    </svg>
  );
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

  if (!run) {
    return (
      <div className="p-8 page-enter">
        <div className="card p-6" style={{ backgroundColor: 'rgba(239, 68, 68, 0.08)', borderColor: 'rgba(239, 68, 68, 0.2)' }}>
          <h3 className="font-semibold mb-1" style={{ color: 'var(--badge-failed)' }}>Run not found</h3>
          <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>The requested run does not exist.</p>
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
          <button
            onClick={() => navigate(`/projects/${run.project_id}/runs`)}
            className="hover:text-[var(--accent)] transition-colors"
          >
            {run.project_name || 'Runs'}
          </button>
          <span>/</span>
          <span style={{ color: 'var(--text-primary)' }}>{run.run_id}</span>
        </div>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="heading-display">{run.name}</h1>
            <p className="mt-1">
              <span className="mono text-sm" style={{ color: 'var(--accent-hover)' }}>{run.run_id}</span>
              {run.group_name && (
                <span className="ml-3 text-sm" style={{ color: 'var(--text-secondary)' }}>Group: {run.group_name}</span>
              )}
            </p>
          </div>
          <div className="flex items-center gap-3">
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
            <button
              onClick={handleDeleteRun}
              disabled={deleteRunMutation.isPending}
              className="btn-secondary text-sm"
              style={{ color: '#ef4444' }}
              title="Delete this run"
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
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b mb-6" style={{ borderColor: 'var(--border)' }}>
        <nav className="-mb-px flex space-x-8">
          {['overview', 'metrics', 'config'].map((tab) => (
            <button
              key={tab}
              onClick={() => setSelectedTab(tab as typeof selectedTab)}
              className="whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm capitalize transition-colors"
              style={{
                borderColor: selectedTab === tab ? 'var(--accent)' : 'transparent',
                color: selectedTab === tab ? 'var(--accent)' : 'var(--text-secondary)',
              }}
              onMouseEnter={(e) => {
                if (selectedTab !== tab) {
                  e.currentTarget.style.color = 'var(--text-primary)';
                  e.currentTarget.style.borderColor = 'var(--text-tertiary)';
                }
              }}
              onMouseLeave={(e) => {
                if (selectedTab !== tab) {
                  e.currentTarget.style.color = 'var(--text-secondary)';
                  e.currentTarget.style.borderColor = 'transparent';
                }
              }}
            >
              {tab}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      {selectedTab === 'overview' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 card-stagger">
          {/* Run Info */}
          <div className="card card-appear">
            <h3 className="heading-md mb-4">Run Information</h3>
            <dl className="space-y-3">
              <div>
                <dt className="text-small">Created</dt>
                <dd className="text-sm mt-1" style={{ color: 'var(--text-primary)' }}>
                  {new Date(run.created_at).toLocaleString()}
                </dd>
              </div>
              <div>
                <dt className="text-small">Updated</dt>
                <dd className="text-sm mt-1" style={{ color: 'var(--text-primary)' }}>
                  {new Date(run.updated_at).toLocaleString()}
                </dd>
              </div>
              <div>
                <dt className="text-small">State</dt>
                <dd className="text-sm mt-1" style={{ color: 'var(--text-primary)' }}>{run.state}</dd>
              </div>
            </dl>
          </div>

          {/* Summary Stats */}
          {summary?.metrics && Object.keys(summary.metrics).length > 0 && (
            <div className="card card-appear lg:col-span-2">
              <h3 className="heading-md mb-4">Summary Metrics</h3>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                {Object.entries(summary.metrics)
                  .filter(([, value]) => {
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
                        <dt className="text-xs truncate" style={{ color: 'var(--text-tertiary)' }} title={key}>
                          {key}
                        </dt>
                        <dd className="text-lg font-semibold mt-1" style={{ color: 'var(--text-primary)' }}>
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
              <Suspense fallback={<div className="card py-12 text-center text-body">Loading chart...</div>}>
                <MetricViewer
                  runId={parseInt(runId || '0')}
                  metricPath={selectedMetric}
                  onClose={() => setSelectedMetric(null)}
                />
              </Suspense>
            ) : (
              <div className="card text-center py-16">
                <ChartIcon className="mx-auto mb-4" style={{ color: 'var(--text-tertiary)' }} />
                <h3 className="heading-md mb-2">Select a metric</h3>
                <p className="text-body max-w-sm mx-auto">
                  Browse the metric tree on the left and click on a metric to view its data
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {selectedTab === 'config' && (
        <div className="card">
          <h3 className="heading-md mb-4">Configuration</h3>
          {(() => {
            const configData = summary?.config || {};

            return Object.keys(configData).length > 0 ? (
              <JsonViewer data={configData} dark={isDarkMode()} />
            ) : (
              <p className="text-center py-8" style={{ color: 'var(--text-secondary)' }}>No configuration data available</p>
            );
          })()}
        </div>
      )}
    </div>
  );
}
