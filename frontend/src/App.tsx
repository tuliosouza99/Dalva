import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ComparisonProvider } from './contexts/ComparisonProvider';
import Layout from './components/Layout';
import ProjectsPage from './pages/ProjectsPage';
import RunsPage from './pages/RunsPage';
import RunDetailPage from './pages/RunDetailPage';
import CompareRunsPage from './pages/CompareRunsPage';
import TablesPage from './pages/TablesPage';
import TableDetailPage from './pages/TableDetailPage';

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30000, // 30 seconds
      refetchOnWindowFocus: false,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ComparisonProvider maxSelections={5}>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<Layout />}>
              <Route index element={<Navigate to="/projects" replace />} />
              <Route path="projects" element={<ProjectsPage />} />
              <Route path="projects/:projectId/runs" element={<RunsPage />} />
              <Route path="projects/:projectId/tables" element={<TablesPage />} />
              <Route path="runs/:runId" element={<RunDetailPage />} />
              <Route path="tables/:tableId" element={<TableDetailPage />} />
              <Route path="compare" element={<CompareRunsPage />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </ComparisonProvider>
    </QueryClientProvider>
  );
}

export default App;
