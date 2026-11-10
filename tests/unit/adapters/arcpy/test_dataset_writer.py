"""The write side's builders on the fake engine: a date field is migrated to the
precision that holds the fraction as it is added, and nothing else is. ADR-0019 PC-D17,
PC-D26."""

from __future__ import annotations

from ag.adapters.arcpy.session import ArcpySession
from ag.adapters.arcpy.support.dataset_writer import (
    MIGRATION_TOOL,
    add_fields,
    create_table,
)
from ag.ports import Field, FieldType
from tests.support.fake_arcpy import FRACTION_PRECISION, MEMORY_WORKSPACE, FakeEngine


def test_create_table_adds_every_field_and_migrates_the_date_ones(
    engine: FakeEngine, session: ArcpySession
) -> None:
    fields = (
        Field("name", FieldType.TEXT, 10),
        Field("seen", FieldType.DATE),
        Field("count", FieldType.LONG),
    )
    create_table(session, path="ws/t", fields=fields)
    assert engine.tool_names() == [
        "management.CreateTable",
        "management.AddField",
        "management.AddField",
        MIGRATION_TOOL,
        "management.AddField",
    ]
    migrated = [args for name, args in engine.calls if name == MIGRATION_TOOL]
    assert migrated == [{"in_table": "ws/t", "date_fields": "seen"}]
    precision = {f.name: f.precision for f in engine.datasets["ws/t"].fields}
    assert precision["seen"] == FRACTION_PRECISION
    assert precision["count"] != FRACTION_PRECISION


def test_a_date_field_in_the_memory_workspace_is_not_migrated(
    engine: FakeEngine, session: ArcpySession
) -> None:
    """The in-memory workspace keeps the fraction as it is and refuses the tool."""
    path = f"{MEMORY_WORKSPACE}/t"
    create_table(session, path=path, fields=(Field("seen", FieldType.DATE),))
    assert MIGRATION_TOOL not in engine.tool_names()


def test_add_fields_without_a_date_runs_no_migration(
    engine: FakeEngine, session: ArcpySession
) -> None:
    create_table(session, path="ws/t", fields=())
    add_fields(session, path="ws/t", fields=(Field("count", FieldType.LONG),))
    assert MIGRATION_TOOL not in engine.tool_names()
