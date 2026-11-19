"""`read_rows` and the catalog against the port's contract, on every adapter.

What: every field type round-trips as the value the case wrote, a date with its
fraction, since every store an adapter creates holds one; every geometry kind the port
holds comes back as the kind that was written, which is the one question about kinds an
engine answers and the one place it fails; an undeclared field is refused before any row
is read; a table has no geometry and an empty field list yields empty attributes.
ADR-0019 PC-D17, PC-D22, PC-D25.

The catalog: `exists` and `data_type_of` on a seeded feature class, a seeded table, a
missing path and a workspace path; `create_workspace`, over every `WorkspaceFormat`
member, makes an absent workspace present, refuses a path something is already at before
anything changes, and names the adapter's tool when the parent is missing. ADR-0019
PC-D31, PC-D32, PC-R8.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ag.core.handles import ScratchHandle
from ag.core.types import DataType
from ag.ports import Row
from ag.ports.attributes import FieldName
from ag.ports.errors import EngineError, PortContractError
from ag.ports.workspace_format import WorkspaceFormat
from tests.conformance.conftest import Adapter
from tests.support.cases import (
    DatasetCase,
    lookup,
    multilines,
    multipoints,
    points,
    polygons,
    roads,
    stamps,
)

KIND_CASES = [roads(), multilines(), multipoints(), points(), polygons()]
FORMATS = list(WorkspaceFormat)


def _rows(
    adapter: Adapter, handle: ScratchHandle, fields: tuple[FieldName, ...]
) -> list[Row]:
    return list(adapter.table_ops.read_rows(input=handle, fields=fields))


@pytest.mark.parametrize(
    "case", [roads(), lookup(), stamps()], ids=["feature-class", "table", "fraction"]
)
def test_read_rows_round_trips_every_field_type(
    adapter: Adapter, case: DatasetCase
) -> None:
    seeded = adapter.seed(case)
    fields = tuple(field.name for field in case.schema.fields)
    rows = _rows(adapter, seeded.handle, fields)
    assert [dict(r.attributes) for r in rows] == [dict(r.attributes) for r in case.rows]


@pytest.mark.parametrize("case", KIND_CASES, ids=[c.name for c in KIND_CASES])
def test_read_rows_round_trips_each_geometry_kind(
    adapter: Adapter, case: DatasetCase
) -> None:
    seeded = adapter.seed(case)
    rows = _rows(adapter, seeded.handle, ("name",))
    assert [r.geometry for r in rows] == [r.geometry for r in case.rows]


def test_read_rows_refuses_an_undeclared_field_before_reading(adapter: Adapter) -> None:
    seeded = adapter.seed(roads())
    with pytest.raises(PortContractError, match="colour"):
        list(adapter.table_ops.read_rows(input=seeded.handle, fields=("colour",)))


def test_read_rows_of_a_table_has_no_geometry_and_no_fields_yields_empty_attributes(
    adapter: Adapter,
) -> None:
    seeded = adapter.seed(lookup())
    rows = _rows(adapter, seeded.handle, ("label",))
    assert [dict(r.attributes) for r in rows] == [{"label": "one"}, {"label": "two"}]
    assert all(r.geometry is None for r in rows)
    assert [dict(r.attributes) for r in _rows(adapter, seeded.handle, ())] == [{}, {}]


def _workspace_path(directory: Path, fmt: WorkspaceFormat, *parts: str) -> str:
    """A workspace path under `directory`, as the format spells it, with `parts` as
    folders between the two."""
    return f"{'/'.join((str(directory), *parts))}/fresh{fmt.suffix}"


def test_exists_and_data_type_of_answer_a_feature_class_and_a_table(
    adapter: Adapter,
) -> None:
    feature_class = adapter.seed(roads()).handle
    table = adapter.seed(lookup()).handle
    assert adapter.table_ops.exists(input=feature_class)
    assert adapter.table_ops.exists(input=table)
    assert adapter.table_ops.data_type_of(input=feature_class) is DataType.FEATURE_CLASS
    assert adapter.table_ops.data_type_of(input=table) is DataType.TABLE


def test_a_missing_path_does_not_exist_and_has_no_data_type(adapter: Adapter) -> None:
    absent = adapter.handle("absent")
    assert not adapter.table_ops.exists(input=absent)
    with pytest.raises(PortContractError) as caught:
        adapter.table_ops.data_type_of(input=absent)
    assert caught.value.context.handle == absent.path


@pytest.mark.parametrize("fmt", FORMATS, ids=[f.name for f in FORMATS])
def test_a_workspace_exists_and_is_refused_as_a_dataset(
    adapter: Adapter, tmp_path: Path, fmt: WorkspaceFormat
) -> None:
    path = _workspace_path(tmp_path, fmt)
    adapter.table_ops.create_workspace(path=path, fmt=fmt)
    at_workspace = adapter.handle("workspace").materialize(path)
    assert adapter.table_ops.exists(input=at_workspace)
    with pytest.raises(PortContractError) as caught:
        adapter.table_ops.data_type_of(input=at_workspace)
    assert caught.value.context.handle == path


@pytest.mark.parametrize("fmt", FORMATS, ids=[f.name for f in FORMATS])
def test_create_workspace_makes_an_absent_workspace_present(
    adapter: Adapter, tmp_path: Path, fmt: WorkspaceFormat
) -> None:
    path = _workspace_path(tmp_path, fmt)
    assert not adapter.workspace_present(path)
    adapter.table_ops.create_workspace(path=path, fmt=fmt)
    assert adapter.workspace_present(path)


@pytest.mark.parametrize("fmt", FORMATS, ids=[f.name for f in FORMATS])
def test_create_workspace_refuses_a_path_something_is_already_at(
    adapter: Adapter, tmp_path: Path, fmt: WorkspaceFormat
) -> None:
    path = _workspace_path(tmp_path, fmt)
    adapter.table_ops.create_workspace(path=path, fmt=fmt)
    with pytest.raises(PortContractError) as caught:
        adapter.table_ops.create_workspace(path=path, fmt=fmt)
    assert caught.value.context.handle == path
    assert adapter.workspace_present(path)


@pytest.mark.parametrize("fmt", FORMATS, ids=[f.name for f in FORMATS])
def test_create_workspace_under_a_missing_parent_is_an_engine_error_naming_the_tool(
    adapter: Adapter, tmp_path: Path, fmt: WorkspaceFormat
) -> None:
    path = _workspace_path(tmp_path, fmt, "no_such_folder")
    with pytest.raises(EngineError) as caught:
        adapter.table_ops.create_workspace(path=path, fmt=fmt)
    assert caught.value.context.tool == adapter.workspace_tool
    assert not adapter.workspace_present(path)
