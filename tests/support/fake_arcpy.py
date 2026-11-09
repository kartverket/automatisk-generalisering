"""A fake `arcpy` module for the adapter's unit tests: datasets, cursors, Describe, tools.

What: `FakeEngine`, a `ModuleType` that the unit tests install as `arcpy` through
`sys.modules` and hand to the session, so the group modules and the session see one
engine; `FakeDataset`, what it holds per path; `seed`, which writes an engine-neutral
case to it with the port's field types mapped to the engine's names.

How: rows are dicts keyed by field name and by the adapter's two cursor tokens, which
are imported, as the engine's type, data-type and shape-type names are, each the
adapter's own table inverted, so the fake spells nothing of the adapter's twice; the
engine's strings are the marked run's to confirm. A toolbox is a namespace
whose attributes are the tools, the structure `run_tool` resolves a dotted name against,
and a tool records itself under that path. A search cursor over an unknown name raises
`RuntimeError` and Describe of an unknown path `OSError`, as the engine's do; a tool records its keyword arguments,
raises `FakeExecuteError` when `failures` names it, and otherwise does the least that
lets the adapter continue: the
select tools copy every row and keep the clause, the explode tool writes the children
`children` scripts for each parent, or one child per row, and adds the fields named in
`reference_fields`, `ORIG_FID` unless a test says otherwise. Nothing here evaluates SQL
or geometry; the engine's behaviour is the marked run's to confirm.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from types import ModuleType, SimpleNamespace, TracebackType
from typing import Self

from ag.adapters.arcpy.support.dataset_schema import (
    DATA_TYPES,
    FIELD_TYPES,
    MEMORY_WORKSPACE_PROG_ID,
    OID_TOKEN,
    SHAPE_TYPES,
    WHOLE_SECOND_PRECISION,
)
from ag.adapters.arcpy.support.dataset_writer import ADD_FIELD_TYPES, MIGRATION_TOOL
from ag.adapters.arcpy.support.geometry_values import WKB_TOKEN
from ag.core.types import DataType
from ag.ports.attributes import FieldType
from ag.ports.geometry import GeometryFamily
from tests.support.cases import DatasetCase
from tests.support.wkb import to_wkb

ENGINE_TYPES = {port: engine for engine, port in FIELD_TYPES.items()}
"""The port's field types to the engine's Describe names: the adapter's own table, inverted."""

ADDED_TYPES = {ADD_FIELD_TYPES[port]: engine for engine, port in FIELD_TYPES.items()}
"""The AddField vocabulary to the Describe names, through the adapter's two tables."""

ENGINE_DATA_TYPES = {port: engine for engine, port in DATA_TYPES.items()}
"""The port's data types to the engine's `dataType` strings, the adapter's table inverted."""

ENGINE_SHAPE_TYPES = {port: engine for engine, port in SHAPE_TYPES.items()}
"""The port's geometry families to the engine's `shapeType` strings, inverted likewise."""

FEATURE_CLASS = ENGINE_DATA_TYPES[DataType.FEATURE_CLASS]
TABLE = ENGINE_DATA_TYPES[DataType.TABLE]

FRACTION_PRECISION = 1
"""The engine `precision` of a date field that holds the fraction, which the migration
tool sets and the adapter's own date fields carry."""

FILE_GDB_PROG_ID = "esriDataSourcesGDB.FileGDBWorkspaceFactory"
"""The engine's `workspaceFactoryProgID` of a file geodatabase, the fake's default
workspace; the adapter never names it, only the memory one."""

MEMORY_WORKSPACE = "memory"
"""The in-memory workspace's path, as the engine spells it."""

FILE_WORKSPACE = "ws"
"""The fake's default workspace, a stand-in file geodatabase."""


def _no_rows() -> list[dict[str, object]]:
    return []


class FakeExecuteError(Exception):
    """Stands in for `arcpy.ExecuteError`."""


class FakeResult:
    def __init__(self, messages: str = "Done") -> None:
        self._messages = messages

    def getMessages(self) -> str:
        return self._messages


@dataclass
class FakeField:
    name: str
    type: str
    length: int = 0
    precision: int = WHOLE_SECOND_PRECISION


@dataclass
class FakeDataset:
    """One dataset: its engine fields, its rows, and what Describe reports about it."""

    data_type: str
    fields: list[FakeField]
    rows: list[dict[str, object]] = field(default_factory=_no_rows)
    epsg: int = 25833
    has_z: bool = False
    has_m: bool = False
    shape_type: str = ENGINE_SHAPE_TYPES[GeometryFamily.LINE]
    workspace: str = FILE_WORKSPACE
    oid_name: str = "OBJECTID"
    shape_name: str = "Shape"
    length_name: str = "Shape_Length"
    area_name: str = ""

    def engine_fields(self) -> list[FakeField]:
        found = [FakeField(self.oid_name, "OID")]
        if self.data_type == FEATURE_CLASS:
            found.append(FakeField(self.shape_name, "Geometry"))
            for name in (self.length_name, self.area_name):
                if name:
                    found.append(FakeField(name, "Double"))
        return found

    def next_oid(self) -> int:
        taken = [int(str(row[OID_TOKEN])) for row in self.rows]
        return max(taken, default=0) + 1


