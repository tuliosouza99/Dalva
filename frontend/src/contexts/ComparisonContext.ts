import { createContext, useContext } from 'react';

export interface ComparisonContextType {
  selectedRunIds: number[];
  setSelectedRunIds: (ids: number[]) => void;
  toggleRunId: (id: number) => void;
  clearSelection: () => void;
  isSelected: (id: number) => boolean;
  isAtMax: () => boolean;
  maxSelections?: number;
}

export const ComparisonContext = createContext<ComparisonContextType | null>(null);

export function useComparison() {
  const context = useContext(ComparisonContext);
  if (!context) {
    throw new Error('useComparison must be used within a ComparisonProvider');
  }
  return context;
}
