import { useParams, useNavigate, useSearchParams } from "react-router-dom";
import { useState, useCallback } from "react";
import { useDebounce } from "../hooks/useDebounce";
import {
  useTable,
  useTableData,
  useTableStats,
  useRun,
  useProject,
  useDeleteTable,
  useUpdateTableState,
  useRemoveAllRows,
} from "../api/client";
import type { ColumnFilter } from "../api/client";
import {
  Link2,
  ChevronLeft,
  ChevronRight,
  Trash2,
  Table2,
  FilterX,
  Code,
} from "lucide-react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import ColumnHeader from "../components/DataTable/ColumnHeader";

const darkTheme = {
  'code[class*="language-"]': { color: "#f0f0f0", background: "none" },
  'pre[class*="language-"]': { color: "#f0f0f0", background: "#1a1a1a" },
  comment: { color: "#6b6b6b" },
  prolog: { color: "#6b6b6b" },
  doctype: { color: "#6b6b6b" },
  cdata: { color: "#6b6b6b" },
  punctuation: { color: "#f0f0f0" },
  property: { color: "#f0b429" },
  tag: { color: "#f0b429" },
  boolean: { color: "#e57373" },
  number: { color: "#e57373" },
  constant: { color: "#e57373" },
  symbol: { color: "#e57373" },
  deleted: { color: "#e57373" },
  selector: { color: "#81c784" },
  "attr-name": { color: "#81c784" },
  string: { color: "#81c784" },
  char: { color: "#81c784" },
  builtin: { color: "#81c784" },
  inserted: { color: "#81c784" },
  operator: { color: "#f0f0f0" },
  entity: { color: "#f0b429" },
  url: { color: "#81c784" },
  variable: { color: "#f0f0f0" },
  atrule: { color: "#81c784" },
  "attr-value": { color: "#81c784" },
  function: { color: "#64b5f6" },
  "class-name": { color: "#64b5f6" },
  keyword: { color: "#ce93d8" },
  regex: { color: "#e57373" },
  important: { color: "#e57373", fontWeight: "bold" },
  bold: { fontWeight: "bold" },
  italic: { fontStyle: "italic" },
};

const lightTheme = {
  'code[class*="language-"]': { color: "#1a1a1a", background: "none" },
  'pre[class*="language-"]': { color: "#1a1a1a", background: "#f5f4f2" },
  comment: { color: "#6b6b6b" },
  prolog: { color: "#6b6b6b" },
  doctype: { color: "#6b6b6b" },
  cdata: { color: "#6b6b6b" },
  punctuation: { color: "#1a1a1a" },
  property: { color: "#b8890f" },
  tag: { color: "#b8890f" },
  boolean: { color: "#c45a3b" },
  number: { color: "#c45a3b" },
  constant: { color: "#c45a3b" },
  symbol: { color: "#c45a3b" },
  deleted: { color: "#c45a3b" },
  selector: { color: "#4a9c6d" },
  "attr-name": { color: "#4a9c6d" },
  string: { color: "#4a9c6d" },
  char: { color: "#4a9c6d" },
  builtin: { color: "#4a9c6d" },
  inserted: { color: "#4a9c6d" },
  operator: { color: "#1a1a1a" },
  entity: { color: "#b8890f" },
  url: { color: "#4a9c6d" },
  variable: { color: "#1a1a1a" },
  atrule: { color: "#4a9c6d" },
  "attr-value": { color: "#4a9c6d" },
  function: { color: "#3b7fc4" },
  "class-name": { color: "#3b7fc4" },
  keyword: { color: "#9b59b6" },
  regex: { color: "#c45a3b" },
  important: { color: "#c45a3b", fontWeight: "bold" },
  bold: { fontWeight: "bold" },
  italic: { fontStyle: "italic" },
};

