"""What the catalog methods expect of the engine beyond the conformance cases: a
workspace that holds a dataset is refused by `create_workspace` before any tool, and the
dataset is still there afterwards, which is the refusal's reason under the session's
overwrite setting; and a dataset in the memory workspace is present and is its kind, so
presence and kind are answered there as in a file geodatabase. ADR-0019 PC-D31, PC-D32.
"""

from __future__ import annotations

import pytest

from ag.adapters.arcpy.table_ops import ArcpyTableOps
from ag.ports.errors import PortContractError
from ag.ports.workspace_format import WorkspaceFormat
from tests.engine.arcpy.conftest import Pro
from tests.support.cases import DatasetCase, lookup, roads
from tests.support.fake_arcpy import MEMORY_WORKSPACE

pytestmark = pytest.mark.arcpy


def test_create_workspace_refuses_the_workspace_a_dataset_lives_in_and_keeps_it(
    pro: Pro,
) -> None:
    seeded = pro.seed(roads())
    ops = ArcpyTableOps(session=pro.session)
    with pytest.raises(PortContractError) as caught:
        ops.create_workspace(path=pro.workspace, fmt=WorkspaceFormat.FILE_GDB)
    assert caught.value.context.handle == pro.workspace
    rows = list(ops.read_rows(input=seeded.handle, fields=("name",)))
    assert len(rows) == len(roads().rows)


@pytest.mark.parametrize("case", [roads(), lookup()], ids=["feature-class", "table"])
def test_a_dataset_in_the_memory_workspace_exists_and_is_its_kind(
    pro: Pro, case: DatasetCase
) -> None:
    seeded = pro.seed(case, workspace=MEMORY_WORKSPACE)
    ops = ArcpyTableOps(session=pro.session)
    assert ops.exists(input=seeded.handle)
    assert ops.data_type_of(input=seeded.handle) is case.schema.data_type
    assert not ops.exists(input=pro.handle("absent", workspace=MEMORY_WORKSPACE))


def test_the_memory_workspace_path_is_refused_by_create_workspace_before_any_tool(
    pro: Pro,
) -> None:
    """The engine's memory workspace has no suffix, so the port refuses it as a path
    and never reaches the tool, whatever the tool would do with it."""
    with pytest.raises(PortContractError, match="does not end in"):
        ArcpyTableOps(session=pro.session).create_workspace(
            path=MEMORY_WORKSPACE, fmt=WorkspaceFormat.FILE_GDB
        )
