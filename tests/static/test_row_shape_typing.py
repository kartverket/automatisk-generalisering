"""The decorator keeps the Protocol's structural type: ADR-0017 RS-3, under pyright.

What: pyright, run on a fixture this test writes, accepts a class that conforms to a
Protocol whose method carries `@row_shape` and refuses one that does not, reporting
exactly the non-conforming assignment.

How: the fixture is written to a temporary directory, so the deliberate non-conformer is
never inside the pyright hook's include list, and it imports the real decorator through
the installed package. The project configuration and the repository root are passed
explicitly, so the result does not depend on where pytest was started. Evidenced like an
import contract: a case in `tools/break_once/cases/` erases the decorator's type
variables and this test must then fail.

Why: a decorator that erases the method's type makes every assignment to the Protocol
type-check. Strict mode cannot show that, because an erased type is a declared `Any`,
not an unknown, so the only evidence is a non-conformer pyright still refuses.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "pyproject.toml"

FIXTURE = """\
from __future__ import annotations

from typing import Protocol

from ag.core.handles import In, Out
from ag.ports.row_shape import Cardinality, Ids, Rows, row_shape


class Ops(Protocol):
    @row_shape(output=Rows(Cardinality.ONE, Ids.CARRY, subject="input"))
    def copy(self, *, input: In, output: Out) -> None: ...


class Conforming:
    def copy(self, *, input: In, output: Out) -> None: ...


class NotConforming:
    def copy(self, *, input: In) -> None: ...


accepted: Ops = Conforming()
refused: Ops = NotConforming()
"""
REFUSED_LINE = FIXTURE.splitlines().index("refused: Ops = NotConforming()") + 1


def diagnostics(fixture: Path) -> list[tuple[str, int]]:
    """(rule, 1-based line) for every diagnostic pyright reports on `fixture`."""
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pyright",
            "--project",
            str(PROJECT),
            "--outputjson",
            str(fixture),
        ],
        cwd=ROOT,
        capture_output=True,
        encoding="utf-8",
        check=False,
    )
    report: dict[str, Any] = json.loads(proc.stdout)
    return [
        (str(item["rule"]), int(item["range"]["start"]["line"]) + 1)
        for item in report["generalDiagnostics"]
    ]


def test_the_decorated_protocol_still_refuses_a_non_conformer(tmp_path: Path) -> None:
    fixture = tmp_path / "fixture.py"
    fixture.write_text(FIXTURE, encoding="utf-8")
    assert diagnostics(fixture) == [("reportAssignmentType", REFUSED_LINE)], (
        "pyright must refuse exactly the non-conforming assignment and accept the "
        "conforming one; anything else means the decorator changed the method's type"
    )
