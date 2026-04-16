import { useMemo } from 'react';
import { Plot } from '../../utils/plotlyComponent';
import type { ChartTrace, ChartConfig } from '../../utils/plotlyComponent';
import { useMetricValues } from '../../api/client';
import { useDarkMode } from '../../hooks/useDarkMode';
import { buildChartLayout, chartColors } from '../../utils/chartTheme';
import type { MetricValue } from '../../api/client';
import CategoryAreaChart from './CategoryAreaChart';

interface MetricChartProps {
  runId: number;
  metricPath: string;
  title?: string;
  height?: number;
  showLegend?: boolean;
}

function isCategoricalSeries(attributeType?: string): boolean {
  return attributeType === 'bool_series' || attributeType === 'string_series';
}

export default function MetricChart({
  runId,
  metricPath,
  title,
  height = 400,
  showLegend = true,
}: MetricChartProps) {
  const { data, isLoading, error } = useMetricValues(runId, metricPath);
  const isDark = useDarkMode();

  const isCategoryChart = isCategoricalSeries(data?.attribute_type);

  const chartData: ChartTrace[] = useMemo(() => {
    if (!data?.data || isCategoryChart) return [];

    const values = data.data;

    const numericValues = values.filter(
      (v: MetricValue) => typeof v.value === 'number'
    );

    if (numericValues.length === 0) return [];

    const hasSteps = numericValues.some((v: MetricValue) => v.step !== null);

    return [
      {
        type: 'scatter',
        mode: 'lines',
        name: metricPath,
        x: hasSteps
          ? numericValues.map((v: MetricValue) => v.step)
          : numericValues.map((_, i: number) => i),
        y: numericValues.map((v: MetricValue) => v.value as number),
        line: {
          color: chartColors.primary,
          width: 2,
          shape: 'spline',
        },
        hovertemplate: hasSteps
          ? '<b>Step:</b> %{x}<br><b>Value:</b> %{y:.6f}<extra></extra>'
          : '<b>Index:</b> %{x}<br><b>Value:</b> %{y:.6f}<extra></extra>',
      },
    ];
  }, [data, metricPath, isCategoryChart]);

  const layout = useMemo(
    () =>
      buildChartLayout(isDark, {
        title: title || metricPath,
        height,
        xAxisTitle: data?.data?.[0]?.step !== null ? 'Step' : 'Index',
        showLegend,
        legendOrientation: 'h',
        legendY: 1.02,
        legendX: 1,
      }),
    [isDark, title, metricPath, height, showLegend, data]
  );

  const config: ChartConfig = useMemo(
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
      <div
        className="rounded-lg border flex items-center justify-center"
        style={{ height, backgroundColor: 'var(--bg-surface)', borderColor: 'var(--border)' }}
      >
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2" style={{ borderColor: 'var(--accent)' }}></div>
          <p className="mt-2 text-sm" style={{ color: 'var(--text-secondary)' }}>Loading chart...</p>
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
          <p style={{ color: 'var(--badge-failed)' }} className="font-semibold">Error loading chart</p>
          <p className="text-sm mt-1" style={{ color: 'var(--badge-failed)' }}>{error.message}</p>
        </div>
      </div>
    );
  }

  if (chartData.length === 0 && !isCategoryChart) {
    return (
      <div
        className="rounded-lg border flex items-center justify-center"
        style={{ height, backgroundColor: 'var(--bg-elevated)', borderColor: 'var(--border)' }}
      >
        <div className="text-center p-4">
          <p style={{ color: 'var(--text-secondary)' }}>No numeric data available for this metric</p>
          <p className="text-sm mt-1" style={{ color: 'var(--text-tertiary)' }}>{metricPath}</p>
        </div>
      </div>
    );
  }

  if (isCategoryChart && data?.data && data.data.length > 0) {
    return (
      <div className="rounded-lg border p-4" style={{ backgroundColor: 'var(--bg-surface)', borderColor: 'var(--border)' }}>
        <CategoryAreaChart
          values={data.data}
          attributeType={data.attribute_type!}
          metricPath={metricPath}
          title={title || metricPath}
          height={height}
        />
      </div>
    );
  }

  return (
    <div className="rounded-lg border p-4" style={{ backgroundColor: 'var(--bg-surface)', borderColor: 'var(--border)' }}>
      <Plot data={chartData} layout={layout} config={config} style={{ width: '100%' }} />
    </div>
  );
}
