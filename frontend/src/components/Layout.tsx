import { Outlet, Link } from 'react-router-dom';
import { useS3Status } from '../api/client';

export default function Layout() {
  const { data: s3Status } = useS3Status();
  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 shadow-sm">
        <div className="px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <h1 className="text-2xl font-bold text-primary-500">Dalva</h1>
              <span className="text-sm text-gray-500">Lightweight Experiment Tracker</span>
            </div>
          </div>
        </div>
      </header>

      {/* Main content */}
      <div className="flex-1 flex">
        {/* Sidebar */}
        <aside className="w-64 bg-white border-r border-gray-200">
          <nav className="p-4 space-y-6">
            {/* Projects Section */}
            <div>
              <Link
                to="/projects"
                className="block px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded-md"
              >
                Projects
              </Link>
            </div>

            {/* S3 Section */}
            <div>
              <div className="flex items-center justify-between px-4 mb-2">
                <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  S3 Storage
                </h3>
                {s3Status && (
                  <div
                    className={`w-2 h-2 rounded-full ${
                      s3Status.configured && s3Status.credentials_valid
                        ? 'bg-green-500'
                        : s3Status.configured
                        ? 'bg-yellow-500'
                        : 'bg-gray-300'
                    }`}
                    title={
                      s3Status.configured && s3Status.credentials_valid
                        ? 'S3 configured and credentials valid'
                        : s3Status.configured
                        ? 'S3 configured but credentials invalid'
                        : 'S3 not configured'
                    }
                  />
                )}
              </div>
              <div className="space-y-1">
                <Link
                  to="/s3/config"
                  className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded-md"
                >
                  S3 Configuration
                </Link>
                <Link
                  to="/s3/pull"
                  className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded-md"
                >
                  S3 Pull
                </Link>
                <Link
                  to="/s3/push"
                  className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded-md"
                >
                  S3 Push
                </Link>
              </div>
            </div>
          </nav>
        </aside>

        {/* Page content */}
        <main className="flex-1 overflow-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
