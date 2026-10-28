# ADR-0019: Port contract: what crosses a port

**Status:** Accepted, 2026-10-22.

**Scope:** The values and method contracts of `ag/ports/`: handles at the boundary,
`ports/predicates.py`, `ports/attributes.py`, `ports/geometry.py`, and row IO on `TableOps`.
Absorbs A2.1, A2.2 and A2.3; A4.1, A4.2 and A4.3 land here. The method contracts for parents
capability and single-part dissolve (A14.1, A18) join when they migrate. Row shape is
ADR-0017.

Related: ADR-0018 (the ports as a package), ADR-0017 (row shape), ADR-0020 (operations).

## Direction

1. A port method that takes a dataset takes it as a `ScratchHandle`. `DataObject` never
   appears in `ports/`, so an adapter sees no identity, classification or location of a
   dataset and cannot branch on them.
2. Selection is an immutable predicate value with a closed algebra. No mutable selection
   crosses a port, and a predicate materialises nothing until it is applied.
3. Attribute predicates are a closed set of structured leaves, evaluated in three values as
   SQL does. A raw expression is a counted escape hatch.
4. No cursor crosses a port. Rows are read, written and updated in bulk, an update keyed on a
   stable id; expression updates are declarative; `Geometry` is an immutable value type.

## PC-1 Handles at the boundary

**Direction.** Port signatures name a dataset by `ScratchHandle`, the operation's view of
data, never by `DataObject`, the planner's.

**Details.**

- **PC-D1** `DataObject` (`ExternalSource`, `ProductIdentity`, `Derived`) is what a stage
  declares; the dependency graph, classification and pinning are computed over it.
  `ScratchHandle` is what an operation receives: a named slot in the pod scratch root, with no
  identity and no location.
- **PC-D2** An operation sees no URI, no client, no partition index and no context radius, and
  the rule extends unchanged to adapters. An adapter resolves no location and sees no
  classification; classification is computed at plan time.
- **PC-D3** `ports/` imports only the `core` modules that `.importlinter` row 4 allows, and
  never `core.pipeline`.
- **PC-D4** Port parameters are keyword-only, with the unit in the name (`width_m`,
  `tolerance_m`). Options are project enums, never vendor strings or bare booleans.

## PC-2 Selection as a predicate

**Direction.** A selection is an immutable predicate: adding to, removing from and subsetting
a selection are disjunction, conjunction with a negation, and conjunction, never a held
selection.

**Details.**

- **PC-D5** `GeometryOps` exposes `select(input, where, output)` and
  `count(input, where) -> int`.
- **PC-D6** `Predicate` is an immutable algebra: the attribute leaves of PC-3, `Spatial`,
  `And`, `Or` and `Not`, built with `&`, `|` and `~`.
- **PC-D7** `Spatial(relate_to, relation, distance_m)` names a handle as a value; `Relation`
  carries the CQL2 relation names, and `DWithin` and `Intersects` are constructors over it.
  Which handles a predicate may name is open.
- **PC-D8** The tree maps onto OGC CQL2 and onto a `WHERE` clause in a SQL adapter.
- **PC-D9** An adapter whose engine inverts only at a leaf pushes negation to the leaves by
  De Morgan inside the adapter; its internal negated node never crosses the port.

## PC-3 Attribute leaves

**Direction.** The attribute leaf is a closed set of structured nodes built through
constructors on a namespace, not a type, and the raw escape hatch is counted.

**Details.**

- **PC-D10** `Attr` is a namespace, not a type, with four constructors: `cmp`, `in_`,
  `is_null` and `raw`.
- **PC-D11** `Attr.cmp(field, op, value)`: `op` is one of `=`, `<>`, `<`, `<=`, `>`, `>=` and
  `LIKE`; `value` is an attribute value other than `None`. A comparison with NULL is refused
  at construction and goes through `Attr.is_null`.
- **PC-D12** `Attr.in_(field, values)`: the values are kept as a tuple, `None` is refused, and
  the empty set is legitimate and matches no row.
- **PC-D13** `Attr.is_null(field)`: `field IS NULL`.
- **PC-D14** `Attr.raw(cql)`: a CQL2 text expression compiled as written. A static test pins
  the count of call sites in the package, so adding one is a deliberate edit to that test.
