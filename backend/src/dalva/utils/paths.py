"""Path utilities for finding static assets in dev and installed modes."""

from pathlib import Path
from typing import Optional


def is_development_mode() -> bool:
    """
    Check if running from source repository.

    Returns True if:
    - pyproject.toml exists in expected location
    - frontend directory exists (indicating source repo)

    Returns:
        True if running from source repository, False if installed package
    """
    try:
        package_dir = Path(__file__).parent.parent  # dalva/utils -> dalva
        repo_root = package_dir.parent.parent.parent  # dalva -> src -> backend -> root

        return (repo_root / "pyproject.toml").exists() and (
            repo_root / "frontend"
        ).exists()
    except Exception:
        return False


def get_static_dir() -> Path:
    """
    Get path to static files, works in both dev and installed modes.

    Development mode: Returns repo root static/ directory
    Installed mode: Returns package-bundled static/ directory

    Returns:
        Path to static directory

    Raises:
        FileNotFoundError: If static directory cannot be found
    """
    if is_development_mode():
        # Development mode: use repo root static/
        package_dir = Path(__file__).parent.parent
        static_dir = package_dir.parent.parent.parent / "static"

        if not static_dir.exists():
            raise FileNotFoundError(
                f"Static directory not found at {static_dir}. "
                f"Run 'npm run build' in the frontend directory."
            )
        return static_dir
    else:
        # Installed mode: use package-bundled static/
        try:
            from importlib.resources import files

            static_dir_traversable = files("dalva") / "static"

            # Convert to Path - handle both Python 3.9+ and 3.11+ behaviors
            # In Python 3.9-3.10, files() returns a Traversable
            # In Python 3.11+, it can be used as a path-like object
            if hasattr(static_dir_traversable, "__fspath__"):
                static_dir = Path(static_dir_traversable)
            else:
                # For Python 3.9-3.10, use as_file context manager
                import importlib.resources as resources

                with resources.as_file(static_dir_traversable) as path:
                    # Verify it exists while in context
                    if not path.exists():
                        raise FileNotFoundError(
                            f"Static directory not found in installed package at {path}. "
                            f"The package may not have been built correctly."
                        )
                    # Return the path (it remains accessible after context exits for package resources)
                    static_dir = Path(path)

            # Verify it exists
            if not static_dir.exists():
                raise FileNotFoundError(
                    "Static directory not found in installed package. "
                    "The package may not have been built correctly."
                )

            return static_dir
        except ImportError as e:
            raise FileNotFoundError(
                f"Cannot locate static directory in installed package. "
                f"importlib.resources not available: {e}"
            )
        except Exception as e:
            raise FileNotFoundError(
                f"Static directory not found in installed package. "
                f"The package may not have been built correctly. Error: {e}"
            )


def get_frontend_dir() -> Optional[Path]:
    """
    Get path to frontend source directory (development mode only).

    Returns:
        Path to frontend directory, or None if not in development mode

    Raises:
        RuntimeError: If called in installed mode (returns None instead of raising)
    """
    if not is_development_mode():
        return None

    package_dir = Path(__file__).parent.parent
    frontend_dir = package_dir.parent.parent.parent / "frontend"

    if not frontend_dir.exists():
        raise FileNotFoundError(f"Frontend directory not found at {frontend_dir}")

    return frontend_dir
