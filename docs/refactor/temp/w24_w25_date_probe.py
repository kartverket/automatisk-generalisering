"""By-hand probe for W24 and W25: what the engine does with a date's fraction.

Run inside the ArcPy image from the repository root, with `src` and the root on the path,
and the `ag_timing` volume mounted at `/timing` for the one production field it describes:

    python docs/refactor/temp/w24_w25_date_probe.py [<path to a copied feature class>]

W24: the raw sources hold sub-second values in their editor-tracking date fields (the
timing run, 2026-11-06), yet a DATE field added with AddField to a fresh file geodatabase
rounded 12:00:00.5 to 12:00:01 (PR A). So the engine has date fields that keep a fraction
and the ones the adapter creates did not, and `write_rows` (slice 2a, A33.2) has to know
what makes the difference before it creates one. W25: whether a file geodatabase where
clause takes a fractional literal and compares it against a stored fraction, since W8
confirmed whole seconds only.

What it does, on synthetic data: creates a fresh file geodatabase and a table with one
AddField DATE field; inserts a fractional value and reads it back; prints every property
the Describe field object exposes for that field, so what might carry a precision shows
by name; tries the engine's high-precision migration tool on the field if the toolbox
has one, then inserts and reads back again; repeats the insert and read in the memory
workspace; and runs where clauses with a fractional and a whole-second literal in two
spellings against the stored rows. Last, when a path is given, it describes that
feature class's date fields the same way, names and properties only.

The data is not open: the production dataset, when given, is read from the working copy
on the `ag_timing` volume, never from the read-only `gis_files` mount, and nothing of it
is printed but field names and field properties. Nothing here asserts; the output is
pasted into the evidence, and A33.2's conformance round trip and the compiler's literal
test take their expectations from it in slice 2a.

Run as a file, this module is `__main__`, and the engine rebinds `datetime` there to the
module when the session opens (observed 2026-11-06), so nothing after `open_session`
consults that name: a value is printed through its `isoformat` attribute. The field is
named `stamp`, not a word any SQL dialect reserves.
"""

from __future__ import annotations

import sys
import tempfile
from collections.abc import Sequence
from datetime import datetime

from ag.adapters.arcpy.session import ArcpySession, open_session
from ag.adapters.arcpy.support.dataset_schema import FIELD_TYPES
from ag.adapters.arcpy.support.dataset_writer import create_table, insert_rows
from ag.ports import Field, FieldType
from tests.support.arcpy import gdb

FRACTION = datetime(2024, 1, 1, 12, 0, 0, 500000)
WHOLE = datetime(2024, 1, 1, 12, 0, 0)
FIELD = "stamp"
MIGRATION_TOOL = "management.MigrateDateFieldToHighPrecision"
"""The engine's documented tool name for the precision change; the probe reports when
the image's toolbox lacks it instead of failing."""

LITERALS = {
    "timestamp-fraction": "timestamp '2024-01-01 12:00:00.500'",
    "timestamp-whole": "timestamp '2024-01-01 12:00:00'",
    "date-fraction": "date '2024-01-01 12:00:00.500'",
    "date-whole": "date '2024-01-01 12:00:00'",
}


def field_properties(session: ArcpySession, path: str, name: str) -> dict[str, object]:
    """Every public property of the Describe field object `name` of `path`, matched
    without regard to case; the names Describe reports are printed first."""
    with session.guard("Describe"):
        import arcpy

        fields = list(arcpy.Describe(path).fields)
        print(f"describe reports fields {[f.name for f in fields]}")
        for found in fields:
            if found.name.lower() == name.lower():
                return {
                    key: getattr(found, key)
                    for key in dir(found)
                    if not key.startswith("_") and not callable(getattr(found, key))
                }
    return {}


def shown(value: object) -> object:
    """A date as ISO text, anything else as it is, without naming the datetime class."""
    isoformat = getattr(value, "isoformat", None)
    return isoformat() if callable(isoformat) else value


def read_back(session: ArcpySession, path: str, where: str | None = None) -> list[object]:
    return [
        cell[0]
        for cell in gdb.read_cells(session, path=path, tokens=(FIELD,), where=where)
    ]


def probe_table(session: ArcpySession, workspace: str, label: str) -> None:
    path = f"{workspace}/dates_{label}"
    create_table(session, path=path, fields=(Field(FIELD, FieldType.DATE),))
    print(f"== {label}: AddField DATE, fresh ==")
    print(f"field properties: {field_properties(session, path, FIELD)}")
    insert_rows(session, path=path, tokens=(FIELD,), rows=[(FRACTION,), (WHOLE,)])
    print(f"written {FRACTION.isoformat()} and {WHOLE.isoformat()}")
    print(f"read back {[shown(v) for v in read_back(session, path)]}")
    for name, literal in LITERALS.items():
        try:
            matched = read_back(session, path, where=f'"{FIELD}" = {literal}')
            print(f"where {name:20} -> {len(matched)} row(s)")
        except Exception as error:  # noqa: BLE001  a probe reports, it does not handle
            print(f"where {name:20} -> {type(error).__name__}")


def probe_migration(session: ArcpySession, workspace: str) -> None:
    path = f"{workspace}/dates_file"
    print(f"== {MIGRATION_TOOL} ==")
    try:
        session.run_tool(MIGRATION_TOOL, in_table=path, field=FIELD)
    except Exception as error:  # noqa: BLE001
        print(f"tool unavailable or refused: {type(error).__name__}")
        return
    print(f"field properties after: {field_properties(session, path, FIELD)}")
    insert_rows(session, path=path, tokens=(FIELD,), rows=[(FRACTION,)])
    print(f"read back {[shown(v) for v in read_back(session, path)]}")
    for name, literal in LITERALS.items():
        try:
            matched = read_back(session, path, where=f'"{FIELD}" = {literal}')
            print(f"where {name:20} -> {len(matched)} row(s)")
        except Exception as error:  # noqa: BLE001
            print(f"where {name:20} -> {type(error).__name__}")


def describe_production(session: ArcpySession, path: str) -> None:
    """The date fields of a working copy: names and Describe properties only."""
    if not path.startswith("/timing/"):
        print(f"refusing {path!r}: the probe reads the working copies under /timing only")
        return
    print(f"== production copy, date fields of {path.rsplit('/', 1)[-1]} ==")
    with session.guard("Describe"):
        import arcpy

        names = [f.name for f in arcpy.Describe(path).fields if f.type == "Date"]
    for name in names:
        print(f"{name}: {field_properties(session, path, name)}")
    print(f"port type for 'Date': {FIELD_TYPES.get('Date')}")


def main(argv: Sequence[str]) -> None:
    session = open_session()
    directory = tempfile.mkdtemp(prefix="w24_")
    workspace = gdb.file_gdb(session, directory=directory, name="probe")
    probe_table(session, workspace, "file")
    probe_migration(session, workspace)
    probe_table(session, "memory", "memory")
    if argv:
        describe_production(session, argv[0])


if __name__ == "__main__":
    main(sys.argv[1:])
