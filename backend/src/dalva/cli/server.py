"""Server management commands."""

import os
import subprocess
import sys
from pathlib import Path

import click

from dalva.cli.utils import find_available_port
from dalva.utils.paths import get_frontend_dir, is_development_mode


@click.group()
def server():
    """Server management commands."""
    pass


@server.command()
@click.option(
    "--port",
    type=int,
    default=None,
    help="Port to run server on (default: auto-detect from 8000)",
)
@click.option("--host", default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)")
@click.option(
    "--reload/--no-reload", default=True, help="Enable auto-reload (default: enabled)"
)
def start(port, host, reload):
    """Start Dalva server in production mode (builds frontend first)."""
    # Find port if not specified
    if port is None:
        port = find_available_port(8000)
        click.echo(f"Found available port: {port}")

    click.echo(click.style("Starting Dalva...", fg="blue", bold=True))

    # No need to build, static files are already in package
    backend_dir = Path(__file__).parent.parent.parent.parent

    # Start backend
    click.echo(click.style(f"Starting backend server on port {port}...", fg="green"))

    cmd = [
        "uvicorn",
        "dalva.api.main:app",
        "--host",
        host,
        "--port",
        str(port),
    ]

    if reload:
        cmd.append("--reload")

    click.echo(click.style("\nDalva is running!", fg="blue", bold=True))
    click.echo(
        f"Access the app at: {click.style(f'http://localhost:{port}', fg='yellow')}"
    )
    click.echo(click.style("\nPress Ctrl+C to stop the server\n", fg="red"))

    try:
        subprocess.run(cmd, cwd=backend_dir)
    except KeyboardInterrupt:
        click.echo(click.style("\nShutting down server...", fg="red"))
        sys.exit(0)


@server.command()
@click.option(
    "--backend-port",
    type=int,
    default=None,
    help="Backend port (default: auto-detect from 8000)",
)
@click.option(
    "--frontend-port",
    type=int,
    default=None,
    help="Frontend port (default: auto-detect from 5173)",
)
def dev(backend_port, frontend_port):
    """Start Dalva in development mode (hot reload for both frontend and backend)."""
    # Find ports if not specified
    if backend_port is None:
        backend_port = find_available_port(8000)
        click.echo(f"Found available backend port: {backend_port}")

    if frontend_port is None:
        frontend_port = find_available_port(5173)
        click.echo(f"Found available frontend port: {frontend_port}")

    # Check if in development mode
    if not is_development_mode():
        click.echo(
            click.style(
                "ERROR: Development mode requires source repository.\n"
                "The 'dalva server dev' command is only available when running "
                "from the source code, not from an installed package.\n"
                "Use 'dalva server start' instead.",
                fg="red",
            ),
            err=True,
        )
        sys.exit(1)

    click.echo(
        click.style("\nStarting Dalva in development mode...", fg="blue", bold=True)
    )

    # Get paths - these will only work in dev mode
    backend_dir = Path(__file__).parent.parent.parent.parent
    frontend_dir = get_frontend_dir()

    # Start backend process
    backend_cmd = [
        "uvicorn",
        "dalva.api.main:app",
        "--reload",
        "--host",
        "0.0.0.0",
        "--port",
        str(backend_port),
    ]

    click.echo(click.style(f"\nStarting backend on port {backend_port}...", fg="green"))
    backend_process = subprocess.Popen(
        backend_cmd,
        cwd=backend_dir,
        # Don't redirect stdout/stderr - let them display normally
    )

    # Start frontend process
    frontend_cmd = ["npm", "run", "dev", "--", "--port", str(frontend_port)]

    # Set environment variable for backend URL
    frontend_env = os.environ.copy()
    frontend_env["VITE_BACKEND_URL"] = f"http://localhost:{backend_port}"

    click.echo(click.style(f"Starting frontend on port {frontend_port}...", fg="green"))
    frontend_process = subprocess.Popen(
        frontend_cmd,
        cwd=frontend_dir,
        env=frontend_env,
        # Don't redirect stdout/stderr - let them display normally
    )

    click.echo(
        click.style("\nDalva is running in development mode!", fg="blue", bold=True)
    )
    click.echo(
        f"Backend:  {click.style(f'http://localhost:{backend_port}', fg='yellow')}"
    )
    click.echo(
        f"Frontend: {click.style(f'http://localhost:{frontend_port}', fg='yellow')}"
    )
    click.echo(click.style("\nPress Ctrl+C to stop both servers\n", fg="red"))

    # Handle cleanup on exit
    def cleanup():
        """Clean up processes on exit."""
        # Terminate processes gracefully (only if still running)
        if backend_process.poll() is None:  # Process is still running
            backend_process.terminate()
            try:
                backend_process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                backend_process.kill()
                backend_process.wait()

        if frontend_process.poll() is None:  # Process is still running
            frontend_process.terminate()
            try:
                frontend_process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                frontend_process.kill()
                frontend_process.wait()

    # Wait for processes
    try:
        backend_process.wait()
        frontend_process.wait()
    except KeyboardInterrupt:
        click.echo(click.style("\nShutting down servers...", fg="red"))
        cleanup()
        click.echo(click.style("Servers stopped", fg="green"))
        sys.exit(0)
    finally:
        cleanup()
