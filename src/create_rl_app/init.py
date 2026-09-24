import argparse
import importlib.resources as pkg_resources
import json
import re
import shutil
import subprocess
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from .scaffold import _VENDOR_PKG, copy_entry, write_file
from .templating import pascal_case, replace_all

# ANSI color codes
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BOLD = "\033[1m"
RESET = "\033[0m"
LIGHT_GRAY = "\033[37m"

_ALGO_CLASSES = {"ppo": "PPO", "sac": "SAC", "dqn": "DQN", "pqn": "PQN"}


def _jaxnasium_root(*, installed: bool = False):
    if installed:
        return pkg_resources.files("jaxnasium")
    return pkg_resources.files(_VENDOR_PKG) / "jaxnasium"


def _parse_version_string(raw_version: str) -> str:
    version_text = raw_version.lstrip("v")
    match = re.match(r"\d+\.\d+\.\d+", version_text)
    return match.group(0) if match else version_text


def get_jaxnasium_version(*, installed: bool = False) -> str:
    """Return jaxnasium version as a plain ``X.Y.Z`` string for dependency pins."""
    if installed:
        try:
            return _parse_version_string(version("jaxnasium"))
        except PackageNotFoundError as e:
            raise RuntimeError("Installed jaxnasium version not found") from e

    vendor_info = _jaxnasium_root(installed=False) / ".vendor_info"
    try:
        raw_version = json.loads(vendor_info.read_text())["version"]
    except (FileNotFoundError, KeyError, json.JSONDecodeError) as e:
        raise RuntimeError(f"Vendored jaxnasium version not found: {e}") from e
    return _parse_version_string(raw_version)


def get_vendored_jaxnasium_version() -> str:
    """Return the vendored jaxnasium version (backward-compatible alias)."""
    return get_jaxnasium_version(installed=False)


def colored_input(prompt, default=""):
    """Display a colored input prompt with default value."""
    default_display = f" ({LIGHT_GRAY}{default}{RESET})" if default else ""
    user_input = input(
        f"{CYAN}{BOLD}?{RESET} {prompt}{YELLOW}{default_display}{RESET}: "
    ).strip()
    return user_input if user_input else default


def yes_no_prompt(question, default="y"):
    """Ask a yes/no question with colored output."""
    options = "(Y/n)" if default.lower() == "y" else "(y/N)"
    while True:
        response = colored_input(f"{question} {options}")
        if not response:
            return default.lower() == "y"
        if response.lower() in ["y", "yes"]:
            return True
        elif response.lower() in ["n", "no"]:
            return False
        print(f"{YELLOW}Please answer with 'y' or 'n'.{RESET}")


def ask_bool(question, default, flag_value, accept_defaults):
    """Resolve a yes/no setting from (in priority order) an explicit CLI flag, `-y` (accept the default) or an interactive prompt."""
    if flag_value is not None:
        return flag_value
    if accept_defaults:
        return default == "y"
    return yes_no_prompt(question, default)


def _uv_or_pipx(*args: str) -> list:
    if shutil.which("uv"):
        return ["uv", *args]
    return ["pipx", "run", "uv", *args]


def run_uv_init(projectname: str) -> None:
    command = _uv_or_pipx("init", "--package", projectname)
    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"Failed to initialize the project: {e}. \n"
            "Most likely neither uv nor pipx are installed."
        )


def run_uv_add_jaxnasium(project_path: Path, *, installed: bool = False) -> None:
    jaxnasium_version = get_jaxnasium_version(installed=installed)
    command = _uv_or_pipx(
        "add",
        "--quiet",
        "--frozen",
        f"jaxnasium[algs]>={jaxnasium_version}",
    )
    subprocess.run(command, check=True, cwd=project_path)


def flatten_src_layout(project_path: Path) -> Path:
    """Removes the src layout created by `uv init --package`"""
    src_dir = project_path / "src"
    package_dir = next(src_dir.iterdir())
    dest = project_path / package_dir.name
    shutil.move(str(package_dir), str(dest))
    shutil.rmtree(src_dir)
    return dest


