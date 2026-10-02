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

## Editors

An editor formats and analyses with whatever copy of a tool it finds, usually its own
bundled one or a global install, not the version pinned in `pyproject.toml`. Point it at
`.venv` so that what it writes on save is what the hooks accept. The same applies to any
editor; the committed settings cover VS Code.

**VS Code.** `.vscode/extensions.json` recommends Python, Pylance, Ruff and Black Formatter;
`.vscode/settings.json` makes ruff the formatter for Python files and runs Black through uv.
Both files are committed; the rest of `.vscode/` is ignored. Select the interpreter per task:
`.venv` for `src/ag`, `tests/` and `tools/`; the cloned ArcGIS Pro environment for the legacy
packages, `tests_legacy/`, scratch scripts and `pytest -m arcpy`. Nothing else is configured
by hand: type checking, the strict scope and the ArcPy stub come from `pyproject.toml`, which
Pylance reads. The Ruff extension's `importStrategy` is `fromEnvironment`: it takes ruff from
the selected interpreter's environment, so it is the pinned one when `.venv` is selected and
the extension's bundled one under the Pro interpreter; that is harmless, because ruff is
force-excluded from the legacy scope and does nothing there.

**What you see.** Under `.venv`, `import arcpy` in a legacy file is reported as unresolved and
gets no completion; switch to the Pro interpreter for that work. A developer with no ArcPy
available at all (WSL, no Pro interpreter) gets no completion in the legacy packages, full
stop: pyright does not check them, so it is that one unresolved-import diagnostic and
nothing else. The fix is not to widen the constrained stub and not to add a `stubPath` to
`pyproject.toml`; either would apply a stub to code it was never written for. In
`src/ag/adapters/arcpy/` and `tests/support/arcpy/` the editor shows the constrained ArcPy
stub whichever interpreter is selected: a tool call, an `arcpy.env` access or
`arcpy.ExecuteError` is an error there, exactly as in the hooks. The response is never to
widen the stub for the editor's sake: a tool goes through `session.run_tool`, and a
non-tool name is added to `stubs/arcpy_constrained/` with its reason in the same pull
request. Elsewhere in `src/ag`, `tests/` and `tools/`, ArcPy is not importable at all, which
is what CI relies on.

**Formatting both scopes by hand:** `tools/format.sh`, which runs ruff over the new code and
Black over the legacy packages, both through uv. On Windows, run it from Git Bash or run its
two commands directly.
