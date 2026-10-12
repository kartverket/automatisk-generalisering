# Slice 1a evidence: the port values

**Status:** EVIDENCE, 2026-10-12 (first run 2026-10-07, rerun after each review round). Produced
for the second pull request of slice 1a (the port values: `ports/geometry.py`,
`ports/attributes.py`, `ports/table_ops.py`, `ports/predicates.py`, `ports/toolbox.py`,
`ports/errors.py`, `core/warnings.py`, their tests, and row 5 of `.importlinter` extended to the
layers inside `ag.ports`) by `python -m tools.break_once ports`, whose case table is
`tools/break_once/cases/ports.py` (A30). Every guard broken once, with the covering tests failing,
then restored; file hashes before and after the run were identical and the set's suite was green
after the last restore. The import contract is broken through
`tests/static/test_import_contracts.py`, which runs import-linter in-process with its cache off and
gives each contract one test, so cases P23 and P24 append a probe import and expect the row-5
test to fail; the first version of this file broke the contract with throwaway probes, which this
rerun replaces.

Case set `ports`, run by `python -m tools.break_once ports`. Per case: its targets pass on the clean tree (baseline), one source file is edited to remove the guard, the same targets must then fail, and the file is restored. The set's suite runs after the last restore.

### P1: TEXT field accepted without a length

File: `src/ag/ports/attributes.py`. Edit: `if self.type is FieldType.TEXT and self.length is None:` -> `if False:`.

Targets: test_a_text_field_needs_a_length_and_no_other_type_takes_one. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       with pytest.raises(ValueError, match="needs a length"):
E       Failed: DID NOT RAISE ValueError
FAILED tests/unit/ports/test_table_values.py::test_a_text_field_needs_a_length_and_no_other_type_takes_one
1 failed in 0.02s
```

### P2: non-TEXT field accepted with a length

File: `src/ag/ports/attributes.py`. Edit: `if self.type is not FieldType.TEXT and self.length is not None:` -> `if False:`.

Targets: test_a_text_field_needs_a_length_and_no_other_type_takes_one. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       with pytest.raises(ValueError, match="takes no length"):
E       Failed: DID NOT RAISE ValueError
FAILED tests/unit/ports/test_table_values.py::test_a_text_field_needs_a_length_and_no_other_type_takes_one
1 failed in 0.02s
```

### P3: feature class schema accepted without a CRS

File: `src/ag/ports/table_ops.py`. Edit: `if self.data_type is DataType.FEATURE_CLASS and self.geometry_crs is None:` -> `if False:`.

Targets: test_a_feature_class_schema_needs_a_crs_and_a_table_does_not. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       with pytest.raises(ValueError, match="needs geometry_crs"):
E       Failed: DID NOT RAISE ValueError
FAILED tests/unit/ports/test_table_values.py::test_a_feature_class_schema_needs_a_crs_and_a_table_does_not
1 failed in 0.02s
```

### P4: Row without slots

File: `src/ag/ports/table_ops.py`. Edit: `@dataclass(frozen=True, slots=True)` -> `@dataclass(frozen=True)`.

Targets: test_a_row_is_frozen_and_uses_slots. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       assert not hasattr(row, "__dict__")
E       AssertionError: assert not True
E        +  where True = hasattr(Row(attributes={'count': 3}, geometry=None), '__dict__')
FAILED tests/unit/ports/test_table_values.py::test_a_row_is_frozen_and_uses_slots
1 failed in 0.02s
```

### P5: empty geometry accepted

File: `src/ag/ports/geometry.py`. Edit: `if not self.parts:` -> `if False:`.