export default function TableDetailPage() {
  const { tableId } = useParams<{ tableId: string }>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const tableIdNum = parseInt(tableId || "0");
  const projectId = searchParams.get("project");

  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(50);
  const [sortBy, setSortBy] = useState<string | null>(null);
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("asc");
  const [filters, setFilters] = useState<ColumnFilter[]>([]);
  const [showCodeWidget, setShowCodeWidget] = useState(false);
  const [copied, setCopied] = useState(false);
  const [isDark, setIsDark] = useState(() =>
    typeof document !== "undefined" &&
    document.documentElement.classList.contains("dark")
  );

  useEffect(() => {
    const observer = new MutationObserver(() => {
      setIsDark(document.documentElement.classList.contains("dark"));
    });
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["class"],
    });
    return () => observer.disconnect();
  }, []);

  const debouncedFilters = useDebounce(filters, 400);

  const { data: table, isLoading: tableLoading } = useTable(tableIdNum);
  const { data: tableData, isLoading: dataLoading } = useTableData(tableIdNum, {
    limit: pageSize,
    offset: page * pageSize,
    sort_by: sortBy || undefined,
    sort_order: sortOrder,
    filters: filters.length > 0 ? filters : undefined,
  });
  const { data: tableStats } = useTableStats(tableIdNum, {
    filters: debouncedFilters.length > 0 ? debouncedFilters : undefined,
  });
  const deleteTableMutation = useDeleteTable();
  const updateTableStateMutation = useUpdateTableState();
  const removeAllRowsMutation = useRemoveAllRows();

  const { data: linkedRun } = useRun(table?.run_id || 0);
  const { data: project } = useProject(table?.project_id || 0);

  const totalPages = Math.ceil((tableData?.total || 0) / pageSize);
  const activeFilterCount = filters.length;

  const handleSort = (column: string) => {
    if (sortBy === column) {
      setSortOrder(sortOrder === "asc" ? "desc" : "asc");
    } else {
      setSortBy(column);
      setSortOrder("asc");
    }
    setPage(0);
  };

  const handleColumnFilter = useCallback(
    (filter: ColumnFilter | undefined, columnName?: string) => {
      setFilters((prev) => {
        const col = filter?.column ?? columnName ?? "";
        const without = prev.filter((f) => f.column !== col);
        if (filter) {
          return [...without, filter];
        }
        return without;
      });
      setPage(0);
    },
    [],
  );

  const clearAllFilters = () => {
    setFilters([]);
    setPage(0);
  };

  const getColumnFilter = (colName: string): ColumnFilter | undefined => {
    return filters.find((f) => f.column === colName);
  };

  const renderCellValue = (value: unknown, type: string): React.ReactNode => {
    if (value === null || value === undefined)
      return <span style={{ color: "var(--text-tertiary)" }}>-</span>;
    if (type === "list" || type === "dict") {
      try {
        return (
          <span
            className="mono text-xs px-1.5 py-0.5 rounded"
            style={{
              backgroundColor: "var(--bg-elevated)",
              color: "var(--text-secondary)",
            }}
          >
            {JSON.stringify(value)}
          </span>
        );
      } catch {
        return String(value);
      }
    }
    if (type === "date") {
      return new Date(String(value)).toLocaleString();
    }
    if (type === "int" || type === "float") {
      return <span className="mono">{String(value)}</span>;
    }
    return String(value);
  };

  const handleDelete = async () => {
    if (confirm("Delete this table? This cannot be undone.")) {
      await deleteTableMutation.mutateAsync(tableIdNum);
      navigate(`/projects/${projectId}/tables`);
    }
  };

  const handleLinkedRunClick = () => {
    if (linkedRun) {
      navigate(`/runs/${linkedRun.id}?project=${projectId}`);
    }
  };

  if (tableLoading) {
    return (
      <div className="p-8 page-enter">
        <div className="mb-6">
          <div className="skeleton h-8 w-48 rounded-md mb-2"></div>
          <div className="skeleton h-4 w-32 rounded"></div>
        </div>
        <div className="space-y-4">
          <div className="skeleton h-32 rounded-lg"></div>
          <div className="skeleton h-64 rounded-lg"></div>
        </div>
      </div>
    );
  }

  if (!table) {
    return (
      <div className="p-8 page-enter">
        <div
          className="card p-6"
          style={{
            backgroundColor: "rgba(239, 68, 68, 0.08)",
            borderColor: "rgba(239, 68, 68, 0.2)",
          }}
        >
          <h3
            className="font-semibold mb-1"
            style={{ color: "var(--badge-failed)" }}
          >
            Table not found
          </h3>
          <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
            The requested table does not exist.
          </p>
        </div>
      </div>
    );
  }

  const columns = tableData?.column_schema || [];

  return (
    <div className="p-8 page-enter">
      <div className="mb-6">
        <div
          className="flex items-center gap-2 text-sm mb-3"
          style={{ color: "var(--text-tertiary)" }}
        >
          <button
            onClick={() => navigate("/projects")}
            className="hover:text-[var(--accent)] transition-colors"
          >
            Projects
          </button>
          <span>/</span>
          <button
            onClick={() => navigate(`/projects/${table.project_id}/tables`)}
            className="hover:text-[var(--accent)] transition-colors"
          >
            {project?.name}
          </button>
          <span>/</span>
          <span style={{ color: "var(--text-primary)" }}>{table.table_id}</span>
        </div>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="heading-display">{table.name || table.table_id}</h1>
            <p className="mt-1">
              <span
                className="mono text-sm"
                style={{ color: "var(--accent-hover)" }}
              >
                {table.table_id}
              </span>
              {table.name && (
                <span
                  className="ml-3 text-sm"
                  style={{ color: "var(--text-secondary)" }}
                >
                  {table.name}
                </span>
              )}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => {
                const newState =
                  table.state === "active" ? "finished" : "active";
                updateTableStateMutation.mutate({
                  tableId: table.id,
                  state: newState,
                });
              }}
              disabled={updateTableStateMutation.isPending}
              className={`badge cursor-pointer transition-opacity hover:opacity-80 ${
                table.state === "active" ? "badge-running" : "badge-completed"
              }`}
              title={`Click to mark as ${table.state === "active" ? "finished" : "active"}`}
            >
              {table.state === "active" && <span className="pulse-dot" />}
              {table.state.charAt(0).toUpperCase() + table.state.slice(1)}
            </button>
            <button
              onClick={handleDelete}
              disabled={deleteTableMutation.isPending}
              className="btn-secondary text-sm"
              style={{ color: "#ef4444" }}
              title="Delete this table"
            >
              {deleteTableMutation.isPending ? (
                "Deleting…"
              ) : (
                <>
                  <Trash2 size={14} />
                  Delete
                </>
              )}
            </button>
            <button
              onClick={async () => {
                if (
                  !confirm(
                    `Remove all ${tableData?.total ?? table.row_count} rows from this table?`,
                  )
                )
                  return;
                await removeAllRowsMutation.mutateAsync(table.id);
              }}
              disabled={removeAllRowsMutation.isPending}
              className="btn-secondary text-sm"
              title="Remove all rows from this table"
            >
              {removeAllRowsMutation.isPending ? (
                "Removing…"
              ) : (
                <>
                  <Trash2 size={14} />
                  Remove All Rows
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6 card-stagger">
        <div className="card card-appear">
          <dt className="text-small">Version</dt>
          <dd
            className="text-lg font-semibold mt-1"
            style={{ color: "var(--text-primary)" }}
          >
            {table.version}
          </dd>
        </div>
        <div className="card card-appear">
          <dt className="text-small">Rows</dt>
          <dd
            className="text-lg font-semibold mt-1"
            style={{ color: "var(--text-primary)" }}
          >
            {(tableData?.total ?? table.row_count).toLocaleString()}
          </dd>
        </div>
        <div className="card card-appear">
          <dt className="text-small">Created</dt>
          <dd className="text-sm mt-1" style={{ color: "var(--text-primary)" }}>
            {new Date(table.created_at).toLocaleString()}
          </dd>
        </div>
      </div>

      {linkedRun && (
        <div className="mb-6">
          <button
            onClick={handleLinkedRunClick}
            className="card flex items-center gap-3 hover:shadow-md transition-shadow cursor-pointer"
            style={{ padding: "12px 16px" }}
          >
            <Link2 size={16} style={{ color: "var(--accent)" }} />
            <span
              className="text-sm"
              style={{ color: "var(--text-secondary)" }}
            >
              Linked Run:
            </span>
            <span
              className="mono text-sm font-medium"
              style={{ color: "var(--accent-hover)" }}
            >
              {linkedRun.run_id}
            </span>
            <span
              className="text-sm"
              style={{ color: "var(--text-secondary)" }}
            >
              {linkedRun.name || "unnamed"}
            </span>
          </button>
        </div>
      )}

      <div
        className="card mb-4"
        style={{ padding: "12px 16px", backgroundColor: "var(--bg-elevated)" }}
      >
        <button
          onClick={() => setShowCodeWidget(!showCodeWidget)}
          className="w-full flex items-center justify-between"
        >
          <div className="flex items-center gap-2">
            <Code size={14} style={{ color: "var(--accent)" }} />
            <span
              className="text-sm font-medium"
              style={{ color: "var(--text-primary)" }}
            >
              Load to Python
            </span>
          </div>
          <span style={{ color: "var(--text-tertiary)" }}>
            {showCodeWidget ? "▲" : "▼"}
          </span>
        </button>
        {showCodeWidget && (
          <div className="mt-3">
            <div className="flex items-center gap-3">
              <button
                onClick={() => {
                  const code = `import dalva

table = dalva.table(
    project="${project?.name || ""}",
    resume_from="${table.table_id}",
)
rows = table.get_table()`;
                  navigator.clipboard.writeText(code);
                  setCopied(true);
                  setTimeout(() => setCopied(false), 2000);
                }}
                className="text-xs px-2 py-1 rounded border transition-colors hover:border-[var(--accent)]"
                style={{
                  borderColor: "var(--border)",
                  color: copied ? "var(--accent)" : "var(--text-secondary)",
                  backgroundColor: "var(--bg-surface)",
                }}
              >
                {copied ? "Copied!" : "Copy code"}
              </button>
            </div>
            <SyntaxHighlighter
              language="python"
              style={isDark ? darkTheme : lightTheme}
              customStyle={{
                marginTop: "8px",
                borderRadius: "6px",
                fontSize: "12px",
                padding: "12px",
              }}
            >
              {`import dalva

table = dalva.table(
    project="${project?.name || ""}",
    resume_from="${table.table_id}",
)
rows = table.get_table()`}
            </SyntaxHighlighter>
          </div>
        )}
      </div>

      <div className="card" style={{ padding: 0, overflow: "hidden" }}>
        <div
          className="flex items-center justify-between px-4 py-3 border-b"
          style={{ borderColor: "var(--border)" }}
        >
          <div className="flex items-center gap-2">
            <Table2 size={16} style={{ color: "var(--text-tertiary)" }} />
            <span
              className="text-sm font-medium"
              style={{ color: "var(--text-primary)" }}
            >
              Data
            </span>
            <span className="text-xs" style={{ color: "var(--text-tertiary)" }}>
              {tableData?.total ?? 0} rows
            </span>
            {activeFilterCount > 0 && (
              <span
                className="text-xs px-1.5 py-0.5 rounded"
                style={{
                  backgroundColor: "var(--accent-muted)",
                  color: "var(--accent)",
                }}
              >
                {activeFilterCount} filter{activeFilterCount > 1 ? "s" : ""}
              </span>
            )}
          </div>
          <div className="flex items-center gap-4">
            {activeFilterCount > 0 && (
              <button
                onClick={clearAllFilters}
                className="flex items-center gap-1 text-xs px-2 py-1 rounded border transition-colors"
                style={{
                  borderColor: "var(--border)",
                  color: "var(--text-secondary)",
                }}
                onMouseEnter={(e) =>
                  (e.currentTarget.style.borderColor = "var(--accent)")
                }
                onMouseLeave={(e) =>
                  (e.currentTarget.style.borderColor = "var(--border)")
                }
              >
                <FilterX size={11} />
                Clear
              </button>
            )}
            <div className="flex items-center gap-2">
              <span
                className="text-xs"
                style={{ color: "var(--text-tertiary)" }}
              >
                Per page:
              </span>
              <select
                value={pageSize}
                onChange={(e) => {
                  setPageSize(Number(e.target.value));
                  setPage(0);
                }}
                className="text-xs px-2 py-1 rounded border"
                style={{
                  backgroundColor: "var(--bg-surface)",
                  borderColor: "var(--border)",
                  color: "var(--text-primary)",
                }}
              >
                <option value={25}>25</option>
                <option value={50}>50</option>
                <option value={100}>100</option>
              </select>
            </div>
            <div className="flex items-center gap-1">
              <button
                onClick={() => setPage((p) => Math.max(0, p - 1))}
                disabled={page === 0}
                className="p-1 rounded hover:bg-[var(--bg-elevated)] disabled:opacity-30 transition-colors"
                style={{ color: "var(--text-secondary)" }}
              >
                <ChevronLeft size={16} />
              </button>
              <span
                className="text-xs"
                style={{ color: "var(--text-secondary)" }}
              >
                {page + 1} / {totalPages || 1}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
                disabled={page >= totalPages - 1}
                className="p-1 rounded hover:bg-[var(--bg-elevated)] disabled:opacity-30 transition-colors"
                style={{ color: "var(--text-secondary)" }}
              >
                <ChevronRight size={16} />
              </button>
            </div>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full min-w-[600px]">
            <thead>
              <tr>
                {columns.map((col) => (
                  <ColumnHeader
                    key={col.name}
                    column={col}
                    stats={tableStats?.columns[col.name]}
                    sortBy={sortBy}
                    sortOrder={sortOrder}
                    filter={getColumnFilter(col.name)}
                    onSort={handleSort}
                    onFilter={handleColumnFilter}
                  />
                ))}
              </tr>
            </thead>
            <tbody>
              {dataLoading ? (
                <tr>
                  <td
                    colSpan={columns.length}
                    className="px-4 py-16 text-center"
                  >
                    <div className="text-body">Loading data...</div>
                  </td>
                </tr>
              ) : (tableData?.rows.length ?? 0) === 0 ? (
                <tr>
                  <td
                    colSpan={columns.length}
                    className="px-4 py-16 text-center"
                  >
                    <Table2
                      size={32}
                      className="mx-auto mb-3"
                      style={{ color: "var(--text-tertiary)" }}
                    />
                    <p className="text-body">
                      {activeFilterCount > 0
                        ? "No rows match filters"
                        : "No data in this table"}
                    </p>
                    {activeFilterCount > 0 && (
                      <button
                        onClick={clearAllFilters}
                        className="mt-2 text-sm underline"
                        style={{ color: "var(--accent)" }}
                      >
                        Clear all filters
                      </button>
                    )}
                  </td>
                </tr>
              ) : (
                tableData?.rows.map((row, idx) => (
                  <tr key={idx} className="table-row">
                    {columns.map((col) => (
                      <td
                        key={col.name}
                        className="px-4 py-2.5 text-sm"
                        style={{ color: "var(--text-primary)" }}
                      >
                        {renderCellValue(row[col.name], col.type)}
                      </td>
                    ))}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
