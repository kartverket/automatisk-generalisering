"""The memory workspace behaves as a file geodatabase where the adapter assumes it does:
Describe reports `FeatureClass` and `Table`, a date literal and `LIKE` select as in a file
geodatabase, and the identifier quoting is the same. ADR-0019 PC-D15, PC-D20.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from ag.adapters.arcpy.geometry_ops import ArcpyGeometryOps
from ag.adapters.arcpy.support.dataset_schema import describe
from ag.adapters.arcpy.table_ops import ArcpyTableOps
from ag.core.handles import ScratchHandle
from ag.core.types import DataType
from ag.ports import Attr, Comparison, Predicate
from tests.engine.arcpy.conftest import Pro
from tests.support.cases import lookup, roads

pytestmark = pytest.mark.arcpy

MEMORY = "memory"


def _names(pro: Pro, handle: ScratchHandle) -> set[str]:
    rows = ArcpyTableOps(session=pro.session).read_rows(input=handle, fields=("name",))
    return {str(row.attributes["name"]) for row in rows}


def _selected(pro: Pro, source: ScratchHandle, where: Predicate, name: str) -> set[str]:
    output = pro.handle(name, workspace=MEMORY)
    ArcpyGeometryOps(session=pro.session).select(
        input=source, where=where, output=output
    )
    return _names(pro, output)


def test_describe_reports_a_memory_feature_class_and_table_as_the_port_sees_them(
    pro: Pro,
) -> None:
    feature_class = pro.seed(roads(), workspace=MEMORY)
    table = pro.seed(lookup(), workspace=MEMORY)
    described = describe(pro.session, str(feature_class.handle.path))
    assert described.schema == roads().schema
    assert described.schema.data_type is DataType.FEATURE_CLASS
    assert describe(pro.session, str(table.handle.path)).schema == lookup().schema


def test_a_date_literal_and_like_select_in_the_memory_workspace_as_in_a_file_geodatabase(
    pro: Pro,
) -> None:
    seeded = pro.seed(roads(), workspace=MEMORY)
    since = Attr.cmp("surveyed", Comparison.GE, datetime(2024, 1, 1))
    assert _selected(pro, seeded.handle, since, "by_date") == {"Alpha road", "Gamma"}
    road = Attr.cmp("name", Comparison.LIKE, "%road")
    assert _selected(pro, seeded.handle, road, "by_like") == {"Alpha road", "beta_road"}
    lower = Attr.cmp("name", Comparison.LIKE, "alpha%")
    assert _selected(pro, seeded.handle, lower, "by_case") == set()
