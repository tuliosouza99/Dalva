import { useMemo } from 'react';
import { useQueries } from '@tanstack/react-query';
import { Plot } from '../../utils/plotlyComponent';
import { useDarkMode } from '../../hooks/useDarkMode';
import { buildChartLayout } from '../../utils/chartTheme';
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
  '#1976d2', // Blue
  '#d32f2f', // Red
  '#388e3c', // Green
  '#f57c00', // Orange
  '#7b1fa2', // Purple
  '#0097a7', // Cyan
  '#c2185b', // Pink
  '#afb42b', // Lime
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

  const chartData = useMemo(() => {
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
    }).filter(Boolean);
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

  const config = useMemo(
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
        className="bg-white rounded-lg border border-gray-200 flex items-center justify-center"
        style={{ height }}
      >
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
          <p className="mt-2 text-sm text-gray-600">Loading charts...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div
        className="bg-red-50 rounded-lg border border-red-200 flex items-center justify-center"
        style={{ height }}
      >
        <div className="text-center p-4">
          <p className="text-red-700 font-semibold">Error loading charts</p>
          <p className="text-red-600 text-sm mt-1">{error.message}</p>
        </div>
      </div>
    );
  }

  if (!hasAnyData) {
    return (
      <div
        className="bg-gray-50 rounded-lg border border-gray-200 flex items-center justify-center"
        style={{ height }}
      >
        <div className="text-center p-4">
          <p className="text-gray-500">No data available for the selected metrics</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {chartData.length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <Plot data={chartData as never[]} layout={layout as never} config={config as never} style={{ width: '100%' }} />
        </div>
      )}
      {categoricalMetrics.map(({ metric, data }) => (
        <div key={metric.metricPath} className="bg-white rounded-lg border border-gray-200 p-4">
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
