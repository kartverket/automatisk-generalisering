# Testing and checks

**Status:** CURRENT.

## The one list of checks

`.pre-commit-config.yaml` is the one list of checks. A commit, a manual run and a pull request
all run that file, and every hook runs its tool through uv at the version pinned in
`pyproject.toml`'s `dev` extra, so a pull request runs exactly what a commit runs and no
machine's `PATH` decides which version that is ([setup and toolchain](toolchain.md)). The
checks are:

| hook | what it covers |
|---|---|
| `ruff format --check` | formatting of every Python file |
| `ruff check` | pyflakes, import order and `SLF001` on `src/ag/generalization/`; on the legacy packages `F401` and `I001` are held back and a per-file baseline applies ([setup and toolchain](toolchain.md)) |
| `pyright` | strict type checking of `src/`, `tests/`, `tools/` |
| `lint-imports` | the import contracts in `.importlinter` |
| `tools/scan_sources.py` | environment reads outside `ag/runtime/env.py`; imports by string outside `ag/runtime/stage_ref.py` |
| `pytest -m "not arcpy"` | every test that does not need ArcPy |
| `check_consistency.py`, `check_terminology.py` | the design record's internal consistency |

### Setting up

Once, from the repository root, with uv installed ([setup and toolchain](toolchain.md)):

```
uv sync --extra dev
pre-commit install
```

The first line creates `.venv` with `ag` editable and the pinned tools; the second makes every
commit run the hooks. The hooks run through uv, so they need `uv` on `PATH` and nothing else;
activating `.venv` is only for typing the tools' names yourself.

### Running checks by hand

All of them, over the whole tree:

```
pre-commit run --all-files
```

One of them, by its id from `.pre-commit-config.yaml`:

```
pre-commit run pyright --all-files
pre-commit run pytest --all-files
```

Or the tool directly, which is the same thing: `pyright`, `lint-imports`,
`pytest -m "not arcpy"`, `ruff check src tests tools`.

## Test layout

```
tests/
  unit/            mirrors src/ag by directory; no engine
  static/          contract tests: import contracts, source scans, row-shape check, port
                   matrix, arcpy-blocked import guard, terminology-matches-code
  conformance/     one module per port method group, parametrized over adapters; the
                   in-memory adapter always, ArcPy under the marker
  goldens/         recorded artifacts and their replay tests
  invariance/      K = 4 against K = 16, local processes; ArcPy
  smoke/           one real stage end to end; ArcPy
  support/         engine-neutral builders, the adapter fixture, local_scope, .gdb builders
  fixtures/        example_pipelines/ (inert until the modules it imports exist), row fixtures
tests_legacy/      the tests of the legacy packages
```

`pyproject.toml` registers the `arcpy` marker and the `testpaths` above, and sets no
`addopts`: what a run selects is always visible on its command line.

## Where each kind of test runs

| tests | pre-commit and CI (both runners) | ArcGIS Pro environment | the image |
|---|---|---|---|
| unit, static, conformance under the in-memory adapter | yes | yes | yes |
| conformance under ArcPy, goldens that replay the engine, invariance, smoke | never | yes, on request | yes, gating image promotion (later) |
| `tests_legacy/` | never | by hand | never |

Neither GitHub runner has ArcPy, on purpose: an `import arcpy` anywhere outside the adapter
fails there, which enforces the no-ArcPy-in-core rule for free.

## The `arcpy` marker

A test that needs ArcPy is marked `@pytest.mark.arcpy`. `tests/conftest.py` gives the marker
the same behaviour in every environment:

- **A bare `pytest` where ArcPy cannot be imported** skips every marked test, with the import
  error as the skip reason. So `pytest` works in WSL, in CI and under any Windows Python.
- **`pytest -m arcpy` where ArcPy cannot be imported** ends the session at once with exit
  code 1. A misconfigured Pro environment cannot report green with every ArcPy test skipped.
- **An unmarked test that imports ArcPy** is not touched: it fails on its `ImportError`. That
  is the property the marker exists for. Mark the test, or stop importing ArcPy.

The pre-commit hook and CI run `pytest -m "not arcpy"` and so exclude by marker, not by the
auto-skip; they select the same tests on every machine, including one where ArcPy is
importable. The auto-skip is for bare manual runs only.

## Running the ArcPy tests

They run under an ArcGIS Pro Python environment. The default `arcgispro-py3` environment is
read-only, so clone it once in the ArcGIS Pro package manager (or with `conda create --clone
arcgispro-py3 --name <name>`), activate the clone, and install the project and pytest into
it with pip, at the pytest version pinned in `pyproject.toml`:

```
pip install -e .
pip install pytest==<version>
pytest -m arcpy
```

The clone gets nothing else: the checks are never run from the Pro environment
([setup and toolchain](toolchain.md), two environments).

`pytest -m arcpy` runs the marked tests only; a bare `pytest` in that environment runs
everything. Later the same tests run in the Linux image, where the conformance suite gates
image promotion.

## `tests_legacy/`

The tests of the legacy packages. They are not collected by a bare `pytest` (they are outside
`testpaths`), are not type-checked, and are formatted and linted by ruff like the packages they
test.
Run them by hand under the ArcGIS Pro environment, from the repository root:

```
pytest tests_legacy
```

They are deleted with the legacy code they test.
