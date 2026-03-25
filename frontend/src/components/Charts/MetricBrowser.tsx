import { useState, useMemo } from 'react';

interface MetricNode {
  name: string;
  fullPath: string;
  isLeaf: boolean;
  children: Map<string, MetricNode>;
}

interface MetricBrowserProps {
  metrics: string[];
  onMetricSelect: (metricPath: string) => void;
  selectedMetric: string | null;
}

function buildMetricTree(metrics: string[]): MetricNode {
  const root: MetricNode = {
    name: 'root',
    fullPath: '',
    isLeaf: false,
    children: new Map(),
  };

  for (const metricPath of metrics) {
    const parts = metricPath.split('/');
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
    // Leaf node - metric
    const isSelected = selectedMetric === node.fullPath;
    return (
      <button
        onClick={() => onMetricSelect(node.fullPath)}
        className={`w-full text-left px-3 py-2 rounded text-sm font-mono transition-colors ${
          isSelected
            ? 'bg-primary-100 dark:bg-primary-900 text-primary-800 dark:text-primary-200 border-2 border-primary-500'
            : 'bg-gray-50 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 border-2 border-transparent'
        }`}
        style={{ marginLeft: `${level * 1.5}rem` }}
      >
        <div className="flex items-center gap-2">
          <svg className="w-4 h-4 text-gray-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
          <span className="truncate">{node.name}</span>
        </div>
      </button>
    );
  }

  // Folder node
  return (
    <div>
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full text-left px-3 py-2 rounded text-sm font-semibold transition-colors hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-900 dark:text-gray-100"
        style={{ marginLeft: `${level * 1.5}rem` }}
      >
        <div className="flex items-center gap-2">
          <svg
            className={`w-4 h-4 text-gray-500 transition-transform flex-shrink-0 ${
              isExpanded ? 'rotate-90' : ''
            }`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
          <svg className="w-4 h-4 text-gray-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
          </svg>
          <span className="truncate text-gray-900 dark:text-gray-100">{node.name}</span>
          <span className="text-xs text-gray-400">({node.children.size})</span>
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
      <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
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
        <p className="text-gray-500 dark:text-gray-400 text-center py-8">No metrics found for this run</p>
      )}
    </div>
  );
}
