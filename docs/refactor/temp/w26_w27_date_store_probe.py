"""By-hand probe for W26 and W27: what the engine's date stores do at the margins the
adapter now relies on.

Run inside the ArcPy image from the repository root, with `src` and the root on the path:

    python docs/refactor/temp/w26_w27_date_store_probe.py

W26: a `precision` 0 field holds whole seconds in a double of days, and about one value
in eight reads back a microsecond off (the date probe, 2026-11-08). `read_rows` reads such
a field to its nearest second. Whether the engine's own where clause, `field = date
'<that second>'`, selects the values that read back off is not shown, and if it does
not, `select` and `read_rows` disagree on the same row (ADR-0019 PC-D17). W27: a
`precision` 1 field holds the fraction; the engine documents it as milliseconds. Whether
a sub-millisecond part is truncated or rounded, and whether a millisecond-aligned value
reads back exact, is not shown either, and A33 asks the adapter to state its store's
precision and to truncate itself to it. The first run (2026-11-09) showed the
millisecond store reads back off by microseconds as the whole-second one does, so the
second question is W26's at the millisecond grain: whether engine equality on the
millisecond-rounded literal, in the compiler's six-digit form, selects those reads.

What it does, on synthetic data: a fresh file geodatabase; a table with one AddField
DATE field at `precision` 0 and a thousand whole-second values spread over several
years, read back, the reads with a fraction counted, and for each of those the rows the
engine selects with the rounded whole-second literal counted; a second table with the
field migrated to `precision` 1 and a thousand millisecond-aligned values plus a set of
sub-millisecond ones, read back and compared with the written value, with the value
truncated to the millisecond and with the value rounded to it, in bands; the same set in
the memory workspace for comparison. Counts only; no value is printed.

Run as a file, this module is `__main__`, and the engine rebinds `datetime` there when
the session opens, so every value is built before `open_session` and compared through
instance methods afterwards.
"""

from __future__ import annotations

import tempfile
from collections import Counter
from datetime import datetime, timedelta

from ag.adapters.arcpy.session import ArcpySession, open_session
from ag.adapters.arcpy.support.dataset_writer import (
    ADD_FIELD_TYPES,
    MIGRATION_TOOL,
    create_table,
    insert_rows,
)
from ag.ports import Field, FieldType
from tests.support.arcpy import gdb

FIELD = "stamp"
BASE = datetime(2019, 3, 7, 6, 15, 31)
WHOLE_SECONDS = [BASE + timedelta(seconds=7919 * i, days=3 * i) for i in range(1000)]
"""A thousand whole seconds over several years, built before the session opens."""

MILLISECONDS = [
    BASE + timedelta(seconds=7919 * i, days=3 * i, milliseconds=(i * 37) % 1000)
    for i in range(1000)
]
"""A thousand millisecond-aligned values."""

SUB_MILLISECOND = [
    BASE.replace(microsecond=part)
    for part in (
        1,
        400,
        499,
        500,
        501,
        999,
        123456,
        500123,
        500499,
        500500,
        500501,
        999400,
        999500,
        999600,
        999999,
    )
]
"""Values with a sub-millisecond part, on both sides of the half millisecond and of the
second."""


def literal(value: datetime) -> str:
    """The compiler's form: the fraction as six digits when there is one."""
    fraction = f".{value.microsecond:06d}" if value.microsecond else ""
    return f"date '{value:%Y-%m-%d %H:%M:%S}{fraction}'"