Targets: test_an_empty_geometry_is_refused. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       with pytest.raises(ValueError, match="null geometry"):
E       Failed: DID NOT RAISE ValueError
FAILED tests/unit/ports/test_geometry.py::test_an_empty_geometry_is_refused
1 failed in 0.02s
```

### P6: multi-coordinate point accepted

File: `src/ag/ports/geometry.py`. Edit: `if self.kind is GeometryKind.POINT and (` -> `if False and (`.

Targets: test_a_point_is_exactly_one_coordinate. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       with pytest.raises(ValueError, match="POINT must be exactly one part"):
E       Failed: DID NOT RAISE ValueError
FAILED tests/unit/ports/test_geometry.py::test_a_point_is_exactly_one_coordinate
1 failed in 0.03s
```

### P7: comparison with NULL accepted

File: `src/ag/ports/predicates.py`. Edit: `if self.value is None:` -> `if False:`.

Targets: test_cmp_refuses_a_null_value. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       with pytest.raises(ValueError, match="Attr.is_null"):
E       Failed: DID NOT RAISE ValueError
FAILED tests/unit/ports/test_predicates.py::test_cmp_refuses_a_null_value - F...
1 failed in 0.02s
```

### P8: NULL member of an IN set accepted

File: `src/ag/ports/predicates.py`. Edit: `if any(value is None for value in self.values):` -> `if False:`.

Targets: test_in_refuses_a_null_member. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       with pytest.raises(ValueError, match="NULL is never IN a set"):
E       Failed: DID NOT RAISE ValueError
FAILED tests/unit/ports/test_predicates.py::test_in_refuses_a_null_member - F...
1 failed in 0.02s
```

### P9: DWITHIN accepted without a distance

File: `src/ag/ports/predicates.py`. Edit: `if needs_distance and self.distance_m is None:` -> `if False:`.

Targets: test_dwithin_carries_its_distance_and_the_others_refuse_one. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       with pytest.raises(ValueError, match="requires distance_m"):
E       Failed: DID NOT RAISE ValueError
FAILED tests/unit/ports/test_predicates.py::test_dwithin_carries_its_distance_and_the_others_refuse_one
1 failed in 0.02s
```

### P10: a distance accepted on a non-distance relation

File: `src/ag/ports/predicates.py`. Edit: `if not needs_distance and self.distance_m is not None:` -> `if False:`.

Targets: test_dwithin_carries_its_distance_and_the_others_refuse_one. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       with pytest.raises(ValueError, match="takes no distance_m"):
E       Failed: DID NOT RAISE ValueError
FAILED tests/unit/ports/test_predicates.py::test_dwithin_carries_its_distance_and_the_others_refuse_one
1 failed in 0.02s
```

### P11: the invert operator simplifies a double negation

File: `src/ag/ports/predicates.py`. Edit: `return Not(self)` -> `return self.term if isinstance(self, Not) else Not(self)`.

Targets: test_the_operators_build_a_tree_and_fold_nothing. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       assert ~~EUROPEAN_ROAD == Not(Not(EUROPEAN_ROAD))
E       AssertionError: assert ~~Compare(field='vegkategori', op=<Comparison.EQ: '='>, value='E') == Not(term=Not(term=Compare(field='vegkategori', op=<Comparison.EQ: '='>, value='E')))
E        +  where Not(term=Not(term=Compare(field='vegkategori', op=<Comparison.EQ: '='>, value='E'))) = Not(Not(term=Compare(field='vegkategori', op=<Comparison.EQ: '='>, value='E')))
E        +    where Not(term=Compare(field='vegkategori', op=<Comparison.EQ: '='>, value='E')) = Not(Compare(field='vegkategori', op=<Comparison.EQ: '='>, value='E'))
FAILED tests/unit/ports/test_predicates.py::test_the_operators_build_a_tree_and_fold_nothing
1 failed in 0.02s
```

### P12: the sentinel reaches a port silently

File: `src/ag/ports/toolbox.py`. Edit: `raise InjectionError(` -> `return None`.

Targets: test_the_sentinel_is_a_toolbox_that_refuses_every_port. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>           with pytest.raises(InjectionError, match=f"tb.{port} was reached"):
E           Failed: DID NOT RAISE InjectionError
FAILED tests/unit/ports/test_toolbox.py::test_the_sentinel_is_a_toolbox_that_refuses_every_port
1 failed in 0.03s
```

### P13: an Attr.raw call site added without touching the pin

File: `src/ag/ports/predicates.py`. Edit: append '_UNPINNED = Attr.raw("1=1")' ....

Targets: test_attr_raw_call_sites_are_pinned. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       assert raw_call_sites() == PINNED_CALL_SITES, (
E       AssertionError: an Attr.raw call site appeared or moved; each one is a deliberate edit to PINNED_CALL_SITES, with its reason in the review
E       assert ['ports/predicates.py:286'] == []
E         Left contains one more item: 'ports/predicates.py:286'
E         Use -v to get more diff
FAILED tests/static/test_attr_raw_count.py::test_attr_raw_call_sites_are_pinned
1 failed in 0.02s
```

### P14: a predicate has a truth value

File: `src/ag/ports/predicates.py`. Edit: `raise TypeError(` -> `return True`.

Targets: test_a_predicate_has_no_truth_value. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       with pytest.raises(TypeError, match="no truth value"):
E       Failed: DID NOT RAISE TypeError
FAILED tests/unit/ports/test_predicates.py::test_a_predicate_has_no_truth_value
1 failed in 0.03s
```

### P15: a connective with fewer than two terms accepted

File: `src/ag/ports/predicates.py`. Edit: `if len(terms) < 2:` -> `if False:`.

Targets: test_a_connective_needs_at_least_two_terms. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>           with pytest.raises(ValueError, match="at least two terms"):
E           Failed: DID NOT RAISE ValueError
FAILED tests/unit/ports/test_predicates.py::test_a_connective_needs_at_least_two_terms
1 failed in 0.03s
```

### P16: LIKE accepted with a non-string value

File: `src/ag/ports/predicates.py`. Edit: `if self.op is Comparison.LIKE and not isinstance(self.value, str):` -> `if False:`.

Targets: test_like_takes_a_string_pattern. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       with pytest.raises(ValueError, match="LIKE takes a string pattern"):
E       Failed: DID NOT RAISE ValueError
FAILED tests/unit/ports/test_predicates.py::test_like_takes_a_string_pattern
1 failed in 0.02s
```

### P17: DWITHIN accepted with a zero or negative distance

File: `src/ag/ports/predicates.py`. Edit: `if needs_distance and self.distance_m is not None and self.distance_m <= 0:` -> `if False:`.

Targets: test_dwithin_requires_a_positive_distance. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>           with pytest.raises(ValueError, match="positive distance_m"):
E           Failed: DID NOT RAISE ValueError
FAILED tests/unit/ports/test_predicates.py::test_dwithin_requires_a_positive_distance
1 failed in 0.02s
```

### P18: a table schema accepted with a CRS

File: `src/ag/ports/table_ops.py`. Edit: `if (` -> `if False:`.

Targets: test_a_feature_class_schema_needs_a_crs_and_a_table_does_not. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       with pytest.raises(ValueError, match="takes no geometry_crs"):
E       Failed: DID NOT RAISE ValueError
FAILED tests/unit/ports/test_table_values.py::test_a_feature_class_schema_needs_a_crs_and_a_table_does_not
1 failed in 0.02s
```

### P19: the sentinel with the dataclass equality

File: `src/ag/ports/toolbox.py`. Edit: delete `def __eq__(self, other: object) -> bool:`.

Targets: test_the_sentinel_compares_by_identity_and_survives_pickling. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       assert second_instance != NOT_INJECTED
>       raise InjectionError(
E       ag.core.errors.InjectionError: tb.geometry was reached on a toolbox that was never injected. The stage entry point must pass its assembled Toolbox to any operation whose signature declares `tb: Toolbox = NOT_INJECTED`.
FAILED tests/unit/ports/test_toolbox.py::test_the_sentinel_compares_by_identity_and_survives_pickling
1 failed in 0.03s
```

### P20: a bool accepted as an attribute value

File: `src/ag/ports/predicates.py`. Edit: `if isinstance(value, bool):` -> `if False:`.

Targets: test_a_bool_is_refused_because_no_field_type_holds_one. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       with pytest.raises(ValueError, match="no field type holds one"):
E       Failed: DID NOT RAISE ValueError
FAILED tests/unit/ports/test_predicates.py::test_a_bool_is_refused_because_no_field_type_holds_one
1 failed in 0.03s
```

### P21: the sentinel pickles as a new instance

File: `src/ag/ports/toolbox.py`. Edit: delete `def __reduce__(self) -> str:`.

Targets: test_the_sentinel_compares_by_identity_and_survives_pickling. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       assert pickle.loads(pickle.dumps(NOT_INJECTED)) is NOT_INJECTED
E       AssertionError: assert NOT_INJECTED is NOT_INJECTED
E        +  where NOT_INJECTED = <built-in function loads>(b'\x80\x04\x95(\x00\x00\x00\x00\x00\x00\x00\x8c\x10ag.ports.toolbox\x94\x8c\x0c_NotInjected\x94\x93\x94)\x81\x94.')
E        +    where <built-in function loads> = pickle.loads
E        +    and   b'\x80\x04\x95(\x00\x00\x00\x00\x00\x00\x00\x8c\x10ag.ports.toolbox\x94\x8c\x0c_NotInjected\x94\x93\x94)\x81\x94.' = <built-in function dumps>(NOT_INJECTED)
E        +      where <built-in function dumps> = pickle.dumps
FAILED tests/unit/ports/test_toolbox.py::test_the_sentinel_compares_by_identity_and_survives_pickling
1 failed in 0.03s
```

### P22: a dunder lookup on the sentinel raises InjectionError

File: `src/ag/ports/toolbox.py`. Edit: `if name.startswith("__") and name.endswith("__"):` -> `if False:`.

Targets: test_the_sentinel_compares_by_identity_and_survives_pickling. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       assert copy.deepcopy(NOT_INJECTED) is NOT_INJECTED
>       raise InjectionError(
E       ag.core.errors.InjectionError: tb.__deepcopy__ was reached on a toolbox that was never injected. The stage entry point must pass its assembled Toolbox to any operation whose signature declares `tb: Toolbox = NOT_INJECTED`.
FAILED tests/unit/ports/test_toolbox.py::test_the_sentinel_compares_by_identity_and_survives_pickling
1 failed in 0.03s
```

### P23: row 5: a bottom module imports the layer above (attributes imports predicates)

File: `src/ag/ports/attributes.py`. Edit: append 'import ag.ports.predicates  # probe' ....

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

### P24: row 5: two Protocol modules import each other (geometry_ops imports table_ops)

File: `src/ag/ports/geometry_ops.py`. Edit: append 'import ag.ports.table_ops  # probe' ....

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
78 passed in 0.15s
```