- **PC-D15** Every adapter evaluates a predicate in three values: TRUE, FALSE or UNKNOWN per
  row, and `select` keeps the rows where it is TRUE. `Compare` and a non-empty `IsIn` are
  UNKNOWN when the field is NULL; the empty `IsIn` is FALSE for every row; `IsNull` is never
  UNKNOWN; `Spatial` is UNKNOWN for a row with a null geometry; `Not` of UNKNOWN is UNKNOWN;
  `And` is FALSE if any term is FALSE and otherwise UNKNOWN if any term is; `Or` is the
  mirror. `~Attr.in_(f, ids)` excludes the NULL rows; a caller that wants them writes
  `~Attr.in_(f, ids) | Attr.is_null(f)`.
- **PC-D16** `LIKE` takes a string pattern, `%` for any run of characters and `_` for one,
  matched case-sensitively with no escape character; a literal `%` or `_` goes through
  `Attr.raw`.
- **PC-D17** A value whose type does not match the field's type is a `PortContractError`
  raised by the adapter when a predicate is evaluated, so an engine's coercion and a Python
  comparison can never disagree. `SHORT` and `LONG` take an `int` within the type's range,
  `DOUBLE` takes `int` or `float`, `TEXT` takes a `str` of at most the field's length in
  characters, `DATE` takes a naive `datetime`; a `bool` is refused at that boundary.
- **PC-D18** A predicate has no truth value in Python: `and`, `or` and `not` raise. A
  connective has at least two terms.
- **PC-D19** The leaves are frozen dataclasses `Compare`, `IsIn`, `IsNull` and `RawAttr`, so
  an adapter pattern-matches them exhaustively, and a type alias names the closed set. The
  algebra lives in `ports/predicates.py` beside the column vocabulary, because two ports take
  predicates and a Protocol file stays the contract.
- **PC-D20** An adapter compiles four leaf shapes plus the raw string, quoting identifiers for
  its workspace type; it never parses. The in-memory adapter evaluates the three-valued rule
  in Python and raises `PortContractError` on `RawAttr`.
- **PC-D21** Structure and value types are checked when a leaf is built, at import for a
  declaration module. A wrong field name is not: that needs schema declarations on handles, a
  stated non-goal.

## PC-4 Rows without a cursor

**Direction.** Expression updates are declared, rows move in bulk, and a bulk update is keyed
on a stable id and may carry geometry.

**Details.**

- **PC-D22** `TableOps` has no cursor. `calculate_field(input, field, expression)` declares an
  expression update; `read_rows(input, fields) -> Iterable[Row]` reads in bulk;
  `write_rows(output, schema, rows)` writes in bulk; `update_rows(input, key, fields, rows)`
  writes back rows computed in Python, keyed on a stable id, with no iteration protocol,
  writing the changed rows and not every row, and may carry `Row.geometry`. The key must be
  stable; `lineage_id` provides one.
- **PC-D23** There is no delete method. Deletion is `select` with a negated membership
  predicate.
- **PC-D24** The bulk mapping: a search cursor becomes `read_rows`; an insert cursor becomes
  `write_rows`; an update cursor becomes `calculate_field` where an expression suffices and
  `update_rows` where values are computed in Python.
- **PC-D25** `ports/geometry.py` defines an immutable `Geometry` value type: geometry kind,
  coordinate sequence, CRS. `read_rows` yields it and `write_rows` accepts it. Domain code
  manipulates `Geometry`; adapters implement it with shapely, GEOS or arcpy geometry and
  convert at the boundary.
- **PC-D26** A row written through the port is held to the field types and ranges of
  PC-D17, with `None` a null in a cell; a mismatch is a `PortContractError` from the
  adapter, raised before anything is written.

## Rejected

- **PC-R1** `any()` on the port. It pays only where a backend can short-circuit; arcpy's
  `GetCount` cannot, and `count(...) > 0` covers the case. Reopened by a backend that
  short-circuits (SQL `EXISTS`, `LIMIT 1`).
- **PC-R2** A mutable selection handle at the port. A held selection is arcpy's idiom, not
  the concept; exposing it makes every future adapter emulate arcpy's statefulness. Reopening
  this changes Direction 2.
- **PC-R3** A text expression as the only attribute leaf. Every adapter must parse to quote
  identifiers, and the string admits expressions no adapter can compile. Reopening this
  changes Direction 3.
- **PC-R4** A cursor or row iterator in the port. Target engines are vectorized; a faithful
  cursor port makes the slowest arcpy-shaped pattern part of the contract and guarantees a bad
  second adapter. Reopening this changes Direction 4.
- **PC-R5** A side table plus a join for computed updates. More portable, but a full write
  plus a join where there was one in-place pass. Reopened by an engine with no keyed bulk
  update, where the adapter would implement `update_rows` this way; the port shape does not
  change.
