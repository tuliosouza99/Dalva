import { useMemo } from 'react';
import Plot from 'react-plotly.js';
import { useMetricValues } from '../../api/client';
import type { MetricValue } from '../../api/client';

function isDarkMode() {
  return typeof document !== 'undefined' && document.documentElement.classList.contains('dark');
}

interface MetricChartProps {
  runId: number;
  metricPath: string;
  title?: string;
  height?: number;
  showLegend?: boolean;
}

export default function MetricChart({
  runId,
  metricPath,
  title,
  height = 400,
  showLegend = true,
}: MetricChartProps) {
  const { data, isLoading, error } = useMetricValues(runId, metricPath);

  const chartData = useMemo(() => {
    if (!data?.data) return [];

    const values = data.data;

    // Separate numeric and non-numeric values
    const numericValues = values.filter(
      (v: MetricValue) => typeof v.value === 'number'
    );

    if (numericValues.length === 0) return [];

    // Check if we have step information
    const hasSteps = numericValues.some((v: MetricValue) => v.step !== null);

    return [
      {
        type: 'scatter',
        mode: 'lines+markers',
        name: metricPath,
        x: hasSteps
          ? numericValues.map((v: MetricValue) => v.step)
          : numericValues.map((_, i: number) => i),
        y: numericValues.map((v: MetricValue) => v.value as number),
        marker: {
          size: 4,
          color: '#1976d2',
        },
        line: {
          color: '#1976d2',
          width: 2,
        },
        hovertemplate: hasSteps
          ? '<b>Step:</b> %{x}<br><b>Value:</b> %{y:.6f}<extra></extra>'
          : '<b>Index:</b> %{x}<br><b>Value:</b> %{y:.6f}<extra></extra>',
      },
    ];
  }, [data, metricPath]);

  const layout = useMemo(
    () => {
      const dark = isDarkMode();
      return {
        title: title || metricPath,
        autosize: true,
        height,
        margin: { t: 50, r: 30, b: 50, l: 60 },
        font: {
          color: dark ? '#e5e7eb' : '#374151',
        },
        xaxis: {
          title: data?.data?.[0]?.step !== null ? 'Step' : 'Index',
          showgrid: true,
          gridcolor: dark ? '#374151' : '#e5e7eb',
          zeroline: false,
          tickcolor: dark ? '#e5e7eb' : '#374151',
          linecolor: dark ? '#e5e7eb' : '#374151',
        },
        yaxis: {
          title: 'Value',
          showgrid: true,
          gridcolor: dark ? '#374151' : '#e5e7eb',
          zeroline: false,
          tickcolor: dark ? '#e5e7eb' : '#374151',
          linecolor: dark ? '#e5e7eb' : '#374151',
        },
        showlegend: showLegend,
        legend: {
          orientation: 'h',
          yanchor: 'bottom',
          y: 1.02,
          xanchor: 'right',
          x: 1,
        },
        hovermode: 'closest',
        plot_bgcolor: dark ? '#1f2937' : '#ffffff',
        paper_bgcolor: dark ? '#111827' : '#ffffff',
      };
    },
    [title, metricPath, height, showLegend, data]
  );

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
      <div
        className="bg-white rounded-lg border border-gray-200 flex items-center justify-center"
        style={{ height }}
      >
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
          <p className="mt-2 text-sm text-gray-600">Loading chart...</p>
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
          <p className="text-red-700 font-semibold">Error loading chart</p>
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
          <p className="text-gray-500">No numeric data available for this metric</p>
          <p className="text-gray-400 text-sm mt-1">{metricPath}</p>
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
