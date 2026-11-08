"""What `shape.py` expects of the multipart-to-singlepart tool, and the holed lake.

What: the tool drops a GlobalID field, keeps the declared fields and adds the reference; when
`ORIG_FID` is already a field the tool writes into it and adds nothing, so such an input
is refused before the tool runs; a multipart polygon with holes is refused on read as one
row and, after `explode_multipart`, reads back as polygons with their holes; the tool
writes a multipoint input's children into a point class, which is the family rule
`GeometryFamily.single` states. ADR-0017 RS-D16, ADR-0019 PC-D25.
"""

from __future__ import annotations

import pytest

from ag.adapters.arcpy.geometry_ops import ArcpyGeometryOps
from ag.adapters.arcpy.support.dataset_schema import describe
from ag.adapters.arcpy.support.dataset_writer import add_fields, insert_rows
from ag.adapters.arcpy.support.geometry_values import WKB_TOKEN
from ag.adapters.arcpy.table_ops import ArcpyTableOps
from ag.core.types import DataType
from ag.ports import CHILD_ID, PARENT_ID, Field, FieldType, GeometryKind
from ag.ports.errors import PortContractError
from tests.engine.arcpy.conftest import Pro
from tests.support import wkb
from tests.support.cases import multilines, multipoints, polygons

pytestmark = pytest.mark.arcpy


def _parents(pro: Pro, path: str) -> set[int]:
    rows = ArcpyTableOps(session=pro.session).read_rows(
        input=pro.handle(path, DataType.TABLE), fields=(PARENT_ID, CHILD_ID)
    )
    found: set[int] = set()
    for row in rows:
        parent = row.attributes[PARENT_ID]
        assert isinstance(parent, int)
        found.add(parent)
    return found


def test_the_tool_drops_a_global_id_field_and_keeps_the_declared_ones(pro: Pro) -> None:
    seeded = pro.seed(multilines())
    path = str(seeded.handle.path)
    pro.session.run_tool("management.AddGlobalIDs", in_datasets=path)
    before = describe(pro.session, path)
    assert "GlobalID" in before.unrepresentable.values(), before.unrepresentable
    output = pro.handle("exploded")
    ArcpyGeometryOps(session=pro.session).explode_multipart(
        input=seeded.handle, output=output, parents=pro.handle("pairs", DataType.TABLE)
    )
    after = describe(pro.session, str(output.path))
    assert after.schema.fields == before.schema.fields
    assert dict(after.unrepresentable) == {}
    assert _parents(pro, "pairs") == set(seeded.indices)


def test_a_multipoint_input_explodes_into_a_point_family_output(pro: Pro) -> None:
    case = multipoints()
    seeded = pro.seed(case)
    output = pro.handle("exploded")
    ArcpyGeometryOps(session=pro.session).explode_multipart(
        input=seeded.handle, output=output
    )
    described = describe(pro.session, str(output.path))
    assert case.schema.geometry_family is not None
    assert described.schema.geometry_family is case.schema.geometry_family.single
    assert described.schema.fields == case.schema.fields


def test_an_input_that_already_has_the_reference_field_is_refused_before_the_tool(
    pro: Pro,
) -> None:
    seeded = pro.seed(multilines())
    path = str(seeded.handle.path)
    add_fields(pro.session, path=path, fields=(Field("ORIG_FID", FieldType.LONG),))
    with pytest.raises(PortContractError, match="ORIG_FID"):
        ArcpyGeometryOps(session=pro.session).explode_multipart(
            input=seeded.handle,
            output=pro.handle("exploded"),
            parents=pro.handle("pairs", DataType.TABLE),
        )
    assert describe(pro.session, path).schema.fields == (
        *polygons().schema.fields,
        Field("ORIG_FID", FieldType.LONG),
    )


def test_a_multipart_polygon_with_holes_is_refused_as_one_row_and_explodes_with_them(
    pro: Pro,
) -> None:
    seeded = pro.seed(polygons())
    path = str(seeded.handle.path)
    insert_rows(
        pro.session,
        path=path,
        tokens=("name", WKB_TOKEN),
        rows=[("lake", wkb.multipolygon_with_hole())],
    )
    table_ops = ArcpyTableOps(session=pro.session)
    with pytest.raises(PortContractError, match="holes"):
        list(table_ops.read_rows(input=seeded.handle, fields=("name",)))
    islands = pro.handle("islands")
    ArcpyGeometryOps(session=pro.session).explode_multipart(
        input=seeded.handle, output=islands
    )
    lakes = [
        row.geometry
        for row in table_ops.read_rows(input=islands, fields=("name",))
        if row.attributes["name"] == "lake"
    ]
    assert all(g is not None and g.kind is GeometryKind.POLYGON for g in lakes)
    assert {g.parts for g in lakes if g is not None} == {
        (wkb.LAKE_OUTER, wkb.LAKE_ISLAND),
        (wkb.LAKE_NEIGHBOUR,),
    }
