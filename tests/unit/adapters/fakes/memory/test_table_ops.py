"""`read_rows` under the in-memory adapter: exactly the named fields, with geometry;
the catalog over the store, with the real parent folder as the one thing the fake checks
outside itself. ADR-0019 PC-D22, PC-D31, PC-D32.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ag.adapters.fakes.memory.store import MemoryStore
from ag.adapters.fakes.memory.table_ops import MemoryTableOps
from ag.adapters.fakes.memory.table_ops.catalog import WORKSPACE_TOOL
from ag.core.types import DataType
from ag.ports.errors import EngineError, PortContractError
from ag.ports.workspace_format import WorkspaceFormat
from tests.support.cases import lookup, roads
from tests.support.memory import memory_handle, seed


def test_read_rows_returns_exactly_the_named_fields_and_the_geometry() -> None:
    store = MemoryStore()
    case = roads()
    seeded = seed(store, case)
    rows = list(
        MemoryTableOps(store=store).read_rows(
            input=seeded.handle, fields=("rank", "name")
        )
    )
    assert [tuple(row.attributes) for row in rows] == [("rank", "name")] * 4
    assert [row.attributes["name"] for row in rows] == [
        r.attributes["name"] for r in case.rows
    ]
    assert [row.geometry for row in rows] == [r.geometry for r in case.rows]
    assert tuple(store.read(seeded.handle).rows) == seeded.indices


def test_read_rows_of_a_table_has_no_geometry_and_no_fields_means_none() -> None:
    store = MemoryStore()
    seeded = seed(store, lookup())
    ops = MemoryTableOps(store=store)
    rows = list(ops.read_rows(input=seeded.handle, fields=("label",)))
    assert [dict(row.attributes) for row in rows] == [
        {"label": "one"},
        {"label": "two"},
    ]
    assert all(row.geometry is None for row in rows)
    bare = ops.read_rows(input=seeded.handle, fields=())
    assert [dict(row.attributes) for row in bare] == [{}, {}]


def test_read_rows_refuses_a_field_the_dataset_does_not_declare() -> None:
    store = MemoryStore()
    seeded = seed(store, lookup())
    with pytest.raises(PortContractError, match="are not fields of"):
        MemoryTableOps(store=store).read_rows(input=seeded.handle, fields=("code", "x"))


def test_exists_and_data_type_of_answer_what_the_store_holds(tmp_path: Path) -> None:
    store = MemoryStore()
    feature_class = seed(store, roads()).handle
    table = seed(store, lookup()).handle
    path = f"{tmp_path}/stage{WorkspaceFormat.FILE_GDB.suffix}"
    ops = MemoryTableOps(store=store)
    ops.create_workspace(path=path, fmt=WorkspaceFormat.FILE_GDB)
    workspace = memory_handle("workspace").materialize(path)
    assert ops.exists(input=feature_class)
    assert ops.exists(input=table)
    assert ops.exists(input=workspace)
    assert not ops.exists(input=memory_handle("absent"))
    assert ops.data_type_of(input=feature_class) is DataType.FEATURE_CLASS
    assert ops.data_type_of(input=table) is DataType.TABLE
    with pytest.raises(PortContractError, match="names a workspace"):
        ops.data_type_of(input=workspace)
    with pytest.raises(PortContractError, match="names no dataset"):
        ops.data_type_of(input=memory_handle("absent"))


def test_create_workspace_records_once_and_refuses_a_taken_path(
    tmp_path: Path,
) -> None:
    store = MemoryStore()
    seeded = seed(store, roads())
    ops = MemoryTableOps(store=store)
    path = f"{tmp_path}/stage{WorkspaceFormat.FILE_GDB.suffix}"
    ops.create_workspace(path=path, fmt=WorkspaceFormat.FILE_GDB)
    assert store.is_workspace(path)
    with pytest.raises(PortContractError, match="already there"):
        ops.create_workspace(path=path, fmt=WorkspaceFormat.FILE_GDB)
    with pytest.raises(PortContractError, match="already there"):
        ops.create_workspace(path=str(seeded.handle.path), fmt=WorkspaceFormat.FILE_GDB)
    assert not store.is_workspace(str(seeded.handle.path))


def test_create_workspace_under_a_missing_parent_names_its_own_method_as_the_tool(
    tmp_path: Path,
) -> None:
    store = MemoryStore()
    path = f"{tmp_path}/no_such_folder/stage{WorkspaceFormat.FILE_GDB.suffix}"
    with pytest.raises(EngineError) as caught:
        MemoryTableOps(store=store).create_workspace(
            path=path, fmt=WorkspaceFormat.FILE_GDB
        )
    assert caught.value.context.tool == WORKSPACE_TOOL
    assert caught.value.context.handle == path
    assert not store.present(path)
