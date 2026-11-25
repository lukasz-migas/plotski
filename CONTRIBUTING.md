# Contributing

Contributions are welcome, and they are greatly appreciated! Every little bit
helps, and credit will always be given.

You can contribute in many ways:

## Types of Contributions

## Report Bugs

Report bugs at https://github.com/lukasz-migas/plotski/issues.

If you are reporting a bug, please include:

* Your operating system name and version.
* Any details about your local setup that might be helpful in troubleshooting.
* Detailed steps to reproduce the bug.

## Fix Bugs

Look through the GitHub issues for bugs. Anything tagged with "bug" and "help
wanted" is open to whoever wants to implement it.

## Implement Features

Look through the GitHub issues for features. Anything tagged with "enhancement"
and "help wanted" is open to whoever wants to implement it.

## Write Documentation

plotski could always use more documentation, whether as part of the
official plotski docs, in docstrings, or even on the web in blog posts,
articles, and such.

## Submit Feedback

The best way to send feedback is to file an issue at https://github.com/lukasz-migas/plotski/issues.

If you are proposing a feature:

* Explain in detail how it would work.
* Keep the scope as narrow as possible, to make it easier to implement.
* Remember that this is a volunteer-driven project, and that contributions
  are welcome :)

## Get started

Fork and clone the repository, then use `uv` to set up an editable install.

```sh
uv sync --extra dev --extra plotly
uv run --extra dev ruff check .
uv run --extra dev ruff format --check .
uv run --extra test --extra plotly pytest
```

For a specific Python version, run `uv run --python 3.12 --extra test --extra plotly pytest`.
Use `make test-all` to run the suite in isolated environments for every Python
version in the CI matrix. Use `make docs` to build the documentation and
`make servedocs` to preview it.

## Pull request guidelines

Before you submit a pull request, check that it meets these guidelines:

1. The pull request should include tests.
2. If the pull request adds functionality, the docs should be updated. Put
   your new functionality into a function with a docstring, and add the
   feature to the usage guide when relevant.
3. Check that GitHub Actions passes for the supported Python versions.

## Releases

The GitHub Actions release workflow runs on tags that start with `v`.
Use `uv build` to build the source distribution and wheel locally.

