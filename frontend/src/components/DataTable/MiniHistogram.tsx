import { useState } from 'react';
import type { NumericBin } from '../../api/client';

interface MiniHistogramProps {
  bins: NumericBin[];
  filterMin?: number;
  filterMax?: number;
  height?: number;
}

interface TooltipState {
  visible: boolean;
  x: number;
  y: number;
  text: string;
}

export default function MiniHistogram({
  bins,
  filterMin,
  filterMax,
  height = 24,
}: MiniHistogramProps) {
  const [tooltip, setTooltip] = useState<TooltipState>({
    visible: false,
    x: 0,
    y: 0,
    text: '',
  });

  if (!bins || bins.length === 0) return null;

  const maxCount = Math.max(...bins.map((b) => b.count), 1);
  const globalMin = bins[0].start;
  const globalMax = bins[bins.length - 1].end;
  const range = globalMax - globalMin || 1;
  const barWidth = 100 / bins.length;

  const filterStartPct =
    filterMin !== undefined ? ((filterMin - globalMin) / range) * 100 : 0;
  const filterEndPct =
    filterMax !== undefined ? ((filterMax - globalMin) / range) * 100 : 100;

  return (
    <div className="mini-histogram-wrapper">
      <svg
        width="100%"
        height={height}
        viewBox={`0 0 100 ${height}`}
        preserveAspectRatio="none"
        className="mini-histogram"
      >
        {bins.map((bin, i) => {
          const barHeight = (bin.count / maxCount) * (height - 2);
          const x = i * barWidth;
          const inFilterRange =
            filterMin !== undefined && filterMax !== undefined
              ? bin.end > filterMin && bin.start < filterMax
              : true;

          return (
            <rect
              key={i}
              x={x + 0.5}
              y={height - barHeight}
              width={Math.max(barWidth - 1, 0.5)}
              height={barHeight}
              fill={inFilterRange ? 'var(--accent)' : 'var(--border)'}
              opacity={inFilterRange ? 0.7 : 0.4}
              rx={0.5}
              onMouseEnter={(e) => {
                const rect = (e.target as SVGRectElement).getBoundingClientRect();
                setTooltip({
                  visible: true,
                  x: rect.left + rect.width / 2,
                  y: rect.top,
                  text: `${bin.start.toFixed(bin.start % 1 === 0 ? 0 : 2)} – ${bin.end.toFixed(bin.end % 1 === 0 ? 0 : 2)}: ${bin.count}`,
                });
              }}
              onMouseLeave={() =>
                setTooltip((t) => ({ ...t, visible: false }))
              }
            />
          );
        })}
        {filterMin !== undefined && filterMax !== undefined && (
          <rect
            x={filterStartPct}
            y={0}
            width={Math.max(filterEndPct - filterStartPct, 0)}
            height={height}
            fill="var(--accent)"
            opacity={0.08}
            rx={1}
          />
        )}
      </svg>
      {tooltip.visible && (
        <div
          className="mini-histogram-tooltip"
          style={{
            left: tooltip.x,
            top: tooltip.y,
            transform: 'translate(-50%, -100%)',
          }}
        >
          {tooltip.text}
        </div>
      )}
    </div>
  );
}
