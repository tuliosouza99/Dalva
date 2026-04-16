"""Custom Hatch build hook to bundle pre-built frontend assets.

This build hook requires pre-built static files to be committed to the repository.
This eliminates the need for Node.js/npm during package installation.

To build the frontend once (before publishing or contributing):
    cd frontend
    npm install
    npm run build

The built files will be in the ../static directory and will be automatically
included in the package.

Set DALVA_SKIP_FRONTEND=1 to skip the frontend requirement (e.g. in CI for
tests/docs where the frontend is not needed).
"""

import os
import shutil
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class FrontendBuildHook(BuildHookInterface):
    """Bundle pre-built frontend assets into package."""

    PLUGIN_NAME = "frontend"

    def initialize(self, version, build_data):
        """Run before wheel is built."""
        repo_root = Path(__file__).parent
        static_source = repo_root / "static"
        package_static_dest = repo_root / "backend" / "src" / "dalva" / "static"

        if (
            package_static_dest.exists()
            and (package_static_dest / "index.html").exists()
        ):
            print("Dalva: Static files already bundled in package")
            return

        if static_source.exists() and (static_source / "index.html").exists():
            print("Dalva: Copying pre-built frontend assets...")
            self._copy_static_files(static_source, package_static_dest)
            return

        if os.environ.get("DALVA_SKIP_FRONTEND"):
            print("Dalva: DALVA_SKIP_FRONTEND is set — skipping frontend assets")
            return

        frontend_dir = repo_root / "frontend"
        has_frontend = frontend_dir.exists()

        error_msg = (
            "Dalva: Pre-built frontend assets not found!\n\n"
            "To fix this, build the frontend:\n"
            "    cd frontend && npm install && npm run build\n\n"
        )

        if not has_frontend:
            error_msg = (
                "Dalva: Frontend source and pre-built assets not found!\n\n"
                "This repository appears incomplete. Please clone from the official source\n"
                "or ensure the 'frontend/' directory exists.\n\n"
            )

        raise RuntimeError(error_msg)

    def _copy_static_files(self, source: Path, dest: Path):
        """Copy static files to package directory."""
        # Remove existing static dir in package
        if dest.exists():
            shutil.rmtree(dest)

        # Copy entire static directory
        shutil.copytree(source, dest)

        # Count files
        file_count = sum(1 for _ in dest.rglob("*") if _.is_file())
        print(f"Dalva: Bundled {file_count} static files")
