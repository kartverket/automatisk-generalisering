# Slice 1a evidence: the in-memory adapter

**Status:** EVIDENCE, 2026-10-28. Produced for the fourth pull request of slice 1a (the in-memory
adapter: `adapters/_shared/field_values.py`; `adapters/fakes/memory/` with `store.py`, `_base.py`,
`support/preconditions.py`, `support/predicate_eval.py` and the `geometry_ops`, `table_ops` and
`cartographic_ops` packages; the fixture builders `tests/support/cases.py` and
`tests/support/memory.py`; the unit tests under `tests/unit/adapters/fakes/memory/`;
`tests/static/test_adapter_groups.py` with the static adapter x port matrix; the stated
preconditions on `select` and `explode_multipart`; ADR-0019 PC-D17 adapted and PC-D26 added,
ADR-0020 OP-D14 corrected) by `python -m tools.break_once memory_adapter`, whose case table is
`tools/break_once/cases/memory_adapter.py`. Every guard broken once, with the covering tests
failing, then restored; the SHA-256 of the nine mutated source files was identical before and
after the run, and the set's suite was green after the last restore. Preflight,
`python -m tools.break_once memory_adapter --check`:
`break-it-once: 29 cases in 1 set(s); needles match, targets collect`.

M13 is the run the review asked for: with the counter reset to 1 on every write, the rewrite
test, the range test and the reassignment test fail, while the partition test still passes
because positions and indices then coincide, which is why it is not that case's target. Two
guards no text edit reaches were broken by hand, after the report: the root-contents rule, with
a stray `helpers.py` in the adapter root, and the static matrix, with a renamed parameter in
`Selection.select`, which pyright reports at the adapter's conformance assignment and at the
matrix row. Each was restored and re-run green.

Case set `memory_adapter`, run by `python -m tools.break_once memory_adapter`. Per case: its targets pass on the clean tree (baseline), one source file is edited to remove the guard, the same targets must then fail, and the file is restored. The set's suite runs after the last restore.

### M1: a helper method on a group class

File: `src/ag/adapters/fakes/memory/geometry_ops/selection.py`. Edit: `def select(` -> `def _prepare(self) -> None: ...`.

