# Slice 1a evidence: the facade spike

**Status:** EVIDENCE, 2026-10-29. Produced for the fifth pull request of slice 1a (the facade
spike: `lineage/facade.py` with `PortCall`, `PortFacade` and `wrap`; the reachability test
`tests/unit/lineage/test_facade.py`; the typing guard `tests/static/test_facade_typing.py`; the
cast count `tests/static/test_cast_count.py`; A11.11's cost sentence reworded and B27 opened) by
`python -m tools.break_once facade`, whose case table is `tools/break_once/cases/facade.py`.
Every guard broken once, with the covering tests failing, then restored; the SHA-256 of the
three mutated source files (`lineage/facade.py`, `runtime/local.py`,
`generalization/__init__.py`) was identical before and after the run, and the set's suite was
green after the last restore. Preflight, `python -m tools.break_once facade --check`:
`break-it-once: 11 cases in 1 set(s); needles match, targets collect`.

## The spike's question

Does pyright strict force per-method code on a generic facade? No. `pyright
src/ag/lineage/facade.py` under the project configuration: `0 errors, 0 warnings, 0
informations`. The module holds one `typing.cast`, in `wrap`, pinned by
`tests/static/test_cast_count.py`; it has no `type: ignore`, no `pyright: ignore` and no
explicit `Any`. What strict loosened besides the cast: the two `getattr` reads in
`__getattr__`, the Protocol function for `__row_shape__` and the port's bound method, come
back as `Any` and land in annotated locals (`Mapping[str, Rows]`, `Callable[..., object]`),
inside the facade and at no call site. The one-generic-facade design stands; 2a builds on it.

The carried finding on `wrap(protocol: type[P], port: P) -> P`: against a non-conformer the
bare call reports nothing, `P` solving to `Ops | NotConforming`. The non-conformer is refused
where the wrapped port is handed out: `reportAssignmentType` on an annotated assignment,
`reportArgumentType` on a dataclass field, which is the Toolbox's shape. A curried
`wrap(Ops)(port)` would fail at the bare call too; the two-argument form was kept because
every real hand-out is a typed Toolbox field. The typing guard asserts the two hand-out
diagnostics exactly and that the bare line reports nothing, so the gap is recorded and a
checker change that closes it is noticed. F6 breaks it by widening `port` to `object`.

F3 removes both defences against a name off the Protocol, the membership check and the
strict lookup on the Protocol, because with the check alone removed the lookup still raises
and the target would fail on its message only. F9's target records the `before` hook: with
the positional refusal removed the port raises its own `TypeError`, and the guard's reason
is that a `PortCall` with empty kwargs reached the hook. F11 removes the dunder guard; the
covering assertion is the bare `copy.copy(facade)`, which recursed before the guard existed.

Case set `facade`, run by `python -m tools.break_once facade`. Per case: its targets pass on the clean tree (baseline), one source file is edited to remove the guard, the same targets must then fail, and the file is restored. The set's suite runs after the last restore.

### F1: the row shape read from the port instance instead of the Protocol

File: `src/ag/lineage/facade.py`. Edit: `declaration = getattr(self._protocol, name)` -> `declaration = getattr(self._port, name)`.

Targets: test_the_rows_come_from_the_protocol_and_not_from_the_adapter. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       assert seen[0].rows == getattr(GeometryOps.select, "__row_shape__")
E       AssertionError: assert mappingproxy(..., refs=None)}) == mappingproxy(..., refs=None)})
E         Differing items:
E         {'output': Rows(cardinality=<Cardinality.GROUP: 'group'>, ids=<Ids.MINT: 'mint'>, subject='input', context=None, refs=None)} != {'output': Rows(cardinality=<Cardinality.ONE: 'one'>, ids=<Ids.CARRY: 'carry'>, subject='input', context=None, refs=None)}
E         Use -v to get more diff
FAILED tests/unit/lineage/test_facade.py::test_the_rows_come_from_the_protocol_and_not_from_the_adapter
1 failed in 0.04s
```

### F2: a second cast, under an alias, in another package

File: `src/ag/runtime/local.py`. Edit: append 'from typing import cast as c  # probe' ....

Targets: test_cast_call_sites_are_pinned. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       assert cast_counts() == PINNED, (
E       AssertionError: a typing.cast call site appeared or moved; each one is a deliberate edit to PINNED, with its reason in the review
E       assert {'lineage/fac.../local.py': 1} == {'lineage/facade.py': 1}
E         Omitting 1 identical items, use -vv to show
E         Left contains 1 more item:
E         {'runtime/local.py': 1}
E         Use -v to get more diff
FAILED tests/static/test_cast_count.py::test_cast_call_sites_are_pinned - Ass...
1 failed in 0.03s
```

### F3: both defences removed: an adapter method off the Protocol reachable and called

File: `src/ag/lineage/facade.py`. Edit: `if name not in self._members:` -> `if False:`; `declaration = getattr(self._protocol, name)` -> `declaration = getattr(self._protocol, name, None)`.

