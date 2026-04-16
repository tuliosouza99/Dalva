"""Skill management commands — install bundled skills into the current project."""

from __future__ import annotations

import shutil
from pathlib import Path

import click


_SKILLS_DIR = Path(__file__).resolve().parent.parent / "assets" / "skills"

_TARGET_DIRS = {
    "agents": ".agents/skills",
    "claude": ".claude/skills",
}


@click.group()
def skill():
    """Manage Dalva skills for agent-assisted experiment monitoring."""
    pass


@skill.command("install")
@click.argument("name", required=False, default="dalva-autoresearch")
@click.option(
    "--target",
    type=click.Choice(list(_TARGET_DIRS.keys())),
    default="agents",
    show_default=True,
    help="Where to install the skill.",
)
@click.option(
    "--cwd",
    "target_cwd",
    default=None,
    help="Target directory (default: current working directory).",
)
def install(name, target, target_cwd):
    """Install a bundled skill into the current project.

    Copies the skill files from the Dalva package into the chosen
    skills directory. Creates the directory if it doesn't exist.

    \b
    dalva skill install                          # .agents/skills/ (default)
    dalva skill install --target claude          # .claude/skills/
    dalva skill install --cwd /path/to/dir       # specify project directory
    """
    source = _SKILLS_DIR / name
    if not source.exists():
        available = (
            [d.name for d in _SKILLS_DIR.iterdir() if d.is_dir()]
            if _SKILLS_DIR.exists()
            else []
        )
        msg = f"Skill '{name}' not found."
        if available:
            msg += f" Available: {', '.join(available)}"
        click.echo(click.style(msg, fg="red"), err=True)
        raise SystemExit(1)

    base = Path(target_cwd) if target_cwd else Path.cwd()
    dest = base / _TARGET_DIRS[target] / name

    if dest.exists():
        click.echo(f"Skill already installed at {dest}")
        click.echo("Removing old version...")
        shutil.rmtree(dest)

    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, dest)

    click.echo(click.style(f"Skill installed: {dest}", fg="green"))
    click.echo(f"\nSkill '{name}' is ready. It will be available to agents that")
    click.echo(f"read skills from {dest.parent}/")
