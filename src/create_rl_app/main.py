import importlib.resources as resources
import sys
from pathlib import Path

from . import init
from .scaffold import _VENDOR_PKG, scaffold_from_pkg


def scaffold_from_vendored(package: str, argv) -> None:
    try:
        root = resources.files(f"{_VENDOR_PKG}.{package}")
        scaffold_from_pkg(root, package, argv)
    except ModuleNotFoundError:
        raise SystemExit(f"Error: package '{package}' is not importable.")


def scaffold_from_installed(package: str, argv) -> None:
    try:
        root = resources.files(package)
        scaffold_from_pkg(root, package, argv)
    except ModuleNotFoundError:
        raise SystemExit(f"Error: package '{package}' is not importable.")


def run_package_cli(package: str, argv: list) -> None:
    """Handle `<package> add <item>`: scaffold from an installed package's own `create-rl-app.toml`, e.g. `uvx jaxnasium add ppo`."""
    command, *rest = argv

    if command == "add":
        scaffold_from_installed(package, rest)

    if command == "init" and package == "jaxnasium":
        init.main(rest)

    raise SystemExit(
        f"Usage: {package} {'add|init' if package == 'jaxnasium' else 'add'} <item> [output]"
    )


def main():
    """
    Dependent packages should set `[project.scripts]` to `create_rl_app.main:main` in their `pyproject.toml`.
    """
    prog = Path(sys.argv[0]).name
    argv = sys.argv[1:]

    if prog not in ["create-rl-app", "create_rl_app", "__main__.py"]:
        run_package_cli(prog, argv)
        return

    if not argv:
        raise SystemExit("Usage: create-rl-app <init|add|PACKAGE> ...")

    command, *rest = argv
    if command == "init":
        init.main(rest)
    elif command == "add":
        scaffold_from_vendored("jaxnasium", rest)
    elif len(rest) >= 1 and rest[0] == "add":
        # `create-rl-app <package> add <item>` when the package has no own console script
        run_package_cli(command, rest)
    else:
        # `create-rl-app <projectname> [-y ...]` (no `init` subcommand)
        init.main(argv)


if __name__ == "__main__":
    main()
