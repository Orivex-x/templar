import sys, os
from rich.progress import track
from rich.text import Text
from rich.console import Group
from templar.cli.BaseCommand import BaseCommand
from templar.core.deployment.Manager import DeploymentManager
from templar.core.deployment.Errors import DeployError

sys.dont_write_bytecode = True

class DeployCommand(BaseCommand):
    name = "deploy"
    help = "Deploy the project"

    @staticmethod
    def add_args(parser):
        parser.add_argument("--provider", default="ssh", help="Provider: ssh|docker")
        parser.add_argument("--image", default=None)
        parser.add_argument("--tag", default=None)
        parser.add_argument("--push", action="store_true")
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--skip-tests", action="store_true")
        parser.add_argument("--ssh-host", default=None)
        parser.add_argument("--ssh-user", default=None)
        parser.add_argument("--ssh-dest", default=None)
        parser.add_argument("--ssh-key", default=None)

    def run(self, args, extra_args=None):
        if extra_args:
            self.output.error(f"Unrecognized arguments: {' '.join(extra_args)}", title="Deployment Error")
            sys.exit(1)

        mgr = DeploymentManager(project_root=os.getcwd())

        try:
            steps = []

            if not args.dry_run and not args.skip_tests:
                steps.append(("Running tests", mgr.run_tests))

            if not args.dry_run:
                steps.append(("Building project", mgr.build))

            steps.append(
                ("Deploying", lambda: mgr.deploy(
                    args.provider,
                    {
                        "image": args.image,
                        "tag": args.tag,
                        "push": args.push,
                        "host": args.ssh_host,
                        "user": args.ssh_user,
                        "dest": args.ssh_dest,
                        "ssh_key": args.ssh_key,
                    },
                    dry_run=args.dry_run
                ))
            )

            result = None
            
            for title, fn in track(steps, description="[cyan]Deployment in progress...[/cyan]"):
                result = fn()

            info = [
                Text("Deployment finished successfully!", style="bold green"),
                Text(str(result), style="green"),
            ]
            
            self.output.panel(Group(*info), title="Deploy Result", border_style="green")

        except DeployError as e:
            self.output.error(f"Deploy failed: {e}", title="Deployment Error")
            sys.exit(2)
        except Exception as e:
            self.output.error(f"Unexpected error: {e}", title="Unexpected Error")
            sys.exit(2)