def fix_build_backend(project_path: Path) -> None:
    """uv-build expects a `src/` layout by default. Need to set the module-root in pyproject.toml"""
    toml_path = project_path / "pyproject.toml"
    content = toml_path.read_text()
    if re.search(r'build-backend\s*=\s*["\']uv_build["\']', content) and not re.search(
        r"\[tool\.uv\.build-backend\]", content
    ):
        toml_path.write_text(content + "\n[tool.uv.build-backend]\nmodule-root = ''\n")


def render_init_file(package_name: str, env_module: str, env_class: str | None) -> str:
    import_line = (
        f"from .{env_module} import {env_class} as {env_class}\n\n\n"
        if env_class
        else ""
    )
    return (
        f'{import_line}def main() -> None:\n    print("Hello from {package_name}!")\n'
    )


def render_env_template(env_class: str, *, installed: bool = False) -> str:
    template = (
        _jaxnasium_root(installed=installed) / "cli" / "_resources" / "env_template.py"
    )
    return replace_all(template.read_text(), {"ExampleEnv": env_class})


def render_train_template(
    *,
    package_name: str,
    env_id: str,
    algorithm: str,
    algorithm_source: bool,
    installed: bool = False,
) -> str:
    """Render `train.py` from the jaxnasium template and replace the chosen algorithm."""
    template = (
        _jaxnasium_root(installed=installed)
        / "cli"
        / "_resources"
        / "train_template.py"
    )
    text = template.read_text()
    algo = _ALGO_CLASSES[algorithm]
    algorithms_module = (
        f"{package_name}.{algorithm}" if algorithm_source else "jaxnasium.algorithms"
    )

    text = text.replace(
        "from jaxnasium.algorithms import PPO as Algo",
        f"from {algorithms_module} import {algo} as Algo",
    )
    text = text.replace("# RL Training", f"# RL Training with {algo}")

    text = f"import {package_name}  # noqa: F401  (registers {env_id})\n" + text
    text = text.replace('jym.make("CartPole-v1")', f'jym.make("{env_id}")')

    return text


def copy_algorithm_source(
    algorithm: str, target_dir: Path, *, installed: bool = False
) -> None:
    copy_entry(_jaxnasium_root(installed=installed), algorithm, str(target_dir))


def print_banner() -> None:
    print(f"{CYAN}{BOLD}")
    print("  ██████╗██████╗ ███████╗ █████╗ ████████╗███████╗")
    print(" ██╔════╝██╔══██╗██╔════╝██╔══██╗╚══██╔══╝██╔════╝")
    print(" ██║     ██████╔╝█████╗  ███████║   ██║   █████╗")
    print(" ██║     ██╔══██╗██╔══╝  ██╔══██║   ██║   ██╔══╝")
    print(" ╚██████╗██║  ██║███████╗██║  ██║   ██║   ███████╗")
    print("  ╚═════╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝   ╚═╝   ╚══════╝")
    print("")
    print(" ██████╗ ██╗               █████╗ ██████╗ ██████╗")
    print(" ██╔══██╗██║              ██╔══██╗██╔══██╗██╔══██╗")
    print(" ██████╔╝██║              ███████║██████╔╝██████╔╝")
    print(" ██╔══██╗██║              ██╔══██║██╔═══╝ ██╔═══╝")
    print(" ██║  ██║███████╗         ██║  ██║██║     ██║")
    print(" ╚═╝  ╚═╝╚══════╝         ╚═╝  ╚═╝╚═╝     ╚═╝")
    print(f"{RESET}")


