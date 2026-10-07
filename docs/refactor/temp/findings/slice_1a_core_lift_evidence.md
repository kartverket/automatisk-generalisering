# Slice 1a evidence: the core lift

**Status:** EVIDENCE, 2026-10-05. Produced for the first pull request of slice 1a (the core lift:
`core/types.py`, `core/injection.py`, `core/handles.py`, `core/operations.py`, `core/errors.py` and
their unit tests). Part 1 was produced by a throwaway probe against the template, on the slice 0
precedent (`slice_0_contract_evidence.md`); part 2 is the output of `python -m tools.break_once
core`, whose case table is `tools/break_once/cases/core.py`, so it can be rerun; part 3 shows the
harness itself catching a stale needle, a renamed test, a stale module path, a target that fails
in isolation, and a relaxed verdict (A30). File hashes before and after every run were identical
and the full suite was green after the last restore.

## Part 1: the template defects, run against `template_code/ag/core/operations.py`

Two tests adapted to the template's API (no scope namespace, a materialiser returning a handle),
run with the template first on `PYTHONPATH`. The first defect: `__set_name__` restamps a handle
bound in two class bodies (template lines 158 to 171). The second: an internal handle is built
with an empty namespace, so two operations' `scratch("dissolved")` are equal (template lines 288
to 292 with `staging/scratch.py:171`).

```
______________ test_a_handle_bound_in_two_class_bodies_is_refused ______________
    def test_a_handle_bound_in_two_class_bodies_is_refused() -> None:
        shared = handle()
        class First:
            h = shared
>       with pytest.raises(TypeError):
             ^^^^^^^^^^^^^^^^^^^^^^^^
E       Failed: DID NOT RAISE TypeError
_________ test_internal_handles_of_two_operations_are_different_values _________
    def test_internal_handles_of_two_operations_are_different_values() -> None:
        first = ScratchScope(trail=(), materialize=_materialize)("dissolved")
        second = ScratchScope(trail=(), materialize=_materialize)("dissolved")
>       assert first != second
E       AssertionError: assert ScratchHandle('dissolved', UNDECLARED) != ScratchHandle('dissolved', UNDECLARED)
2 failed in 0.01s
```

## Part 2: every guard broken once

Case set `core`, run by `python -m tools.break_once core`. Per case: its targets pass on the clean tree (baseline), one source file is edited to remove the guard, the same targets must then fail, and the file is restored. The set's suite runs after the last restore.

### O1: bare Injected base accepted

File: `src/ag/core/operations.py`. Edit: `if hint is Injected:` -> `if False:`.

Targets: test_the_bare_injected_base_is_rejected. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       with pytest.raises(TypeError, match="bare Injected base"):
E       Failed: DID NOT RAISE TypeError
FAILED tests/unit/core/test_operation_classification.py::test_the_bare_injected_base_is_rejected
1 failed in 0.02s
```

### O2: injected default not required / not checked against its kind

File: `src/ag/core/operations.py`. Edit: `if not isinstance(parameter.default, kind):` -> `if False:`.

Targets: test_an_injected_parameter_without_a_default_is_rejected, test_an_injected_default_of_the_wrong_kind_is_rejected. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       with pytest.raises(TypeError, match="needs that kind's sentinel"):
E       Failed: DID NOT RAISE TypeError
FAILED tests/unit/core/test_operation_classification.py::test_an_injected_parameter_without_a_default_is_rejected
FAILED tests/unit/core/test_operation_classification.py::test_an_injected_default_of_the_wrong_kind_is_rejected
2 failed in 0.03s
```

### O3: default on an In/Out handle accepted

File: `src/ag/core/operations.py`. Edit: `if parameter.default is not _EMPTY:` -> `if False:`.

