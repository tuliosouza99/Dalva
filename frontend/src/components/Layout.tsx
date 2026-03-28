import { Outlet, Link } from 'react-router-dom';
import ThemeToggle from './ThemeToggle';

export default function Layout() {
  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 shadow-sm">
        <div className="px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <img src="/logo.svg" alt="Dalva Logo" className="w-8 h-8" />
              <h1 className="text-2xl font-bold text-primary-500">Dalva</h1>
            </div>
            <ThemeToggle />
          </div>
        </div>
      </header>

      {/* Main content */}
      <div className="flex-1 flex">
        {/* Sidebar */}
        <aside className="w-64 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700">
          <nav className="p-4 space-y-6">
            {/* Projects Section */}
            <div>
              <Link
                to="/projects"
                className="block px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md"
              >
                Projects
              </Link>
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
