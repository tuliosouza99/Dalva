# Architecture

This document describes Dalva's internal architecture.

## System Overview

Dalva is a full-stack application with:

- **Backend**: FastAPI + SQLAlchemy + DuckDB
- **Frontend**: React + TypeScript + Vite
- **Database**: DuckDB (SQLite-like, file-based)

```mermaid
graph TB
subgraph SDK["Python SDK"]
sdk_run[Run Class]
sdk_table[Table Class]
end
sdk_run -->|HTTP POST| api[REST API]
sdk_table -->|HTTP POST| api
subgraph FE["Frontend - React"]
fe_proj[Projects Page]
fe_runs[Runs Page]
fe_tables[Tables Page]
fe_metrics[Metrics Charts]
fe_compare[Compare Runs Page]
end
FE --> rq[React Query Cache]
rq --> api
subgraph BE["Backend - FastAPI"]
routes[API Routes]
logger[Logger Functions]
end
api --> routes
routes --> logger
logger --> db[(DuckDB)]
db --> tbl_projects[projects]
db --> tbl_runs[runs]
db --> tbl_metrics[metrics]
db --> tbl_configs[configs]
db --> tbl_dalva_tables[dalva_tables]
db --> tbl_dalva_rows[dalva_table_rows]
```

## Backend Architecture

### Key Design Decisions

#### 1. Short-Lived Sessions (DuckDB Compatibility)

DuckDB allows **one writer per file** across OS processes. The old design held sessions open during training, blocking the web server.

**Solution**: Every logger function opens a fresh session, writes, commits, and closes immediately:

```python
def log_metrics(run_id, metrics, step=None):
    with session_scope() as db:  # Opens session
        for metric_path, value in metrics.items():
            db.add(Metric(...))
    # Session automatically closed here
```

#### 2. EAV Model for Metrics

The `Metric` table uses an Entity-Attribute-Value model for flexibility:

```sql
CREATE TABLE metrics (
    id INTEGER PRIMARY KEY,
    run_id INTEGER REFERENCES runs(id),
    attribute_path TEXT,      -- e.g., "train/loss"
    attribute_type TEXT,     -- e.g., "float_series"
    step INTEGER,            -- NULL for summary, int for series
    float_value REAL,
    int_value INTEGER,
    string_value TEXT,
    bool_value BOOLEAN
);
```

This allows logging arbitrary metrics without schema changes.

#### 3. Series vs Scalar Types via Step

The `step` parameter determines metric type:

| Step Value | Type Suffix | Example |
|------------|-------------|---------|
| `None` | (none) | `float`, `int`, `string`, `bool` |
| `0, 1, 2, ...` | `_series` | `float_series`, `int_series`, etc. |

This is enforced at write time - attempting to write a different type for the same metric key raises an error.

### Database Schema

```mermaid
erDiagram
    projects {
        int id PK
        string name
        string project_id
        datetime created_at
        datetime updated_at
    }
    
    runs {
        int id PK
        int project_id FK
        string run_id
        string name
        string state
        datetime created_at
        datetime updated_at
    }
    
    metrics {
        int id PK
        int run_id FK
        string attribute_path
        string attribute_type
        int step
        float float_value
        int int_value
        string string_value
        bool bool_value
    }
    
    configs {
        int id PK
        int run_id FK
        string key
        string value
    }
    
    dalva_tables {
        int id PK
        int project_id FK
        string table_id
        string name
        int run_id FK
        string log_mode
        int version
        int row_count
        string column_schema
        string state
        datetime created_at
        datetime updated_at
    }
    
    dalva_table_rows {
        int id PK
        int table_id FK
        int version
        string row_data
    }
    
    projects ||--o{ runs : "has"
    projects ||--o{ dalva_tables : "has"
    runs ||--o{ metrics : "logs"
    runs ||--o{ configs : "has"
    runs ||--o{ dalva_tables : "linked to"
    dalva_tables ||--o{ dalva_table_rows : "contains"
```

## Frontend Architecture

### Data Flow

```mermaid
sequenceDiagram
    User Action->>React Component: Click/Interact
    React Component->>React Query Hook: API call
    React Query Hook->>Backend: HTTP Request
    Backend->>Database: Query
    Database-->>Backend: Result
    Backend-->>React Query Hook: JSON Response
    React Query Hook-->>React Component: Data update
    React Component-->>User: Rendered UI
```

### React Query Configuration

```typescript
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,      // 30 seconds
      refetchOnWindowFocus: false,
    },
  },
});
```

### Chart Rendering Logic

The `MetricViewer` component decides how to render a metric based on its type:

```typescript
const isSeries = attributeType?.endsWith('_series') ?? false;

if (isSeries) {
  // Render interactive chart with Plotly
  return <MetricChart data={values} hasSteps={hasSteps} />;
} else {
  // Render single value card
  return <ValueCard value={values[0].value} />;
}
```
