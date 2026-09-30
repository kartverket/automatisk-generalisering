# Setup and toolchain

**Status:** CURRENT.

uv manages the project environment and the development tools. It creates `.venv` from
`uv.lock`, and the pre-commit hooks and CI run every tool through it, so a check always runs
the pinned version whatever a machine has on `PATH`. What the checks are and how to run them
is in [testing and checks](testing.md); the Python version is in
[the Python target](python-version.md).

## Installing uv

uv is the one tool that has to be on `PATH`. It needs no admin rights and does not touch the
system Python.

- Linux and WSL: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- Windows: `winget install --id=astral-sh.uv`, or
  `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`

Both installers put `uv` in a user directory and add it to `PATH` for new shells.

## Setting up the project

From the repository root:

```
uv sync --extra dev
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pre-commit install
```

- `uv sync --extra dev` reads `.python-version`, downloads that Python if the machine has
  none, creates `.venv` and installs the project (editable) plus the `dev` extra at exactly
  the versions in `uv.lock`. It is also the command to run again after a pin changes.
- Activating is for your own shell, so that `pytest`, `ruff` and the rest resolve to the
  project's copies when you type them. The hooks do not need it (below).
- `pre-commit install` makes every commit run the hooks.

## `uv.lock`

`uv.lock` is the exact resolution of `pyproject.toml`: every package, version and hash the
environment contains. It is committed, and only uv writes it. When a pin in
`pyproject.toml` changes, run `uv lock` (or `uv sync --extra dev`, which locks first) and
commit the new lock file with the change. Never edit it by hand; a lock file that does not
match `pyproject.toml` makes every hook fail with `--locked`, which is the intended signal.

## How the hooks find their tools

Every hook in `.pre-commit-config.yaml` runs as `uv run --locked --extra dev <tool>`. uv
first brings `.venv` up to date with `uv.lock`, then runs the tool from that environment.
Two consequences:

- the hooks do not depend on shell activation or on `PATH` order: a global `ruff` or
  `black` of another version is never what runs;
- a package installed into `.venv` by hand is removed at the next hook run, because the
  sync is exact. Add it to `pyproject.toml` instead.

CI (`.github/workflows/checks.yml`) does the same: `uv sync --locked --extra dev`, then
`uv run --locked --extra dev pre-commit run --all-files`, on Linux and Windows.

## What uv does not own

Dependencies stay in the standard `pyproject.toml` tables (`[project]` and
`[project.optional-dependencies]`). uv-specific extensions such as `[tool.uv.sources]` and
workspaces are not used, so `pip install -e ".[dev]"` into any Python 3.13 environment
remains a working fallback for the project itself. If uv is ever replaced, the work is
regenerating the lock file in the new tool's format and changing the hook invocations and
the CI step; the dependency declarations do not change.

## Two environments on Windows

A developer on Windows keeps two environments and uses each for one purpose.

| environment | created by | Python | for |
|---|---|---|---|
| `.venv` in the repository | `uv sync --extra dev` | 3.13, no ArcPy | `src/ag`, every check, every commit |
| a clone of `arcgispro-py3` | the ArcGIS Pro package manager, or `conda create --clone arcgispro-py3 --name <name>` | the Pro interpreter, with ArcPy | `pytest -m arcpy` and the legacy code |

- In an editor, select `.venv`'s interpreter when working on `src/ag`, `tests/` or `tools/`;
  select the Pro clone's interpreter when running ArcPy tests or the legacy packages.
- The Pro clone is managed with pip, not uv: `pip install -e .` there installs the project
  beside ArcPy, and `pip install pytest==<version>` adds pytest at the version pinned in
  `pyproject.toml`'s `dev` extra. It does not get the `dev` extra: the checks are never run
  from the Pro environment, so ruff, pyright, Black, import-linter and pre-commit have no
  place in it. **Never run `uv sync` in the Pro environment**; it would replace it with a
  Python that has no ArcPy.
- Commits are made from a shell where `uv` is on `PATH`; which interpreter the shell has
  active does not matter, because the hooks run through uv.

The default `arcgispro-py3` environment is read-only, which is why the clone exists.
