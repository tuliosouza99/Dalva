import axios from 'axios';
import { useQuery, useInfiniteQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { UseQueryOptions } from '@tanstack/react-query';

// Types
export interface Project {
  id: number;
  name: string;
  project_id: string;
  created_at: string;
  updated_at: string;
  total_runs?: number;
  running_runs?: number;
  completed_runs?: number;
  failed_runs?: number;
}

export interface Run {
  id: number;
  project_id: number;
  run_id: string;
  name: string | null;
  group_name: string | null;
  tags: string | null;
  state: 'running' | 'completed' | 'failed';
  fork_from: number | null;
  created_at: string;
  updated_at: string;
}

export interface RunSummary extends Run {
  metrics: Record<string, unknown>;
  config: Record<string, unknown>;
}

export interface RunsListResponse {
  runs: Run[];
  total: number;
  has_more: boolean;
}

export interface MetricValue {
  step: number | null;
  timestamp: string | null;
  value: number | string | boolean;
  attribute_type?: string;
}

export interface MetricValuesResponse {
  data: MetricValue[];
  has_more: boolean;
  attribute_type?: string;
}

export interface MetricInfo {
  path: string;
  attribute_type: string;
}

export interface RunFilters {
  project_id?: number;
  group?: string;
  state?: string;
  search?: string;
  tags?: string;  // Comma-separated tags
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

export interface CustomView {
  id: number;
  project_id: number;
  name: string;
  filters: string | null;  // JSON string
  columns: string | null;  // JSON string
  sort_by: string | null;  // JSON string
  created_at: string;
}

export interface CustomViewCreate {
  name: string;
  filters?: string | null;
  columns?: string | null;
  sort_by?: string | null;
}

// Table types
export interface ColumnSchema {
  name: string;
  type: 'int' | 'float' | 'bool' | 'str' | 'date' | 'list' | 'dict';
}

export interface DalvaTable {
  id: number;
  project_id: number;
  table_id: string;
  name: string | null;
  run_id: number | null;
  log_mode: 'IMMUTABLE' | 'MUTABLE' | 'INCREMENTAL';
  version: number;
  row_count: number;
  column_schema: string;  // JSON string
  config: string | null;  // JSON string
  state: 'active' | 'finished';
  created_at: string;
  updated_at: string;
}

export interface TableListResponse {
  tables: DalvaTable[];
  total: number;
  has_more: boolean;
}

export interface TableDataResponse {
  rows: Record<string, unknown>[];
  total: number;
  column_schema: ColumnSchema[];
  has_more: boolean;
}

export interface TableFilters {
  project_id?: number;
  run_id?: number;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

export interface ColumnFilter {
  column: string;
  op: 'between' | 'contains' | 'eq';
  min?: number;
  max?: number;
  value?: unknown;
}

export interface NumericBin {
  start: number;
  end: number;
  count: number;
}

export interface NumericStats {
  type: 'numeric';
  min: number | null;
  max: number | null;
  bins: NumericBin[];
  null_count: number;
}

export interface BoolStats {
  type: 'bool';
  counts: { true: number; false: number };
  null_count: number;
}

export interface StringTopValue {
  value: string;
  count: number;
}

export interface StringStats {
  type: 'string';
  top_values: StringTopValue[];
  unique_count: number;
  null_count: number;
}

export interface SkippedStats {
  type: 'date' | 'list' | 'dict';
  null_count: number;
}

export type ColumnStats = NumericStats | BoolStats | StringStats | SkippedStats;

export interface TableStatsResponse {
  columns: Record<string, ColumnStats>;
}

// API Client
const apiClient = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

// API functions
export const api = {
  // Projects
  getProjects: async (): Promise<Project[]> => {
    const { data } = await apiClient.get('/projects/');
    return data;
  },

  getProject: async (projectId: number): Promise<Project> => {
    const { data } = await apiClient.get(`/projects/${projectId}`);
    return data;
  },

  getProjectTags: async (projectId: number): Promise<string[]> => {
    const { data } = await apiClient.get(`/projects/${projectId}/tags`);
    return data;
  },

  getAvailableColumns: async (projectId: number): Promise<string[]> => {
    const { data } = await apiClient.get(`/projects/${projectId}/available-columns`);
    return data;
  },

  // Runs
  getRuns: async (filters: RunFilters & { limit?: number; offset?: number }): Promise<RunsListResponse> => {
    const { data } = await apiClient.get('/runs/', { params: filters });
    return data;
  },

  getRun: async (runId: number): Promise<Run> => {
    const { data } = await apiClient.get(`/runs/${runId}`);
    return data;
  },

  getRunSummary: async (runId: number): Promise<RunSummary> => {
    const { data } = await apiClient.get(`/runs/${runId}/summary`);
    return data;
  },

  // Metrics
  getRunMetrics: async (runId: number): Promise<MetricInfo[]> => {
    const { data} = await apiClient.get(`/metrics/runs/${runId}`);
    return data;
  },

  getMetricValues: async (
    runId: number,
    metricPath: string,
    params?: { limit?: number; offset?: number; step_min?: number; step_max?: number }
  ): Promise<MetricValuesResponse> => {
    const { data } = await apiClient.get(`/metrics/runs/${runId}/metric/${metricPath}`, { params });
    return data;
  },

  compareMetrics: async (runIds: number[], metricPaths: string[]) => {
    const { data } = await apiClient.post('/metrics/compare', { run_ids: runIds, metric_paths: metricPaths });
    return data;
  },

  getSummaryMetrics: async (runIds: number[], metricPaths: string[]): Promise<Record<string, Record<string, number | string | boolean | null>>> => {
    const { data } = await apiClient.post('/metrics/summary', {
      run_ids: runIds,
      metric_paths: metricPaths
    });
    return data;
  },

  // Custom Views
  getCustomViews: async (projectId: number): Promise<CustomView[]> => {
    const { data } = await apiClient.get(`/views/projects/${projectId}/views`);
    return data;
  },

  createCustomView: async (projectId: number, view: CustomViewCreate): Promise<CustomView> => {
    const { data } = await apiClient.post(`/views/projects/${projectId}/views`, view);
    return data;
  },

  updateCustomView: async (viewId: number, view: CustomViewCreate): Promise<CustomView> => {
    const { data } = await apiClient.put(`/views/views/${viewId}`, view);
    return data;
  },

  deleteCustomView: async (viewId: number): Promise<void> => {
    await apiClient.delete(`/views/views/${viewId}`);
  },

  // Delete
  deleteProject: async (projectId: number): Promise<void> => {
    await apiClient.delete(`/projects/${projectId}`);
  },

  deleteRun: async (runId: number): Promise<void> => {
    await apiClient.delete(`/runs/${runId}`);
  },

  // Tables
  getTables: async (filters: TableFilters & { limit?: number; offset?: number }): Promise<TableListResponse> => {
    const { data } = await apiClient.get('/tables/', { params: filters });
    return data;
  },

  getTable: async (tableId: number): Promise<DalvaTable> => {
    const { data } = await apiClient.get(`/tables/${tableId}`);
    return data;
  },

  getTableData: async (
    tableId: number,
    params?: { version?: number; limit?: number; offset?: number; sort_by?: string; sort_order?: 'asc' | 'desc'; filters?: ColumnFilter[] }
  ): Promise<TableDataResponse> => {
    const queryParams: Record<string, string> = {};
    if (params?.version !== undefined) queryParams.version = String(params.version);
    if (params?.limit !== undefined) queryParams.limit = String(params.limit);
    if (params?.offset !== undefined) queryParams.offset = String(params.offset);
    if (params?.sort_by) queryParams.sort_by = params.sort_by;
    if (params?.sort_order) queryParams.sort_order = params.sort_order;
    if (params?.filters && params.filters.length > 0) queryParams.filters = JSON.stringify(params.filters);
    const { data } = await apiClient.get(`/tables/${tableId}/data`, { params: queryParams });
    return data;
  },

  getTableStats: async (
    tableId: number,
    params?: { version?: number; filters?: ColumnFilter[] }
  ): Promise<TableStatsResponse> => {
    const queryParams: Record<string, string> = {};
    if (params?.version !== undefined) queryParams.version = String(params.version);
    if (params?.filters && params.filters.length > 0) queryParams.filters = JSON.stringify(params.filters);
    const { data } = await apiClient.get(`/tables/${tableId}/stats`, { params: queryParams });
    return data;
  },

  getTablesForRun: async (runId: number): Promise<DalvaTable[]> => {
    const { data } = await apiClient.get(`/runs/${runId}/tables`);
    return data;
  },

  deleteTable: async (tableId: number): Promise<void> => {
    await apiClient.delete(`/tables/${tableId}`);
  },

  updateTableState: async (tableId: number, state: string): Promise<{ state: string }> => {
    const { data } = await apiClient.patch(`/tables/${tableId}/state`, null, { params: { state } });
    return data;
  },

  updateRunState: async (runId: number, state: string): Promise<Run> => {
    const { data } = await apiClient.patch(`/runs/${runId}/state`, null, { params: { state } });
    return data;
  },
};

// React Query Hooks
export function useProjects(options?: Omit<UseQueryOptions<Project[], Error>, 'queryKey' | 'queryFn'>) {
  return useQuery({
    queryKey: ['projects'],
    queryFn: api.getProjects,
    ...options,
  });
}

export function useProject(projectId: number, options?: Omit<UseQueryOptions<Project, Error>, 'queryKey' | 'queryFn'>) {
  return useQuery({
    queryKey: ['projects', projectId],
    queryFn: () => api.getProject(projectId),
    enabled: !!projectId,
    ...options,
  });
}

export function useProjectTags(projectId: number, options?: Omit<UseQueryOptions<string[], Error>, 'queryKey' | 'queryFn'>) {
  return useQuery({
    queryKey: ['projects', projectId, 'tags'],
    queryFn: () => api.getProjectTags(projectId),
    enabled: !!projectId,
    ...options,
  });
}

export function useAvailableColumns(projectId: number, options?: Omit<UseQueryOptions<string[], Error>, 'queryKey' | 'queryFn'>) {
  return useQuery({
    queryKey: ['projects', projectId, 'available-columns'],
    queryFn: () => api.getAvailableColumns(projectId),
    enabled: !!projectId,
    ...options,
  });
}

export function useRuns(
  filters: RunFilters,
  options?: Omit<UseQueryOptions<RunsListResponse, Error>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: ['runs', filters],
    queryFn: () => api.getRuns({ ...filters, limit: 100 }),
    ...options,
  });
}

export function useInfiniteRuns(filters: RunFilters) {
  return useInfiniteQuery({
    queryKey: ['runs', 'infinite', filters],
    queryFn: ({ pageParam = 0 }) =>
      api.getRuns({ ...filters, limit: 50, offset: pageParam as number }),
    getNextPageParam: (lastPage, allPages) => {
      if (!lastPage.has_more) return undefined;
      return allPages.reduce((sum, page) => sum + page.runs.length, 0);
    },
    initialPageParam: 0,
  });
}

export function useRun(runId: number, options?: Omit<UseQueryOptions<Run, Error>, 'queryKey' | 'queryFn'>) {
  return useQuery({
    queryKey: ['runs', runId],
    queryFn: () => api.getRun(runId),
    enabled: !!runId,
    ...options,
  });
}

export function useRunSummary(runId: number, options?: Omit<UseQueryOptions<RunSummary, Error>, 'queryKey' | 'queryFn'>) {
  return useQuery({
    queryKey: ['runs', runId, 'summary'],
    queryFn: () => api.getRunSummary(runId),
    enabled: !!runId,
    ...options,
  });
}

export function useRunMetrics(runId: number, options?: Omit<UseQueryOptions<MetricInfo[], Error>, 'queryKey' | 'queryFn'>) {
  return useQuery({
    queryKey: ['metrics', runId],
    queryFn: () => api.getRunMetrics(runId),
    enabled: !!runId,
    ...options,
  });
}

export function useMetricValues(
  runId: number,
  metricPath: string,
  options?: Omit<UseQueryOptions<MetricValuesResponse, Error>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: ['metrics', runId, metricPath],
    queryFn: () => api.getMetricValues(runId, metricPath),
    enabled: !!runId && !!metricPath,
    ...options,
  });
}

