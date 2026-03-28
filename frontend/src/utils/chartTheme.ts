interface ChartLayoutOptions {
  title?: string;
  height?: number;
  xAxisTitle?: string;
  yAxisTitle?: string;
  showLegend?: boolean;
  legendOrientation?: 'h' | 'v';
  legendY?: number;
  legendX?: number;
}

export function buildChartLayout(
  isDark: boolean,
  options: ChartLayoutOptions = {}
) {
  const {
    title,
    height = 400,
    xAxisTitle = 'Step',
    yAxisTitle = 'Value',
    showLegend = true,
    legendOrientation = 'h',
    legendY = 1.02,
    legendX = 1,
  } = options;

  return {
    title,
    autosize: true,
    height,
    margin: { t: 50, r: 30, b: 50, l: 60 },
    font: {
      color: isDark ? '#e5e7eb' : '#374151',
    },
    xaxis: {
      title: xAxisTitle,
      showgrid: true,
      gridcolor: isDark ? '#374151' : '#e5e7eb',
      zeroline: false,
      tickcolor: isDark ? '#e5e7eb' : '#374151',
      linecolor: isDark ? '#e5e7eb' : '#374151',
    },
    yaxis: {
      title: yAxisTitle,
      showgrid: true,
      gridcolor: isDark ? '#374151' : '#e5e7eb',
      zeroline: false,
      tickcolor: isDark ? '#e5e7eb' : '#374151',
      linecolor: isDark ? '#e5e7eb' : '#374151',
    },
    showlegend: showLegend,
    legend: {
      orientation: legendOrientation,
      yanchor: legendOrientation === 'h' ? 'bottom' : 'top',
      y: legendY,
      xanchor: legendOrientation === 'h' ? 'right' : 'left',
      x: legendX,
    },
    hovermode: 'closest' as const,
    plot_bgcolor: isDark ? '#1f2937' : '#ffffff',
    paper_bgcolor: isDark ? '#111827' : '#ffffff',
  };
}
