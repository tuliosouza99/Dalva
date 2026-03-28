import { useMemo } from 'react';
import Plot from 'react-plotly.js';
import { useMetricValues } from '../../api/client';
import { useDarkMode } from '../../hooks/useDarkMode';
import { buildChartLayout } from '../../utils/chartTheme';
import type { MetricValue } from '../../api/client';

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

export default function MultiMetricChart({
  metrics,
  title = 'Metrics Comparison',
  height = 400,
  yAxisTitle = 'Value',
}: MultiMetricChartProps) {
  const metricData = metrics.map((metric) =>
    // eslint-disable-next-line react-hooks/rules-of-hooks
    useMetricValues(metric.runId, metric.metricPath)
  );

  const isLoading = metricData.some((m) => m.isLoading);
  const error = metricData.find((m) => m.error)?.error;
  const isDark = useDarkMode();

  const chartData = useMemo(() => {
    if (isLoading || !metricData.every((m) => m.data)) return [];

    return metrics.map((metric, idx) => {
      const data = metricData[idx].data?.data || [];
      const numericValues = data.filter(
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
  }, [metricData, metrics, isLoading]);

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

  if (chartData.length === 0) {
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
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <Plot data={chartData as any} layout={layout as any} config={config as any} style={{ width: '100%' }} />
    </div>
  );
}
