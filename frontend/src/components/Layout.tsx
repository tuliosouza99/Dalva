import { Outlet, Link, NavLink, useLocation, useParams, useSearchParams } from 'react-router-dom';
import ThemeToggle from './ThemeToggle';
import { useProject } from '../api/client';
import { useComparison } from '../contexts/ComparisonContext';
import { Folder, FolderOpen, GitCompare, Table2, BarChart3 } from 'lucide-react';

export default function Layout() {
  const location = useLocation();
  const { projectId } = useParams<{ projectId: string }>();
  const [searchParams] = useSearchParams();
  
  // Get projectId from path param OR from query param (for compare page)
  const projectIdFromPath = projectId ? parseInt(projectId) : null;
  const projectIdFromQuery = searchParams.get('project');
  const effectiveProjectId = projectIdFromPath || (projectIdFromQuery ? parseInt(projectIdFromQuery) : null);
  
  // Check if we're in a project context
  const isOnProjectPage = location.pathname.includes('/projects/') && projectIdFromPath;
  const isRunPage = location.pathname.startsWith('/runs/');
  const isTableDetailPage = location.pathname.startsWith('/tables/');
  const isTablePage = isTableDetailPage || location.pathname.includes('/tables');
  const isComparePage = location.pathname === '/compare';
  const isCompareWithProject = isComparePage && projectIdFromQuery;
  const isRunWithProject = isRunPage && projectIdFromQuery;
  const isTableWithProject = isTableDetailPage && projectIdFromQuery;
  const isInProject = isOnProjectPage || isCompareWithProject || isRunWithProject || isTableWithProject;

  // Get comparison selection count
  const { selectedRunIds } = useComparison();
  const selectedCount = selectedRunIds.length;
  
  // Use projectId from path if available, otherwise use query param
  const { data: project } = useProject(effectiveProjectId || 0);

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header 
        className="border-b"
        style={{ backgroundColor: 'var(--bg-surface)', borderColor: 'var(--border)' }}
      >
        <div className="px-6 py-4">
          <div className="flex items-center justify-between">
            <Link to="/projects" className="flex items-center gap-3 group">
              <img src="/logo.svg" alt="Dalva Logo" className="w-8 h-8 transition-transform group-hover:scale-105" />
              <h1 
                className="text-2xl font-bold tracking-tight"
                style={{ color: 'var(--accent)' }}
              >
                Dalva
              </h1>
            </Link>
            <ThemeToggle />
          </div>
        </div>
      </header>

      {/* Main content */}
      <div className="flex-1 flex">
        {/* Sidebar */}
        <aside 
          className="w-56 flex flex-col"
          style={{ backgroundColor: 'var(--bg-surface)', borderColor: 'var(--border)', borderRight: '1px solid' }}
        >
          <nav className="flex-1 p-4">
            <div className="nav-section-label">Workspace</div>
            <div className="mt-1 space-y-1">
              {/* Projects Link */}
              <NavLink
                to="/projects"
                end
                className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
              >
                <Folder size={18} />
                Projects
              </NavLink>

              {/* Project Tree - shown when inside a project */}
              {isInProject && project && (
                <div className="ml-2 mt-1 space-y-1">
                  {/* Project Name Header */}
                  <div 
                    className="flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium"
                    style={{ color: 'var(--accent)' }}
                  >
                    <FolderOpen size={16} />
                    <span className="truncate">{project.name}</span>
                  </div>
                  
                  {/* Nested Project Items */}
                  <div className="ml-2 space-y-1">
                    {/* Runs */}
                    <NavLink
                      to={`/projects/${effectiveProjectId}/runs`}
                      className={() => `nav-item text-sm ${(isOnProjectPage && !isTablePage) || isRunPage ? 'active' : ''}`}
                      style={{ paddingLeft: '12px' }}
                    >
                      <BarChart3 size={14} />
                      Runs
                    </NavLink>

                    <NavLink
                      to={`/projects/${effectiveProjectId}/tables`}
                      className={() => `nav-item text-sm ${isTablePage ? 'active' : ''}`}
                      style={{ paddingLeft: '12px' }}
                    >
                      <Table2 size={14} />
                      Tables
                    </NavLink>
                    
                    {/* Compare */}
                    <NavLink
                      to={`/compare?project=${effectiveProjectId}`}
                      className={({ isActive }) => `nav-item text-sm ${isActive ? 'active' : ''}`}
                      style={{ paddingLeft: '12px' }}
                    >
                      <GitCompare size={14} />
                      <span className="flex-1 truncate">Compare Runs</span>
                      {selectedCount > 0 && (
                        <span 
                          className="text-xs px-1.5 py-0.5 rounded-full"
                          style={{ 
                            backgroundColor: 'var(--accent)',
                            color: 'var(--bg-surface)',
                            fontWeight: 600
                          }}
                        >
                          {selectedCount}
                        </span>
                      )}
                    </NavLink>
                  </div>
                </div>
              )}
            </div>
          </nav>
          
          {/* Sidebar footer */}
          <div 
            className="p-4 border-t"
            style={{ borderColor: 'var(--border)' }}
          >
            <div className="text-small">
              <span style={{ color: 'var(--text-tertiary)' }}>Experiment Tracker</span>
            </div>
          </div>
        </aside>

        {/* Page content */}
        <main 
          className="flex-1 overflow-auto"
          style={{ backgroundColor: 'var(--bg-primary)' }}
        >
          <Outlet />
        </main>
      </div>
    </div>
  );
}
