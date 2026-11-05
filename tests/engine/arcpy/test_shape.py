"""What `shape.py` expects of the multipart-to-singlepart tool, and the holed lake.

What: the tool keeps a GlobalID field as it is and adds no field but the reference; when
`ORIG_FID` is taken the reference gets another name and the diff finds it; a multipart
polygon with holes is refused on read as one row and, after `explode_multipart`, reads
back as polygons with their holes. ADR-0017 RS-D16, ADR-0019 PC-D25.
"""

from __future__ import annotations

import pytest

from ag.adapters.arcpy.geometry_ops import ArcpyGeometryOps
from ag.adapters.arcpy.support.dataset_schema import describe
from ag.adapters.arcpy.support.dataset_writer import add_fields, insert_rows
from ag.adapters.arcpy.support.geometry_values import WKB_TOKEN
from ag.adapters.arcpy.table_ops import ArcpyTableOps
from ag.core.types import DataType
from ag.ports import CHILD_ID, PARENT_ID, Field, FieldType, Geometry, GeometryKind
from ag.ports.errors import PortContractError
from tests.engine.arcpy.conftest import Pro
from tests.support import wkb
from tests.support.cases import CRS, multilines, multilines_children, polygons

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


def test_the_tool_keeps_a_global_id_field_and_adds_only_the_reference(pro: Pro) -> None:
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
    assert dict(after.unrepresentable) == dict(before.unrepresentable)
    assert _parents(pro, "pairs") == set(seeded.indices)


def test_the_reference_is_found_by_diff_when_orig_fid_is_taken(pro: Pro) -> None:
    seeded = pro.seed(multilines())
    path = str(seeded.handle.path)
    add_fields(pro.session, path=path, fields=(Field("ORIG_FID", FieldType.LONG),))
    output = pro.handle("exploded")
    ArcpyGeometryOps(session=pro.session).explode_multipart(
        input=seeded.handle, output=output, parents=pro.handle("pairs", DataType.TABLE)
    )
    assert (
        describe(pro.session, str(output.path)).schema.fields
        == describe(pro.session, path).schema.fields
    )
    assert _parents(pro, "pairs") == set(seeded.indices)
    children = ArcpyTableOps(session=pro.session).read_rows(
        input=output, fields=("name",)
    )
    assert len(list(children)) == sum(len(g) for g in multilines_children().values())


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
    assert lakes == [
        Geometry(
            GeometryKind.POLYGON,
            (
                ((0.0, 0.0), (4.0, 0.0), (4.0, 4.0), (0.0, 4.0), (0.0, 0.0)),
                ((1.0, 1.0), (2.0, 1.0), (2.0, 2.0), (1.0, 2.0), (1.0, 1.0)),
            ),
            CRS,
        )
    ]
