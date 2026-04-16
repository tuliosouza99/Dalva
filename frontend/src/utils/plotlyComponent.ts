import createPlotlyComponent from 'react-plotly.js/factory';
import Plotly from 'plotly.js-dist-min';

const factory = typeof createPlotlyComponent === 'function'
  ? createPlotlyComponent
  : (createPlotlyComponent as any).default;

export const Plot = factory(Plotly);
