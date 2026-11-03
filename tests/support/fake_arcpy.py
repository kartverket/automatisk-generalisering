"""A fake `arcpy` module for the adapter's unit tests: datasets, cursors, Describe, tools.

What: `FakeEngine`, a `ModuleType` that the unit tests install as `arcpy` through
`sys.modules` and hand to the session, so the group modules and the session see one
engine; `FakeDataset`, what it holds per path; `seed`, which writes an engine-neutral
case to it with the port's field types mapped to the engine's names.

How: rows are dicts keyed by field name and by the two cursor tokens, `OID@` and
`SHAPE@WKB`. A search cursor over an unknown name raises `RuntimeError`, as the engine's
is expected to; a tool records its keyword arguments, raises `FakeExecuteError` when
`failures` names it, and otherwise does the least that lets the adapter continue: the
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

from ag.ports.attributes import FieldType
from tests.support.cases import DatasetCase
from tests.support.wkb import to_wkb

OID = "OID@"
WKB = "SHAPE@WKB"
ENGINE_TYPES = {
    FieldType.SHORT: "SmallInteger",
    FieldType.LONG: "Integer",
    FieldType.DOUBLE: "Double",
    FieldType.TEXT: "String",
    FieldType.DATE: "Date",
}


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


@dataclass
class FakeDataset:
    """One dataset: its engine fields, its rows, and what Describe reports about it."""

    data_type: str
    fields: list[FakeField]
    rows: list[dict[str, object]] = field(default_factory=_no_rows)
    epsg: int = 25833
    has_z: bool = False
    has_m: bool = False
    oid_name: str = "OBJECTID"
    shape_name: str = "Shape"
    length_name: str = "Shape_Length"
    area_name: str = ""

    def engine_fields(self) -> list[FakeField]:
        found = [FakeField(self.oid_name, "OID")]
        if self.data_type == "FeatureClass":
            found.append(FakeField(self.shape_name, "Geometry"))
            for name in (self.length_name, self.area_name):
                if name:
                    found.append(FakeField(name, "Double"))
        return found

    def next_oid(self) -> int:
        taken = [int(str(row[OID])) for row in self.rows]
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
                and row[OID] == self._engine.fail_at_row
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
            {OID: oid, **dict(zip(self._names, row, strict=True))}
        )
        return oid


class FakeEngine(ModuleType):
    """The fake `arcpy`: what the session resolves on it and what the groups reach."""

    def __init__(self) -> None:
        super().__init__("arcpy")
        self.env = SimpleNamespace()
        self.ExecuteError = FakeExecuteError
        self.buffer = ""
        self.datasets: dict[str, FakeDataset] = {}
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
        self.management = SimpleNamespace(
            MultipartToSinglepart=self._tool(
                "management.MultipartToSinglepart", self._explode
            ),
            CreateTable=self._tool("management.CreateTable", self._create_table),
            AddField=self._tool("management.AddField", self._add_field),
            DeleteField=self._tool("management.DeleteField", self._delete_field),
        )
        self.analysis = SimpleNamespace(
            Select=self._tool("analysis.Select", self._select),
            TableSelect=self._tool("analysis.TableSelect", self._select),
        )

    def GetMessages(self) -> str:
        return self.buffer

    def _search_cursor(
        self, path: str, names: Sequence[str], where_clause: str = ""
    ) -> _SearchCursor:
        return _SearchCursor(self, path, names)

    def _insert_cursor(self, path: str, names: Sequence[str]) -> _InsertCursor:
        return _InsertCursor(self, path, names)

    def SpatialReference(self, epsg: int) -> tuple[str, int]:
        return ("sr", epsg)

    def AddFieldDelimiters(self, datasource: str, field: str) -> str:
        if "AddFieldDelimiters" in self.failures:
            raise RuntimeError(self.failures["AddFieldDelimiters"])
        self.quoted.append((datasource, field))
        return f'"{field}"'

    def Describe(self, path: str) -> SimpleNamespace:
        dataset = self.dataset(path)
        return SimpleNamespace(
            dataType=dataset.data_type,
            fields=[*dataset.engine_fields(), *dataset.fields],
            OIDFieldName=dataset.oid_name,
            shapeFieldName=dataset.shape_name,
            lengthFieldName=dataset.length_name,
            areaFieldName=dataset.area_name,
            hasZ=dataset.has_z,
            hasM=dataset.has_m,
            spatialReference=SimpleNamespace(factoryCode=dataset.epsg),
        )

    def dataset(self, path: str) -> FakeDataset:
        found = self.datasets.get(path)
        if found is None:
            raise RuntimeError(f"{path} does not exist")
        return found

    def tool_names(self) -> list[str]:
        return [name for name, _ in self.calls]

    def _tool(self, name: str, body: Callable[..., None]) -> Callable[..., FakeResult]:
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
        output = FakeDataset("FeatureClass", fields, epsg=source.epsg)
        for row in source.rows:
            parent = int(str(row[OID]))
            for shape in scripted.get(parent, [row[WKB]]):
                child = {k: v for k, v in row.items() if k not in (OID, WKB)}
                child[OID] = output.next_oid()
                child[WKB] = shape
                for name in self.reference_fields:
                    child[name] = parent
                output.rows.append(child)
        self.datasets[out_feature_class] = output

    def _create_table(self, *, out_path: str, out_name: str) -> None:
        self.datasets[f"{out_path}/{out_name}"] = FakeDataset("Table", [])

    def _add_field(self, *, in_table: str, field_name: str, field_type: str) -> None:
        self.dataset(in_table).fields.append(
            FakeField(field_name, {"LONG": "Integer"}[field_type])
        )

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
        output = FakeDataset(source.data_type, [*source.fields], epsg=source.epsg)
        for row in source.rows:
            output.rows.append({**row, OID: output.next_oid()})
        self.datasets[target] = output


def seed(engine: FakeEngine, case: DatasetCase, *, path: str) -> FakeDataset:
    """Writes `case` to `engine` under `path`, with native indices 1 to n in order."""
    schema = case.schema
    fields = [
        FakeField(f.name, ENGINE_TYPES[f.type], f.length or 0) for f in schema.fields
    ]
    data_type = "FeatureClass" if schema.geometry_crs is not None else "Table"
    dataset = FakeDataset(data_type, fields)
    for position, row in enumerate(case.rows, start=1):
        values: dict[str, object] = {**row.attributes, OID: position}
        if data_type == "FeatureClass":
            values[WKB] = None if row.geometry is None else to_wkb(row.geometry)
        dataset.rows.append(values)
    engine.datasets[path] = dataset
    return dataset
