# ADR-0015: Attribute predicates are structured leaves, with a counted escape hatch

**Status:** Accepted (decided 2026-09-21, recorded here 2026-10-07)

**Amends:** ADR-0001, whose `Attr` leaf was one CQL2 text string. The algebra, the
`Spatial`, `And`, `Or` and `Not` nodes and the operators are unchanged.

## Context

ADR-0001 made selection a composable predicate value and gave the attribute leaf the form
`Attr(cql: str)`: a CQL2-Text expression the adapter compiles. Writing the first adapter and
the first operations showed two costs of the string.

An opaque expression forces every adapter to write a parser before it can quote an
identifier correctly: the engine's field delimiters differ by workspace type, and a parser
is the only way to find the identifiers in a string. And the string admits expressions no
adapter can compile. The template contained two, both subqueries against a scratch handle
(`... in (select ... from merge_report)`), and a third in the one place that demonstrated the
legitimate domain-key lookup. All three type-checked and would have failed in a pod.

Three independent needs converged on a membership leaf: the predicate design itself, the
39 legacy row-deletion sites, which become `select(where=~Attr.in_(id, ids))`, and the
work-key API's `where_in`. This record absorbs A2.1, A2.2 and A2.3 of the lineage decision
record.

## Decision

The attribute leaf is a closed set of structured nodes, built through four constructors on
`Attr`, which is a namespace and not a type:

- `Attr.cmp(field, op, value)`: `field <op> value`, where `op` is one of `=`, `<>`, `<`,
  `<=`, `>`, `>=` and `LIKE`, and `value` is an attribute value other than `None`. A
  comparison with `NULL` is never true in SQL, so it is refused at construction and a null
  test goes through `Attr.is_null`; no adapter has to special-case it.
- `Attr.in_(field, values)`: `field IN (values)`. The values are kept as a tuple, `None` is
  refused, and the empty set is legitimate: it matches no row, which an adapter must honour,
  because `~Attr.in_(id, ids)` with nothing to exclude is an ordinary call.
- `Attr.is_null(field)`: `field IS NULL`.
- `Attr.raw(cql)`: a CQL2 text expression compiled as written. The escape hatch for what the
  structured leaves cannot say; every call site in the package is counted by a static test
  pinned to the current number, so adding one is a deliberate edit to that test.

The leaves are frozen dataclasses (`Compare`, `IsIn`, `IsNull`, `RawAttr`) so that an adapter
pattern-matches them exhaustively, and a type alias names the closed set. The algebra lives in
its own module, `ports/predicates.py`, beside the column vocabulary it names, because two
ports take predicates and the Protocol file should stay the contract.

## Consequences

Structure and value types are checked when a leaf is built, which is at import for a
declaration module. A wrong field name is not: that needs schema declarations on handles,
which would be additive to this decision and is a stated non-goal here.

An adapter compiles four leaf shapes plus the raw string, quoting identifiers for its
workspace type as it goes; it never parses. The ArcPy adapter still pushes negation to the
leaves by De Morgan, as ADR-0001 says, and its adapter-internal `Negated` node still never
crosses the port.

The three uncompilable template expressions are rewritten under this form: the subqueries
become a `read_rows` of the small table followed by `Attr.in_`, and the lookup example
becomes `Attr.in_(code_field, codes)`. The 39 deletion sites have a target form.
