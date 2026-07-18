"""Scaffold files into a project from a ``create-rl-app.toml`` registry.
requires a `create-rl-app.toml` file in the root directory.
See https://github.com/ponseko/jaxnasium/blob/main/src/jaxnasium/create-rl-app.toml for an example.
"""

import argparse
import tomllib
from pathlib import Path

_VENDOR_PKG = "create_rl_app._vendored"
_TOML_NAME = "create-rl-app.toml"


def load_registry(root) -> dict:
    """Loads the `create-rl-app.toml` file at `root` and returns a registry of the entries."""
    toml = root / _TOML_NAME
    if not toml.is_file():
        raise SystemExit(f"Error: no {_TOML_NAME} found in {root}.")
    data = tomllib.loads(toml.read_text())
    registry: dict = {}
    for kind in ("file", "bundle"):
        for key, entry in data.get(kind, {}).items():
            name = entry.get("name", key)
            if name in registry:
                raise SystemExit(f"Error: duplicate scaffold name '{name}'.")
            registry[name] = (kind, entry)
    return registry


def write_file(dest: Path, content: str) -> None:
    """Write `content` to `dest`, creating parent directories as needed.

    Shared by the registry-driven copy below and by ``init.py``, which renders
    template files itself before writing them.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content)
    print(f"Created {dest}")


def copy_entry(root, name: str, output=None) -> None:
    """Copy a single registry entry (file or bundle) by name into `output`.

    This is the what `<...> add <name>` does.
    """
    registry = load_registry(root)
    if name not in registry:
        available = ", ".join(sorted(registry)) or "(none)"
        raise SystemExit(f"Error: unknown name '{name}'. Available: {available}")
    _copy(*registry[name], root, name, output)


def _copy(kind: str, entry: dict, root, name: str, output=None) -> None:
    """Copy a file (to `output`) or a bundle's files (into `output`, or the current directory if `output` is not given).

    Each file may set `on_exists` to `error` (default) or `skip`.
    """
    if kind == "bundle":
        base = Path(output or entry.get("dest") or ".")
        pairs = [
            (f["source"], base / f["dest"], f.get("on_exists", "error"))
            for f in entry["files"]
        ]
    elif kind == "file":
        default = entry.get("dest") or Path(entry["source"]).name.lstrip("_")
        dest = Path(output or default)
        pairs = [(entry["source"], dest, entry.get("on_exists", "error"))]
    else:
        raise SystemExit(f"Error: unknown kind '{kind}'.")

    # Resolve conflicts first so an `error` never leaves a partial result behind.
    to_write = []
    for source, dest, on_exists in pairs:
        if dest.exists():
            if on_exists == "skip":
                print(f"Skipped {dest} (already exists)")
                continue
            raise SystemExit(f"Error: {dest} already exists.")
        to_write.append((source, dest))

    for source, dest in to_write:
        src = root / source
        if not src.is_file():
            raise SystemExit(f"Error: source not found: {src}")
        write_file(dest, src.read_text())


def scaffold_from_pkg(root, label: str, argv=None) -> None:
    """Parse args and scaffold from a single registry ``root``."""
    registry = load_registry(root)
    parser = argparse.ArgumentParser(
        label, description=f"Scaffold {label} files into your project."
    )
    parser.add_argument("-l", "--list", action="store_true", help="List scaffolds.")
    parser.add_argument("name", nargs="?", help="File or bundle to copy.")
    parser.add_argument("output", nargs="?", help="Output file or folder name.")
    args = parser.parse_args(argv)

    if args.list or not args.name:
        for n in sorted(registry):
            kind, entry = registry[n]
            print(f"  {n:<16} [{kind:<6}] {entry.get('description', '')}")
        return

    copy_entry(root, args.name, args.output)
