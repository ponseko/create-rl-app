import subprocess
import sys


def check_correct_initialized_and_runs(test_dir):
    assert test_dir.exists(), "Project directory wasn't created"

    # Check for expected files/folders in the structure
    expected_files = ["pyproject.toml", "train.py", "README.md"]
    for file in expected_files:
        assert (test_dir / file).exists(), f"Expected file {file} not found"

    # Test running a file from the created structure
    test_file = "train.py"
    run_result = subprocess.run(
        [sys.executable, test_dir / test_file], capture_output=True, text=True
    )
    assert run_result.returncode == 0, (
        f"Created file failed to run: {run_result.stderr}"
    )


def test_cli_legacy_project_arg(tmp_path):
    """`uvx . <project>` without the `init` subcommand (backward compat)."""
    test_dir = tmp_path / "test_project"
    subprocess.run(["uvx", "--no-cache", ".", test_dir, "-y"])
    check_correct_initialized_and_runs(test_dir)


def test_cli_jaxnasium_uvx(tmp_path):
    test_dir = tmp_path / "test_project"
    subprocess.run(["uvx", "--no-cache", ".", "init", test_dir, "-y"])
    check_correct_initialized_and_runs(test_dir)


def test_cli_jaxnasium_pipx(tmp_path):
    test_dir = tmp_path / "test_project"

    # Use Python 3.11+ for pipx run since the package requires it
    result = subprocess.run(
        [
            "pipx",
            "run",
            "--no-cache",
            "--python",
            "python3.11",  # Specify Python 3.11+ as required by the package
            "--spec",
            ".",
            "create-rl-app",
            "init",
            test_dir,
            "-y",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"CLI failed with: {result.stderr}"
    check_correct_initialized_and_runs(test_dir)


def test_cli_no_env_template(tmp_path):
    test_dir = tmp_path / "test_project"
    subprocess.run(["uvx", "--no-cache", ".", "init", test_dir, "-y", "--no-env-template"])
    check_correct_initialized_and_runs(test_dir)


def test_cli_algorithm_source(tmp_path):
    test_dir = tmp_path / "test_project"
    subprocess.run(["uvx", "--no-cache", ".", "init", test_dir, "-y", "--algorithm-source"])
    check_correct_initialized_and_runs(test_dir)

    # Chosen algorithm (default ppo) is copied flat into the package, not
    # nested under an `algorithms/` subfolder.
    package_dir = test_dir / "test_project"
    assert (package_dir / "ppo.py").exists()
    assert (package_dir / "agent_networks.py").exists()
    assert not (package_dir / "algorithms").exists()


def test_cli_sac(tmp_path):
    test_dir = tmp_path / "test_project"
    subprocess.run(["uvx", "--no-cache", ".", "init", test_dir, "-y", "--algorithm", "sac"])
    check_correct_initialized_and_runs(test_dir)


def test_cli_neither_option(tmp_path):
    test_dir = tmp_path / "test_project"
    subprocess.run(
        [
            "uvx",
            "--no-cache",
            ".",
            "init",
            test_dir,
            "-y",
            "--no-env-template",
            "--no-algorithm-source",
        ]
    )
    check_correct_initialized_and_runs(test_dir)
