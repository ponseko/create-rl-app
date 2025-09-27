# create-rl-app

[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://python.org)
[![Jaxnasium Version](https://badge.fury.io/py/jaxnasium.svg)](https://github.com/ponseko/jaxnasium)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

A CLI application to bootstrap reinforcement learning applications within the Jaxnasium ecosystem. Quickly scaffold new RL projects for either developing environments with baseline algorithms or for altering existing baselines.

## What it does

`create-rl-app` is a command-line tool that helps you quickly set up new reinforcement learning projects using the Jaxnasium framework. It creates a well-structured project template with:

- 🚀 **Quick Setup**: Get a new RL project running in seconds
- 🏗️ **Helpful Templates**: Templates for environments and algorithms for you to start with.
- ⚡ **Performance Optimized**: Sets you up with PureJaxRL compatible agents and environments for performance and GPU scalability.

## Useage

### uvx (Recommended)

```bash
uvx create-rl-app <project_name>
cd <project_name>
uv run train_example.py
```

### pipx

```bash
pipx run create-rl-app <project_name>
cd <project_name>
# Create a new environment (e.g. conda, venv, etc.)
# source .../bin/activate
python train_example.py
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