Targets: test_a_defaulted_handle_is_rejected. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       with pytest.raises(TypeError, match="has a default"):
E       Failed: DID NOT RAISE TypeError
FAILED tests/unit/core/test_operation_classification.py::test_a_defaulted_handle_is_rejected
1 failed in 0.02s
```

### O4: default on config accepted

File: `src/ag/core/operations.py`. Edit: `if parameter.default is not _EMPTY:` -> `if False:`.

Targets: test_a_defaulted_config_is_rejected. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       with pytest.raises(TypeError, match="config has a default"):
E       Failed: DID NOT RAISE TypeError
FAILED tests/unit/core/test_operation_classification.py::test_a_defaulted_config_is_rejected
1 failed in 0.02s
```

### O5: config annotation not checked to be a frozen dataclass type

File: `src/ag/core/operations.py`. Edit: `if not _is_frozen_dataclass_type(hint):` -> `if False:`.

Targets: test_a_mutable_config_type_is_rejected, test_a_config_that_is_not_a_dataclass_type_is_rejected. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       with pytest.raises(TypeError, match="not a frozen dataclass type"):
E       Failed: DID NOT RAISE TypeError
FAILED tests/unit/core/test_operation_classification.py::test_a_mutable_config_type_is_rejected
FAILED tests/unit/core/test_operation_classification.py::test_a_config_that_is_not_a_dataclass_type_is_rejected
2 failed in 0.02s
```

### O6: config hashability not checked at the declaration site

File: `src/ag/core/operations.py`. Edit: `hash(value)` -> `pass`.

Targets: test_a_frozen_config_with_a_list_field_is_rejected_as_unhashable. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       with pytest.raises(TypeError, match="hashable"):
E       Failed: DID NOT RAISE TypeError
FAILED tests/unit/core/test_operation_classification.py::test_a_frozen_config_with_a_list_field_is_rejected_as_unhashable
1 failed in 0.02s
```

### O7: positional parameter accepted

File: `src/ag/core/operations.py`. Edit: `if parameter.kind is not inspect.Parameter.KEYWORD_ONLY:` -> `if False:`.

Targets: test_a_positional_parameter_is_rejected. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       with pytest.raises(TypeError, match="keyword-only"):
E       Failed: DID NOT RAISE TypeError
FAILED tests/unit/core/test_operation_classification.py::test_a_positional_parameter_is_rejected
1 failed in 0.02s
```

### O8: unannotated parameter not reported as such

File: `src/ag/core/operations.py`. Edit: `if hint is None:` -> `if False:`.

Targets: test_an_unannotated_parameter_is_rejected. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       with pytest.raises(TypeError, match="no annotation"):
E       AssertionError: Regex pattern did not match.
E         Expected regex: 'no annotation'
E         Actual message: "unannotated: parameter 'whatever' is annotated None, which is not a recognised kind. An operation takes In and Out handles, one frozen config dataclass, and whatever the runtime injects. Tuning values go in the config rather than as loose parameters, so a run manifest can record what tuning produced an output without special-casing each operation."
FAILED tests/unit/core/test_operation_classification.py::test_an_unannotated_parameter_is_rejected
1 failed in 0.02s
```

### O9: port-only markers accepted on an operation

File: `src/ag/core/operations.py`. Edit: `elif direction in _PORT_ONLY:` -> `elif False:`.

Targets: test_the_mutates_marker_is_rejected_on_an_operation, test_the_parents_out_marker_is_rejected_on_an_operation. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       with pytest.raises(TypeError, match="port-only marker Mutates"):
E       Failed: DID NOT RAISE TypeError
>       with pytest.raises(TypeError, match="port-only marker ParentsOut"):
FAILED tests/unit/core/test_operation_classification.py::test_the_mutates_marker_is_rejected_on_an_operation
FAILED tests/unit/core/test_operation_classification.py::test_the_parents_out_marker_is_rejected_on_an_operation
2 failed in 0.02s
```

### O10: two parameters of one injected kind accepted

File: `src/ag/core/operations.py`. Edit: `if kind in injected:` -> `if False:`.

Targets: test_two_parameters_of_one_injected_kind_are_rejected. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       with pytest.raises(TypeError, match="both Ports"):
E       Failed: DID NOT RAISE TypeError
FAILED tests/unit/core/test_operation_classification.py::test_two_parameters_of_one_injected_kind_are_rejected
1 failed in 0.02s
```