export function useCustomViews(projectId: number, options?: Omit<UseQueryOptions<CustomView[], Error>, 'queryKey' | 'queryFn'>) {
  return useQuery({
    queryKey: ['custom-views', projectId],
    queryFn: () => api.getCustomViews(projectId),
    enabled: !!projectId,
    ...options,
  });
}

export function useCreateCustomView(projectId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (view: CustomViewCreate) => api.createCustomView(projectId, view),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['custom-views', projectId] });
    },
  });
}

export function useUpdateCustomView(projectId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ viewId, view }: { viewId: number; view: CustomViewCreate }) =>
      api.updateCustomView(viewId, view),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['custom-views', projectId] });
    },
  });
}

export function useDeleteCustomView(projectId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (viewId: number) => api.deleteCustomView(viewId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['custom-views', projectId] });
    },
  });
}

export function useDeleteProject() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (projectId: number) => api.deleteProject(projectId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] });
    },
  });
}

export function useDeleteRun() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (runId: number) => api.deleteRun(runId),
    onSuccess: (_data, runId) => {
      queryClient.invalidateQueries({ queryKey: ['runs'] });
      queryClient.removeQueries({ queryKey: ['runs', runId] });
    },
  });
}

// Table hooks
export function useTables(
  filters: TableFilters,
  options?: Omit<UseQueryOptions<TableListResponse, Error>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: ['tables', filters],
    queryFn: () => api.getTables({ ...filters, limit: 100 }),
    staleTime: 0,
    ...options,
  });
}

