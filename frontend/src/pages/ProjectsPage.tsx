import { useNavigate } from 'react-router-dom';
import { useProjects, useDeleteProject } from '../api/client';

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
      <div className="p-8">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-1/4 mb-4"></div>
          <div className="space-y-3">
            <div className="h-24 bg-gray-200 dark:bg-gray-700 rounded"></div>
            <div className="h-24 bg-gray-200 dark:bg-gray-700 rounded"></div>
            <div className="h-24 bg-gray-200 dark:bg-gray-700 rounded"></div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8">
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 text-red-700 dark:text-red-400">
          <h3 className="font-semibold mb-1">Error loading projects</h3>
          <p className="text-sm">{error.message}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">Projects</h1>
        <p className="text-gray-600 dark:text-gray-400 mt-1">
          {projects?.length || 0} {projects?.length === 1 ? 'project' : 'projects'}
        </p>
      </div>

      {projects && projects.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {projects.map((project) => (
            <div
              key={project.id}
              className="card hover:shadow-md transition-shadow"
            >
              <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
                {project.name}
              </h3>
              <p className="text-sm text-gray-500 dark:text-gray-400 mb-4 font-mono">
                {project.project_id}
              </p>

              <div className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <span className="text-gray-500 dark:text-gray-400">Total Runs</span>
                  <p className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                    {project.total_runs || 0}
                  </p>
                </div>
                <div>
                  <span className="text-gray-500 dark:text-gray-400">Running</span>
                  <p className="text-lg font-semibold text-green-600 dark:text-green-400">
                    {project.running_runs || 0}
                  </p>
                </div>
                <div>
                  <span className="text-gray-500 dark:text-gray-400">Completed</span>
                  <p className="text-lg font-semibold text-blue-600 dark:text-blue-400">
                    {project.completed_runs || 0}
                  </p>
                </div>
                <div>
                  <span className="text-gray-500 dark:text-gray-400">Failed</span>
                  <p className="text-lg font-semibold text-red-600 dark:text-red-400">
                    {project.failed_runs || 0}
                  </p>
                </div>
              </div>

              <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700 flex gap-2">
                <button
                  onClick={() => navigate(`/projects/${project.id}/runs`)}
                  className="flex-1 px-3 py-2 text-sm bg-primary-600 text-white rounded hover:bg-primary-700 transition-colors"
                >
                  View Runs
                </button>
                <button
                  onClick={() => handleDeleteProject(project.id, project.name)}
                  disabled={deleteProjectMutation.isPending}
                  className="px-3 py-2 text-sm text-red-600 dark:text-red-400 border border-red-300 dark:border-red-700 rounded hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors disabled:opacity-50"
                  title="Delete project and all its runs"
                >
                  🗑️
                </button>
              </div>

              <div className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                Updated {new Date(project.updated_at).toLocaleDateString()}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="card text-center py-12">
          <p className="text-gray-500 dark:text-gray-400 text-lg">No projects found</p>
          <p className="text-gray-400 dark:text-gray-500 text-sm mt-2">
            Start tracking experiments by using the dalva Python API
          </p>
        </div>
      )}
    </div>
  );
}
