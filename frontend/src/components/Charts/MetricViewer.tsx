import { useMemo } from 'react';
import { Plot } from '../../utils/plotlyComponent';
import { useMetricValues } from '../../api/client';
import { useDarkMode } from '../../hooks/useDarkMode';
import { buildChartLayout } from '../../utils/chartTheme';
import type { MetricValue } from '../../api/client';
import CategoryAreaChart from './CategoryAreaChart';

interface MetricViewerProps {
  runId: number;
  metricPath: string;
  onClose: () => void;
}

function isCategoricalSeries(attributeType?: string): boolean {
  return attributeType === 'bool_series' || attributeType === 'string_series';
}

export default function MetricViewer({ runId, metricPath, onClose }: MetricViewerProps) {
  const { data, isLoading, error } = useMetricValues(runId, metricPath);
  const isDark = useDarkMode();

  const metricAnalysis = useMemo(() => {
    if (!data?.data || data.data.length === 0) {
      return { type: 'empty', values: [] };
    }

    const values = data.data;
    const attributeType = data.attribute_type;
    const isSeries = attributeType?.endsWith('_series') ?? false;

    if (isSeries && isCategoricalSeries(attributeType)) {
      return {
        type: 'category',
        values,
        attributeType: attributeType!,
      };
    }

    if (isSeries) {
      const numericValues = values.filter(
        (v: MetricValue) => typeof v.value === 'number'
      );
      const hasSteps = numericValues.some((v: MetricValue) => v.step !== null);
      return {
        type: 'chart',
        values: numericValues,
        hasSteps,
      };
    }

    return {
      type: 'single',
      value: values[0].value,
      step: values[0].step,
      timestamp: values[0].timestamp,
    };
  }, [data]);

  const chartData = useMemo(() => {
    if (metricAnalysis.type !== 'chart') return [];

    const values = metricAnalysis.values as MetricValue[];
    const hasSteps = metricAnalysis.hasSteps;

    return [
      {
        type: 'scatter',
        mode: 'lines',
        name: metricPath,
        x: hasSteps
          ? values.map((v: MetricValue) => v.step)
          : values.map((_, i: number) => i),
        y: values.map((v: MetricValue) => v.value as number),
        line: {
          color: 'var(--accent)',
          width: 2,
          shape: 'spline',
        },
        hovertemplate: hasSteps
          ? '<b>Step:</b> %{x}<br><b>Value:</b> %{y:.6f}<extra></extra>'
          : '<b>Index:</b> %{x}<br><b>Value:</b> %{y:.6f}<extra></extra>',
      },
    ];
  }, [metricAnalysis, metricPath]);

  const layout = useMemo(() => {
    if (metricAnalysis.type !== 'chart') return {};

    const hasSteps = metricAnalysis.hasSteps;
    return buildChartLayout(isDark, {
      title: metricPath,
      height: 400,
      xAxisTitle: hasSteps ? 'Step' : 'Index',
      showLegend: false,
    });
  }, [isDark, metricAnalysis, metricPath]);

  const config = useMemo(
    () => ({
      responsive: true,
      displayModeBar: true,
      displaylogo: false,
      modeBarButtonsToRemove: ['lasso2d', 'select2d'],
      toImageButtonOptions: {
        format: 'png',
        filename: `${metricPath.replace(/\//g, '_')}_chart`,
        height: 800,
        width: 1200,
        scale: 2,
      },
    }),
    [metricPath]
  );

  if (isLoading) {
    return (
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h3 className="heading-md mono">{metricPath}</h3>
          <button
            onClick={onClose}
            className="transition-colors"
            style={{ color: 'var(--text-tertiary)' }}
            onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--text-primary)')}
            onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--text-tertiary)')}
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <div className="flex items-center justify-center py-12">
          <div className="text-center">
            <div className="skeleton w-8 h-8 rounded-full mx-auto mb-2"></div>
            <p className="text-small">Loading metric...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h3 className="heading-md mono">{metricPath}</h3>
          <button
            onClick={onClose}
            className="transition-colors"
            style={{ color: 'var(--text-tertiary)' }}
            onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--text-primary)')}
            onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--text-tertiary)')}
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <div className="card p-4" style={{ backgroundColor: 'rgba(239, 68, 68, 0.08)', borderColor: 'rgba(239, 68, 68, 0.2)' }}>
          <p style={{ color: 'var(--badge-failed)' }} className="font-semibold">Error loading metric</p>
          <p className="text-sm mt-1" style={{ color: 'var(--badge-failed)' }}>{error.message}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-4">
        <h3 className="heading-md mono">{metricPath}</h3>
        <button
          onClick={onClose}
          className="transition-colors"
          style={{ color: 'var(--text-tertiary)' }}
          onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--text-primary)')}
          onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--text-tertiary)')}
        >
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {metricAnalysis.type === 'empty' && (
        <div className="card text-center py-8">
          <p className="text-body">No data available for this metric</p>
        </div>
      )}

      {metricAnalysis.type === 'single' && (
        <div 
          className="rounded-lg border p-8"
          style={{ 
            backgroundColor: 'var(--accent-muted)', 
            borderColor: 'var(--accent)'
          }}
        >
          <div className="text-center">
            <p className="text-small mb-2">Value</p>
            <p className="text-4xl font-bold" style={{ color: 'var(--text-primary)' }}>
              {typeof metricAnalysis.value === 'number'
                ? metricAnalysis.value.toFixed(6)
                : String(metricAnalysis.value)}
            </p>
            {metricAnalysis.timestamp && (
              <p className="text-small mt-2">
                {new Date(metricAnalysis.timestamp).toLocaleString()}
              </p>
            )}
          </div>
        </div>
      )}

      {metricAnalysis.type === 'chart' && chartData.length > 0 && (
        <div 
          className="rounded-lg border p-4"
          style={{ 
            backgroundColor: 'var(--bg-surface)', 
            borderColor: 'var(--border)'
          }}
        >
          <Plot data={chartData as never} layout={layout as never} config={config as never} style={{ width: '100%' }} />
        </div>
      )}

      {metricAnalysis.type === 'category' && (
        <div 
          className="rounded-lg border p-4"
          style={{ 
            backgroundColor: 'var(--bg-surface)', 
            borderColor: 'var(--border)'
          }}
        >
          <CategoryAreaChart
            values={metricAnalysis.values as MetricValue[]}
            attributeType={metricAnalysis.attributeType as string}
            metricPath={metricPath}
          />
        </div>
      )}
    </div>
  );
}
