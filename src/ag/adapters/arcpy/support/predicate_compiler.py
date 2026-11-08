"""A `Predicate` compiled to a WHERE clause for the engine's selection tools.

What: `check(predicate, dataset=)`, one walk that raises for what cannot be compiled
over that dataset; `where_clause(predicate, session=, dataset=)`, the clause.

How: attribute leaves compile to SQL, which evaluates in three values exactly as the port
specifies, so no negation is rewritten and no selection state is held: `NOT (...)` over
an UNKNOWN comparison stays UNKNOWN and the row is excluded (ADR-0019 PC-D15). The empty
`IsIn`, which SQL cannot spell, compiles to `("f" IS NULL AND "f" IS NOT NULL)`, FALSE for
every row; its negation is then TRUE for every row, as under the in-memory adapter.
`LIKE` passes its `%` and `_` through with no ESCAPE clause (PC-D16). Every value is
checked against its field through the shared rule before anything compiles (PC-D17): a
wrong type, an out-of-range integer, an over-long text, a bool, and an undeclared or
unrepresentable field are a `PortContractError` from `check`, so an engine coercion and
a Python comparison can never disagree; a `LIKE` pattern is held to the field's type and
not its length. A `RawAttr` is compiled as written (PC-D14). Identifiers are quoted by
the engine's own rule for the dataset's workspace (PC-D20); text literals by SQL's
doubled quote; dates in the file geodatabase form, `date 'YYYY-MM-DD HH:MM:SS'`, with
the fraction appended as `.ffffff` when there is one, which both workspaces compare with
its fraction (the probe of 2026-11-08: a fractional literal matched the stored fraction
and nothing else), so a whole-second literal never matches a value a microsecond off.
An enterprise geodatabase dialect is not built. A `Spatial` leaf is not compiled yet and
raises `NotImplementedError`, which is not a port error, so no caller mistakes it for a
contract breach; its route, the engine's layer selection with negation pushed to the
leaves, lands with its first caller.

Second caller: `GeometryOps.count`, ADR-0019 PC-D5, not yet landed.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime

from ag.adapters._shared.field_values import type_mismatch
from ag.adapters.arcpy.session import ArcpySession
from ag.adapters.arcpy.support.dataset_schema import DescribedDataset, declared_field
from ag.ports.attributes import AttributeValue, Field, FieldName, FieldType
from ag.ports.errors import PortContractError
from ag.ports.predicates import (
    And,
    Compare,
    Comparison,
    IsIn,
    IsNull,
    Not,
    Or,
    Predicate,
    RawAttr,
    Spatial,
)


def check(predicate: Predicate, *, dataset: DescribedDataset) -> None:
    """Raises `PortContractError` for anything in `predicate` that cannot compile over
    `dataset`: an undeclared or unrepresentable field, a value that does not fit its
    field; `NotImplementedError` for a spatial leaf. Runs once per call, before any row."""
    match predicate:
        case Compare(field=name, op=Comparison.LIKE):
            field = declared_field(dataset, name)
            if field.type is not FieldType.TEXT:
                raise PortContractError(
                    f"LIKE on {name!r}, a {field.type.value} field; a pattern matches "
                    "text only."
                )
        case Compare(field=name, value=value):
            _fit(value=value, field=declared_field(dataset, name))
        case IsIn(field=name, values=values):
            field = declared_field(dataset, name)
            for value in values:
                _fit(value=value, field=field)
        case IsNull(field=name):
            declared_field(dataset, name)
        case RawAttr():
            pass
        case Spatial():
            raise NotImplementedError(
                f"{predicate!r}: a spatial leaf is not compiled by the ArcPy adapter yet."
            )
        case Not(term=term):
            check(term, dataset=dataset)
        case And(terms=terms) | Or(terms=terms):
            for term in terms:
                check(term, dataset=dataset)
        case _:
            raise TypeError(
                f"{predicate!r} is not a predicate node this adapter knows."
            )


def where_clause(
    predicate: Predicate, *, session: ArcpySession, dataset: DescribedDataset
) -> str:
    """The clause for `predicate` over `dataset`; `check` has run."""
    quoted = _quoted(session, path=dataset.path, names=_fields_of(predicate))
    return _compile(predicate, quoted=quoted)


def _fields_of(predicate: Predicate) -> frozenset[FieldName]:
    match predicate:
        case Compare(field=name) | IsIn(field=name) | IsNull(field=name):
            return frozenset({name})
        case Not(term=term):
            return _fields_of(term)
        case And(terms=terms) | Or(terms=terms):
            return frozenset[FieldName]().union(*(_fields_of(term) for term in terms))
        case _:
            return frozenset()


def _quoted(
    session: ArcpySession, *, path: str, names: frozenset[FieldName]
) -> Mapping[FieldName, str]:
    """Each field name quoted as the dataset's workspace requires, by the engine's rule."""
    quoted: dict[FieldName, str] = {}
    with session.guard("AddFieldDelimiters"):
        import arcpy

        for name in sorted(names):
            quoted[name] = arcpy.AddFieldDelimiters(path, name)
    return quoted


def _compile(predicate: Predicate, *, quoted: Mapping[FieldName, str]) -> str:
    match predicate:
        case Compare(field=name, op=op, value=value):
            return f"{quoted[name]} {op.value} {_literal(value)}"
        case IsIn(field=name, values=values):
            if not values:
                return f"({quoted[name]} IS NULL AND {quoted[name]} IS NOT NULL)"
            return f"{quoted[name]} IN ({', '.join(_literal(v) for v in values)})"
        case IsNull(field=name):
            return f"{quoted[name]} IS NULL"
        case RawAttr(cql=cql):
            return f"({cql})"
        case Not(term=term):
            return f"NOT ({_compile(term, quoted=quoted)})"
        case And(terms=terms):
            return "(" + " AND ".join(_compile(t, quoted=quoted) for t in terms) + ")"
        case Or(terms=terms):
            return "(" + " OR ".join(_compile(t, quoted=quoted) for t in terms) + ")"
        case _:
            raise TypeError(f"{predicate!r} reached compilation; check() runs first.")


def _literal(value: AttributeValue) -> str:
    """A SQL literal for a checked value; `check` has refused None and bool."""
    if isinstance(value, str):
        return "'" + value.replace("'", "''") + "'"
    if isinstance(value, datetime):
        fraction = f".{value.microsecond:06d}" if value.microsecond else ""
        return f"date '{value:%Y-%m-%d %H:%M:%S}{fraction}'"
    if value is None:
        raise TypeError("a null reached compilation; check() refuses it.")
    return repr(value)


def _fit(*, value: AttributeValue, field: Field) -> None:
    reason = type_mismatch(value=value, field=field)
    if reason is not None:
        raise PortContractError(f"predicate on field {field.name!r}: {reason}.")