### O11: unrecognised kind silently skipped

File: `src/ag/core/operations.py`. Edit: `else:` -> `else:`.

Targets: test_a_loose_tuning_parameter_is_rejected, test_a_generic_alias_is_rejected_without_crashing_the_classifier, test_a_type_statement_alias_is_never_silently_misclassified. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       with pytest.raises(TypeError, match="not a recognised kind"):
E       Failed: DID NOT RAISE TypeError
FAILED tests/unit/core/test_operation_classification.py::test_a_loose_tuning_parameter_is_rejected
FAILED tests/unit/core/test_operation_classification.py::test_a_generic_alias_is_rejected_without_crashing_the_classifier
FAILED tests/unit/core/test_operation_classification.py::test_a_type_statement_alias_is_never_silently_misclassified
3 failed in 0.03s
```

### O12: injected argument passed by hand accepted

File: `src/ag/core/operations.py`. Edit: `if param in bound.arguments:` -> `if False:`.

Targets: test_an_injected_argument_may_not_be_passed_at_a_declaration_site. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
______ test_an_injected_argument_may_not_be_passed_at_a_declaration_site _______
    def test_an_injected_argument_may_not_be_passed_at_a_declaration_site() -> None:
>       with pytest.raises(TypeError, match="declaration site"):
E       Failed: DID NOT RAISE TypeError
FAILED tests/unit/core/test_operation_classification.py::test_an_injected_argument_may_not_be_passed_at_a_declaration_site
1 failed in 0.02s
```

### O13: undeclared handle accepted

File: `src/ag/core/operations.py`. Edit: `if not value.namespace:` -> `if False:`.

Targets: test_an_undeclared_handle_is_rejected. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       with pytest.raises(TypeError, match="undeclared handle"):
E       Failed: DID NOT RAISE TypeError
FAILED tests/unit/core/test_operation_classification.py::test_an_undeclared_handle_is_rejected
1 failed in 0.02s
```

### O14: config of another type accepted

File: `src/ag/core/operations.py`. Edit: `if not isinstance(value, config_type):` -> `if False:`.

Targets: test_a_config_of_another_type_is_rejected. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       with pytest.raises(TypeError, match="instance of ExampleConfig"):
E       Failed: DID NOT RAISE TypeError
FAILED tests/unit/core/test_operation_classification.py::test_a_config_of_another_type_is_rejected
1 failed in 0.02s
```

### O15: union containing an injected kind not reported as such

File: `src/ag/core/operations.py`. Edit: `elif union_kind is not None:` -> `elif False:`.

Targets: test_a_union_containing_an_injected_kind_is_rejected. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       with pytest.raises(TypeError, match="union containing the injected kind Ports"):
E       AssertionError: Regex pattern did not match.
E         Expected regex: 'union containing the injected kind Ports'
E         Actual message: "optional: parameter 'tb' is annotated tests.unit.core.test_operation_classification.Ports | None, which is not a recognised kind. An operation takes In and Out handles, one frozen config dataclass, and whatever the runtime injects. Tuning values go in the config rather than as loose parameters, so a run manifest can record what tuning produced an output without special-casing each operation."
FAILED tests/unit/core/test_operation_classification.py::test_a_union_containing_an_injected_kind_is_rejected
1 failed in 0.02s
```

### O16: get_type_hints without include_extras

File: `src/ag/core/operations.py`. Edit: `get_type_hints(fn, include_extras=True)` -> `get_type_hints(fn)`.

Targets: tests/unit/core/test_operation_classification.py. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
E   TypeError: worked: parameter 'roads' is annotated <class 'ag.core.handles.ScratchHandle'>, which is not a recognised kind. An operation takes In and Out handles, one frozen config dataclass, and whatever the runtime injects. Tuning values go in the config rather than as loose parameters, so a run manifest can record what tuning produced an output without special-casing each operation.
ERROR tests/unit/core/test_operation_classification.py - TypeError: worked: p...
```

