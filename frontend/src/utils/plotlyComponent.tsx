import createPlotlyComponent from 'react-plotly.js/factory';
import Plotly from 'plotly.js-dist-min';

type CreatePlotlyComponentType = typeof createPlotlyComponent;

const factory: CreatePlotlyComponentType =
  typeof createPlotlyComponent === 'function'
    ? createPlotlyComponent
    : (createPlotlyComponent as { default: CreatePlotlyComponentType }).default;

const PlotlyPlot = factory(Plotly);

export interface ChartTrace {
  type?: string;
  mode?: string;
  name?: string;
  x?: (number | null)[];
  y?: (number | null)[];
  line?: { color?: string; width?: number; shape?: string };
  fill?: string;
  stackgroup?: string;
  hovertemplate?: string;
}

export interface ChartConfig {
  responsive?: boolean;
  displayModeBar?: boolean;
  displaylogo?: boolean;
  modeBarButtonsToRemove?: string[];
  toImageButtonOptions?: {
    format?: string;
    filename?: string;
    height?: number;
    width?: number;
    scale?: number;
  };
}

export interface ChartProps {
  data: ChartTrace[];
  layout: Record<string, unknown>;
  config: ChartConfig;
  style?: React.CSSProperties;
}

export function Plot({ data, layout, config, style }: ChartProps) {
  return (
    <PlotlyPlot
      data={data as never[]}
      layout={layout as never}
      config={config as never}
      style={style}
    />
  );
}
