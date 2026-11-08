"""An engine-neutral case into a file geodatabase: the glue between `tests.support.cases`
and the engine-touching builders.

What: `seed_case`, which encodes a case's rows as cell tuples, the geometry as well-known
binary through the test-side encoder, hands them with the case's schema to the builders
and returns a `Seeded`; `handle_at`, a materialised handle for a dataset in a workspace.

Why: the builders import `ag` and the engine only, under the constrained stub, so the
encoder and the cases cannot be theirs; this module sits outside that root and joins the
two. It imports the builders at module level, which import the engine lazily, and is
itself imported inside an `arcpy`-marked fixture or test, never at the top of a test
module: collection imports test modules, and CI has no ArcPy.
"""

from __future__ import annotations

from ag.adapters.arcpy.session import ArcpySession
from ag.core.handles import ScratchHandle
from ag.core.types import DataType
from ag.ports.table_ops import Row, Schema
from tests.support.arcpy import gdb
from tests.support.cases import DatasetCase, Seeded
from tests.support.wkb import to_wkb

NAMESPACE = "tests.support.gdb_cases"


def handle_at(
    workspace: str, name: str, data_type: DataType = DataType.FEATURE_CLASS
) -> ScratchHandle:
    """A declared-and-materialised handle whose path is `<workspace>/<name>`."""
    return ScratchHandle(
        name=name, data_type=data_type, namespace=NAMESPACE
    ).materialize(f"{workspace}/{name}")


def cells_of(schema: Schema, rows: tuple[Row, ...]) -> list[tuple[object, ...]]:
    """The rows as cell tuples in the schema's field order, a feature class with the
    geometry as well-known binary, or None, in the last cell."""
    names = [field.name for field in schema.fields]
    cells: list[tuple[object, ...]] = []
    for row in rows:
        attributes = tuple(row.attributes[name] for name in names)
        if schema.data_type is DataType.TABLE:
            cells.append(attributes)
        else:
            shape = None if row.geometry is None else to_wkb(row.geometry)
            cells.append((*attributes, shape))
    return cells


def seed_case(
    session: ArcpySession,
    *,
    workspace: str,
    case: DatasetCase,
    name: str | None = None,
) -> Seeded:
    """Writes `case` to `workspace` under `name`, the case's own by default."""
    name = case.name if name is None else name
    indices = gdb.seed(
        session,
        workspace=workspace,
        name=name,
        schema=case.schema,
        cells=cells_of(case.schema, case.rows),
    )
    return Seeded(
        handle=handle_at(workspace, name, case.schema.data_type), indices=indices
    )
