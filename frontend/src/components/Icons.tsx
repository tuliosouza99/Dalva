import { ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-react';

interface ForkIconProps {
  className?: string;
  size?: number;
}

export function ForkIcon({ className, size = 18 }: ForkIconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      style={{ color: 'var(--accent)' }}
      aria-label="Forked run"
    >
      <circle cx="12" cy="18" r="3" />
      <circle cx="6" cy="6" r="3" />
      <circle cx="18" cy="6" r="3" />
      <path d="M18 9v1a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2V9" />
      <path d="M12 12v3" />
    </svg>
  );
}

interface ChartIconProps {
  className?: string;
  style?: React.CSSProperties;
  size?: number;
  strokeWidth?: number;
}

export function ChartIcon({ className = '', style, size = 48, strokeWidth = 1.5 }: ChartIconProps) {
  return (
    <svg
      className={className}
      style={style}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <line x1="18" y1="20" x2="18" y2="10" />
      <line x1="12" y1="20" x2="12" y2="4" />
      <line x1="6" y1="20" x2="6" y2="14" />
    </svg>
  );
}

interface SortIconProps {
  column: string;
  sortBy: string | null;
  sortOrder: string;
  size?: number;
}

export function SortIcon({ column, sortBy, sortOrder, size = 14 }: SortIconProps) {
  if (sortBy !== column) return <ArrowUpDown size={size} className="opacity-40" />;
  return sortOrder === 'asc' ? <ArrowUp size={size} /> : <ArrowDown size={size} />;
}
