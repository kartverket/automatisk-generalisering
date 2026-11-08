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
AddField DATE field; inserts a fractional value and reads it back; prints the named
properties of that field's `ListFields` object and the dataset-level Describe attributes
with scalar values, since the Field object showed no difference between a field that
rounds and one that keeps a fraction (third run); runs the engine's high-precision
migration tool on the table, prints what the migration changed, then inserts and reads
back again; repeats the insert and read in the memory workspace; and runs where clauses
with a fractional and a whole-second literal in two spellings against the stored rows.
Last, when a path is given, it describes that feature class's date fields the same way,
names and properties only, and prints the dataset attributes that differ from the fresh
table's.

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

import inspect
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
"""The engine's tool for the precision change; its signature on the image is
`(in_table, date_fields)`, `date_fields` required (fourth run)."""

LITERALS = {
    "timestamp-fraction": "timestamp '2024-01-01 12:00:00.500'",
    "timestamp-whole": "timestamp '2024-01-01 12:00:00'",
    "date-fraction": "date '2024-01-01 12:00:00.500'",
    "date-whole": "date '2024-01-01 12:00:00'",
}


PROPERTIES = (
    "name",
    "baseName",
    "aliasName",
    "type",
    "length",
    "precision",
    "scale",
    "isNullable",
    "required",
    "editable",
    "domain",
    "defaultValue",
    "isHighPrecision",
    "highPrecision",
    "dateFormat",
)
"""The Field properties asked for by name: the documented ones, then candidates for a
precision flag. A walk over `dir()` returned nothing on the image (2026-11-08), so the
dump names what it wants and reports what is absent."""


def field_properties(session: ArcpySession, path: str, name: str) -> dict[str, object]:
    """The named properties of the `ListFields` object `name` of `path`, matched without
    regard to case, with the object's type and its public attribute names printed once
    so the next run shows what the engine exposes."""
    missing = object()
    with session.guard("ListFields"):
        import arcpy

        fields = list(arcpy.ListFields(path))
        print(f"list fields reports {[f.name for f in fields]}")
        for found in fields:
            if found.name.lower() == name.lower():
                print(f"field object {type(found).__module__}.{type(found).__name__}")
                print(f"public attributes {[k for k in dir(found) if not k.startswith('_')]}")
                return {
                    key: value
                    for key in PROPERTIES
                    if (value := getattr(found, key, missing)) is not missing
                }
    return {}


DATASET_PROPERTIES = (
    # the documented table, geodatabase-table and feature-class properties
    "dataType",
    "datasetType",
    "hasOID",
    "OIDFieldName",
    "hasGlobalID",
    "globalIDFieldName",
    "aliasName",
    "modelName",
    "subtypeFieldName",
    "defaultSubtypeCode",
    "isVersioned",
    "canVersion",
    "isArchived",
    "changeTracked",
    "editorTrackingEnabled",
    "createdAtField",
    "editedAtField",
    "creatorField",
    "editorField",
    "isTimeInUTC",
    "versionedView",
    "featureType",
    "shapeType",
    "hasM",
    "hasZ",
    "hasSpatialIndex",
    "isCompressed",
    "workspaceType",
    "workspaceFactoryProgID",
    "release",
    "currentRelease",
    # candidates for a date precision flag, asked for by name
    "dateFieldsPrecision",
    "dateFieldsTimePrecision",
    "dateTimePrecision",
    "timePrecision",
    "hasHighPrecisionDateFields",
    "highPrecisionDateFields",
    "isHighPrecisionDate",
    "highPrecisionDate",
    "supportsHighPrecisionDates",
)
"""The Describe attributes asked for by name, since `dir()` lists nothing on a Describe
object (fourth run), as it listed nothing on a Field object. The workspace's are asked
of the dataset's workspace too."""

ABSENT = "<absent>"


def dataset_properties(session: ArcpySession, path: str) -> dict[str, object]:
    """The named Describe attributes of `path` and of its workspace, each present with
    its scalar value or marked absent: names and scalar values, never rows. Where the
    engine exposes a date precision of a dataset, it is here and not on the Field
    object (third run)."""
    found: dict[str, object] = {}
    with session.guard("Describe"):
        import arcpy

        for prefix, described in (
            ("", arcpy.Describe(path)),
            ("workspace.", arcpy.Describe(path.rsplit("/", 1)[0])),
        ):
            for key in DATASET_PROPERTIES:
                try:
                    value = getattr(described, key)
                except Exception:  # noqa: BLE001  a property this kind lacks
                    found[prefix + key] = ABSENT
                    continue
                if isinstance(value, bool | int | float | str):
                    found[prefix + key] = value if len(str(value)) < 80 else "<long>"
                else:
                    found[prefix + key] = f"<{type(value).__name__}>"
    return found


