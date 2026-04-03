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

const lightColors = {
  text: '#374151',
  grid: '#e8e6e3',
  accent: '#d4a012',
  bg: '#ffffff',
};

const darkColors = {
  text: '#e5e7eb',
  grid: '#2e2e2e',
  accent: '#f0b429',
  bg: '#1a1a1a',
};

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

  const colors = isDark ? darkColors : lightColors;

  return {
    title,
    autosize: true,
    height,
    margin: { t: 50, r: 30, b: 50, l: 60 },
    font: {
      family: 'DM Sans, sans-serif',
      color: colors.text,
      size: 12,
    },
    xaxis: {
      title: xAxisTitle,
      showgrid: true,
      gridcolor: colors.grid,
      zeroline: false,
      tickcolor: colors.text,
      linecolor: colors.text,
      titlefont: {
        family: 'DM Sans, sans-serif',
        size: 12,
        color: colors.text,
      },
    },
    yaxis: {
      title: yAxisTitle,
      showgrid: true,
      gridcolor: colors.grid,
      zeroline: false,
      tickcolor: colors.text,
      linecolor: colors.text,
      titlefont: {
        family: 'DM Sans, sans-serif',
        size: 12,
        color: colors.text,
      },
    },
    showlegend: showLegend,
    legend: {
      font: {
        family: 'DM Sans, sans-serif',
        size: 12,
        color: colors.text,
      },
      orientation: legendOrientation,
      yanchor: legendOrientation === 'h' ? 'bottom' : 'top',
      y: legendY,
      xanchor: legendOrientation === 'h' ? 'right' : 'left',
      x: legendX,
    },
    hovermode: 'closest' as const,
    plot_bgcolor: colors.bg,
    paper_bgcolor: colors.bg,
  };
}

export const chartColors = {
  primary: '#d4a012',
  secondary: '#6366f1',
  tertiary: '#22c55e',
  quaternary: '#f43f5e',
  quinary: '#8b5cf6',
  senary: '#14b8a6',
  septenary: '#f97316',
  octonary: '#ec4899',
};
