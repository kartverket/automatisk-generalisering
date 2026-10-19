# Slice 1a evidence: the row-shape grammar

**Status:** EVIDENCE, 2026-10-19. Produced for the third pull request of slice 1a (the row-shape
grammar: `ports/row_shape.py`, `ports/columns.py`, the three Protocol methods `read_rows`,
`select` and `explode_multipart`, the check over the surface in `tests/static/test_row_shape.py`,
the typing guard in `tests/static/test_row_shape_typing.py`, the unit tests of `Rows` and the
decorator, ADR-0017, and row 5 of `.importlinter` extended with `row_shape` and `columns`) by
`python -m tools.break_once row_shape`, whose case table is `tools/break_once/cases/row_shape.py`
(A30). Every guard broken once, with the covering tests failing, then restored; the SHA-256 of
the three mutated source files was identical before and after the run, and the set's suite was
green after the last restore. R10 is the typing guard: the real test, under the project
configuration (`--project pyproject.toml`, working directory the repository root), passes on the
clean tree (its baseline), fails once the decorator's type variables are erased, and passes again
after the restore (the suite line at the end). R17 breaks the row-5 contract through
`tests/static/test_import_contracts.py`, as P23 and P24 did for the port values.

Case set `row_shape`, run by `python -m tools.break_once row_shape`. Per case: its targets pass on the clean tree (baseline), one source file is edited to remove the guard, the same targets must then fail, and the file is restored. The set's suite runs after the last restore.

### R1: GROUP + CARRY and GROUP + FOREIGN accepted

File: `src/ag/ports/row_shape.py`. Edit: `if self.cardinality is Cardinality.GROUP and self.ids is not Ids.MINT:` -> `if False:`.

Targets: test_group_with_carry_or_foreign_is_refused_because_a_scalar_cannot_hold_a_set. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>           with pytest.raises(ValueError, match="scalar cannot hold a set"):
E           Failed: DID NOT RAISE ValueError
FAILED tests/unit/ports/test_row_shape.py::test_group_with_carry_or_foreign_is_refused_because_a_scalar_cannot_hold_a_set
1 failed in 0.03s
```

### R2: MANY + CARRY accepted

File: `src/ag/ports/row_shape.py`. Edit: `if self.cardinality is Cardinality.MANY and self.ids is Ids.CARRY:` -> `if False:`.

Targets: test_many_with_carry_is_refused_as_the_inheritance_model. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       with pytest.raises(ValueError, match="inheritance model lineage rejects"):
E       Failed: DID NOT RAISE ValueError
FAILED tests/unit/ports/test_row_shape.py::test_many_with_carry_is_refused_as_the_inheritance_model
1 failed in 0.02s
```

### R3: CARRY or MINT accepted without a subject

File: `src/ag/ports/row_shape.py`. Edit: `if self.subject is None:` -> `if False:`.

Targets: test_carry_and_mint_need_a_subject_and_take_no_refs. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>           with pytest.raises(ValueError, match="subject= is required"):
E           Failed: DID NOT RAISE ValueError
FAILED tests/unit/ports/test_row_shape.py::test_carry_and_mint_need_a_subject_and_take_no_refs
1 failed in 0.02s
```

### R4: CARRY or MINT accepted with refs

File: `src/ag/ports/row_shape.py`. Edit: `if self.refs:` -> `if False:`.

Targets: test_carry_and_mint_need_a_subject_and_take_no_refs. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>           with pytest.raises(ValueError, match="refs are for FOREIGN"):
E           Failed: DID NOT RAISE ValueError
FAILED tests/unit/ports/test_row_shape.py::test_carry_and_mint_need_a_subject_and_take_no_refs
1 failed in 0.02s
```

### R5: FOREIGN accepted without refs

File: `src/ag/ports/row_shape.py`. Edit: `if not self.refs:` -> `if False:`.

Targets: test_foreign_needs_refs_and_has_no_subject. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       with pytest.raises(ValueError, match="refs={column: input} is required"):
E       Failed: DID NOT RAISE ValueError
FAILED tests/unit/ports/test_row_shape.py::test_foreign_needs_refs_and_has_no_subject
1 failed in 0.03s
```

### R6: FOREIGN accepted with a subject

File: `src/ag/ports/row_shape.py`. Edit: `if self.subject is not None:` -> `if False:`.

Targets: test_foreign_needs_refs_and_has_no_subject. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       with pytest.raises(ValueError, match="has no subject"):
E       Failed: DID NOT RAISE ValueError
FAILED tests/unit/ports/test_row_shape.py::test_foreign_needs_refs_and_has_no_subject
1 failed in 0.03s
```

### R7: an axis given a default

