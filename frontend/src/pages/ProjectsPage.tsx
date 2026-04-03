import { useNavigate } from 'react-router-dom';
import { useProjects, useDeleteProject } from '../api/client';

function FolderIcon({ className = '' }: { className?: string }) {
  return (
    <svg className={className} width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 20h16a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.93a2 2 0 0 1-1.66-.9l-.82-1.2A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13c0 1.1.9 2 2 2Z"/>
    </svg>
  );
}

export default function ProjectsPage() {
  const navigate = useNavigate();
  const { data: projects, isLoading, error } = useProjects();
  const deleteProjectMutation = useDeleteProject();

  const handleDeleteProject = (projectId: number, projectName: string) => {
    if (!confirm(`Delete project "${projectName}" and ALL its runs? This cannot be undone.`)) return;
    deleteProjectMutation.mutate(projectId);
  };

  if (isLoading) {
    return (
      <div className="p-8 page-enter">
        <div className="mb-6">
          <div className="skeleton h-8 w-32 rounded-md mb-2"></div>
          <div className="skeleton h-4 w-24 rounded"></div>
        </div>
        <div className="space-y-3">
          <div className="skeleton h-32 rounded-lg"></div>
          <div className="skeleton h-32 rounded-lg"></div>
          <div className="skeleton h-32 rounded-lg"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8 page-enter">
        <div className="card p-6" style={{ backgroundColor: 'rgba(239, 68, 68, 0.08)', borderColor: 'rgba(239, 68, 68, 0.2)' }}>
          <h3 className="font-semibold mb-1" style={{ color: 'var(--badge-failed)' }}>Error loading projects</h3>
          <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>{error.message}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8 page-enter">
      <div className="mb-8">
        <h1 className="heading-display">Projects</h1>
        <p className="text-body mt-1">
          {projects?.length || 0} {projects?.length === 1 ? 'project' : 'projects'}
        </p>
      </div>

      {projects && projects.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 card-stagger">
          {projects.map((project) => (
            <div
              key={project.id}
              className="card card-appear group cursor-pointer"
              onClick={() => navigate(`/projects/${project.id}/runs`)}
            >
              <div className="flex items-start justify-between mb-3">
                <div>
                  <h3 className="heading-md mb-1 group-hover:text-[var(--accent)] transition-colors">
                    {project.name}
                  </h3>
                  <p className="mono text-small">
                    {project.project_id}
                  </p>
                </div>
                <div 
                  className="p-2 rounded-lg transition-colors"
                  style={{ backgroundColor: 'var(--accent-muted)', color: 'var(--accent)' }}
                >
                  <FolderIcon className="w-5 h-5" />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4 text-sm mb-4">
                <div>
                  <span className="text-small">Total Runs</span>
                  <p className="text-xl font-semibold" style={{ color: 'var(--text-primary)' }}>
                    {project.total_runs || 0}
                  </p>
                </div>
                <div>
                  <span className="text-small">Running</span>
                  <p className="text-xl font-semibold" style={{ color: '#22c55e' }}>
                    {project.running_runs || 0}
                  </p>
                </div>
                <div>
                  <span className="text-small">Completed</span>
                  <p className="text-xl font-semibold" style={{ color: 'var(--accent)' }}>
                    {project.completed_runs || 0}
                  </p>
                </div>
                <div>
                  <span className="text-small">Failed</span>
                  <p className="text-xl font-semibold" style={{ color: '#ef4444' }}>
                    {project.failed_runs || 0}
                  </p>
                </div>
              </div>

              <div 
                className="pt-4 border-t flex gap-2"
                style={{ borderColor: 'var(--border)' }}
                onClick={(e) => e.stopPropagation()}
              >
                <button
                  onClick={() => navigate(`/projects/${project.id}/runs`)}
                  className="btn-primary flex-1 text-sm"
                >
                  View Runs
                </button>
                <button
                  onClick={() => handleDeleteProject(project.id, project.name)}
                  disabled={deleteProjectMutation.isPending}
                  className="px-3 py-2 text-sm rounded-md border transition-colors"
                  style={{ borderColor: 'var(--border)', color: 'var(--text-secondary)' }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.backgroundColor = 'rgba(239, 68, 68, 0.08)';
                    e.currentTarget.style.borderColor = 'rgba(239, 68, 68, 0.3)';
                    e.currentTarget.style.color = '#ef4444';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.backgroundColor = 'transparent';
                    e.currentTarget.style.borderColor = 'var(--border)';
                    e.currentTarget.style.color = 'var(--text-secondary)';
                  }}
                  title="Delete project and all its runs"
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="3 6 5 6 21 6"/>
                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                    <line x1="10" y1="11" x2="10" y2="17"/>
                    <line x1="14" y1="11" x2="14" y2="17"/>
                  </svg>
                </button>
              </div>

              <div className="mt-3 text-xs" style={{ color: 'var(--text-tertiary)' }}>
                Updated {new Date(project.updated_at).toLocaleDateString()}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="card text-center py-16">
          <svg className="mx-auto mb-4" width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" style={{ color: 'var(--text-tertiary)' }}>
            <path d="M4 20h16a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.93a2 2 0 0 1-1.66-.9l-.82-1.2A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13c0 1.1.9 2 2 2Z"/>
          </svg>
          <h3 className="heading-md mb-2">No projects yet</h3>
          <p className="text-body max-w-md mx-auto">
            Start tracking experiments by using the dalva Python API in your training scripts.
          </p>
        </div>
      )}
    </div>
  );
}
