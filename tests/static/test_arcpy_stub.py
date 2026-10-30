"""The constrained ArcPy stub refuses what the session alone may touch: ADR-0018 AR-D23.

What: pyright, run on a probe this test writes under a configuration that puts the real
stub on `extraPaths` exactly as `pyproject.toml` does for the adapter root, refuses a
tool call, an `arcpy.env` access, the vendor exception name and a `from arcpy import`
of a toolbox or of `env`, exactly those lines and no other, and reports nothing on a
`getattr` or a `__dict__` lookup, which is why the static scan exists.

How: the probe is written to a temporary directory with its own `pyrightconfig.json`, so
it is never inside the hook's include list. The refused lines are the stub's own and
are pinned on every interpreter. A second probe holds the two submodule-import forms,
`import arcpy.management` and `from arcpy.management import Delete`: on an interpreter
without ArcPy they are unresolved imports and the tool reached through one is not
refused, which is pinned here and is why the scan refuses those forms; on an
interpreter with ArcPy they resolve past the stub, which the first run under the engine
records, so that part is asserted only where ArcPy is absent. Evidenced like an import
contract: a case in `tools/break_once/cases/` widens the stub with a toolbox and this
test must then fail.

Why: a stub that declares nothing is only a constraint while pyright applies it; this
test is the evidence that it does, independent of the editor a developer uses.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
STUB = ROOT / "stubs" / "arcpy_constrained"
REFUSED = "reportAttributeAccessIssue"
UNRESOLVED = "reportMissingImports"

PROBE = """\
import arcpy
from arcpy import env
from arcpy import management

arcpy.management.Delete("x")
arcpy.env.workspace = "x"
try:
    pass
except arcpy.ExecuteError:
    pass
found = getattr(arcpy, "management")
looked_up = arcpy.__dict__["management"]
"""
SUBMODULE_PROBE = """\
import arcpy
import arcpy.management
from arcpy.management import Delete

arcpy.management.Delete("x")
Delete("y")
"""


def line_of(probe: str, text: str) -> int:
    """1-based line of the probe line that reads exactly `text`."""
    return tuple(probe.splitlines()).index(text) + 1


def diagnostics(directory: Path, probe: str) -> list[tuple[str, int]]:
    """(rule, 1-based line) for every diagnostic pyright reports on `probe`."""
    (directory / "probe.py").write_text(probe, encoding="utf-8")
    config = directory / "pyrightconfig.json"
    config.write_text(
        json.dumps(
            {
                "include": ["probe.py"],
                "typeCheckingMode": "strict",
                "pythonVersion": "3.13",
                "extraPaths": [str(STUB)],
            }
        ),
        encoding="utf-8",
    )
    proc = subprocess.run(
        [sys.executable, "-m", "pyright", "--project", str(config), "--outputjson"],
        cwd=directory,
        capture_output=True,
        encoding="utf-8",
        check=False,
    )
    report: dict[str, Any] = json.loads(proc.stdout)
    return sorted(
        (str(item["rule"]), int(item["range"]["start"]["line"]) + 1)
        for item in report["generalDiagnostics"]
    )


def test_the_stub_refuses_tools_env_and_the_exception_name(tmp_path: Path) -> None:
    found = diagnostics(tmp_path, PROBE)

    refused = [line for rule, line in found if rule == REFUSED]
    assert refused == [
        line_of(PROBE, "from arcpy import env"),
        line_of(PROBE, "from arcpy import management"),
        line_of(PROBE, 'arcpy.management.Delete("x")'),
        line_of(PROBE, 'arcpy.env.workspace = "x"'),
        line_of(PROBE, "except arcpy.ExecuteError:"),
    ]
    behind_the_stub = {
        line_of(PROBE, 'found = getattr(arcpy, "management")'),
        line_of(PROBE, 'looked_up = arcpy.__dict__["management"]'),
    }
    assert [line for _, line in found if line in behind_the_stub] == []


@pytest.mark.skipif(
    importlib.util.find_spec("arcpy") is not None,
    reason="with ArcPy installed the submodule imports resolve past the stub",
)
def test_a_submodule_import_is_unresolved_and_its_tool_is_not_refused(
    tmp_path: Path,
) -> None:
    found = diagnostics(tmp_path, SUBMODULE_PROBE)

    unresolved = [line for rule, line in found if rule == UNRESOLVED]
    assert unresolved == [
        line_of(SUBMODULE_PROBE, "import arcpy.management"),
        line_of(SUBMODULE_PROBE, "from arcpy.management import Delete"),
    ]
    assert [line for rule, line in found if rule == REFUSED] == []
