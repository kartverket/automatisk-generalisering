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
- Activating is optional and only for your own shell: it makes `pytest`, `ruff` and the rest
  resolve to the project's copies when you type them. Nothing else needs it. The hooks run
  through uv whether a shell is activated or not (below), and scripts that use ArcPy run with
  the ArcGIS Pro interpreter, never from `.venv` (see
  [running legacy scripts](#running-legacy-scripts)).
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

- the hooks do not depend on shell activation or on `PATH` order: a global `ruff` of
  another version is never what runs;
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

A developer on Windows uses two interpreters, each for one purpose.

| interpreter | comes from | for |
|---|---|---|
| `.venv` in the repository | `uv sync --extra dev` | `src/ag`, every check, every commit |
| the ArcGIS Pro interpreter, the default `arcgispro-py3` environment | the ArcGIS Pro install (`C:\ArcGIS_Pro\bin\Python\envs\arcgispro-py3` on the team's machines) | legacy scripts, `tests_legacy/`, scratch scripts |

- Nothing is installed into the Pro environment, by pip or by uv: Esri's package manager
  treats it as read-only, and a Pro upgrade replaces it. A legacy script needs no install
  (below), and `tests_legacy/` needs nothing the Pro environment does not already ship
  ([testing and checks](testing.md)). The one uv command that can write into it is
  `uv pip install --python <pro python>` without `--target`; do not run it. `uv sync` only
  ever touches `.venv`, whichever interpreter an editor or a shell has selected.
- Commits are made from a shell where `uv` is on `PATH`; which interpreter the shell has
  active does not matter, because the hooks run through uv.
- The environment for `pytest -m arcpy` is open, see B23 in the design record: no test
  carries the marker yet, and the first ones arrive with the ArcPy adapter. Until then no
  run needs `ag` or pytest beside ArcPy.

## Running legacy scripts

The legacy packages at the repository root (`generalization/`, `data_orchestrator/`,
`composition_configs/` and the rest) are not installed into any environment;
`pyproject.toml` installs only `src/ag`. A script among them runs when four things hold:

| requirement | why |
|---|---|
| the ArcGIS Pro interpreter | the scripts import ArcPy, which `.venv` does not have |
| the repository root on the import path | the scripts import the legacy packages by their top-level names |
| the repository root as the working directory | `paths.py` reads `.env` from the working directory |
| a `.env` in the repository root | `paths.py` and the configuration modules require the variables listed in `.env.example` |

Create `.env` once per clone by copying `.env.example` and filling in your own paths, without
quotes: `paths.py` keeps quote characters as part of the value. `PYTHONPATH` is the clone's
root. `.env` is ignored by git.

From a terminal in the repository root, run the script as a module, with dots in place of
slashes and no `.py`. The interpreter path below is the team's usual ArcGIS Pro install; if
the command is not found, check where ArcGIS Pro is installed on your machine.

```
C:\ArcGIS_Pro\bin\Python\envs\arcgispro-py3\python.exe -m generalization.n100.road.data_preparation_2
```

`-m` puts the working directory on the import path, so nothing else is needed. Running the
file by its path puts only the script's own folder there, and the first legacy import fails
unless `PYTHONPATH` is set to the repository root, as the VS Code terminal opt-in does. For
VS Code, see [VS Code setup](vscode.md).

## Editors

An editor formats and analyses with whatever copy of a tool it finds, usually its own
bundled one or a global install, not the version pinned in `pyproject.toml`. Point it at
`.venv` so that what it writes on save is what the hooks accept. The same applies to any
editor; the committed settings cover VS Code. Which interpreter runs a script is a separate
choice (see [running legacy scripts](#running-legacy-scripts)).

**VS Code.** The committed `.vscode/` files, the extensions, choosing the interpreter, running
scripts and the optional terminal setting are in [VS Code setup](vscode.md).

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

**Formatting by hand:** `tools/format.sh` sorts imports and formats the whole repository with
the pinned ruff through uv. On Windows, run it from Git Bash or run its two commands directly.

## One formatter, and lint on the legacy packages

Ruff formats and lints the whole repository; there is no second formatter. The legacy
packages were reformatted once when ruff became the formatter, as a whitespace-only commit
that changed no file's syntax tree; its SHA is in `.git-blame-ignore-revs`, so run
`git config blame.ignoreRevsFile .git-blame-ignore-revs` once per clone and `git blame`
skips it.

Lint runs on the legacy packages too, with two rules held back there: `F401` (unused import)
and `I001` (import order) have autofixes that remove or reorder imports, and the legacy
convention is side-effect imports, so `pyproject.toml` ignores them under the legacy
directories. Below those entries sits a per-file baseline: the findings that were present when
linting was switched on, listed file by file with the rules they fail. A baseline entry is
removed when its file is cleaned, and nothing else is exempt: a new file, or a new finding in
a file not on the list, fails the hook. The hooks only report; no rule is fixed
automatically, and the editor settings run no fixes on save.
