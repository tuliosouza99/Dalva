import { useState } from 'react';
import type { BoolStats, StringStats } from '../../api/client';

interface MiniCategoryBarProps {
  stats: BoolStats | StringStats;
  height?: number;
}

interface TooltipState {
  visible: boolean;
  x: number;
  y: number;
  text: string;
}

export default function MiniCategoryBar({ stats, height = 28 }: MiniCategoryBarProps) {
  const [tooltip, setTooltip] = useState<TooltipState>({
    visible: false,
    x: 0,
    y: 0,
    text: '',
  });

  if (stats.type === 'bool') {
    const t = stats.counts.true || 0;
    const f = stats.counts.false || 0;
    const total = t + f + stats.null_count;
    if (total === 0) return null;

    const truePct = (t / total) * 100;
    const falsePct = (f / total) * 100;

    return (
      <div className="mini-histogram-wrapper">
        <svg
          width="100%"
          height={height}
          viewBox={`0 0 100 ${height}`}
          preserveAspectRatio="none"
          className="mini-category-bar"
        >
          <rect
            x={0} y={2} width={truePct} height={height - 4}
            fill="var(--accent)" opacity={0.7} rx={2}
            onMouseEnter={(e) => {
              const rect = (e.target as SVGRectElement).getBoundingClientRect();
              setTooltip({ visible: true, x: rect.left + rect.width / 2, y: rect.top, text: `true: ${t}` });
            }}
            onMouseLeave={() => setTooltip((t) => ({ ...t, visible: false }))}
          />
          <rect
            x={truePct} y={2} width={falsePct} height={height - 4}
            fill="var(--border)" opacity={0.6} rx={2}
            onMouseEnter={(e) => {
              const rect = (e.target as SVGRectElement).getBoundingClientRect();
              setTooltip({ visible: true, x: rect.left + rect.width / 2, y: rect.top, text: `false: ${f}` });
            }}
            onMouseLeave={() => setTooltip((t) => ({ ...t, visible: false }))}
          />
          {stats.null_count > 0 && (
            <rect
              x={truePct + falsePct} y={2}
              width={(stats.null_count / total) * 100} height={height - 4}
              fill="var(--text-tertiary)" opacity={0.3} rx={2}
              onMouseEnter={(e) => {
                const rect = (e.target as SVGRectElement).getBoundingClientRect();
                setTooltip({ visible: true, x: rect.left + rect.width / 2, y: rect.top, text: `null: ${stats.null_count}` });
              }}
              onMouseLeave={() => setTooltip((t) => ({ ...t, visible: false }))}
            />
          )}
        </svg>
        {tooltip.visible && (
          <div
            className="mini-histogram-tooltip"
            style={{ left: tooltip.x, top: tooltip.y, transform: 'translate(-50%, -100%)' }}
          >
            {tooltip.text}
          </div>
        )}
      </div>
    );
  }

  if (stats.type === 'string' && stats.top_values.length > 0) {
    const maxCount = Math.max(...stats.top_values.map((v) => v.count), 1);
    const values = stats.top_values.slice(0, 5);
    const barCount = values.length;
    const gap = 2;
    const totalGap = gap * (barCount - 1);
    const barW = Math.max((100 - totalGap) / barCount, 1);

    return (
      <div className="mini-histogram-wrapper">
        <svg
          width="100%"
          height={height}
          viewBox={`0 0 100 ${height}`}
          preserveAspectRatio="none"
          className="mini-category-bar"
        >
          {values.map((v, i) => {
            const barH = (v.count / maxCount) * (height - 4);
            const x = i * (barW + gap);
            const y = height - barH;
            const isOther = v.value === '(other)';
            return (
              <rect
                key={i}
                x={x} y={y} width={barW} height={barH}
                fill={isOther ? 'var(--text-tertiary)' : 'var(--accent)'}
                opacity={isOther ? 0.4 : 0.5 + 0.3 * (1 - i / barCount)}
                rx={1}
                onMouseEnter={(e) => {
                  const rect = (e.target as SVGRectElement).getBoundingClientRect();
                  setTooltip({ visible: true, x: rect.left + rect.width / 2, y: rect.top, text: `${v.value}: ${v.count}` });
                }}
                onMouseLeave={() => setTooltip((t) => ({ ...t, visible: false }))}
              />
            );
          })}
        </svg>
        {tooltip.visible && (
          <div
            className="mini-histogram-tooltip"
            style={{ left: tooltip.x, top: tooltip.y, transform: 'translate(-50%, -100%)' }}
          >
            {tooltip.text}
          </div>
        )}
      </div>
    );
  }

  return null;
}
