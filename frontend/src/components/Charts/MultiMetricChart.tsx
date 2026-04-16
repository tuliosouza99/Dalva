import { useMemo } from 'react';
import { useQueries } from '@tanstack/react-query';
import { Plot } from '../../utils/plotlyComponent';
import type { ChartTrace, ChartConfig } from '../../utils/plotlyComponent';
import { useDarkMode } from '../../hooks/useDarkMode';
import { buildChartLayout, chartColors } from '../../utils/chartTheme';
import type { MetricValue, MetricValuesResponse } from '../../api/client';
import CategoryAreaChart from './CategoryAreaChart';

interface MetricConfig {
  runId: number;
  metricPath: string;
  name?: string;
  color?: string;
}

interface MultiMetricChartProps {
  metrics: MetricConfig[];
  title?: string;
  height?: number;
  yAxisTitle?: string;
}

const DEFAULT_COLORS = [
  chartColors.primary,
  chartColors.secondary,
  chartColors.tertiary,
  chartColors.quaternary,
  chartColors.quinary,
  chartColors.senary,
  chartColors.septenary,
  chartColors.octonary,
];

function isCategoricalSeries(attributeType?: string): boolean {
  return attributeType === 'bool_series' || attributeType === 'string_series';
}

export default function MultiMetricChart({
  metrics,
  title = 'Metrics Comparison',
  height = 400,
  yAxisTitle = 'Value',
}: MultiMetricChartProps) {
  const queryResults = useQueries({
    queries: metrics.map((metric) => ({
      queryKey: ['metrics', metric.runId, metric.metricPath],
      queryFn: async (): Promise<MetricValuesResponse> => {
        const res = await fetch(`/api/metrics/runs/${metric.runId}/metric/${metric.metricPath}`);
        if (!res.ok) throw new Error('Failed to fetch metric');
        return res.json();
      },
      enabled: !!metric.runId && !!metric.metricPath,
    })),
  });

  const isLoading = queryResults.some((m) => m.isLoading);
  const error = queryResults.find((m) => m.error)?.error;
  const isDark = useDarkMode();

  const categoricalMetrics = useMemo(() => {
    if (isLoading || !queryResults.every((m) => m.data)) return [];
    return metrics
      .map((metric, idx) => ({
        metric,
        idx,
        data: queryResults[idx].data!,
      }))
      .filter(({ data }) => isCategoricalSeries(data.attribute_type));
  }, [queryResults, metrics, isLoading]);

  const chartData: ChartTrace[] = useMemo(() => {
    if (isLoading || !queryResults.every((m) => m.data)) return [];

    return metrics.map((metric, idx) => {
      const data = queryResults[idx].data;

      if (isCategoricalSeries(data?.attribute_type)) return null;

      const values = data?.data || [];
      const numericValues = values.filter(
        (v: MetricValue) => typeof v.value === 'number'
      );

      if (numericValues.length === 0) return null;

      const hasSteps = numericValues.some((v: MetricValue) => v.step !== null);

      return {
        type: 'scatter',
        mode: 'lines',
        name: metric.name || metric.metricPath,
        x: hasSteps
          ? numericValues.map((v: MetricValue) => v.step)
          : numericValues.map((_, i: number) => i),
        y: numericValues.map((v: MetricValue) => v.value as number),
        line: {
          color: metric.color || DEFAULT_COLORS[idx % DEFAULT_COLORS.length],
          width: 2,
          shape: 'spline',
        },
        hovertemplate: hasSteps
          ? '<b>Step:</b> %{x}<br><b>Value:</b> %{y:.6f}<extra></extra>'
          : '<b>Index:</b> %{x}<br><b>Value:</b> %{y:.6f}<extra></extra>',
      };
    }).filter(Boolean) as ChartTrace[];
  }, [queryResults, metrics, isLoading]);

  const hasAnyData = chartData.length > 0 || categoricalMetrics.length > 0;

  const layout = useMemo(
    () =>
      buildChartLayout(isDark, {
        title,
        height,
        xAxisTitle: 'Step',
        yAxisTitle,
        showLegend: true,
        legendOrientation: 'v',
        legendY: 1,
        legendX: 1.02,
      }),
    [isDark, title, height, yAxisTitle]
  );

  const config: ChartConfig = useMemo(
    () => ({
      responsive: true,
      displayModeBar: true,
      displaylogo: false,
      modeBarButtonsToRemove: ['lasso2d', 'select2d'],
      toImageButtonOptions: {
        format: 'png',
        filename: 'multi_metric_chart',
        height: 800,
        width: 1200,
        scale: 2,
      },
    }),
    []
  );

  if (isLoading) {
    return (
      <div
        className="rounded-lg border flex items-center justify-center"
        style={{ height, backgroundColor: 'var(--bg-surface)', borderColor: 'var(--border)' }}
      >
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2" style={{ borderColor: 'var(--accent)' }}></div>
          <p className="mt-2 text-sm" style={{ color: 'var(--text-secondary)' }}>Loading charts...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div
        className="rounded-lg border flex items-center justify-center"
        style={{ height, backgroundColor: 'rgba(239, 68, 68, 0.06)', borderColor: 'rgba(239, 68, 68, 0.2)' }}
      >
        <div className="text-center p-4">
          <p style={{ color: 'var(--badge-failed)' }} className="font-semibold">Error loading charts</p>
          <p className="text-sm mt-1" style={{ color: 'var(--badge-failed)' }}>{error.message}</p>
        </div>
      </div>
    );
  }

  if (!hasAnyData) {
    return (
      <div
        className="rounded-lg border flex items-center justify-center"
        style={{ height, backgroundColor: 'var(--bg-elevated)', borderColor: 'var(--border)' }}
      >
        <div className="text-center p-4">
          <p style={{ color: 'var(--text-secondary)' }}>No data available for the selected metrics</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {chartData.length > 0 && (
        <div className="rounded-lg border p-4" style={{ backgroundColor: 'var(--bg-surface)', borderColor: 'var(--border)' }}>
          <Plot data={chartData} layout={layout} config={config} style={{ width: '100%' }} />
        </div>
      )}
      {categoricalMetrics.map(({ metric, data }) => (
        <div key={metric.metricPath} className="rounded-lg border p-4" style={{ backgroundColor: 'var(--bg-surface)', borderColor: 'var(--border)' }}>
          <CategoryAreaChart
            values={data.data}
            attributeType={data.attribute_type!}
            metricPath={metric.name || metric.metricPath}
            title={metric.name || metric.metricPath}
            height={height}
          />
        </div>
      ))}
    </div>
  );
}
