"""Tests for repository metadata."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_supported_runtime_baselines_are_declared() -> None:
    """Ensure the package metadata advertises the upgraded support floor."""
    pyproject_text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert 'requires-python = ">=3.10"' in pyproject_text
    assert '"numpy>=2"' in pyproject_text
    assert 'target-version = "py310"' in pyproject_text


def test_tooling_is_consolidated_around_ruff() -> None:
    """Ensure superseded formatting tools are no longer configured."""
    pyproject_text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    pre_commit_text = (ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")

    assert "[tool.black]" not in pyproject_text
    assert "[tool.isort]" not in pyproject_text
    assert '"black==22.1.0"' not in pyproject_text
    assert "id: black" not in pre_commit_text
    assert "id: isort" not in pre_commit_text
    assert "id: pycln" not in pre_commit_text
    assert "id: ruff-check" in pre_commit_text
    assert "id: ruff-format" in pre_commit_text
