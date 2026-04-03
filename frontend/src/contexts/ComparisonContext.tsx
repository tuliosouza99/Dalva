import { createContext, useContext, useState, useEffect, type ReactNode } from 'react';

interface ComparisonContextType {
  selectedRunIds: number[];
  setSelectedRunIds: (ids: number[]) => void;
  toggleRunId: (id: number) => void;
  clearSelection: () => void;
  isSelected: (id: number) => boolean;
  isAtMax: () => boolean;
  maxSelections?: number;
}

const ComparisonContext = createContext<ComparisonContextType | null>(null);

const STORAGE_KEY = 'dalva-comparison-runs';

export function ComparisonProvider({ children, maxSelections }: { children: ReactNode; maxSelections?: number }) {
  const [selectedRunIds, setSelectedRunIds] = useState<number[]>(() => {
    if (typeof window === 'undefined') return [];
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      return stored ? JSON.parse(stored) : [];
    } catch {
      return [];
    }
  });

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(selectedRunIds));
    } catch {
      // Ignore storage errors
    }
  }, [selectedRunIds]);

  const toggleRunId = (id: number) => {
    setSelectedRunIds(prev => {
      if (prev.includes(id)) {
        return prev.filter(runId => runId !== id);
      }
      if (maxSelections && prev.length >= maxSelections) {
        return prev;
      }
      return [...prev, id];
    });
  };

  const clearSelection = () => {
    setSelectedRunIds([]);
  };

  const isSelected = (id: number) => selectedRunIds.includes(id);

  const isAtMax = () => maxSelections !== undefined && selectedRunIds.length >= maxSelections;

  return (
    <ComparisonContext.Provider value={{ selectedRunIds, setSelectedRunIds, toggleRunId, clearSelection, isSelected, isAtMax, maxSelections }}>
      {children}
    </ComparisonContext.Provider>
  );
}

export function useComparison() {
  const context = useContext(ComparisonContext);
  if (!context) {
    throw new Error('useComparison must be used within a ComparisonProvider');
  }
  return context;
}