### O17: call mappings not wrapped read-only

File: `src/ag/core/operations.py`. Edit: `inputs=MappingProxyType(inputs),` -> `inputs=inputs,`.

Targets: test_the_mappings_are_read_only_views. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>           assert isinstance(mapping, MappingProxyType)
E           AssertionError: assert False
E            +  where False = isinstance({'roads': ScratchHandle(tests.unit.core.test_operation_classification.Example.roads)}, MappingProxyType)
FAILED tests/unit/core/test_operation_classification.py::test_the_mappings_are_read_only_views
1 failed in 0.02s
```

### O18: OperationCall with value equality

File: `src/ag/core/operations.py`. Edit: `@dataclass(frozen=True, eq=False)` -> `@dataclass(frozen=True)`.

Targets: test_two_identical_declarations_are_two_calls. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       assert first != second
E       AssertionError: assert OperationCall(operation='worked', qualified_name='tests.unit.core.test_operation_classification.worked', fn=<function ...lass 'tests.unit.core.test_operation_classification.Ports'>: 'tb', <class 'ag.core.handles.ScratchScope'>: 'scratch'})) != OperationCall(operation='worked', qualified_name='tests.unit.core.test_operation_classification.worked', fn=<function ...lass 'tests.unit.core.test_operation_classification.Ports'>: 'tb', <class 'ag.core.handles.ScratchScope'>: 'scratch'}))
FAILED tests/unit/core/test_operation_classification.py::test_two_identical_declarations_are_two_calls
1 failed in 0.02s
```

### O19: frozen dataclass type accepted without eq

File: `src/ag/core/operations.py`. Edit: `return frozen and eq` -> `return frozen`.

Targets: test_a_frozen_config_type_without_equality_is_rejected. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       with pytest.raises(TypeError, match="not a frozen dataclass type with equality"):
E       Failed: DID NOT RAISE TypeError
FAILED tests/unit/core/test_operation_classification.py::test_a_frozen_config_type_without_equality_is_rejected
1 failed in 0.02s
```

### H1: __set_name__ restamps silently

File: `src/ag/core/handles.py`. Edit: `if self.name or self.namespace:` -> `if False:`.

Targets: test_a_handle_bound_in_two_class_bodies_is_refused, test_a_prenamed_handle_is_refused_as_a_class_attribute. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       with pytest.raises(TypeError, match="already named"):
E       Failed: DID NOT RAISE TypeError
FAILED tests/unit/core/test_handles.py::test_a_handle_bound_in_two_class_bodies_is_refused
FAILED tests/unit/core/test_handles.py::test_a_prenamed_handle_is_refused_as_a_class_attribute
2 failed in 0.03s
```

### H2: internal handle not stamped with the scope namespace

File: `src/ag/core/handles.py`. Edit: `namespace=self.namespace,` -> `namespace="",`.

Targets: test_internal_handles_of_two_operations_are_different_values. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       assert first != second
E       AssertionError: assert ScratchHandle('dissolved', UNDECLARED, path='/scratch/dissolved') != ScratchHandle('dissolved', UNDECLARED, path='/scratch/dissolved')
FAILED tests/unit/core/test_handles.py::test_internal_handles_of_two_operations_are_different_values
1 failed in 0.03s
```

### H3: internal handle named by leaf only, not trail

File: `src/ag/core/handles.py`. Edit: `name=TRAIL_SEPARATOR.join((*self.trail, name)),` -> `name=name,`.

Targets: test_the_same_leaf_at_three_points_of_one_trail_is_three_handles. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       assert at_root != in_first_child
E       AssertionError: assert ScratchHandle(op.x, path='/scratch/x') != ScratchHandle(op.x, path='/scratch/h__x')
FAILED tests/unit/core/test_handles.py::test_the_same_leaf_at_three_points_of_one_trail_is_three_handles
1 failed in 0.02s
```