def to_millisecond(value: datetime) -> datetime:
    """`value` rounded to its nearest millisecond, the fraction store's grain."""
    rounded = value + timedelta(microseconds=500)
    return rounded.replace(microsecond=rounded.microsecond // 1000 * 1000)


def read_all(session: ArcpySession, path: str) -> list[object]:
    return [c[0] for c in gdb.read_cells(session, path=path, tokens=(FIELD,))]


def count_selected(session: ArcpySession, path: str, where: str) -> int:
    return len(gdb.read_cells(session, path=path, tokens=(FIELD,), where=where))


def whole_second_store(session: ArcpySession, workspace: str) -> None:
    """W26: the reads that come back off their second, and whether the engine's own
    equality on the rounded second selects them."""
    path = f"{workspace}/whole"
    create_table(session, path=path, fields=())
    session.run_tool(
        "management.AddField",
        in_table=path,
        field_name=FIELD,
        field_type=ADD_FIELD_TYPES[FieldType.DATE],
    )
    insert_rows(session, path=path, tokens=(FIELD,), rows=[(v,) for v in WHOLE_SECONDS])
    read = read_all(session, path)
    off = [v for v in read if getattr(v, "microsecond", 0)]
    print(f"== W26, precision 0, {len(WHOLE_SECONDS)} whole seconds written ==")
    print(f"read back: {len(read)}; with a microsecond part: {len(off)}")
    selected = Counter[str]()
    for value in off:
        rounded = (value + timedelta(microseconds=500_000)).replace(microsecond=0)
        hit = count_selected(session, path, f'"{FIELD}" = {literal(rounded)}')
        selected["selected by the rounded literal" if hit else "missed"] += 1
    print(f"of those, engine equality on the rounded second: {dict(selected)}")
    exact = [v for v in read if not getattr(v, "microsecond", 0)]
    sample = exact[:: max(1, len(exact) // 50)]
    hits = sum(
        count_selected(session, path, f'"{FIELD}" = {literal(v)}') for v in sample
    )
    print(f"control, {len(sample)} exact reads selected by their own literal: {hits}")


def fraction_store(session: ArcpySession, workspace: str, *, migrate: bool) -> None:
    """W27: what a fraction-holding store keeps of a millisecond-aligned and of a
    sub-millisecond value, against the written value, its truncation and its rounding
    to the millisecond."""
    path = f"{workspace}/fraction"
    create_table(session, path=path, fields=())
    session.run_tool(
        "management.AddField",
        in_table=path,
        field_name=FIELD,
        field_type=ADD_FIELD_TYPES[FieldType.DATE],
    )
    if migrate:
        session.run_tool(MIGRATION_TOOL, in_table=path, date_fields=FIELD)
    written = [*MILLISECONDS, *SUB_MILLISECOND]
    insert_rows(session, path=path, tokens=(FIELD,), rows=[(v,) for v in written])
    read = read_all(session, path)
    label = "precision 1" if migrate else "memory, precision 0"
    print(f"== W27, {label}, {len(written)} values written, {len(read)} read ==")
    bands = Counter[str]()
    for sent, got in zip(written, read, strict=True):
        if not hasattr(got, "replace"):
            bands["not a datetime"] += 1
            continue
        truncated = sent.replace(microsecond=sent.microsecond // 1000 * 1000)
        rounded = (sent + timedelta(microseconds=500)).replace(microsecond=0)
        rounded = rounded.replace(
            microsecond=((sent.microsecond + 500) // 1000 * 1000) % 1_000_000
        )
        kind = "millisecond-aligned" if sent.microsecond % 1000 == 0 else "sub-millisecond"
        if got == sent:
            bands[f"{kind}: exact"] += 1
        elif got == truncated:
            bands[f"{kind}: truncated to the millisecond"] += 1
        elif got == rounded:
            bands[f"{kind}: rounded to the millisecond"] += 1
        else:
            bands[f"{kind}: other"] += 1
    for key in sorted(bands):
        print(f"  {key}: {bands[key]}")
    noisy = [
        (sent, got)
        for sent, got in zip(written, read, strict=True)
        if sent.microsecond % 1000 == 0 and hasattr(got, "replace") and got != sent
    ]
    hits = sum(
        count_selected(session, path, f'"{FIELD}" = {literal(to_millisecond(got))}')
        for _, got in noisy
    )
    print(
        f"  millisecond-aligned reads that came back off: {len(noisy)}; selected by "
        f"engine equality on the millisecond-rounded literal: {hits}"
    )
    exact = [got for sent, got in zip(written, read, strict=True) if got == sent]
    sample = exact[:: max(1, len(exact) // 50)]
    control = sum(
        count_selected(session, path, f'"{FIELD}" = {literal(v)}') for v in sample
    )
    print(f"  control, {len(sample)} exact reads selected by their own literal: {control}")


def main() -> None:
    session = open_session()
    directory = tempfile.mkdtemp(prefix="w26_")
    workspace = gdb.file_gdb(session, directory=directory, name="probe")
    whole_second_store(session, workspace)
    fraction_store(session, workspace, migrate=True)
    fraction_store(session, "memory", migrate=False)


if __name__ == "__main__":
    main()
