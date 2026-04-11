import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react';

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
      // storage unavailable
    }
  }, [selectedRunIds]);

  useEffect(() => {
    const handleStorage = (e: StorageEvent) => {
      if (e.key === STORAGE_KEY && e.newValue) {
        try {
          const parsed = JSON.parse(e.newValue);
          if (Array.isArray(parsed)) {
            setSelectedRunIds(parsed);
          }
        } catch {
          // invalid json
        }
      }
    };
    window.addEventListener('storage', handleStorage);
    return () => window.removeEventListener('storage', handleStorage);
  }, []);

  const toggleRunId = useCallback((id: number) => {
    setSelectedRunIds(prev => {
      if (prev.includes(id)) {
        return prev.filter(runId => runId !== id);
      }
      if (maxSelections && prev.length >= maxSelections) {
        return prev;
      }
      return [...prev, id];
    });
  }, [maxSelections]);

  const clearSelection = useCallback(() => {
    setSelectedRunIds([]);
  }, []);

  const isSelected = useCallback((id: number) => selectedRunIds.includes(id), [selectedRunIds]);

  const isAtMax = useCallback(() => maxSelections !== undefined && selectedRunIds.length >= maxSelections, [maxSelections, selectedRunIds.length]);

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