### H4: child segments not deduplicated

File: `src/ag/core/handles.py`. Edit: `while segment in self._issued:` -> `while False:`.

Targets: test_repeated_child_labels_take_the_first_unused_index, test_a_tagged_label_and_a_label_spelled_like_it_are_two_segments. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       assert segments == ["a", "a_2", "a_2_2"]
E       AssertionError: assert ['a', 'a', 'a_2'] == ['a', 'a_2', 'a_2_2']
E         At index 1 diff: 'a' != 'a_2'
E         Use -v to get more diff
>       assert spelled == "a_b_2"
E       AssertionError: assert 'a_b' == 'a_b_2'
E         - a_b_2
E         ?    --
E         + a_b
FAILED tests/unit/core/test_handles.py::test_repeated_child_labels_take_the_first_unused_index
FAILED tests/unit/core/test_handles.py::test_a_tagged_label_and_a_label_spelled_like_it_are_two_segments
2 failed in 0.02s
```

### H5: label, tag and leaf not validated

File: `src/ag/core/handles.py`. Edit: `if _SEGMENT.fullmatch(text) is None:` -> `if False:`.

Targets: test_a_label_or_tag_that_cannot_be_a_layer_name_part_is_refused, test_a_leaf_that_cannot_be_a_layer_name_part_is_refused. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>           with pytest.raises(ValueError, match="letters, digits and single underscores"):
E           Failed: DID NOT RAISE ValueError
>           with pytest.raises(ValueError, match="scope leaf"):
FAILED tests/unit/core/test_handles.py::test_a_label_or_tag_that_cannot_be_a_layer_name_part_is_refused
FAILED tests/unit/core/test_handles.py::test_a_leaf_that_cannot_be_a_layer_name_part_is_refused
2 failed in 0.02s
```

### H6: child() on the unbound sentinel allowed

File: `src/ag/core/handles.py`. Edit: `if self.materialize is _unbound:` -> `if False:`.

Targets: test_the_injected_sentinel_refuses_a_child_before_any_bookkeeping. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       with pytest.raises(InjectionError, match="never bound"):
E       Failed: DID NOT RAISE InjectionError
FAILED tests/unit/core/test_handles.py::test_the_injected_sentinel_refuses_a_child_before_any_bookkeeping
1 failed in 0.02s
```

### H7: ScratchScope with value equality

File: `src/ag/core/handles.py`. Edit: `@dataclass(kw_only=True, eq=False)` -> `@dataclass(kw_only=True)`.

Targets: test_a_scope_has_identity_equality_and_is_hashable. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       assert one != other
E       AssertionError: assert ScratchScope(namespace='op', trail=(), materialize=<function _fake_materialize at 0x7701eae3d4e0>) != ScratchScope(namespace='op', trail=(), materialize=<function _fake_materialize at 0x7701eae3d4e0>)
FAILED tests/unit/core/test_handles.py::test_a_scope_has_identity_equality_and_is_hashable
1 failed in 0.02s
```

### H8: In written as a PEP 695 type statement

File: `src/ag/core/handles.py`. Edit: `In: TypeAlias = Annotated[ScratchHandle, Direction.IN]` -> `type In = Annotated[ScratchHandle, Direction.IN]`.