Targets: test_a_public_name_on_the_adapter_but_off_the_protocol_is_not_reachable. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       with pytest.raises(AttributeError, match="GeometryOps has no member 'extra'"):
E       Failed: DID NOT RAISE AttributeError
FAILED tests/unit/lineage/test_facade.py::test_a_public_name_on_the_adapter_but_off_the_protocol_is_not_reachable
1 failed in 0.03s
```

### F4: the before hook not called

File: `src/ag/lineage/facade.py`. Edit: delete `self._before(call)`.

Targets: test_the_hooks_see_the_call_with_the_protocols_rows_in_order. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       assert before_seen == [expected]
E       AssertionError: assert [] == [PortCall(pro...ory:/kept')})]
E         Right contains one more item: PortCall(protocol=<class 'ag.ports.geometry_ops.GeometryOps'>, method='select', rows=mappingproxy({'output': Rows(card...d='rank', op=<Comparison.GE: '>='>, value=2), 'output': ScratchHandle(tests.support.memory.kept, path='memory:/kept')})
E         Use -v to get more diff
FAILED tests/unit/lineage/test_facade.py::test_the_hooks_see_the_call_with_the_protocols_rows_in_order
1 failed in 0.03s
```

### F5: the after hook not called

File: `src/ag/lineage/facade.py`. Edit: delete `self._after(call, result)`.

Targets: test_the_hooks_see_the_call_with_the_protocols_rows_in_order. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       assert after_seen == [(expected, None)]
E       AssertionError: assert [] == [(PortCall(pr...pt')}), None)]
E         Right contains one more item: (PortCall(protocol=<class 'ag.ports.geometry_ops.GeometryOps'>, method='select', rows=mappingproxy({'output': Rows(car...', op=<Comparison.GE: '>='>, value=2), 'output': ScratchHandle(tests.support.memory.kept, path='memory:/kept')}), None)
E         Use -v to get more diff
FAILED tests/unit/lineage/test_facade.py::test_the_hooks_see_the_call_with_the_protocols_rows_in_order
1 failed in 0.03s
```

### F6: wrap's port parameter widened to object, so a non-conformer is handed out

File: `src/ag/lineage/facade.py`. Edit: `port: P,` -> `port: object,`.

Targets: test_a_non_conformer_is_refused_where_the_wrapped_port_is_handed_out. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       assert diagnostics(fixture) == [
E       AssertionError: pyright must refuse the non-conformer at both hand-outs, accept the conformer everywhere, and report nothing on the bare call; anything else means wrap's type changed
E       assert [] == [('reportAssi...entType', 33)]
E         Right contains 2 more items, first extra item: ('reportAssignmentType', 32)
E         Use -v to get more diff
FAILED tests/static/test_facade_typing.py::test_a_non_conformer_is_refused_where_the_wrapped_port_is_handed_out
1 failed in 0.60s
```

### F7: the port's result not returned

File: `src/ag/lineage/facade.py`. Edit: `return result` -> `return None`.

Targets: test_a_call_through_the_facade_equals_the_direct_call[TableOps.read_rows]. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>           assert list(wrapped_result) == list(direct_result)
E           TypeError: 'NoneType' object is not iterable
FAILED tests/unit/lineage/test_facade.py::test_a_call_through_the_facade_equals_the_direct_call[TableOps.read_rows]
1 failed in 0.04s
```

### F8: the parents keyword dropped before forwarding

File: `src/ag/lineage/facade.py`. Edit: `result = target(**kwargs)` -> `result = target(`.

Targets: test_a_call_through_the_facade_equals_the_direct_call[GeometryOps.explode_multipart]. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>           assert wrapped_store.read(handle) == direct_store.read(handle), name
>           raise PortContractError(
E           ag.ports.errors.PortContractError: ScratchHandle(tests.support.memory.pairs, path='memory:/pairs') names no dataset: nothing has been written to 'memory:/pairs'.
FAILED tests/unit/lineage/test_facade.py::test_a_call_through_the_facade_equals_the_direct_call[GeometryOps.explode_multipart]
1 failed in 0.04s
```

### F9: a positional call forwarded instead of refused

File: `src/ag/lineage/facade.py`. Edit: `if args:` -> `if False:`.

Targets: test_a_positional_call_fails_at_the_facade_naming_the_method. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       with pytest.raises(TypeError, match="GeometryOps.select takes keyword arguments"):
E       AssertionError: Regex pattern did not match.
E         Expected regex: 'GeometryOps.select takes keyword arguments'
E         Actual message: "Selection.select() missing 3 required keyword-only arguments: 'input', 'where', and 'output'"
FAILED tests/unit/lineage/test_facade.py::test_a_positional_call_fails_at_the_facade_naming_the_method
1 failed in 0.04s
```

### F10: row 10: the domain imports the facade

File: `src/ag/generalization/__init__.py`. Edit: append 'import ag.lineage.facade  # probe' ....

Targets: test_contract_is_kept[row-10-lineage-is-runtimes-alone]. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       assert verdicts[CONTRACTS[contract]] == "KEPT", contract
E       AssertionError: row-10-lineage-is-runtimes-alone
E       assert 'BROKEN' == 'KEPT'
E         - KEPT
E         + BROKEN
FAILED tests/static/test_import_contracts.py::test_contract_is_kept[row-10-lineage-is-runtimes-alone]
1 failed in 0.09s
```

### F11: the dunder guard removed, so a copy probe recurses into the facade's state

File: `src/ag/lineage/facade.py`. Edit: delete `if name.startswith("_"):`.

Targets: test_a_name_off_the_protocol_raises_and_the_facade_has_no_public_name. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       copy.copy(facade)
E   RecursionError: maximum recursion depth exceeded
FAILED tests/unit/lineage/test_facade.py::test_a_name_off_the_protocol_raises_and_the_facade_has_no_public_name
1 failed in 0.04s
```

### After the last restore

```
93 passed in 1.48s
```
