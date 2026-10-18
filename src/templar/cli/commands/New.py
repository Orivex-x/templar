"""Backward-compatible alias for the canonical project scaffolder."""

from templar.cli.commands import Create as _create_module


class NewCommand(_create_module.CreateCommand):
    """Scaffold a project using the same behavior as ``templar create``."""

    name = "new"
    help = "Alias for 'create'; scaffold a new Templar project"