class _SearchCursor:
    def __init__(self, engine: FakeEngine, path: str, names: Sequence[str]) -> None:
        self._dataset = engine.dataset(path)
        for name in names:
            if name not in self._dataset.rows[0] if self._dataset.rows else False:
                raise RuntimeError(
                    f"A column was specified that does not exist. [{name}]"
                )
        self._names = tuple(names)
        self._engine = engine
        engine.cursors_opened += 1

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self._engine.cursors_closed += 1

    def __iter__(self) -> Iterator[tuple[object, ...]]:
        for row in self._dataset.rows:
            if (
                self._engine.fail_at_row is not None
                and row[OID_TOKEN] == self._engine.fail_at_row
            ):
                raise RuntimeError("The cursor failed mid-read.")
            yield tuple(row[name] for name in self._names)


class _InsertCursor:
    def __init__(self, engine: FakeEngine, path: str, names: Sequence[str]) -> None:
        self._dataset = engine.dataset(path)
        self._names = tuple(names)

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        return None

    def insertRow(self, row: Sequence[object]) -> int:
        oid = self._dataset.next_oid()
        self._dataset.rows.append(
            {OID_TOKEN: oid, **dict(zip(self._names, row, strict=True))}
        )
        return oid


class _Toolbox(SimpleNamespace):
    """One engine toolbox: each attribute is a tool recorded as `<toolbox>.<Tool>`."""

    def __init__(
        self, engine: FakeEngine, name: str, **bodies: Callable[..., None]
    ) -> None:
        super().__init__(
            **{
                tool: engine.recorder(f"{name}.{tool}", body)
                for tool, body in bodies.items()
            }
        )


