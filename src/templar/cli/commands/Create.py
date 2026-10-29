import sys
import shutil
from pathlib import Path
from templar.cli.BaseCommand import BaseCommand

sys.dont_write_bytecode = True

class CreateCommand(BaseCommand):
    name = "create"
    help = "Create a new Templar project from the skeleton template"

    @staticmethod
    def add_args(parser):
        parser.add_argument("name", help="Name of the new project")

    def _resolve_skeleton_dir(self) -> Path:
        current = Path(__file__).resolve()
        candidates = [current.parents[2] / "skeleton"]

        for candidate in candidates:
            if (candidate / "templar.config.yml").exists():
                return candidate

        return candidates[-1]

    def run(self, args, extra_args=None):
        if extra_args:
            self.output.error(f"Unrecognized arguments: {' '.join(extra_args)}")
            sys.exit(1)

        project_dir = Path(args.name)

        if project_dir.exists():
            self.output.error(f"Directory '{args.name}' already exists.")
            sys.exit(1)

        # Get the skeleton template directory
        skeleton_dir = self._resolve_skeleton_dir()
        
        if not skeleton_dir.exists():
            self.output.error(f"Skeleton template not found at {skeleton_dir}")
            sys.exit(1)

        # Copy skeleton to new project directory - ignoring __pycache__ and common ignored files
        def ignore_patterns(directory, files):
            ignored = set()

            for file in files:
                if file in {'__pycache__', '.pyc', '.egg-info'}:
                    ignored.add(file)

            return ignored
        
        shutil.copytree(skeleton_dir, project_dir, ignore=ignore_patterns)

        # Ensure all necessary directories exist (in case they weren't in skeleton)
        for directory in (
            project_dir / "static" / "css",
            project_dir / "static" / "javascript",
            project_dir / "static" / "assets" / "images",
            project_dir / "static" / "assets" / "videos",
            project_dir / "static" / "assets" / "documents",
            project_dir / "logs",
            project_dir / "migrations",
            project_dir / "models",
            project_dir / "themes",
            project_dir / "components",
        ):
            directory.mkdir(parents=True, exist_ok=True)

        readme_path = project_dir / "README.md"
        readme_path.write_text(
            readme_path.read_text(encoding="utf-8").replace("# MyApp", f"# {args.name}", 1),
            encoding="utf-8",
        )

        (project_dir / "requirements.txt").write_text(
            "templar\n",
            encoding="utf-8"
        )

        self.output.panel(
            f"New Templar project created at:\n{project_dir.resolve()}\n\n"
            f"[✔] Project '{args.name}' initialized successfully!\n\n"
            f"Next steps:\n"
            f"  1. cd {args.name}\n"
            f"  2. pip install -r requirements.txt\n"
            f"  3. templar run",
            title="Templar Project Created"
        )