Targets: test_each_marker_carries_its_direction, tests/unit/core/test_operation_classification.py. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
E   TypeError: worked: parameter 'roads' is annotated In, which is not a recognised kind. An operation takes In and Out handles, one frozen config dataclass, and whatever the runtime injects. Tuning values go in the config rather than as loose parameters, so a run manifest can record what tuning produced an output without special-casing each operation.
>       assert get_origin(marker) is Annotated
E       assert None is Annotated
E        +  where None = get_origin(In)
ERROR tests/unit/core/test_operation_classification.py - TypeError: worked: p...
FAILED tests/unit/core/test_handles.py::test_each_marker_carries_its_direction[In-Direction.IN]
1 failed, 3 passed, 1 error in 0.03s
```

### H9: leaf not validated

File: `src/ag/core/handles.py`. Edit: delete `_check_segment(text=name, what="leaf")`.

Targets: test_a_leaf_that_cannot_be_a_layer_name_part_is_refused. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>           with pytest.raises(ValueError, match="scope leaf"):
E           Failed: DID NOT RAISE ValueError
FAILED tests/unit/core/test_handles.py::test_a_leaf_that_cannot_be_a_layer_name_part_is_refused
1 failed in 0.02s
```

### H10: leaf validated before the unbound check

File: `src/ag/core/handles.py`. Edit: delete `if self.materialize is _unbound:`.