Targets: test_rule_holds[memory-protocol-methods-only]. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       assert broken == [], "\n".join(broken)
E       AssertionError: memory/geometry_ops/selection.py: class Selection defines '_prepare', which is not a method of the Protocol; a helper is a module-level function.
E       assert ['memory/geom...el function.'] == []
E         Left contains one more item: "memory/geometry_ops/selection.py: class Selection defines '_prepare', which is not a method of the Protocol; a helper is a module-level function."
E         Use -v to get more diff
FAILED tests/static/test_adapter_groups.py::test_rule_holds[memory-protocol-methods-only]
1 failed in 0.04s
```

### M2: a Protocol method defined in two groups

File: `src/ag/adapters/fakes/memory/geometry_ops/shape.py`. Edit: `def explode_multipart(` -> `def select(self) -> None: ...`.

Targets: test_rule_holds[memory-no-duplicate-method], test_every_protocol_method_is_implemented_by_one_group[memory-geometry_ops]. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       assert broken == [], "\n".join(broken)
E       AssertionError: memory/geometry_ops: 'select' is defined in Selection and in Shape; a Protocol method has one group.
E       assert ['memory/geom...s one group.'] == []
E         Left contains one more item: "memory/geometry_ops: 'select' is defined in Selection and in Shape; a Protocol method has one group."
E         Use -v to get more diff
>           assert len(owners) == 1, (
E           AssertionError: memory/geometry_ops: select is implemented by ['Selection', 'Shape']
E           assert 2 == 1
E            +  where 2 = len(['Selection', 'Shape'])
FAILED tests/static/test_adapter_groups.py::test_rule_holds[memory-no-duplicate-method]
FAILED tests/static/test_adapter_groups.py::test_every_protocol_method_is_implemented_by_one_group[memory-geometry_ops]
2 failed in 0.04s
```

### M3: a self assignment in a group method

File: `src/ag/adapters/fakes/memory/geometry_ops/selection.py`. Edit: `distinct_paths(handles=(input, output))` -> `self._last = output`.

Targets: test_rule_holds[memory-no-state-outside-base]. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       assert broken == [], "\n".join(broken)
E       AssertionError: memory: geometry_ops/selection.py:24 self._last; a group holds no state, and only _base.py and the shared object assign an attribute.
E       assert ['memory: geo...n attribute.'] == []
E         Left contains one more item: 'memory: geometry_ops/selection.py:24 self._last; a group holds no state, and only _base.py and the shared object assign an attribute.'
E         Use -v to get more diff
FAILED tests/static/test_adapter_groups.py::test_rule_holds[memory-no-state-outside-base]
1 failed in 0.04s
```

### M4: a body on the composed class

File: `src/ag/adapters/fakes/memory/geometry_ops/__init__.py`. Edit: `"""`GeometryOps` over the in-memory store, composed from its method groups."""` -> `"""`GeometryOps` over the in-memory store, composed from its method groups."""`.

Targets: test_rule_holds[memory-composed-body-empty]. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       assert broken == [], "\n".join(broken)
E       AssertionError: memory/geometry_ops: composed class MemoryGeometryOps defines ('limit',); its body is empty, the groups define everything.
E       assert ['memory/geom... everything.'] == []
E         Left contains one more item: "memory/geometry_ops: composed class MemoryGeometryOps defines ('limit',); its body is empty, the groups define everything."
E         Use -v to get more diff
FAILED tests/static/test_adapter_groups.py::test_rule_holds[memory-composed-body-empty]
1 failed in 0.04s
```

### M5: a composed class not in the matrix

File: `src/ag/adapters/fakes/memory/cartographic_ops/__init__.py`. Edit: append 'class Extra(MemoryPortBase):  # probe' ....

Targets: test_every_composed_class_is_in_the_matrix. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>                   assert node.name in listed, (
E                   AssertionError: memory/cartographic_ops: Extra is not in MATRIX
E                   assert 'Extra' in {'MemoryCartographicOps', 'MemoryGeometryOps', 'MemoryTableOps'}
E                    +  where 'Extra' = <ast.ClassDef object at 0x7857cf3ed890>.name
FAILED tests/static/test_adapter_groups.py::test_every_composed_class_is_in_the_matrix
1 failed in 0.03s
```

### M6: a Protocol method implemented by no group

File: `src/ag/adapters/fakes/memory/table_ops/row_io.py`. Edit: `def read_rows(` -> `def read_rows_(`.

Targets: test_every_protocol_method_is_implemented_by_one_group[memory-table_ops], test_rule_holds[memory-protocol-methods-only]. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>           assert len(owners) == 1, (
E           AssertionError: memory/table_ops: read_rows is implemented by no group
E           assert 0 == 1
E            +  where 0 = len([])
>       assert broken == [], "\n".join(broken)
E       AssertionError: memory/table_ops/row_io.py: class RowIO defines 'read_rows_', which is not a method of the Protocol; a helper is a module-level function.
E       assert ['memory/tabl...el function.'] == []
E         Left contains one more item: "memory/table_ops/row_io.py: class RowIO defines 'read_rows_', which is not a method of the Protocol; a helper is a module-level function."
E         Use -v to get more diff
FAILED tests/static/test_adapter_groups.py::test_every_protocol_method_is_implemented_by_one_group[memory-table_ops]
FAILED tests/static/test_adapter_groups.py::test_rule_holds[memory-protocol-methods-only]
2 failed in 0.04s
```

### M7: UNKNOWN collapsed to FALSE on a NULL comparison

File: `src/ag/adapters/fakes/memory/support/predicate_eval.py`. Edit: `return Truth.UNKNOWN` -> `return Truth.FALSE`.

Targets: test_compare_is_unknown_on_a_null_field_and_so_is_its_negation, test_select_under_a_negation_excludes_the_null_row_until_is_null_is_added. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       assert truth(rank_is_one, BETA) is Truth.UNKNOWN
E       AssertionError: assert <Truth.FALSE: 'false'> is <Truth.UNKNOWN: 'unknown'>
E        +  where <Truth.FALSE: 'false'> = truth(Compare(field='rank', op=<Comparison.EQ: '='>, value=1), Row(attributes={'name': 'beta_road', 'rank': None, 'width_m': 3.0, 'surveyed': None}, geometry=Geometry(kind=<GeometryKind.LINESTRING: 'LineString'>, parts=(((0.0, 0.0), (1.0, 1.0)),), crs='EPSG:25833')))
E        +  and   <Truth.UNKNOWN: 'unknown'> = Truth.UNKNOWN
>       assert names_a == ["Gamma", "delta"]
E       AssertionError: assert ['beta_road',...mma', 'delta'] == ['Gamma', 'delta']
E         At index 0 diff: 'beta_road' != 'Gamma'
E         Left contains one more item: 'delta'
E         Use -v to get more diff
FAILED tests/unit/adapters/fakes/memory/test_predicate_eval.py::test_compare_is_unknown_on_a_null_field_and_so_is_its_negation
FAILED tests/unit/adapters/fakes/memory/test_geometry_ops.py::test_select_under_a_negation_excludes_the_null_row_until_is_null_is_added
2 failed in 0.04s
```

### M8: the type check on predicate values removed

File: `src/ag/adapters/fakes/memory/support/predicate_eval.py`. Edit: `if reason is not None:` -> `if False:`.

Targets: test_check_refuses_what_the_adapter_cannot_evaluate[float-on-long], test_check_refuses_what_the_adapter_cannot_evaluate[long-overflow-lt]. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       with pytest.raises(PortContractError, match=reason):
E       Failed: DID NOT RAISE PortContractError
FAILED tests/unit/adapters/fakes/memory/test_predicate_eval.py::test_check_refuses_what_the_adapter_cannot_evaluate[float-on-long]
FAILED tests/unit/adapters/fakes/memory/test_predicate_eval.py::test_check_refuses_what_the_adapter_cannot_evaluate[long-overflow-lt]
2 failed in 0.04s
```

### M9: RawAttr passed through the check

File: `src/ag/adapters/fakes/memory/support/predicate_eval.py`. Edit: `case RawAttr(cql=cql):` -> `case RawAttr():`.

Targets: test_check_refuses_what_the_adapter_cannot_evaluate[raw], test_a_bad_predicate_on_an_empty_dataset_raises[raw]. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       with pytest.raises(PortContractError, match=reason):
E       Failed: DID NOT RAISE PortContractError
>       with pytest.raises(PortContractError):
FAILED tests/unit/adapters/fakes/memory/test_predicate_eval.py::test_check_refuses_what_the_adapter_cannot_evaluate[raw]
FAILED tests/unit/adapters/fakes/memory/test_geometry_ops.py::test_a_bad_predicate_on_an_empty_dataset_raises[raw]
2 failed in 0.04s
```

### M10: LIKE accepted on a non-text field

File: `src/ag/adapters/fakes/memory/support/predicate_eval.py`. Edit: `if field.type is not FieldType.TEXT:` -> `if False:`.

Targets: test_check_refuses_what_the_adapter_cannot_evaluate[like-on-a-number]. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       with pytest.raises(PortContractError, match=reason):
E       Failed: DID NOT RAISE PortContractError
FAILED tests/unit/adapters/fakes/memory/test_predicate_eval.py::test_check_refuses_what_the_adapter_cannot_evaluate[like-on-a-number]
1 failed in 0.03s
```

### M11: the check skipped before the rows, so an empty input hides a bad predicate

File: `src/ag/adapters/fakes/memory/geometry_ops/selection.py`. Edit: delete `check(where, schema=dataset.schema)`.

Targets: test_a_bad_predicate_on_an_empty_dataset_raises. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       with pytest.raises(PortContractError):
E       Failed: DID NOT RAISE PortContractError
FAILED tests/unit/adapters/fakes/memory/test_geometry_ops.py::test_a_bad_predicate_on_an_empty_dataset_raises[raw]
FAILED tests/unit/adapters/fakes/memory/test_geometry_ops.py::test_a_bad_predicate_on_an_empty_dataset_raises[unknown-field]
FAILED tests/unit/adapters/fakes/memory/test_geometry_ops.py::test_a_bad_predicate_on_an_empty_dataset_raises[long-overflow]
FAILED tests/unit/adapters/fakes/memory/test_geometry_ops.py::test_a_bad_predicate_on_an_empty_dataset_raises[spatial]
4 failed in 0.04s
```

### M12: pairs written under parents=None

File: `src/ag/adapters/fakes/memory/geometry_ops/shape.py`. Edit: `return` -> `parents = ScratchHandle(`.

Targets: test_explode_without_parents_writes_the_children_and_nothing_else. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       assert (
E       AssertionError: assert 19 == ((4 + 7) + 1)
E        +  where 7 = len(mappingproxy({5: Row(attributes=mappingproxy({'name': 'a'}), geometry=Geometry(kind=<GeometryKind.LINESTRING: 'LineStr...roxy({'name': 'd'}), geometry=Geometry(kind=<GeometryKind.POINT: 'Point'>, parts=(((0.0, 3.0),),), crs='EPSG:25833'))}))
E        +    where mappingproxy({5: Row(attributes=mappingproxy({'name': 'a'}), geometry=Geometry(kind=<GeometryKind.LINESTRING: 'LineStr...roxy({'name': 'd'}), geometry=Geometry(kind=<GeometryKind.POINT: 'Point'>, parts=(((0.0, 3.0),),), crs='EPSG:25833'))}) = Dataset(schema=Schema(fields=(Field(name='name', type=<FieldType.TEXT: 'text'>, length=5),), data_type=<DataType.FEATU...oxy({'name': 'd'}), geometry=Geometry(kind=<GeometryKind.POINT: 'Point'>, parts=(((0.0, 3.0),),), crs='EPSG:25833'))})).rows
FAILED tests/unit/adapters/fakes/memory/test_geometry_ops.py::test_explode_without_parents_writes_the_children_and_nothing_else
1 failed in 0.03s
```

### M13: the native index numbered 1..n per write instead of from one counter

File: `src/ag/adapters/fakes/memory/store.py`. Edit: `start = self._next_index` -> `start = 1`.

Targets: test_rewriting_a_dataset_assigns_fresh_indices, test_indices_are_dense_from_one_and_a_second_write_takes_the_next_range, test_explode_leaves_the_input_index_unchanged_and_the_next_write_reassigns_it. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       assert set(first.indices).isdisjoint(second.indices)
E       AssertionError: assert False
E        +  where False = <built-in method isdisjoint of set object at 0x76fd19ef7bc0>((1, 2, 3, 4))
E        +    where <built-in method isdisjoint of set object at 0x76fd19ef7bc0> = {1, 2, 3, 4}.isdisjoint
E        +      where {1, 2, 3, 4} = set((1, 2, 3, 4))
E        +        where (1, 2, 3, 4) = Seeded(handle=ScratchHandle(tests.support.memory.roads, path='memory:/roads'), indices=(1, 2, 3, 4)).indices
E        +    and   (1, 2, 3, 4) = Seeded(handle=ScratchHandle(tests.support.memory.roads, path='memory:/roads'), indices=(1, 2, 3, 4)).indices
>       assert second.indices == (5, 6)
E       assert (1, 2) == (5, 6)
E         At index 0 diff: 1 != 5
E         Use -v to get more diff
>       assert set(rewritten.indices).isdisjoint(seeded.indices)
E        +  where False = <built-in method isdisjoint of set object at 0x76fd19ef5d20>((1, 2, 3, 4))
E        +    where <built-in method isdisjoint of set object at 0x76fd19ef5d20> = {1, 2, 3, 4}.isdisjoint
```

### M14: the empty-geometry guard removed

File: `src/ag/adapters/fakes/memory/geometry_ops/shape.py`. Edit: `if nulls:` -> `if False:`.

Targets: test_explode_refuses_a_null_geometry_before_writing_whether_or_not_parents_asked. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       with pytest.raises(EmptyGeometryError) as caught:
E       Failed: DID NOT RAISE EmptyGeometryError
FAILED tests/unit/adapters/fakes/memory/test_geometry_ops.py::test_explode_refuses_a_null_geometry_before_writing_whether_or_not_parents_asked
1 failed in 0.04s
```

### M15: handles compared by name, type and namespace instead of path

File: `src/ag/adapters/fakes/memory/support/preconditions.py`. Edit: `path = os.fspath(handle)` -> `path = f"{handle.name}:{handle.data_type}:{handle.namespace}"`.

Targets: test_explode_refuses_two_handles_on_one_path. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       with pytest.raises(PortContractError, match="both name"):
E       Failed: DID NOT RAISE PortContractError
FAILED tests/unit/adapters/fakes/memory/test_geometry_ops.py::test_explode_refuses_two_handles_on_one_path
1 failed in 0.04s
```

### M16: the SHORT and LONG range check removed

File: `src/ag/adapters/_shared/field_values.py`. Edit: `if not low <= value <= high:` -> `if False:`.

Targets: test_a_row_that_does_not_fit_the_schema_is_refused[long-overflow], test_short_overflow_and_geometry_on_a_table_are_refused, test_check_refuses_what_the_adapter_cannot_evaluate[long-overflow-lt]. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       with pytest.raises(PortContractError, match=reason):
E       Failed: DID NOT RAISE PortContractError
>       with pytest.raises(PortContractError, match="outside the short range"):
FAILED tests/unit/adapters/fakes/memory/test_store.py::test_a_row_that_does_not_fit_the_schema_is_refused[long-overflow]
FAILED tests/unit/adapters/fakes/memory/test_store.py::test_short_overflow_and_geometry_on_a_table_are_refused
FAILED tests/unit/adapters/fakes/memory/test_predicate_eval.py::test_check_refuses_what_the_adapter_cannot_evaluate[long-overflow-lt]
3 failed in 0.04s
```

### M17: the TEXT length check removed

File: `src/ag/adapters/_shared/field_values.py`. Edit: `if field.length is not None and len(value) > field.length:` -> `if False:`.

Targets: test_a_row_that_does_not_fit_the_schema_is_refused[text-too-long], test_check_refuses_what_the_adapter_cannot_evaluate[text-too-long]. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       with pytest.raises(PortContractError, match=reason):
E       Failed: DID NOT RAISE PortContractError
FAILED tests/unit/adapters/fakes/memory/test_store.py::test_a_row_that_does_not_fit_the_schema_is_refused[text-too-long]
FAILED tests/unit/adapters/fakes/memory/test_predicate_eval.py::test_check_refuses_what_the_adapter_cannot_evaluate[text-too-long]
2 failed in 0.04s
```

### M18: a bool accepted as a cell value

File: `src/ag/adapters/_shared/field_values.py`. Edit: `if isinstance(value, bool):` -> `if False:`.

Targets: test_a_row_that_does_not_fit_the_schema_is_refused[bool-on-long]. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       with pytest.raises(PortContractError, match=reason):
E       Failed: DID NOT RAISE PortContractError
FAILED tests/unit/adapters/fakes/memory/test_store.py::test_a_row_that_does_not_fit_the_schema_is_refused[bool-on-long]
1 failed in 0.03s
```

### M19: rows stored by reference instead of as read-only copies

File: `src/ag/adapters/fakes/memory/store.py`. Edit: `checked = tuple(_frozen(row) for row in rows)` -> `checked = tuple(rows)`.

Targets: test_mutating_the_callers_mapping_after_a_write_leaves_the_stored_row_unchanged. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       assert dict(stored.attributes) == {"code": 1, "label": "one"}
E       AssertionError: assert {'code': True... 'extra': 'x'} == {'code': 1, 'label': 'one'}
E         Omitting 2 identical items, use -vv to show
E         Left contains 1 more item:
E         {'extra': 'x'}
E         Use -v to get more diff
FAILED tests/unit/adapters/fakes/memory/test_store.py::test_mutating_the_callers_mapping_after_a_write_leaves_the_stored_row_unchanged
1 failed in 0.03s
```

### M20: the distinct-paths check removed from select

File: `src/ag/adapters/fakes/memory/geometry_ops/selection.py`. Edit: delete `distinct_paths(handles=(input, output))`.

Targets: test_select_refuses_an_output_on_the_input_path. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       with pytest.raises(PortContractError, match="both name"):
E       Failed: DID NOT RAISE PortContractError
FAILED tests/unit/adapters/fakes/memory/test_geometry_ops.py::test_select_refuses_an_output_on_the_input_path
1 failed in 0.04s
```

### M21: a table input accepted by explode_multipart

File: `src/ag/adapters/fakes/memory/geometry_ops/shape.py`. Edit: `if dataset.schema.data_type is not DataType.FEATURE_CLASS:` -> `if False:`.

Targets: test_explode_refuses_a_table_input. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>           MemoryGeometryOps(store=store).explode_multipart(
>           raise EmptyGeometryError(
E           ag.ports.errors.EmptyGeometryError: 2 row(s) of 'memory:/lookup' have a null geometry, which has no parts; explode_multipart refuses them rather than drop them.
FAILED tests/unit/adapters/fakes/memory/test_geometry_ops.py::test_explode_refuses_a_table_input
1 failed in 0.04s
```

### M22: an unknown field accepted by read_rows

File: `src/ag/adapters/fakes/memory/table_ops/row_io.py`. Edit: `if unknown:` -> `if False:`.

Targets: test_read_rows_refuses_a_field_the_dataset_does_not_declare. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>           MemoryTableOps(store=store).read_rows(input=seeded.handle, fields=("code", "x"))
>           attributes={name: row.attributes[name] for name in fields},
E   KeyError: 'x'
FAILED tests/unit/adapters/fakes/memory/test_table_ops.py::test_read_rows_refuses_a_field_the_dataset_does_not_declare
1 failed in 0.03s
```

### M23: an unknown field accepted by the check

File: `src/ag/adapters/fakes/memory/support/predicate_eval.py`. Edit: `raise PortContractError(` -> `return Field(name, FieldType.TEXT, 100)`.

Targets: test_check_refuses_what_the_adapter_cannot_evaluate[unknown-field], test_check_refuses_what_the_adapter_cannot_evaluate[unknown-field-is-null], test_a_bad_predicate_on_an_empty_dataset_raises[unknown-field]. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       with pytest.raises(PortContractError, match=reason):
E       Failed: DID NOT RAISE PortContractError
>       with pytest.raises(PortContractError):
FAILED tests/unit/adapters/fakes/memory/test_predicate_eval.py::test_check_refuses_what_the_adapter_cannot_evaluate[unknown-field]
FAILED tests/unit/adapters/fakes/memory/test_predicate_eval.py::test_check_refuses_what_the_adapter_cannot_evaluate[unknown-field-is-null]
FAILED tests/unit/adapters/fakes/memory/test_geometry_ops.py::test_a_bad_predicate_on_an_empty_dataset_raises[unknown-field]
3 failed in 0.04s
```

### M24: a Spatial leaf passed through the check

File: `src/ag/adapters/fakes/memory/support/predicate_eval.py`. Edit: `raise PortContractError(` -> `pass`.

Targets: test_check_refuses_what_the_adapter_cannot_evaluate[spatial], test_a_bad_predicate_on_an_empty_dataset_raises[spatial]. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       with pytest.raises(PortContractError, match=reason):
E       Failed: DID NOT RAISE PortContractError
>       with pytest.raises(PortContractError):
FAILED tests/unit/adapters/fakes/memory/test_predicate_eval.py::test_check_refuses_what_the_adapter_cannot_evaluate[spatial]
FAILED tests/unit/adapters/fakes/memory/test_geometry_ops.py::test_a_bad_predicate_on_an_empty_dataset_raises[spatial]
2 failed in 0.04s
```

### M25: the field-set check on write removed

File: `src/ag/adapters/fakes/memory/store.py`. Edit: `if names != declared.keys():` -> `if False:`.

Targets: test_a_row_that_does_not_fit_the_schema_is_refused[missing-field]. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       with pytest.raises(PortContractError, match=reason):
E       Failed: DID NOT RAISE PortContractError
FAILED tests/unit/adapters/fakes/memory/test_store.py::test_a_row_that_does_not_fit_the_schema_is_refused[missing-field]
1 failed in 0.03s
```

### M26: a handle's DataType not checked against the schema

File: `src/ag/adapters/fakes/memory/store.py`. Edit: `if handle.data_type is not schema.data_type:` -> `if False:`.

Targets: test_a_table_handle_refuses_a_feature_class_schema. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       with pytest.raises(PortContractError, match="names one kind of dataset"):
E       Failed: DID NOT RAISE PortContractError
FAILED tests/unit/adapters/fakes/memory/test_store.py::test_a_table_handle_refuses_a_feature_class_schema
1 failed in 0.03s
```

### M27: a geometry accepted on a table

File: `src/ag/adapters/fakes/memory/store.py`. Edit: `if schema.data_type is not DataType.FEATURE_CLASS:` -> `if False:`.

Targets: test_short_overflow_and_geometry_on_a_table_are_refused. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       with pytest.raises(PortContractError, match="has none"):
E       AssertionError: Regex pattern did not match.
E         Expected regex: 'has none'
E         Actual message: "row 0 written to 'memory:/lookup' is in 'EPSG:25833'; the schema declares None."
FAILED tests/unit/adapters/fakes/memory/test_store.py::test_short_overflow_and_geometry_on_a_table_are_refused
1 failed in 0.03s
```

### M28: the CRS check on write removed

File: `src/ag/adapters/fakes/memory/store.py`. Edit: `if row.geometry.crs != schema.geometry_crs:` -> `if False:`.

Targets: test_a_row_that_does_not_fit_the_schema_is_refused[wrong-crs]. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       with pytest.raises(PortContractError, match=reason):
E       Failed: DID NOT RAISE PortContractError
FAILED tests/unit/adapters/fakes/memory/test_store.py::test_a_row_that_does_not_fit_the_schema_is_refused[wrong-crs]
1 failed in 0.03s
```

### M29: an aware datetime accepted

File: `src/ag/adapters/_shared/field_values.py`. Edit: `if value.tzinfo is not None:` -> `if False:`.

Targets: test_a_row_that_does_not_fit_the_schema_is_refused[aware-datetime]. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       with pytest.raises(PortContractError, match=reason):
E       Failed: DID NOT RAISE PortContractError
FAILED tests/unit/adapters/fakes/memory/test_store.py::test_a_row_that_does_not_fit_the_schema_is_refused[aware-datetime]
1 failed in 0.03s
```

### After the last restore

```
150 passed in 0.86s
```

## Manual breaks

### Root contents: a stray `helpers.py` in `src/ag/adapters/fakes/memory/`

Target: `tests/static/test_adapter_groups.py::test_rule_holds[memory-root-contents]`. The file
was created, the target run, the file deleted.

Result: **FAILED as expected** (exit 1)

```
E       AssertionError: memory: helpers.py is in the adapter root, which holds only ['__init__.py', '_base.py', 'cartographic_ops', 'geometry_ops', 'store.py', 'support', 'table_ops'].
FAILED tests/static/test_adapter_groups.py::test_rule_holds[memory-root-contents]
1 failed in 0.05s
```

### Static matrix: `where` renamed to `predicate` in `Selection.select`

Checked by pyright, not pytest: `pyright src/ag/adapters/fakes/memory/geometry_ops/__init__.py
tests/static/test_adapter_groups.py` on the mutated file, then the original bytes restored.

Result: **FAILED as expected** (exit 1)

```
src/ag/adapters/fakes/memory/geometry_ops/__init__.py:25:33 - error: Type "MemoryGeometryOps" is not assignable to declared type "GeometryOps"
tests/static/test_adapter_groups.py:44:37 - error: Type "MemoryGeometryOps" is not assignable to declared type "GeometryOps"
2 errors, 0 warnings, 0 informations
```

After the restore, `pyright src/ag/adapters tests/static`: `0 errors, 0 warnings, 0 informations`.
