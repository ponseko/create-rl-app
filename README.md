# create-rl-app

[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://python.org)
[![Jaxnasium Version](https://badge.fury.io/py/jaxnasium.svg)](https://github.com/ponseko/jaxnasium)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

A CLI application to bootstrap reinforcement learning applications within the Jaxnasium ecosystem. Quickly scaffold new RL projects for either developing environments with baseline algorithms or for altering existing baselines.

## What it does

`create-rl-app` is a command-line tool that helps you quickly set up new reinforcement learning projects using the Jaxnasium framework. It has three commands:

- `create-rl-app init <project_name>` - bootstrap a new project (`uv init --package` + `uv add jaxnasium` + a training script and, optionally, an example environment and algorithm source code).
- `create-rl-app add <item>` - scaffold an individual file (algorithm, architecture, ...) from jaxnasium into the current directory. Run `create-rl-app add --list` to see what's available.
- `<package> add <item>` - the same, but for any other installed package that ships its own `create-rl-app.toml` (e.g. `uvx jaxnasium add ppo`).

## Useage

### uvx (Recommended)

```bash
uvx create-rl-app init <project_name>
cd <project_name>
uv run train.py
```
### pipx

```bash
pipx run create-rl-app <project_name>
cd <project_name>
# Create a new environment (e.g. conda, venv, etc.)
# source .../bin/activate
python train.py
```

### Or Install Globally

```bash
uv tool install create-rl-app
```

```bash
pip install create-rl-app
```

## Dependencies

None.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

