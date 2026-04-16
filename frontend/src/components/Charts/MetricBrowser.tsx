import { useState, useMemo } from 'react';
import type { MetricInfo } from '../../api/client';

interface MetricNode {
  name: string;
  fullPath: string;
  isLeaf: boolean;
  attributeType?: string;
  children: Map<string, MetricNode>;
}

interface MetricBrowserProps {
  metrics: MetricInfo[];
  onMetricSelect: (metricPath: string) => void;
  selectedMetric: string | null;
}

function getTypeLabel(attributeType?: string): string | null {
  if (!attributeType) return null;
  if (attributeType === 'bool_series' || attributeType === 'string_series') return 'cat';
  if (attributeType.endsWith('_series')) return 'series';
  if (attributeType === 'bool' || attributeType === 'string') return 'scalar';
  return null;
}

function buildMetricTree(metrics: MetricInfo[]): MetricNode {
  const root: MetricNode = {
    name: 'root',
    fullPath: '',
    isLeaf: false,
    children: new Map(),
  };

  for (const metric of metrics) {
    const parts = metric.path.split('/');
    let currentNode = root;

    for (let i = 0; i < parts.length; i++) {
      const part = parts[i];
      const isLastPart = i === parts.length - 1;
      const fullPath = parts.slice(0, i + 1).join('/');

      if (!currentNode.children.has(part)) {
        currentNode.children.set(part, {
          name: part,
          fullPath,
          isLeaf: isLastPart,
          attributeType: isLastPart ? metric.attribute_type : undefined,
          children: new Map(),
        });
      }

      currentNode = currentNode.children.get(part)!;
    }
  }

  return root;
}

function MetricTreeNode({
  node,
  onMetricSelect,
  selectedMetric,
  level = 0,
}: {
  node: MetricNode;
  onMetricSelect: (metricPath: string) => void;
  selectedMetric: string | null;
  level?: number;
}) {
  const [isExpanded, setIsExpanded] = useState(false); // Collapsed by default

  const sortedChildren = useMemo(() => {
    // Sort folders first, then metrics
    const childArray = Array.from(node.children.values());
    return childArray.sort((a, b) => {
      if (a.isLeaf !== b.isLeaf) {
        return a.isLeaf ? 1 : -1;
      }
      return a.name.localeCompare(b.name);
    });
  }, [node.children]);

  if (node.isLeaf) {
    const isSelected = selectedMetric === node.fullPath;
    const typeLabel = getTypeLabel(node.attributeType);
    return (
      <button
        onClick={() => onMetricSelect(node.fullPath)}
        className="w-full text-left px-3 py-2 rounded text-sm font-mono transition-all"
        style={{
          marginLeft: `${level * 1.5}rem`,
          backgroundColor: isSelected ? 'var(--accent-muted)' : 'var(--bg-elevated)',
          color: isSelected ? 'var(--accent)' : 'var(--text-primary)',
          border: isSelected ? '2px solid var(--accent)' : '2px solid transparent',
        }}
        onMouseEnter={(e) => {
          if (!isSelected) {
            e.currentTarget.style.backgroundColor = 'var(--bg-surface)';
          }
        }}
        onMouseLeave={(e) => {
          if (!isSelected) {
            e.currentTarget.style.backgroundColor = 'var(--bg-elevated)';
          }
        }}
      >
        <div className="flex items-center gap-2">
          <svg 
            className="w-4 h-4 flex-shrink-0" 
            style={{ color: isSelected ? 'var(--accent)' : 'var(--text-tertiary)' }}
            fill="none" 
            stroke="currentColor" 
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
          <span className="truncate">{node.name}</span>
          {typeLabel && (
            <span
              className="text-[10px] px-1.5 py-0.5 rounded font-sans font-medium uppercase flex-shrink-0"
              style={{
                backgroundColor: typeLabel === 'cat'
                  ? 'var(--badge-quinary-bg, rgba(139, 92, 246, 0.15))'
                  : typeLabel === 'series'
                  ? 'var(--badge-secondary-bg, rgba(99, 102, 241, 0.15))'
                  : 'var(--bg-elevated)',
                color: typeLabel === 'cat'
                  ? 'var(--badge-quinary, #8b5cf6)'
                  : typeLabel === 'series'
                  ? 'var(--badge-secondary, #6366f1)'
                  : 'var(--text-tertiary)',
              }}
            >
              {typeLabel}
            </span>
          )}
        </div>
      </button>
    );
  }

  // Folder node
  return (
    <div>
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full text-left px-3 py-2 rounded text-sm font-semibold transition-colors"
        style={{ 
          marginLeft: `${level * 1.5}rem`,
          color: 'var(--text-primary)'
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.backgroundColor = 'var(--bg-elevated)';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.backgroundColor = 'transparent';
        }}
      >
        <div className="flex items-center gap-2">
          <svg
            className="w-4 h-4 transition-transform flex-shrink-0"
            style={{ 
              color: 'var(--text-tertiary)',
              transform: isExpanded ? 'rotate(90deg)' : 'rotate(0deg)'
            }}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
          <svg 
            className="w-4 h-4 flex-shrink-0" 
            style={{ color: 'var(--text-tertiary)' }}
            fill="none" 
            stroke="currentColor" 
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
          </svg>
          <span className="truncate">{node.name}</span>
          <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>({node.children.size})</span>
        </div>
      </button>
      {isExpanded && (
        <div className="mt-1 space-y-1">
          {sortedChildren.map((child) => (
            <MetricTreeNode
              key={child.fullPath}
              node={child}
              onMetricSelect={onMetricSelect}
              selectedMetric={selectedMetric}
              level={level + 1}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export default function MetricBrowser({ metrics, onMetricSelect, selectedMetric }: MetricBrowserProps) {
  const metricTree = useMemo(() => buildMetricTree(metrics), [metrics]);

  return (
    <div className="card">
      <h3 className="heading-md mb-4">
        Available Metrics ({metrics.length})
      </h3>
      {metrics.length > 0 ? (
        <div className="space-y-1 max-h-[600px] overflow-y-auto">
          {Array.from(metricTree.children.values()).map((node) => (
            <MetricTreeNode
              key={node.fullPath}
              node={node}
              onMetricSelect={onMetricSelect}
              selectedMetric={selectedMetric}
            />
          ))}
        </div>
      ) : (
        <p className="text-center py-8" style={{ color: 'var(--text-secondary)' }}>No metrics found for this run</p>
      )}
    </div>
  );
}
