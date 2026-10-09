# VS Code setup

**Status:** CURRENT.

How to set up VS Code to edit this repository and run its scripts. The editor-neutral parts
(uv, the checks, what a script run needs) are in [setup and toolchain](toolchain.md); this
page maps them to VS Code.

## Extensions

When the repository is opened, VS Code offers to install the extensions that
`.vscode/extensions.json` recommends: Python, Pylance and Ruff. The Python extension brings
two more with it: Python Debugger, which runs `.vscode/launch.json`, and Python Environments,
which manages the interpreter selection.

## Open the repository folder

Open the repository root itself (**File > Open Folder**), not a folder above it. VS Code reads
`.vscode/` and resolves `${workspaceFolder}` from the folder that is open; opened one level
up, neither the committed settings nor the run configuration are used.

## The committed files

| file | what it does |
|---|---|
| `.vscode/extensions.json` | recommends Python, Pylance and Ruff |
| `.vscode/settings.json` | ruff formats every Python file on save and organises its imports; Pylance analyses open files only |
| `.vscode/launch.json` | the run configuration described under [running scripts](#running-scripts) |

The rest of `.vscode/` is ignored by git. Personal settings go in your user settings, not in
`.vscode/settings.json`. Selecting an interpreter can add a `python-envs.*` line to
`.vscode/settings.json`; do not commit it.

## Choosing the interpreter

Select the interpreter per task with **Python: Select Interpreter** (`Ctrl+Shift+P`); the
status bar shows the current one. The choice is stored per machine and folder, not in the
repository.

| work | interpreter |
|---|---|
| legacy scripts, `tests_legacy/`, scratch scripts | ArcGIS Pro |
| `src/ag`, `tests/`, `tools/` | `.venv` |
| `pytest -m arcpy` | open until the first marked test lands: B23 in the design record (The environment for `pytest -m arcpy`)|

Once `uv sync` has created `.venv`, VS Code tends to select it on its own; switch to the
ArcGIS Pro interpreter before running a legacy script. If it is not listed, choose **Enter
interpreter path** and give `C:\ArcGIS_Pro\bin\Python\envs\arcgispro-py3\python.exe`, the
team's usual install.

Nothing else is configured by hand: type checking, the strict scope and the ArcPy stub come
from `pyproject.toml`, which Pylance reads. The Ruff extension takes ruff from the selected
interpreter's environment: the pinned version under `.venv`, the extension's bundled version
under the ArcGIS Pro interpreter. The two can format differently; if the `ruff-format` hook
reports a file you saved under the ArcGIS Pro interpreter, run `tools/format.sh`.

## Running scripts

Create `.env` first (see [running legacy scripts](toolchain.md#running-legacy-scripts)) and
select the ArcGIS Pro interpreter. Then, with the script open:

- `F5` runs it in the debugger;
- `Ctrl+F5` runs it without the debugger.

Both use the configuration **Python: current file (repo root on path)**; pick it in the Run
and Debug view (`Ctrl+Shift+D`) if VS Code asks. It runs the open file with the selected
interpreter, from the repository root, with the repository root on `PYTHONPATH` and `.env`
loaded. These settings apply to that run only; terminals and the checks are unaffected.

The run button in the editor's top-right corner does not use `launch.json`. Without the
setting below it fails on the first legacy import.

## Optional: `.env` in terminals

The Python Environments extension loads `.env` into VS Code terminals only when
`python.terminal.useEnvFile` is `true`; the default is `false`, and VS Code warns that "an
environment file is configured but terminal environment injection is disabled". Turning it on
makes the run button and `python path\to\script.py` in a VS Code terminal work, because
`PYTHONPATH` from `.env` reaches them.

The cost: every VS Code terminal gets every variable in `.env`, including the terminals where
you run `uv run ...` or `git commit`. The legacy packages are then importable there, which
they never are in CI, so a change that imports legacy code from `src/ag`, `tests/` or `tools/`
can pass the checks locally and fail in CI. Commit from a terminal outside VS Code, or run the
full check there before pushing, to keep the local result identical to CI. The setting also
applies to every other project you open that has a `.env`.

To turn it on, run **Preferences: Open User Settings (JSON)** and add:

```json
"python.terminal.useEnvFile": true
```

Do not add it to `.vscode/settings.json`. `PYTHONPATH` in `.env` must be your clone's root,
without quotes. Open a new terminal afterwards; `$env:PYTHONPATH` should print the
repository root.

## Committing

The hooks run through uv whichever interpreter is selected, so neither the interpreter nor
activating `.venv` matters for a commit.

## Troubleshooting

| symptom | cause | fix |
|---|---|---|
| `No module named 'data_orchestrator'` (or another legacy package) | the repository root is not on the import path: the run button or `python <file>` without the optional setting, or VS Code opened on a parent folder | run with `F5` or `Ctrl+F5`, or open the repository folder itself |
| `No module named 'arcpy'` | `.venv` is the selected interpreter | select the ArcGIS Pro interpreter |
| `Required environment variable ... is not set!` | no `.env` in the repository root, a key missing or misspelt, or the run did not start in the repository root | copy `.env.example` to `.env` and fill it in; run with `F5` or from the repository root |
| a path from `.env` fails and contains `"` | quotes around the value in `.env` | remove the quotes |
| warning: "An environment file is configured but terminal environment injection is disabled" | expected: `.env` exists and the optional setting is off | ignore it, or turn the setting on |
| a changed `.env` value is not picked up | terminals keep the previous values ([vscode-python-environments#1838](https://github.com/microsoft/vscode-python-environments/issues/1838)) | **Developer: Reload Window** |
| `No module named /generalization/...` | `-m` was given a file path | use the module name: `-m generalization.n100.road.data_preparation_2` |
