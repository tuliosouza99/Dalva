"""Custom Hatch build hook to bundle pre-built frontend assets."""

import shutil
import subprocess
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class FrontendBuildHook(BuildHookInterface):
    """Build frontend and bundle static assets into package."""

    PLUGIN_NAME = "frontend"

    def initialize(self, version, build_data):
        """Run before wheel is built."""
        print("=" * 60)
        print("TrackAI: Building frontend assets...")
        print("=" * 60)

        # Get paths
        repo_root = Path(__file__).parent
        frontend_dir = repo_root / "frontend"
        static_source = repo_root / "static"
        package_static_dest = repo_root / "backend" / "src" / "trackai" / "static"

        # Check if static files are already bundled in package
        # This happens when building wheel from sdist
        if package_static_dest.exists() and (package_static_dest / "index.html").exists():
            print("Static files already bundled in package, skipping build")
            print(f"Found at: {package_static_dest}")
            return

        # Check if pre-built static files exist (use without building)
        if static_source.exists() and (static_source / "index.html").exists():
            print(f"Using existing static files from: {static_source}")
            self._copy_static_files(static_source, package_static_dest)
            return

        # Check if frontend exists
        if not frontend_dir.exists():
            print("WARNING: Frontend directory not found")
            print(f"Looked in: {frontend_dir}")
            raise RuntimeError(
                "Cannot build package: frontend directory not found and no pre-built static files.\n"
                "This usually means you're building from an incomplete source distribution."
            )

        # Check if npm is available
        if shutil.which("npm") is None:
            print("WARNING: npm not found")
            print("Install Node.js and npm to build frontend automatically")
            raise RuntimeError(
                "Cannot build package: npm not found.\n"
                "Install Node.js and npm, then run 'npm run build' in frontend/"
            )

        # Check if node_modules exists, install dependencies if needed
        node_modules = frontend_dir / "node_modules"
        if not node_modules.exists():
            print("Installing frontend dependencies...")
            try:
                result = subprocess.run(
                    ["npm", "install"],
                    cwd=frontend_dir,
                    capture_output=True,
                    text=True,
                    check=True,
                )
                print("Frontend dependencies installed successfully!")
            except subprocess.CalledProcessError as e:
                print("ERROR: Failed to install frontend dependencies!")
                if e.stdout:
                    print(e.stdout)
                if e.stderr:
                    print(e.stderr)
                raise RuntimeError(
                    f"npm install failed with exit code {e.returncode}.\n"
                    f"Run 'npm install' in frontend/ to see the full error."
                )

        # Build frontend
        print(f"Building frontend in: {frontend_dir}")
        try:
            result = subprocess.run(
                ["npm", "run", "build"],
                cwd=frontend_dir,
                capture_output=True,
                text=True,
                check=True,
            )
            print("Frontend build succeeded!")
            if result.stdout:
                print(result.stdout)
        except subprocess.CalledProcessError as e:
            print("ERROR: Frontend build failed!")
            if e.stdout:
                print(e.stdout)
            if e.stderr:
                print(e.stderr)
            raise RuntimeError(
                f"Frontend build failed with exit code {e.returncode}.\n"
                f"Run 'npm run build' in frontend/ to see the full error."
            )

        # Copy static files into package
        if static_source.exists():
            self._copy_static_files(static_source, package_static_dest)
        else:
            print(f"WARNING: No static directory found at {static_source}")
            raise RuntimeError(
                f"Frontend build completed but no static files found at {static_source}.\n"
                f"Check the frontend build configuration."
            )

    def _copy_static_files(self, source: Path, dest: Path):
        """Copy static files to package directory."""
        print(f"Copying static files:")
        print(f"  From: {source}")
        print(f"  To:   {dest}")

        # Remove existing static dir in package
        if dest.exists():
            shutil.rmtree(dest)

        # Copy entire static directory
        shutil.copytree(source, dest)

        # Count files
        file_count = sum(1 for _ in dest.rglob("*") if _.is_file())
        print(f"  Copied {file_count} files")
        print("Static files bundled successfully!")
