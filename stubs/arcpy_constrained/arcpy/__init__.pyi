"""The constrained ArcPy stub: the names the ArcPy adapter may reach on `arcpy` directly.

Pyright applies this stub to `src/ag/adapters/arcpy/`, `tests/support/arcpy/` and
`tools/engine/`, so every attribute of `arcpy` not declared here is an error there: a tool goes through the
session's `run_tool`, and `arcpy.env` and the vendor exceptions are the session's alone;
`ag.adapters.arcpy.session` states the rule and cites its record. A non-tool name that a
group module needs on the engine directly is declared here with its reason, in the
change that needs it, and never widened for an editor's sake. Each declaration is the
narrowest signature the adapter uses, not the engine's full one; a cursor row is a tuple
of `object`, narrowed where it is read. This stub does not cover a submodule import such
as `import arcpy.management`, and attributes reached through one are not checked; the
static scan refuses that form.

Declared, and why:

- `da.SearchCursor`, `da.InsertCursor`: bulk row IO and the parents table go through
  cursors inside the session's guard; no tool reads rows as values.
- `da.UpdateCursor`: the engine-touching fixture builders delete chosen rows to make a
  native index non-dense. No port method deletes, since deletion is a selection
  (ADR-0019 PC-D23), and no tool deletes chosen rows of a dataset without layer state.
- `Describe`: a dataset's schema, data type, Z and M flags and spatial reference, read
  before a tool runs, and the names of the fields the engine maintains itself;
  `shapeType`, the geometry family of a feature class, which `describe` reads into
  `Schema.geometry_family` and the timing run's preflight reports for a raw source.
- `AddFieldDelimiters`: identifier quoting per workspace type for a compiled predicate,
  which is the engine's table and not one to restate.
"""

from collections.abc import Iterator, Sequence
from types import TracebackType
from typing import Self

class _Field:
    name: str
    type: str
    length: int
    precision: int

class _SpatialReference:
    factoryCode: int

class _Describe:
    dataType: str
    fields: list[_Field]
    OIDFieldName: str
    shapeFieldName: str
    lengthFieldName: str
    areaFieldName: str
    hasZ: bool
    hasM: bool
    shapeType: str
    spatialReference: _SpatialReference

class da:
    class SearchCursor:
        def __init__(
            self, in_table: str, field_names: Sequence[str], where_clause: str = ...
        ) -> None: ...
        def __enter__(self) -> Self: ...
        def __exit__(
            self,
            exc_type: type[BaseException] | None,
            exc: BaseException | None,
            tb: TracebackType | None,
        ) -> None: ...
        def __iter__(self) -> Iterator[tuple[object, ...]]: ...

    class InsertCursor:
        def __init__(self, in_table: str, field_names: Sequence[str]) -> None: ...
        def __enter__(self) -> Self: ...
        def __exit__(
            self,
            exc_type: type[BaseException] | None,
            exc: BaseException | None,
            tb: TracebackType | None,
        ) -> None: ...
        def insertRow(self, row: Sequence[object]) -> int: ...

    class UpdateCursor:
        def __init__(
            self, in_table: str, field_names: Sequence[str], where_clause: str = ...
        ) -> None: ...
        def __enter__(self) -> Self: ...
        def __exit__(
            self,
            exc_type: type[BaseException] | None,
            exc: BaseException | None,
            tb: TracebackType | None,
        ) -> None: ...
        def __iter__(self) -> Iterator[tuple[object, ...]]: ...
        def deleteRow(self) -> None: ...

def Describe(value: str) -> _Describe: ...
def AddFieldDelimiters(datasource: str, field: str) -> str: ...
