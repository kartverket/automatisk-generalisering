"""The facade hands a wrapped port out as the port type, and pyright still refuses a
non-conformer there: the one `cast` erases nothing a caller relies on.

What: pyright, run on a fixture this test writes, accepts a conforming adapter through
`wrap` and refuses a non-conforming one at the two places a wrapped port is handed out,
an annotated assignment and a dataclass field, which is the Toolbox's shape. The bare
call, with no declared type to meet, reports nothing: the type variable solves to a union
of the Protocol and the adapter, and the fixture records that gap by asserting the exact
diagnostics, so a change in the checker that closes it is noticed.

How: as `test_row_shape_typing.py`: the fixture is written to a temporary directory, so
the non-conformer is never in the pyright hook's include list, and it imports the real
`wrap` through the installed package.

Why: `wrap` returns `P` through a `cast`; if that `cast` or the signature ever erased the
type, every hand-out would type-check and nothing in strict mode would say so.
"""

from __future__ import annotations

from pathlib import Path

from tests.static.test_row_shape_typing import diagnostics

FIXTURE = """\
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from ag.core.handles import In, Out
from ag.lineage.facade import wrap
from ag.ports.row_shape import Cardinality, Ids, Rows, row_shape


class Ops(Protocol):
    @row_shape(output=Rows(Cardinality.ONE, Ids.CARRY, subject="input"))
    def copy(self, *, input: In, output: Out) -> None: ...


class Conforming:
    def copy(self, *, input: In, output: Out) -> None: ...


class NotConforming:
    def copy(self, *, input: In) -> None: ...


@dataclass(frozen=True)
class Box:
    ops: Ops


accepted: Ops = wrap(Ops, Conforming())
boxed_ok = Box(ops=wrap(Ops, Conforming()))
bare = wrap(Ops, NotConforming())
refused: Ops = wrap(Ops, NotConforming())
boxed = Box(ops=wrap(Ops, NotConforming()))
"""
LINES = FIXTURE.splitlines()
REFUSED_LINE = LINES.index("refused: Ops = wrap(Ops, NotConforming())") + 1
BOXED_LINE = LINES.index("boxed = Box(ops=wrap(Ops, NotConforming()))") + 1


def test_a_non_conformer_is_refused_where_the_wrapped_port_is_handed_out(
    tmp_path: Path,
) -> None:
    fixture = tmp_path / "fixture.py"
    fixture.write_text(FIXTURE, encoding="utf-8")
    assert diagnostics(fixture) == [
        ("reportAssignmentType", REFUSED_LINE),
        ("reportArgumentType", BOXED_LINE),
    ], (
        "pyright must refuse the non-conformer at both hand-outs, accept the conformer "
        "everywhere, and report nothing on the bare call; anything else means wrap's "
        "type changed"
    )