Targets: test_the_injected_sentinel_reports_the_missing_binding_before_the_leaf. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>           INJECTED("a/b")
>           raise ValueError(
E           ValueError: scope leaf 'a/b' must be letters, digits and single underscores; it becomes part of a layer name.
FAILED tests/unit/core/test_handles.py::test_the_injected_sentinel_reports_the_missing_binding_before_the_leaf
1 failed in 0.03s
```

### T1: Classification.join with the fail-open logic and a third member

File: `src/ag/core/types.py`. Edit: `if self is Classification.CLOUD_OK and other is Classification.CLOUD_OK:` -> `if self is Classification.PREM_ONLY or other is Classification.PREM_ONLY:`; `PREM_ONLY = "prem_only"` -> `PREM_ONLY = "prem_only"`.

Targets: test_join_truth_table, test_every_classification_permits_its_own_storage. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       assert len(Classification) == 2
E       assert 3 == 2
E        +  where 3 = len(Classification)
>           assert member.permits(member), member
E           AssertionError: <Classification.RESTRICTED: 'restricted'>
E           assert False
E            +  where False = permits(<Classification.RESTRICTED: 'restricted'>)
E            +    where permits = <Classification.RESTRICTED: 'restricted'>.permits
FAILED tests/unit/core/test_types.py::test_join_truth_table - assert 3 == 2
FAILED tests/unit/core/test_types.py::test_every_classification_permits_its_own_storage
2 failed in 0.02s
```

### T2: Scale rank mapping out of order

File: `src/ag/core/types.py`. Edit: `Scale.N25: 25,` -> `Scale.N25: 125,`.

Targets: test_rank_orders_every_scale_finest_to_coarsest. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       assert tuple(sorted(Scale, key=lambda scale: scale.rank)) == FINEST_TO_COARSEST
E       AssertionError: assert (<Scale.RAW: ...N250: 'n250'>) == (<Scale.RAW: ...N250: 'n250'>)
E         At index 2 diff: <Scale.N50: 'n50'> != <Scale.N25: 'n25'>
E         Use -v to get more diff
FAILED tests/unit/core/test_types.py::test_rank_orders_every_scale_finest_to_coarsest
1 failed in 0.01s
```

### T3: a Scale member without a rank entry

File: `src/ag/core/types.py`. Edit: delete `Scale.N250: 250,`.

Targets: test_every_member_has_a_rank_and_definition_order_is_rank_order. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       ranks = [scale.rank for scale in Scale]
>       return _SCALE_RANK[self]
E       KeyError: <Scale.N250: 'n250'>
FAILED tests/unit/core/test_types.py::test_every_member_has_a_rank_and_definition_order_is_rank_order
1 failed in 0.01s
```

### E1: an AgError subclass with a required keyword-only constructor argument

File: `src/ag/core/errors.py`. Edit: append 'class _Probe(AgError):' ....

Targets: test_every_error_survives_a_pickle_round_trip. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       original = error_type("the message", context=context)
E       TypeError: _Probe.__init__() missing 1 required keyword-only argument: 'code'
FAILED tests/unit/core/test_errors.py::test_every_error_survives_a_pickle_round_trip[ag.core.errors._Probe]
1 failed, 2 passed in 0.03s
```

### E2: fill_context overwrites instead of filling empty fields

File: `src/ag/core/errors.py`. Edit: `return offered if current is None else current` -> `return current if offered is None else offered`.

Targets: test_fill_context_fills_empty_fields_only, test_fill_context_never_replaces_the_operation. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       assert error.context.method == "dissolve"
E       AssertionError: assert 'select' == 'dissolve'
E         - dissolve
E         + select
>       assert error.context.operation == "resolve_ramps"
E       AssertionError: assert 'thin_road_network' == 'resolve_ramps'
E         - resolve_ramps
E         + thin_road_network
FAILED tests/unit/core/test_errors.py::test_fill_context_fills_empty_fields_only
FAILED tests/unit/core/test_errors.py::test_fill_context_never_replaces_the_operation
2 failed in 0.02s
```

### E3: row sample not capped on construction

File: `src/ag/core/errors.py`. Edit: `object.__setattr__(self, "row_indices", indices[:ROW_INDEX_CAP])` -> `object.__setattr__(self, "row_indices", indices)`.

Targets: test_fill_context_caps_the_row_sample_and_derives_the_count, test_a_directly_constructed_context_is_capped_and_counted. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       assert error.context.row_indices == tuple(range(ROW_INDEX_CAP))
E       assert (0, 1, 2, 3, 4, 5, ...) == (0, 1, 2, 3, 4, 5, ...)
E         Left contains 80 more items, first extra item: 20
E         Use -v to get more diff
>       assert context.row_indices == tuple(range(ROW_INDEX_CAP))
FAILED tests/unit/core/test_errors.py::test_fill_context_caps_the_row_sample_and_derives_the_count
FAILED tests/unit/core/test_errors.py::test_a_directly_constructed_context_is_capped_and_counted
2 failed in 0.02s
```

### E4: indices and count filled independently

File: `src/ag/core/errors.py`. Edit: `if current.row_indices or current.row_count is not None:` -> `if current.row_indices and current.row_count is not None:`.

Targets: test_fill_context_keeps_indices_and_count_as_one_pair. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       assert only_count.context.row_indices == ()
E       assert (1, 2, 3) == ()
E         Left contains 3 more items, first extra item: 1
E         Use -v to get more diff
FAILED tests/unit/core/test_errors.py::test_fill_context_keeps_indices_and_count_as_one_pair
1 failed in 0.02s
```

### E5: generator materialised although the count is known

File: `src/ag/core/errors.py`. Edit: `indices = tuple(islice(offered_rows, ROW_INDEX_CAP))` -> `indices = tuple(offered_rows)`.

Targets: test_fill_context_reads_a_generator_only_up_to_the_cap_when_the_count_is_given. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       assert next(produced) == ROW_INDEX_CAP
E       StopIteration
FAILED tests/unit/core/test_errors.py::test_fill_context_reads_a_generator_only_up_to_the_cap_when_the_count_is_given
1 failed in 0.02s
```

### E6: truth test on an array-like argument

File: `src/ag/core/errors.py`. Edit: `offered_rows: Iterable[int] = () if row_indices is None else row_indices` -> `offered_rows: Iterable[int] = row_indices or ()`.

Targets: test_fill_context_accepts_array_like_rows_and_messages. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       fill_context(
>       raise ValueError("the truth value of an array is ambiguous")
E       ValueError: the truth value of an array is ambiguous
FAILED tests/unit/core/test_errors.py::test_fill_context_accepts_array_like_rows_and_messages
1 failed in 0.02s
```

### E7: indices not normalised through operator.index

File: `src/ag/core/errors.py`. Edit: `indices = tuple(operator.index(index) for index in self.row_indices)` -> `indices = tuple(self.row_indices)`.

Targets: test_a_directly_constructed_context_normalises_its_sequences, test_a_float_row_position_is_refused_rather_than_truncated. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       assert all(type(index) is int for index in context.row_indices)
E       assert False
E        +  where False = all(<generator object test_a_directly_constructed_context_normalises_its_sequences.<locals>.<genexpr> at 0x731431df42b0>)
>       with pytest.raises(TypeError):
E       Failed: DID NOT RAISE TypeError
FAILED tests/unit/core/test_errors.py::test_a_directly_constructed_context_normalises_its_sequences
FAILED tests/unit/core/test_errors.py::test_a_float_row_position_is_refused_rather_than_truncated
2 failed in 0.02s
```

### E8: a bare string as tool_messages taken as its characters

File: `src/ag/core/errors.py`. Edit: `if isinstance(value, str):` -> `if False:`.

Targets: test_a_bare_string_is_one_tool_message. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       assert context.tool_messages == ("ERROR 000210",)
E       AssertionError: assert ('E', 'R', 'R...'R', ' ', ...) == ('ERROR 000210',)
E         At index 0 diff: 'E' != 'ERROR 000210'
E         Left contains 11 more items, first extra item: 'R'
E         Use -v to get more diff
FAILED tests/unit/core/test_errors.py::test_a_bare_string_is_one_tool_message
1 failed in 0.02s
```

### After the last restore

```
83 passed in 0.06s
```

## Part 3: the harness catching its own failure modes

Produced by a throwaway self-check script run against the committed engine; each scenario builds a probe case in memory, so the case tables are untouched. A30.

### A. A renamed node id stops at preflight, nothing edited

```
targets do not collect:
  ERROR: not found: /home/elling/projects/ag_refactor_docs/tests/unit/core/test_operation_classification.py::test_this_name_does_not_exist
```

### B. With preflight bypassed, the baseline stops the same case

```
**HARNESS ERROR, nothing mutated**

```
baseline exit 4:
no PASSED line for tests/unit/core/test_operation_classification.py::test_this_name_does_not_exist
```
```

### C. With preflight and baseline bypassed, the verdict reports UNEXPECTED

```
exit 4; verdict False -> UNEXPECTED
ERROR: not found: /home/elling/projects/ag_refactor_docs/tests/unit/core/test_operation_classification.py::test_this_name_does_not_exist
(no match in any of [<Module test_operation_classification.py>])
```

### D. A stale module path on a module-target case

```
preflight:
targets do not collect:
  ERROR: file or directory not found: tests/unit/core/test_no_such_module.py

baseline (preflight bypassed): **HARNESS ERROR, nothing mutated**

verdict (both bypassed): exit 4; verdict False
```

### E. A target that fails in isolation is stopped by the baseline

```
preflight problems: none (it collects)
whole file: exit 0, 2 passed in 0.01s
run_case: **HARNESS ERROR, nothing mutated**

```
baseline exit 1:
FAILED tests/unit/core/test_zz_probe_order.py::test_second - assert []
```
```

### F. The relaxed verdict (any nonzero exit, name anywhere in output) turns the stale-name probe green

```
relaxed verdict on the stale-name output: True
(engine.py restored)
```

### G. A parametrised target reports FAILED as expected under the exact matcher

```
**FAILED as expected** (exit 1)

```
>       original = error_type("the message", context=context)
E       TypeError: _Probe.__init__() missing 1 required keyword-only argument: 'code'
FAILED tests/unit/core/test_errors.py::test_every_error_survives_a_pickle_round_trip[ag.core.errors._Probe]
1 failed, 2 passed in 0.02s
```
```

### H. The `--check` hook fails when a referenced test is renamed

```
exit 1
break-it-once: harness errors, nothing was edited
  targets do not collect:
  ERROR: not found: /home/elling/projects/ag_refactor_docs/tests/unit/core/test_types.py::test_rank_orders_every_scale_finest_to_coarsest
(test_types.py restored)
```

### Hashes

Every watched file under `src/ag/core`, `tests/unit/core` and the engine is byte-identical before and after the scenarios above.

