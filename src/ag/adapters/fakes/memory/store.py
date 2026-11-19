"""`MemoryStore`, the one object that holds every dataset of the in-memory adapter.

What: datasets keyed by the handle's path, each a `Schema` and an ordered mapping from
native index to `Row`; `write` replaces a dataset and `read` returns one; values are held
to the shared field rule. Workspaces keyed by path, each its `WorkspaceFormat`:
`record_workspace` records one, `is_workspace` answers whether a path is one, and
`present` whether anything, dataset or workspace, is at a path. A dataset write does not
require its workspace to be recorded: the fake computes no path and the store holds what
the port was told. ADR-0019 PC-D32.

How: the native index is a dense integer range taken from one counter for the whole
store, so a rewrite of the same rows gets new indices and a pairs table can never be
read as positions; the index is valid until the dataset is next written. A handle is
resolved through `os.fspath`, so an unmaterialised handle fails here as it would under an
engine. A write checks the handle's `DataType` against the schema, that each row holds
exactly the schema's fields, that each value fits its field's type and range or is None,
and that geometry appears only on a feature class, in the schema's CRS and of a kind in
the schema's geometry family, since a feature class holds one geometry type on every
engine; a bad row is a `PortContractError` raised before anything is replaced. Rows are stored as copies with
read-only attributes, so what was checked is what stays. ADR-0019 PC-D17, PC-D26.

Why: all mutable state of the fake is in this one object, handed to every port class, so
what one port wrote is what another reads, and the group classes hold none. The store is
row-identity accurate and geometry naive: it computes no geometry.
"""

from __future__ import annotations

import os
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from types import MappingProxyType

from ag.adapters._shared.field_values import type_mismatch
from ag.core.errors import ErrorContext
from ag.core.handles import ScratchHandle
from ag.core.types import DataType
from ag.ports.errors import PortContractError
from ag.ports.table_ops import Row, Schema
from ag.ports.workspace_format import WorkspaceFormat


@dataclass(frozen=True)
class Dataset:
    """One dataset: its schema, and its rows by native index in write order."""

    schema: Schema
    rows: Mapping[int, Row]


class MemoryStore:
    """The datasets of one fake, keyed by path, with one native-index counter."""

    def __init__(self) -> None:
        self._datasets: dict[str, Dataset] = {}
        self._workspaces: dict[str, WorkspaceFormat] = {}
        self._next_index = 1

    def present(self, path: str) -> bool:
        """Whether a dataset or a workspace is at `path`."""
        return path in self._datasets or path in self._workspaces

    def is_workspace(self, path: str) -> bool:
        """Whether a workspace was recorded at `path`."""
        return path in self._workspaces

    def record_workspace(self, path: str, *, fmt: WorkspaceFormat) -> None:
        """Records an empty workspace at `path`; a path something is already at is a
        contract error, raised before anything is recorded."""
        if self.present(path):
            raise PortContractError(
                f"{path!r} is already there; a workspace is created once.",
                context=ErrorContext(handle=path),
            )
        self._workspaces[path] = fmt

    def read(self, handle: ScratchHandle) -> Dataset:
        """The dataset `handle` names; a handle nothing was written to is a contract error."""
        path = os.fspath(handle)
        found = self._datasets.get(path)
        if found is None:
            raise PortContractError(
                f"{handle!r} names no dataset: nothing has been written to {path!r}.",
                context=ErrorContext(handle=path),
            )
        return found

    def write(
        self, handle: ScratchHandle, *, schema: Schema, rows: Iterable[Row]
    ) -> tuple[int, ...]:
        """Replaces the dataset `handle` names; returns the native indices it assigned.

        The indices are the next contiguous range of the store's counter, in row order,
        so the caller can pair them with the rows it passed without knowing the rule.
        """
        path = os.fspath(handle)
        if handle.data_type is not schema.data_type:
            raise PortContractError(
                f"{handle!r} is declared {handle.data_type.value} and the schema written "
                f"to it is {schema.data_type.value}; a handle names one kind of dataset.",
                context=ErrorContext(handle=path),
            )
        checked = tuple(_frozen(row) for row in rows)
        for position, row in enumerate(checked):
            _check_row(row=row, schema=schema, path=path, position=position)
        start = self._next_index
        indices = tuple(range(start, start + len(checked)))
        self._next_index = start + len(checked)
        self._datasets[path] = Dataset(
            schema=schema,
            rows=MappingProxyType(dict(zip(indices, checked, strict=True))),
        )
        return indices


def _frozen(row: Row) -> Row:
    """A copy of `row` whose attributes are a read-only mapping of the caller's.

    The store keeps what it checked: a caller that changes its own mapping after the
    write changes nothing here, and a child row built from a stored row shares no
    mutable state with it.
    """
    return Row(attributes=MappingProxyType(dict(row.attributes)), geometry=row.geometry)


def _check_row(*, row: Row, schema: Schema, path: str, position: int) -> None:
    """Rejects a row that does not fit `schema`, naming the row's position in the write."""
    declared = {field.name: field for field in schema.fields}
    names = set(row.attributes)
    if names != declared.keys():
        missing = sorted(declared.keys() - names)
        extra = sorted(names - declared.keys())
        raise PortContractError(
            f"row {position} written to {path!r} does not match the schema: "
            f"missing {missing}, unexpected {extra}; a row holds exactly the schema's "
            "fields.",
            context=ErrorContext(handle=path),
        )
    for name, value in row.attributes.items():
        reason = type_mismatch(value=value, field=declared[name])
        if reason is not None:
            raise PortContractError(
                f"row {position} written to {path!r}, field {name!r}: {reason}.",
                context=ErrorContext(handle=path),
            )
    if row.geometry is None:
        return
    if schema.data_type is not DataType.FEATURE_CLASS:
        raise PortContractError(
            f"row {position} written to {path!r} carries a geometry, and a "
            f"{schema.data_type.value} has none.",
            context=ErrorContext(handle=path),
        )
    if row.geometry.crs != schema.geometry_crs:
        raise PortContractError(
            f"row {position} written to {path!r} is in {row.geometry.crs!r}; the "
            f"schema declares {schema.geometry_crs!r}.",
            context=ErrorContext(handle=path),
        )
    family = schema.geometry_family
    if family is not None and row.geometry.kind.family is not family:
        raise PortContractError(
            f"row {position} written to {path!r} is a {row.geometry.kind.value}, "
            f"outside the schema's {family.value} family; a feature class holds one "
            "geometry type.",
            context=ErrorContext(handle=path),
        )