File: `src/ag/ports/row_shape.py`. Edit: `ids: Ids` -> `ids: Ids = Ids.CARRY`.

Targets: test_both_axes_are_required. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>           Rows(Cardinality.ONE)  # type: ignore[call-arg]
>               raise ValueError(
E               ValueError: a CARRY output names the input its rows derive from: subject= is required.
FAILED tests/unit/ports/test_row_shape.py::test_both_axes_are_required - Valu...
1 failed in 0.03s
```

### R8: the decorator returns a plain wrapper instead of the function

File: `src/ag/ports/row_shape.py`. Edit: `from typing import Any, TypeVar` -> `from typing import Any, TypeVar, cast`; `setattr(fn, "__row_shape__", MappingProxyType(dict(outputs)))` -> `def wrapper(*args: Any, **kwargs: Any) -> Any:`.

Targets: test_the_decorator_leaves_signature_and_hints_unchanged. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       assert inspect.signature(declared) == inspect.signature(reference)
E       AssertionError: assert <Signature (*args: 'Any', **kwargs: 'Any') -> 'Any'> == <Signature (self, *, input: 'In', output: 'Out') -> 'None'>
E        +  where <Signature (*args: 'Any', **kwargs: 'Any') -> 'Any'> = <function signature at 0x7156a454a480>(<function row_shape.<locals>.attach.<locals>.wrapper at 0x7156a3aa5940>)
E        +    where <function signature at 0x7156a454a480> = inspect.signature
E        +  and   <Signature (self, *, input: 'In', output: 'Out') -> 'None'> = <function signature at 0x7156a454a480>(<function Undecorated.copy at 0x7156a3aa5800>)
FAILED tests/unit/ports/test_row_shape.py::test_the_decorator_leaves_signature_and_hints_unchanged
1 failed in 0.03s
```

### R9: the decorator returns a functools.wraps wrapper instead of the function

File: `src/ag/ports/row_shape.py`. Edit: `from __future__ import annotations` -> `from __future__ import annotations`; `from typing import Any, TypeVar` -> `from typing import Any, TypeVar, cast`; `setattr(fn, "__row_shape__", MappingProxyType(dict(outputs)))` -> `@functools.wraps(fn)`.

Targets: test_the_decorator_returns_the_function_itself. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       assert not hasattr(declared, "__wrapped__")
E       AssertionError: assert not True
E        +  where True = hasattr(<function Ops.copy at 0x7de7cdb8d940>, '__wrapped__')
FAILED tests/unit/ports/test_row_shape.py::test_the_decorator_returns_the_function_itself
1 failed in 0.03s
```

### R10: the decorator erases the method's type

File: `src/ag/ports/row_shape.py`. Edit: `def row_shape(**outputs: Rows) -> Callable[[F], F]:` -> `def row_shape(**outputs: Rows) -> Callable[[Any], Any]:`; `def attach(fn: F) -> F:` -> `def attach(fn: Any) -> Any:`.

Targets: test_the_decorated_protocol_still_refuses_a_non_conformer. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       assert diagnostics(fixture) == [("reportAssignmentType", REFUSED_LINE)], (
E       AssertionError: pyright must refuse exactly the non-conforming assignment and accept the conforming one; anything else means the decorator changed the method's type
E       assert [] == [('reportAssignmentType', 23)]
E         Right contains one more item: ('reportAssignmentType', 23)
E         Use -v to get more diff
FAILED tests/static/test_row_shape_typing.py::test_the_decorated_protocol_still_refuses_a_non_conformer
1 failed in 0.74s
```

### R11: an Out with no row

File: `src/ag/ports/geometry_ops.py`. Edit: delete `@row_shape(output=Rows(Cardinality.ONE, Ids.CARRY, subject="input"))`.

Targets: test_rule_holds[out-without-row]. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       assert broken == [], "\n".join(broken)
E       AssertionError: GeometryOps.select: output 'output' declares no row shape. Add it to @row_shape, or, for a method whose rows the caller builds, declare the ids axis at the call site once that declaration type exists.
E       assert ['GeometryOps...type exists.'] == []
E         Left contains one more item: "GeometryOps.select: output 'output' declares no row shape. Add it to @row_shape, or, for a method whose rows the caller builds, declare the ids axis at the call site once that declaration type exists."
E         Use -v to get more diff
FAILED tests/static/test_row_shape.py::test_rule_holds[out-without-row] - Ass...
1 failed in 0.03s
```

### R12: a row naming the ParentsOut parameter instead of the Out

File: `src/ag/ports/geometry_ops.py`. Edit: `@row_shape(output=Rows(Cardinality.MANY, Ids.MINT, subject="input"))` -> `@row_shape(parents=Rows(Cardinality.MANY, Ids.MINT, subject="input"))`.

Targets: test_rule_holds[row-names-non-out]. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       assert broken == [], "\n".join(broken)
E       AssertionError: GeometryOps.explode_multipart: @row_shape names 'parents', which is not an Out parameter; a ParentsOut carries no row.
E       assert ['GeometryOps...ries no row.'] == []
E         Left contains one more item: "GeometryOps.explode_multipart: @row_shape names 'parents', which is not an Out parameter; a ParentsOut carries no row."
E         Use -v to get more diff
FAILED tests/static/test_row_shape.py::test_rule_holds[row-names-non-out] - A...
1 failed in 0.03s
```

### R13: a subject naming a parameter that is not an In

File: `src/ag/ports/geometry_ops.py`. Edit: `@row_shape(output=Rows(Cardinality.ONE, Ids.CARRY, subject="input"))` -> `@row_shape(output=Rows(Cardinality.ONE, Ids.CARRY, subject="where"))`.

Targets: test_rule_holds[input-names-non-in]. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       assert broken == [], "\n".join(broken)
E       AssertionError: GeometryOps.select: row 'output' names 'where', which is not an In parameter of the method.
E       assert ['GeometryOps... the method.'] == []
E         Left contains one more item: "GeometryOps.select: row 'output' names 'where', which is not an In parameter of the method."
E         Use -v to get more diff
FAILED tests/static/test_row_shape.py::test_rule_holds[input-names-non-in] - ...
1 failed in 0.03s
```

### R14: an output annotated as a bare ScratchHandle

File: `src/ag/ports/geometry_ops.py`. Edit: `from ag.core.handles import In, Out, ParentsOut` -> `from ag.core.handles import In, Out, ParentsOut, ScratchHandle`; `def select(self, *, input: In, where: Predicate, output: Out) -> None:` -> `def select(`.

Targets: test_rule_holds[unmarked-handle]. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       assert broken == [], "\n".join(broken)
E       AssertionError: GeometryOps.select: 'output' is a handle with no direction marker; every port handle parameter is In, Out, Mutates or ParentsOut.
E       assert ['GeometryOps... ParentsOut.'] == []
E         Left contains one more item: "GeometryOps.select: 'output' is a handle with no direction marker; every port handle parameter is In, Out, Mutates or ParentsOut."
E         Use -v to get more diff
FAILED tests/static/test_row_shape.py::test_rule_holds[unmarked-handle] - Ass...
1 failed in 0.03s
```

### R15: a method with no Out that is not in the query list

File: `src/ag/ports/geometry_ops.py`. Edit: append 'class Probe(Protocol):  # probe' ....

Targets: test_rule_holds[unlisted-query]. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       assert broken == [], "\n".join(broken)
E       AssertionError: Probe.count: writes no handle and is not in the query list; a query is listed, never inferred from a missing Out.
E       assert ['Probe.count...missing Out.'] == []
E         Left contains one more item: 'Probe.count: writes no handle and is not in the query list; a query is listed, never inferred from a missing Out.'
E         Use -v to get more diff
FAILED tests/static/test_row_shape.py::test_rule_holds[unlisted-query] - Asse...
1 failed in 0.03s
```

### R16: a Mutates parameter on the surface

File: `src/ag/ports/geometry_ops.py`. Edit: append 'from ag.core.handles import Mutates  # probe' ....

Targets: test_rule_holds[mutates-fails-closed]. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       assert broken == [], "\n".join(broken)
E       AssertionError: Probe.touch: ['input'] is Mutates, and the declaration form for a method that changes its input in place is not decided; the surface may not carry one until it is.
E       assert ['Probe.touch...until it is.'] == []
E         Left contains one more item: "Probe.touch: ['input'] is Mutates, and the declaration form for a method that changes its input in place is not decided; the surface may not carry one until it is."
E         Use -v to get more diff
FAILED tests/static/test_row_shape.py::test_rule_holds[mutates-fails-closed]
1 failed in 0.03s
```

### R17: row 5: columns imports its sibling predicates

File: `src/ag/ports/columns.py`. Edit: append 'import ag.ports.predicates  # probe' ....

Targets: test_contract_is_kept[row-05-port-layers]. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       assert verdicts[CONTRACTS[contract]] == "KEPT", contract
E       AssertionError: row-05-port-layers
E       assert 'BROKEN' == 'KEPT'
E         - KEPT
E         + BROKEN
FAILED tests/static/test_import_contracts.py::test_contract_is_kept[row-05-port-layers]
1 failed in 0.09s
```

### After the last restore

```
95 passed in 0.92s
```