class FakeEngine(ModuleType):
    """The fake `arcpy`: what the session resolves on it and what the groups reach."""

    def __init__(self) -> None:
        super().__init__("arcpy")
        self.env = SimpleNamespace()
        self.ExecuteError = FakeExecuteError
        self.buffer = ""
        self.datasets: dict[str, FakeDataset] = {}
        self.workspaces: dict[str, str] = {
            FILE_WORKSPACE: FILE_GDB_PROG_ID,
            MEMORY_WORKSPACE: MEMORY_WORKSPACE_PROG_ID,
        }
        self.calls: list[tuple[str, dict[str, object]]] = []
        self.failures: dict[str, str] = {}
        self.children: dict[str, Mapping[int, Sequence[object]]] = {}
        self.reference_fields: list[str] = ["ORIG_FID"]
        self.fail_at_row: int | None = None
        self.cursors_opened = 0
        self.cursors_closed = 0
        self.quoted: list[tuple[str, str]] = []
        self.da = SimpleNamespace(
            SearchCursor=self._search_cursor, InsertCursor=self._insert_cursor
        )
        self.management = _Toolbox(
            self,
            "management",
            MultipartToSinglepart=self._explode,
            CreateTable=self._create_table,
            AddField=self._add_field,
            DeleteField=self._delete_field,
            **{MIGRATION_TOOL.split(".")[1]: self._migrate_date_field},
        )
        self.analysis = _Toolbox(
            self, "analysis", Select=self._select, TableSelect=self._select
        )

    def GetMessages(self) -> str:
        return self.buffer

    def _search_cursor(
        self, path: str, names: Sequence[str], where_clause: str = ""
    ) -> _SearchCursor:
        return _SearchCursor(self, path, names)

    def _insert_cursor(self, path: str, names: Sequence[str]) -> _InsertCursor:
        return _InsertCursor(self, path, names)

    def SpatialReference(self, epsg: int) -> SimpleNamespace:
        return SimpleNamespace(factoryCode=epsg)

    def AddFieldDelimiters(self, datasource: str, field: str) -> str:
        if "AddFieldDelimiters" in self.failures:
            raise RuntimeError(self.failures["AddFieldDelimiters"])
        self.quoted.append((datasource, field))
        return f'"{field}"'

    def Describe(self, path: str) -> SimpleNamespace:
        dataset = self.datasets.get(path)
        if dataset is None:
            prog_id = self.workspaces.get(path)
            if prog_id is None:
                raise OSError(f'"{path}" does not exist')
            return SimpleNamespace(workspaceFactoryProgID=prog_id)
        return SimpleNamespace(
            path=dataset.workspace,
            dataType=dataset.data_type,
            fields=[*dataset.engine_fields(), *dataset.fields],
            OIDFieldName=dataset.oid_name,
            shapeFieldName=dataset.shape_name,
            lengthFieldName=dataset.length_name,
            areaFieldName=dataset.area_name,
            hasZ=dataset.has_z,
            hasM=dataset.has_m,
            shapeType=dataset.shape_type,
            spatialReference=SimpleNamespace(factoryCode=dataset.epsg),
        )

    def dataset(self, path: str) -> FakeDataset:
        found = self.datasets.get(path)
        if found is None:
            raise RuntimeError(f"{path} does not exist")
        return found

    def tool_names(self) -> list[str]:
        return [name for name, _ in self.calls]

    def recorder(
        self, name: str, body: Callable[..., None]
    ) -> Callable[..., FakeResult]:
        """`body` as a tool recorded under `name`, the path `run_tool` resolves."""

        def tool(**arguments: object) -> FakeResult:
            self.calls.append((name, arguments))
            if name in self.failures:
                self.buffer = self.failures[name]
                raise FakeExecuteError(f"{name} failed")
            body(**arguments)
            return FakeResult()

        return tool

    def _explode(self, *, in_features: str, out_feature_class: str) -> None:
        source = self.dataset(in_features)
        scripted = self.children.get(in_features, {})
        fields = [*source.fields]
        for name in self.reference_fields:
            fields.append(FakeField(name, "Integer"))
        family = SHAPE_TYPES[source.shape_type].single
        output = FakeDataset(
            FEATURE_CLASS,
            fields,
            epsg=source.epsg,
            shape_type=ENGINE_SHAPE_TYPES[family],
            workspace=source.workspace,
        )
        for row in source.rows:
            parent = int(str(row[OID_TOKEN]))
            for shape in scripted.get(parent, [row[WKB_TOKEN]]):
                child = {
                    k: v for k, v in row.items() if k not in (OID_TOKEN, WKB_TOKEN)
                }
                child[OID_TOKEN] = output.next_oid()
                child[WKB_TOKEN] = shape
                for name in self.reference_fields:
                    child[name] = parent
                output.rows.append(child)
        self.datasets[out_feature_class] = output

    def _create_table(self, *, out_path: str, out_name: str) -> None:
        self.datasets[f"{out_path}/{out_name}"] = FakeDataset(
            TABLE, [], workspace=out_path
        )

    def _add_field(
        self,
        *,
        in_table: str,
        field_name: str,
        field_type: str,
        field_length: int | None = None,
    ) -> None:
        self.dataset(in_table).fields.append(
            FakeField(field_name, ADDED_TYPES[field_type], field_length or 0)
        )

    def _migrate_date_field(self, *, in_table: str, date_fields: str) -> None:
        dataset = self.dataset(in_table)
        if self.workspaces.get(dataset.workspace) == MEMORY_WORKSPACE_PROG_ID:
            raise FakeExecuteError(
                "ERROR 002764: The operation is not supported by this implementation."
            )
        for found in dataset.fields:
            if found.name == date_fields:
                found.precision = FRACTION_PRECISION

    def _delete_field(self, *, in_table: str, drop_field: str) -> None:
        dataset = self.dataset(in_table)
        dataset.fields = [f for f in dataset.fields if f.name != drop_field]
        for row in dataset.rows:
            row.pop(drop_field, None)

    def _select(self, **arguments: object) -> None:
        source = self.dataset(
            str(arguments.get("in_features", arguments.get("in_table")))
        )
        target = str(arguments.get("out_feature_class", arguments.get("out_table")))
        output = FakeDataset(
            source.data_type,
            [*source.fields],
            epsg=source.epsg,
            shape_type=source.shape_type,
            workspace=source.workspace,
        )
        for row in source.rows:
            output.rows.append({**row, OID_TOKEN: output.next_oid()})
        self.datasets[target] = output


def seed(
    engine: FakeEngine,
    case: DatasetCase,
    *,
    path: str,
    date_precision: int = FRACTION_PRECISION,
) -> FakeDataset:
    """Writes `case` to `engine` under `path`, with native indices 1 to n in order; its
    date fields at `date_precision`, the adapter's own by default, a whole-second store
    when a test stands in for a raw source."""
    schema = case.schema
    fields = [
        FakeField(
            f.name,
            ENGINE_TYPES[f.type],
            f.length or 0,
            date_precision if f.type is FieldType.DATE else WHOLE_SECOND_PRECISION,
        )
        for f in schema.fields
    ]
    data_type = ENGINE_DATA_TYPES[schema.data_type]
    workspace, _, _ = path.rpartition("/")
    dataset = FakeDataset(data_type, fields, workspace=workspace or FILE_WORKSPACE)
    if schema.geometry_family is not None:
        dataset.shape_type = ENGINE_SHAPE_TYPES[schema.geometry_family]
    for position, row in enumerate(case.rows, start=1):
        values: dict[str, object] = {**row.attributes, OID_TOKEN: position}
        if data_type == FEATURE_CLASS:
            values[WKB_TOKEN] = None if row.geometry is None else to_wkb(row.geometry)
        dataset.rows.append(values)
    engine.datasets[path] = dataset
    return dataset
