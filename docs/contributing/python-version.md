# The Python target

**Status:** CURRENT.

**The target is Python 3.13.** There is no fixed lower constraint. The project follows its
runtimes upward: the target is the lowest Python minor version across the supported runtimes,
which are the ArcGIS Pro interpreter the team develops with and the Linux image. Nothing is in
production yet, so no older build constrains it.

## Where it is stated

Four settings state the target, and they always change together:

| setting | where |
|---|---|
| `requires-python = ">=3.13"` | `pyproject.toml`, `[project]` |
| `pythonVersion = "3.13"` | `pyproject.toml`, `[tool.pyright]` |
| `target-version = "py313"` | `pyproject.toml`, `[tool.ruff]` |
| `3.13` | `.python-version`: the interpreter uv creates `.venv` with, locally and in CI |

Black, which checks only the legacy packages until they are migrated, infers its target from
`requires-python` and needs no setting of its own.

CI runs every check on that version, on both `ubuntu-latest` and `windows-latest`
(`.github/workflows/checks.yml`).

## Raising the floor

Raise it only when every supported runtime has moved. In one pull request:

1. change the four settings;
2. run the full check set (`pre-commit run --all-files`), which includes pyright and the
   pure-core test suite;
3. say in the pull request which runtime had been holding the floor.

Do not raise it for a language feature.

## One thing a raise must not do

Do not convert the `In` and `Out` handle markers to PEP 695 `type` statements. With a
`TypeAliasType` the `Annotated` metadata is hidden from `@operation`, which then classifies no
parameter at all. A unit test pins this.