def main(argv=None, *, use_installed_jaxnasium: bool = False):
    parser = argparse.ArgumentParser(description="Initialize a new jaxnasium project.")
    parser.add_argument("projectname", help="The path to the new project directory.")
    parser.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="Automatically accept the default for any unspecified option.",
    )
    parser.add_argument(
        "--env-template",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Include an example environment template.",
    )
    parser.add_argument(
        "--algorithm-source",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Copy the algorithm source into your project instead of importing it.",
    )
    parser.add_argument(
        "--algorithm",
        choices=sorted(_ALGO_CLASSES),
        default="ppo",
        help="Algorithm to set up the training script with (default: ppo).",
    )
    DEFAULT_ENVIRONMENT = "CartPole-v1"  # set if --env-template is not set
    parser.add_argument(
        "--environment",
        default=argparse.SUPPRESS,
        help=(
            "Environment id passed to jym.make(...) when no custom env template is "
            f"included (defaults to: {DEFAULT_ENVIRONMENT})."
        ),
    )
    args = parser.parse_args(argv)

    print_banner()

    projectname = args.projectname
    if any(char.isupper() for char in projectname):
        print(f"{YELLOW} Project name has been altered to lowercase{RESET}")
    projectname = projectname.lower()

    print(
        f"{LIGHT_GRAY}Setting up a new Jaxnasium project "
        f"(v{get_jaxnasium_version(installed=use_installed_jaxnasium)}){RESET}"
    )
    print(f"{LIGHT_GRAY}{'─' * 60}{RESET}\n")
    print(f"{LIGHT_GRAY}Project name: {projectname}{RESET}")

    ########## Questions ##########

    if "environment" not in args:
        build_env = ask_bool(
            "Would you like to include an environment template?",
            "y",
            args.env_template,
            args.yes,
        )
        if not build_env:
            args.environment = DEFAULT_ENVIRONMENT
    else:
        build_env = False
    include_algorithm_source = ask_bool(
        "Instead of importing, would you like to copy the algorithm source code into your project?",
        "n",
        args.algorithm_source,
        args.yes,
    )

    print(f"\n{BOLD}📋 Project configuration summary:{RESET}")
    print(f"  • Project name: {projectname}")
    print(f"  • Algorithm: {_ALGO_CLASSES[args.algorithm]}")
    print(f"  • Include environment template: {'Yes' if build_env else 'No'}")
    if build_env:
        print(f"  • Environment: {pascal_case(projectname)}Env (custom template)")
    else:
        print(f"  • Environment: {args.environment}")
    print(
        f"  • Copy algorithm source code: {'Yes' if include_algorithm_source else 'No'}"
    )

    if not args.yes:
        if not yes_no_prompt("\nDo you want to proceed with this configuration?"):
            print("Setup cancelled.")
            return

    #### SETUP PROJECT ####

    run_uv_init(projectname)

    project_path = Path(projectname).resolve()
    package_dir = flatten_src_layout(project_path)
    fix_build_backend(project_path)
    run_uv_add_jaxnasium(project_path, installed=use_installed_jaxnasium)

    class_name = pascal_case(package_dir.name)
    env_class = f"{class_name}Env" if build_env else None
    env_module = f"{package_dir.name}_env"

    write_file(
        package_dir / "__init__.py",
        render_init_file(package_dir.name, env_module, env_class),
    )

    if build_env:
        write_file(
            package_dir / f"{env_module}.py",
            render_env_template(env_class, installed=use_installed_jaxnasium),
        )

    if include_algorithm_source:
        copy_algorithm_source(
            args.algorithm, package_dir, installed=use_installed_jaxnasium
        )

    write_file(
        project_path / "train.py",
        render_train_template(
            package_name=package_dir.name,
            env_id=env_class if build_env else args.environment,
            algorithm=args.algorithm,
            algorithm_source=include_algorithm_source,
            installed=use_installed_jaxnasium,
        ),
    )

    if include_algorithm_source:
        other_algorithms = [a for a in sorted(_ALGO_CLASSES) if a != args.algorithm]
        print(
            f"\n{LIGHT_GRAY}{_ALGO_CLASSES[args.algorithm]} was copied into "
            f"{package_dir.name}/{args.algorithm}.py{RESET}"
        )
        print(
            f"{LIGHT_GRAY}To add another algorithm, run e.g.:{RESET}\n"
            f"  create-rl-app add [{'|'.join(other_algorithms)}] {package_dir.name}"
        )


if __name__ == "__main__":
    main()
