import re


def pascal_case(name: str) -> str:
    """Turn "my-rl-project" / "my_rl_project" into "MyRlProject"."""
    return "".join(part.capitalize() for part in re.split(r"[-_]+", name) if part)


def replace_all(text: str, replacements: dict[str, str]) -> str:
    """Apply a sequence of exact substring replacements."""
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text
