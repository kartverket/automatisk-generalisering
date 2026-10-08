# Slice 1a evidence: the port values

**Status:** EVIDENCE, 2026-10-08 (first run 2026-10-07). Produced for the second pull request of
slice 1a (the port values: `ports/geometry.py`, `ports/attributes.py`, `ports/table_ops.py`,
`ports/predicates.py`, `ports/toolbox.py`, `ports/errors.py`, `core/warnings.py` and their tests).
Part 1 is the output of `python -m tools.break_once ports`, whose case table is
`tools/break_once/cases/ports.py` (A30): every guard broken once, with the covering tests failing,
then restored; file hashes before and after the run were identical and the set's suite was green
after the last restore. Part 2 breaks the extended row-5 import contract (the layers inside
`ag.ports`) once per direction with throwaway probe imports, on the slice 0 precedent.

## Part 1: every guard broken once

Case set `ports`, run by `python -m tools.break_once ports`. Per case: its targets pass on the clean tree (baseline), one source file is edited to remove the guard, the same targets must then fail, and the file is restored. The set's suite runs after the last restore.

### P1: TEXT field accepted without a length

File: `src/ag/ports/attributes.py`. Edit: `if self.type is FieldType.TEXT and self.length is None:` -> `if False:`.

Targets: test_a_text_field_needs_a_length_and_no_other_type_takes_one. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       with pytest.raises(ValueError, match="needs a length"):
E       Failed: DID NOT RAISE ValueError
FAILED tests/unit/ports/test_table_values.py::test_a_text_field_needs_a_length_and_no_other_type_takes_one
1 failed in 0.03s
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
1 failed in 0.02s
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
1 failed in 0.03s
```

### P9: DWITHIN accepted without a distance

File: `src/ag/ports/predicates.py`. Edit: `if needs_distance and self.distance_m is None:` -> `if False:`.

Targets: test_dwithin_carries_its_distance_and_the_others_refuse_one. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       with pytest.raises(ValueError, match="requires distance_m"):
E       Failed: DID NOT RAISE ValueError
FAILED tests/unit/ports/test_predicates.py::test_dwithin_carries_its_distance_and_the_others_refuse_one
1 failed in 0.03s
```

### P10: a distance accepted on a non-distance relation

File: `src/ag/ports/predicates.py`. Edit: `if not needs_distance and self.distance_m is not None:` -> `if False:`.

Targets: test_dwithin_carries_its_distance_and_the_others_refuse_one. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       with pytest.raises(ValueError, match="takes no distance_m"):
E       Failed: DID NOT RAISE ValueError
FAILED tests/unit/ports/test_predicates.py::test_dwithin_carries_its_distance_and_the_others_refuse_one
1 failed in 0.03s
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
1 failed in 0.03s
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
E       assert ['ports/predicates.py:272'] == []
E         Left contains one more item: 'ports/predicates.py:272'
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
1 failed in 0.03s
```

### P18: a table schema accepted with a CRS

File: `src/ag/ports/table_ops.py`. Edit: `if (` -> `if False:`.

Targets: test_a_feature_class_schema_needs_a_crs_and_a_table_does_not. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       with pytest.raises(ValueError, match="takes no geometry_crs"):
E       Failed: DID NOT RAISE ValueError
FAILED tests/unit/ports/test_table_values.py::test_a_feature_class_schema_needs_a_crs_and_a_table_does_not
1 failed in 0.03s
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

### After the last restore

```
52 passed in 0.07s
```

## Part 2: the layers inside ag.ports, broken once per direction

Each probe appends one import to a module in `src/ag/ports`, runs `lint-imports`, and restores the file. The contract is row 5 of `.importlinter`: `toolbox` above `cartographic_ops` above the three independent Protocols above `predicates` above `geometry | attributes | errors`.

**attributes imports predicates (bottom imports the layer above)** (`src/ag/ports/attributes.py` + `import ag.ports.predicates  # probe`): BROKEN as expected

```
Contracts: 23 kept, 1 broken.
ag.ports.attributes is not allowed to import ag.ports.predicates:
- ag.ports.attributes -> ag.ports.predicates (l.64)
```

**predicates imports table_ops (algebra imports a Protocol module)** (`src/ag/ports/predicates.py` + `import ag.ports.table_ops  # probe`): BROKEN as expected

```
Contracts: 23 kept, 1 broken.
ag.ports.predicates is not allowed to import ag.ports.table_ops:
- ag.ports.predicates -> ag.ports.table_ops (l.271)
```

**geometry imports toolbox (bottom imports the top)** (`src/ag/ports/geometry.py` + `import ag.ports.toolbox  # probe`): BROKEN as expected

```
Contracts: 23 kept, 1 broken.
ag.ports.geometry is not allowed to import ag.ports.toolbox:
- ag.ports.geometry -> ag.ports.toolbox (l.108)
```

**geometry_ops imports table_ops (sibling Protocols)** (`src/ag/ports/geometry_ops.py` + `import ag.ports.table_ops  # probe`): BROKEN as expected

```
Contracts: 23 kept, 1 broken.
ag.ports.geometry_ops is not allowed to import ag.ports.table_ops:
- ag.ports.geometry_ops -> ag.ports.table_ops (l.21)
```

**cartographic_ops imports toolbox (Protocol imports the bundle)** (`src/ag/ports/cartographic_ops.py` + `import ag.ports.toolbox  # probe`): BROKEN as expected

```
Contracts: 23 kept, 1 broken.
ag.ports.cartographic_ops is not allowed to import ag.ports.toolbox:
- ag.ports.cartographic_ops -> ag.ports.toolbox (l.20)
```

**allowed: table_ops imports attributes and geometry; toolbox imports the four Protocols**: `Contracts: 24 kept, 0 broken.` (the current imports, unchanged)

