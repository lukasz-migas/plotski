"""Pin minimum requirements declared in ``pyproject.toml``.

This keeps the optional minimum-requirements workflow usable after the project
moved from ``setup.cfg`` metadata to PEP 621 metadata in ``pyproject.toml``.
The script is a no-op unless ``MIN_REQ=1`` is present in the environment.
"""

from __future__ import annotations

import os
from pathlib import Path


def pin_config_minimum_requirements(config_filename: str) -> None:
    """Pin package dependency lower bounds in the project metadata file.

    Parameters
    ----------
    config_filename : str
        Path to the ``pyproject.toml`` file to rewrite.
    """
    config_path = Path(config_filename)
    lines = config_path.read_text(encoding="utf-8").splitlines()

    in_optional_dependencies = False
    in_dependency_array = False
    pinned_lines: list[str] = []

    for line in lines:
        stripped = line.strip()

        if stripped == "[project.optional-dependencies]":
            in_optional_dependencies = True
        elif stripped.startswith("[") and stripped != "[project.optional-dependencies]":
            in_optional_dependencies = False

        if stripped == "dependencies = [" or (in_optional_dependencies and stripped.endswith("= [")):
            in_dependency_array = True
            pinned_lines.append(line)
            continue

        if in_dependency_array:
            if stripped == "]":
                in_dependency_array = False
            elif stripped.startswith('"') and ">=" in stripped:
                line = line.replace(">=", "==", 1)

        pinned_lines.append(line)

    config_path.write_text("\n".join(pinned_lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    if os.environ.get("MIN_REQ", "") == "1":
        # find pyproject.toml
        config_filename = Path(__file__).parent.parent / "pyproject.toml"
        if not config_filename.exists():
            print("Config file does not exist.")
        else:
            pin_config_minimum_requirements(str(config_filename))
            print("Pinned minimum requirements in pyproject.toml.")
