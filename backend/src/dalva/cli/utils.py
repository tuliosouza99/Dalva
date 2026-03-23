"""Utility functions for CLI commands."""

import socket


def find_available_port(start_port: int = 8000, max_port: int = 8100) -> int:
    """
    Find an available port starting from start_port.

    Args:
        start_port: Port to start searching from
        max_port: Maximum port to try

    Returns:
        Available port number

    Raises:
        RuntimeError: If no available port found
    """
    for port in range(start_port, max_port + 1):
        if is_port_available(port):
            return port

    raise RuntimeError(f"No available ports found between {start_port}-{max_port}")


def is_port_available(port: int) -> bool:
    """
    Check if a port is available.

    Args:
        port: Port number to check

    Returns:
        True if port is available, False otherwise
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("localhost", port))
            return True
    except OSError:
        return False
