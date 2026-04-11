import { useMemo, useState } from 'react';
import Plot from 'react-plotly.js';
import { useDarkMode } from '../../hooks/useDarkMode';
import { buildChartLayout, chartColors } from '../../utils/chartTheme';
import type { MetricValue } from '../../api/client';

interface CategoryAreaChartProps {
  values: MetricValue[];
  attributeType: string;
  metricPath: string;
  height?: number;
  title?: string;
}

const AREA_COLORS = [
  chartColors.primary,
  chartColors.secondary,
  chartColors.tertiary,
  chartColors.quaternary,
  chartColors.quinary,
  chartColors.senary,
  chartColors.septenary,
  chartColors.octonary,
  '#64748b',
  '#78716c',
];

function computeCategoryData(
  values: MetricValue[],
  topN: number
) {
  const sorted = [...values].sort(
    (a, b) => (a.step ?? 0) - (b.step ?? 0)
  );

  const categoryCounts = new Map<string, number>();
  for (const v of sorted) {
    const key = String(v.value);
    categoryCounts.set(key, (categoryCounts.get(key) || 0) + 1);
  }

  const allCategories = [...categoryCounts.entries()]
    .sort((a, b) => b[1] - a[1])
    .map(([cat]) => cat);

  const nUnique = allCategories.length;
  const effectiveTopN = Math.min(topN, nUnique);

  const topCategories = allCategories.slice(0, effectiveTopN);
  const hasOther = nUnique > effectiveTopN;
  const displayCategories = hasOther
    ? [...topCategories, 'Other']
    : topCategories;

  const otherSet = hasOther
    ? new Set(allCategories.slice(effectiveTopN))
    : null;

  const stepMap = new Map<number, Map<string, number>>();
  const cumulative = new Map<string, number>();
  for (const cat of displayCategories) {
    cumulative.set(cat, 0);
  }

  for (const v of sorted) {
    const step = v.step ?? 0;
    const rawKey = String(v.value);
    const cat = otherSet?.has(rawKey) ? 'Other' : rawKey;

    if (!stepMap.has(step)) {
      stepMap.set(step, new Map());
    }
    cumulative.set(cat, (cumulative.get(cat) || 0) + 1);
    for (const c of displayCategories) {
      stepMap.get(step)!.set(c, (cumulative.get(c) || 0));
    }
  }

  const steps = [...stepMap.keys()].sort((a, b) => a - b);

  const traces = displayCategories.map((cat) => ({
    category: cat,
    x: steps,
    y: steps.map((s) => stepMap.get(s)?.get(cat) || 0),
  }));

  return { traces, nUnique, displayCategories };
}

export default function CategoryAreaChart({
  values,
  attributeType,
  metricPath,
  height = 400,
  title,
}: CategoryAreaChartProps) {
  const isDark = useDarkMode();
  const isBool = attributeType === 'bool_series';

  const defaultTopN = isBool ? 2 : 3;
  const [topN, setTopN] = useState(defaultTopN);

  const { traces, nUnique, displayCategories } = useMemo(
    () => computeCategoryData(values, topN),
    [values, topN]
  );

  const maxTopN = Math.min(10, nUnique);

  const chartData = useMemo(
    () =>
      traces.map((trace, idx) => ({
        type: 'scatter' as const,
        mode: 'lines' as const,
        name: trace.category,
        x: trace.x,
        y: trace.y,
        stackgroup: 'one',
        fill: idx === 0 ? ('tozeroy' as const) : ('tonexty' as const),
        line: {
          color: AREA_COLORS[idx % AREA_COLORS.length],
          width: 1,
          shape: 'spline' as const,
        },
        hovertemplate:
          '<b>Step:</b> %{x}<br><b>' +
          trace.category +
          ':</b> %{y}<extra></extra>',
      })),
    [traces]
  );

  const layout = useMemo(
    () =>
      buildChartLayout(isDark, {
        title: title || metricPath,
        height,
        xAxisTitle: 'Step',
        yAxisTitle: 'Cumulative Count',
        showLegend: true,
        legendOrientation: 'v',
        legendY: 1,
        legendX: 1.02,
      }),
    [isDark, title, metricPath, height]
  );

  const config = useMemo(
    () => ({
      responsive: true,
      displayModeBar: true,
      displaylogo: false,
      modeBarButtonsToRemove: ['lasso2d', 'select2d'],
      toImageButtonOptions: {
        format: 'png',
        filename: `${metricPath.replace(/\//g, '_')}_category_chart`,
        height: 800,
        width: 1200,
        scale: 2,
      },
    }),
    [metricPath]
  );

  return (
    <div>
      <Plot
        data={chartData as never[]}
        layout={layout as never}
        config={config as never}
        style={{ width: '100%' }}
      />
      {!isBool && nUnique > 3 && (
        <div
          className="flex items-center gap-2 mt-2 px-2"
          style={{ color: 'var(--text-secondary)' }}
        >
          <span className="text-xs">Show top</span>
          {Array.from({ length: maxTopN - 2 }, (_, i) => i + 3).map((n) => (
            <button
              key={n}
              onClick={() => setTopN(n)}
              className="text-xs px-2 py-0.5 rounded transition-colors"
              style={{
                backgroundColor:
                  topN === n ? 'var(--accent)' : 'var(--bg-elevated)',
                color: topN === n ? 'white' : 'var(--text-secondary)',
                border: `1px solid ${topN === n ? 'var(--accent)' : 'var(--border)'}`,
              }}
              onMouseEnter={(e) => {
                if (topN !== n) {
                  e.currentTarget.style.borderColor = 'var(--accent)';
                }
              }}
              onMouseLeave={(e) => {
                if (topN !== n) {
                  e.currentTarget.style.borderColor = 'var(--border)';
                }
              }}
            >
              {n}
            </button>
          ))}
          <span className="text-xs">
            of {nUnique} categories
          </span>
        </div>
      )}
      {isBool && (
        <div
          className="flex items-center gap-2 mt-2 px-2"
          style={{ color: 'var(--text-tertiary)' }}
        >
          {displayCategories.map((cat, idx) => (
            <span key={cat} className="flex items-center gap-1 text-xs">
              <span
                className="inline-block w-3 h-3 rounded-sm"
                style={{ backgroundColor: AREA_COLORS[idx % AREA_COLORS.length] }}
              />
              {cat}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