export function useTable(tableId: number, options?: Omit<UseQueryOptions<DalvaTable, Error>, 'queryKey' | 'queryFn'>) {
  return useQuery({
    queryKey: ['tables', tableId],
    queryFn: () => api.getTable(tableId),
    enabled: !!tableId,
    ...options,
  });
}

export function useTableData(
  tableId: number,
  params?: { version?: number; limit?: number; offset?: number; sort_by?: string; sort_order?: 'asc' | 'desc'; filters?: ColumnFilter[] },
  options?: Omit<UseQueryOptions<TableDataResponse, Error>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: ['tables', tableId, 'data', params],
    queryFn: () => api.getTableData(tableId, params),
    enabled: !!tableId,
    ...options,
  });
}

export function useTableStats(
  tableId: number,
  params?: { version?: number; filters?: ColumnFilter[] },
  options?: Omit<UseQueryOptions<TableStatsResponse, Error>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: ['tables', tableId, 'stats', params],
    queryFn: () => api.getTableStats(tableId, params),
    enabled: !!tableId,
    staleTime: 30_000,
    ...options,
  });
}

export function useTablesForRun(runId: number, options?: Omit<UseQueryOptions<DalvaTable[], Error>, 'queryKey' | 'queryFn'>) {
  return useQuery({
    queryKey: ['runs', runId, 'tables'],
    queryFn: () => api.getTablesForRun(runId),
    enabled: !!runId,
    ...options,
  });
}

export function useDeleteTable() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (tableId: number) => api.deleteTable(tableId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tables'] });
    },
  });
}

export function useUpdateTableState() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ tableId, state }: { tableId: number; state: string }) =>
      api.updateTableState(tableId, state),
    onSuccess: (_data, { tableId }) => {
      queryClient.invalidateQueries({ queryKey: ['tables'] });
      queryClient.invalidateQueries({ queryKey: ['tables', tableId] });
      queryClient.invalidateQueries({ queryKey: ['runs'] });
    },
  });
}

export function useUpdateRunState() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ runId, state }: { runId: number; state: string }) =>
      api.updateRunState(runId, state),
    onSuccess: (_data, { runId }) => {
      queryClient.invalidateQueries({ queryKey: ['runs'] });
      queryClient.invalidateQueries({ queryKey: ['runs', runId] });
    },
  });
}