def present(properties: dict[str, object]) -> dict[str, object]:
    """The attributes a dataset has, for printing without the absent ones."""
    return {key: value for key, value in properties.items() if value != ABSENT}


def differing(
    a: dict[str, object], b: dict[str, object]
) -> dict[str, tuple[object, object]]:
    """The keys whose values differ, or that one side lacks."""
    return {
        key: (a.get(key, "<absent>"), b.get(key, "<absent>"))
        for key in sorted(set(a) | set(b))
        if a.get(key, "<absent>") != b.get(key, "<absent>")
    }


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


def probe_migration(session: ArcpySession, workspace: str) -> dict[str, object]:
    """The migration tool on the fresh table, the table alone as its argument; on a
    refusal the tool's signature is printed so the next run can call it right. Returns
    the dataset properties after the attempt."""
    path = f"{workspace}/dates_file"
    print(f"== {MIGRATION_TOOL} ==")
    try:
        session.run_tool(MIGRATION_TOOL, in_table=path, date_fields=FIELD)
    except Exception as error:  # noqa: BLE001
        # A synthetic table: the message carries no data and says what the tool wanted.
        print(f"tool unavailable or refused: {type(error).__name__}: {error}")
        with session.guard("signature"):
            import arcpy

            tool = getattr(arcpy.management, MIGRATION_TOOL.split(".")[1], None)
            print(f"signature: {None if tool is None else inspect.signature(tool)}")
        return dataset_properties(session, path)
    after = dataset_properties(session, path)
    print(f"field properties after: {field_properties(session, path, FIELD)}")
    insert_rows(session, path=path, tokens=(FIELD,), rows=[(FRACTION,)])
    print(f"read back {[shown(v) for v in read_back(session, path)]}")
    for name, literal in LITERALS.items():
        try:
            matched = read_back(session, path, where=f'"{FIELD}" = {literal}')
            print(f"where {name:20} -> {len(matched)} row(s)")
        except Exception as error:  # noqa: BLE001
            print(f"where {name:20} -> {type(error).__name__}")
    return after


def describe_production(
    session: ArcpySession, path: str, *, fresh: dict[str, object]
) -> None:
    """The date fields of a working copy, names and Field properties only, and the
    dataset-level Describe attributes that differ from the fresh table's."""
    if not path.startswith("/timing/"):
        print(f"refusing {path!r}: the probe reads the working copies under /timing only")
        return
    print(f"== production copy, date fields of {path.rsplit('/', 1)[-1]} ==")
    with session.guard("ListFields"):
        import arcpy

        names = [f.name for f in arcpy.ListFields(path) if f.type == "Date"]
    for name in names:
        print(f"{name}: {field_properties(session, path, name)}")
    print(f"port type for 'Date': {FIELD_TYPES.get('Date')}")
    production = dataset_properties(session, path)
    print(f"dataset attributes, production: {present(production)}")
    print(
        "differing from the fresh table (fresh, production): "
        f"{differing(fresh, production)}"
    )


def main(argv: Sequence[str]) -> None:
    session = open_session()
    directory = tempfile.mkdtemp(prefix="w24_")
    workspace = gdb.file_gdb(session, directory=directory, name="probe")
    probe_table(session, workspace, "file")
    before = dataset_properties(session, f"{workspace}/dates_file")
    print(f"dataset attributes, fresh table: {present(before)}")
    after = probe_migration(session, workspace)
    print(
        "dataset attributes changed by the migration (before, after): "
        f"{differing(before, after)}"
    )
    probe_table(session, "memory", "memory")
    memory = dataset_properties(session, "memory/dates_memory")
    print(
        "dataset attributes, memory table, differing from fresh (fresh, memory): "
        f"{differing(before, memory)}"
    )
    if argv:
        describe_production(session, argv[0], fresh=before)


if __name__ == "__main__":
    main(sys.argv[1:])
