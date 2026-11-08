"""What `dataset_schema.py` expects of the engine beyond what the conformance round trip
pins: the class Describe raises for a path that does not exist, and the four `shapeType`
spellings `SHAPE_TYPES` maps, read back from a class of each family in a file
geodatabase and in the memory workspace (W23). The type names of the five field types,
the empty length and area names, and the `dataType` strings are pinned by the
conformance suite's round trips and the memory-workspace module. ADR-0018 AR-D23,
ADR-0019 PC-D22.
"""

from __future__ import annotations

import pytest

from ag.adapters.arcpy.support.dataset_schema import describe
from ag.ports.errors import EngineError
from tests.engine.arcpy.conftest import MEMORY_WORKSPACE, Pro
from tests.support.cases import DatasetCase, multilines, multipoints, points, polygons

pytestmark = pytest.mark.arcpy

FAMILY_CASES = [points(), multipoints(), multilines(), polygons()]


@pytest.mark.parametrize("case", FAMILY_CASES, ids=[c.name for c in FAMILY_CASES])
@pytest.mark.parametrize(
    "workspace", [None, MEMORY_WORKSPACE], ids=["file-gdb", "memory"]
)
def test_describe_reads_each_family_from_the_shape_type(
    pro: Pro, case: DatasetCase, workspace: str | None
) -> None:
    seeded = pro.seed(case, workspace=workspace)
    described = describe(pro.session, str(seeded.handle.path))
    assert described.schema.geometry_family is case.schema.geometry_family
    assert described.schema == case.schema


def test_describe_of_a_missing_dataset_is_an_engine_error(pro: Pro) -> None:
    with pytest.raises(EngineError) as caught:
        describe(pro.session, pro.path("no_such_dataset"))
    assert caught.value.context.tool == "Describe"
