"""Cases for the core lift: `core/operations.py`, `core/handles.py`, `core/types.py` and
`core/errors.py`, each guard named by the test that catches it.
"""

from __future__ import annotations

from ..engine import Case, tests_in

OPS = "src/ag/core/operations.py"
HANDLES = "src/ag/core/handles.py"
TYPES = "src/ag/core/types.py"
ERRORS = "src/ag/core/errors.py"
T_OPS = "tests/unit/core/test_operation_classification.py"
T_HANDLES = "tests/unit/core/test_handles.py"
T_TYPES = "tests/unit/core/test_types.py"
T_ERRORS = "tests/unit/core/test_errors.py"

CASES: tuple[Case, ...] = (
    Case(
        "O1",
        "bare Injected base accepted",
        OPS,
        (("        if hint is Injected:\n", "        if False:\n"),),
        tests_in(T_OPS, "test_the_bare_injected_base_is_rejected"),
    ),
    Case(
        "O2",
        "injected default not required / not checked against its kind",
        OPS,
        (
            (
                "            if not isinstance(parameter.default, kind):",
                "            if False:",
            ),
        ),
        tests_in(
            T_OPS,
            "test_an_injected_parameter_without_a_default_is_rejected",
            "test_an_injected_default_of_the_wrong_kind_is_rejected",
        ),
    ),
    Case(
        "O3",
        "default on an In/Out handle accepted",
        OPS,
        (
            (
                "            if parameter.default is not _EMPTY:\n"
                "                raise TypeError(\n"
                '                    f"{name}: parameter {param!r} has a default.',
                "            if False:\n"
                "                raise TypeError(\n"
                '                    f"{name}: parameter {param!r} has a default.',
            ),
        ),
        tests_in(T_OPS, "test_a_defaulted_handle_is_rejected"),
    ),
    Case(
        "O4",
        "default on config accepted",
        OPS,
        (
            (
                "            if parameter.default is not _EMPTY:\n"
                "                raise TypeError(\n"
                '                    f"{name}: {CONFIG_PARAM} has a default.',
                "            if False:\n"
                "                raise TypeError(\n"
                '                    f"{name}: {CONFIG_PARAM} has a default.',
            ),
        ),
        tests_in(T_OPS, "test_a_defaulted_config_is_rejected"),
    ),
    Case(
        "O5",
        "config annotation not checked to be a frozen dataclass type",
        OPS,
        (
            (
                "            if not _is_frozen_dataclass_type(hint):",
                "            if False:",
            ),
        ),
        tests_in(
            T_OPS,
            "test_a_mutable_config_type_is_rejected",
            "test_a_config_that_is_not_a_dataclass_type_is_rejected",
        ),
    ),
    Case(
        "O6",
        "config hashability not checked at the declaration site",
        OPS,
        (
            (
                "        hash(value)\n    except TypeError:",
                "        pass\n    except TypeError:",
            ),
        ),
        tests_in(
            T_OPS, "test_a_frozen_config_with_a_list_field_is_rejected_as_unhashable"
        ),
    ),
    Case(
        "O7",
        "positional parameter accepted",
        OPS,
        (
            (
                "        if parameter.kind is not inspect.Parameter.KEYWORD_ONLY:",
                "        if False:",
            ),
        ),
        tests_in(T_OPS, "test_a_positional_parameter_is_rejected"),
    ),
    Case(
        "O8",
        "unannotated parameter not reported as such",
        OPS,
        (
            (
                "        if hint is None:\n"
                "            raise TypeError(\n"
                '                f"{name}: parameter {param!r} has no annotation.',
                "        if False:\n"
                "            raise TypeError(\n"
                '                f"{name}: parameter {param!r} has no annotation.',
            ),
        ),
        tests_in(T_OPS, "test_an_unannotated_parameter_is_rejected"),
    ),
    Case(
        "O9",
        "port-only markers accepted on an operation",
        OPS,
        (("        elif direction in _PORT_ONLY:", "        elif False:"),),
        tests_in(
            T_OPS,
            "test_the_mutates_marker_is_rejected_on_an_operation",
            "test_the_parents_out_marker_is_rejected_on_an_operation",
        ),
    ),
    Case(
        "O10",
        "two parameters of one injected kind accepted",
        OPS,
        (("            if kind in injected:", "            if False:"),),
        tests_in(T_OPS, "test_two_parameters_of_one_injected_kind_are_rejected"),
    ),
    Case(
        "O11",
        "unrecognised kind silently skipped",
        OPS,
        (
            (
                "        else:\n            raise TypeError(\n",
                "        else:\n            continue\n            raise TypeError(\n",
            ),
        ),
        tests_in(
            T_OPS,
            "test_a_loose_tuning_parameter_is_rejected",
            "test_a_generic_alias_is_rejected_without_crashing_the_classifier",
            "test_a_type_statement_alias_is_never_silently_misclassified",
        ),
    ),
    Case(
        "O12",
        "injected argument passed by hand accepted",
        OPS,
        (("            if param in bound.arguments:", "            if False:"),),
        tests_in(
            T_OPS, "test_an_injected_argument_may_not_be_passed_at_a_declaration_site"
        ),
    ),
    Case(
        "O13",
        "undeclared handle accepted",
        OPS,
        (("    if not value.namespace:", "    if False:"),),
        tests_in(T_OPS, "test_an_undeclared_handle_is_rejected"),
    ),
    Case(
        "O14",
        "config of another type accepted",
        OPS,
        (("    if not isinstance(value, config_type):", "    if False:"),),
        tests_in(T_OPS, "test_a_config_of_another_type_is_rejected"),
    ),
    Case(
        "O15",
        "union containing an injected kind not reported as such",
        OPS,
        (("        elif union_kind is not None:", "        elif False:"),),
        tests_in(T_OPS, "test_a_union_containing_an_injected_kind_is_rejected"),
    ),
    Case(
        "O16",
        "get_type_hints without include_extras",
        OPS,
        (("get_type_hints(fn, include_extras=True)", "get_type_hints(fn)"),),
        (T_OPS,),
    ),
    Case(
        "O17",
        "call mappings not wrapped read-only",
        OPS,
        (
            (
                "            inputs=MappingProxyType(inputs),",
                "            inputs=inputs,",
            ),
        ),
        tests_in(T_OPS, "test_the_mappings_are_read_only_views"),
    ),
    Case(
        "O18",
        "OperationCall with value equality",
        OPS,
        (
            (
                "@dataclass(frozen=True, eq=False)\nclass OperationCall:",
                "@dataclass(frozen=True)\nclass OperationCall:",
            ),
        ),
        tests_in(T_OPS, "test_two_identical_declarations_are_two_calls"),
    ),
    Case(
        "O19",
        "frozen dataclass type accepted without eq",
        OPS,
        (("    return frozen and eq", "    return frozen"),),
        tests_in(T_OPS, "test_a_frozen_config_type_without_equality_is_rejected"),
    ),
    Case(
        "H1",
        "__set_name__ restamps silently",
        HANDLES,
        (("        if self.name or self.namespace:", "        if False:"),),
        tests_in(
            T_HANDLES,
            "test_a_handle_bound_in_two_class_bodies_is_refused",
            "test_a_prenamed_handle_is_refused_as_a_class_attribute",
        ),
    ),
    Case(
        "H2",
        "internal handle not stamped with the scope namespace",
        HANDLES,
        (
            (
                "            namespace=self.namespace,\n            path=path,",
                '            namespace="",\n            path=path,',
            ),
        ),
        tests_in(
            T_HANDLES, "test_internal_handles_of_two_operations_are_different_values"
        ),
    ),
    Case(
        "H3",
        "internal handle named by leaf only, not trail",
        HANDLES,
        (
            (
                "            name=TRAIL_SEPARATOR.join((*self.trail, name)),",
                "            name=name,",
            ),
        ),
        tests_in(
            T_HANDLES,
            "test_the_same_leaf_at_three_points_of_one_trail_is_three_handles",
        ),
    ),
    Case(
        "H4",
        "child segments not deduplicated",
        HANDLES,
        (("        while segment in self._issued:", "        while False:"),),
        tests_in(
            T_HANDLES,
            "test_repeated_child_labels_take_the_first_unused_index",
            "test_a_tagged_label_and_a_label_spelled_like_it_are_two_segments",
        ),
    ),
    Case(
        "H5",
        "label, tag and leaf not validated",
        HANDLES,
        (("    if _SEGMENT.fullmatch(text) is None:", "    if False:"),),
        tests_in(
            T_HANDLES,
            "test_a_label_or_tag_that_cannot_be_a_layer_name_part_is_refused",
            "test_a_leaf_that_cannot_be_a_layer_name_part_is_refused",
        ),
    ),
    Case(
        "H6",
        "child() on the unbound sentinel allowed",
        HANDLES,
        (
            (
                "        if self.materialize is _unbound:\n"
                "            raise InjectionError("
                '_unbound_message(call=f"scratch.child({label!r})"))',
                "        if False:\n"
                "            raise InjectionError("
                '_unbound_message(call=f"scratch.child({label!r})"))',
            ),
        ),
        tests_in(
            T_HANDLES,
            "test_the_injected_sentinel_refuses_a_child_before_any_bookkeeping",
        ),
    ),
    Case(
        "H7",
        "ScratchScope with value equality",
        HANDLES,
        (("@dataclass(kw_only=True, eq=False)", "@dataclass(kw_only=True)"),),
        tests_in(T_HANDLES, "test_a_scope_has_identity_equality_and_is_hashable"),
    ),
    Case(
        "H8",
        "In written as a PEP 695 type statement",
        HANDLES,
        (
            (
                "In: TypeAlias = Annotated[ScratchHandle, Direction.IN]",
                "type In = Annotated[ScratchHandle, Direction.IN]",
            ),
        ),
        tests_in(T_HANDLES, "test_each_marker_carries_its_direction") + (T_OPS,),
    ),
    Case(
        "H9",
        "leaf not validated",
        HANDLES,
        (('        _check_segment(text=name, what="leaf")\n', ""),),
        tests_in(T_HANDLES, "test_a_leaf_that_cannot_be_a_layer_name_part_is_refused"),
    ),
    Case(
        "H10",
        "leaf validated before the unbound check",
        HANDLES,
        (
            (
                "        if self.materialize is _unbound:\n"
                "            raise InjectionError("
                '_unbound_message(call=f"scratch({name!r})"))\n',
                "",
            ),
        ),
        tests_in(
            T_HANDLES,
            "test_the_injected_sentinel_reports_the_missing_binding_before_the_leaf",
        ),
    ),
    Case(
        "T1",
        "Classification.join with the fail-open logic and a third member",
        TYPES,
        (
            (
                "        if self is Classification.CLOUD_OK and other is "
                "Classification.CLOUD_OK:\n"
                "            return Classification.CLOUD_OK\n"
                "        return Classification.PREM_ONLY",
                "        if self is Classification.PREM_ONLY or other is "
                "Classification.PREM_ONLY:\n"
                "            return Classification.PREM_ONLY\n"
                "        return Classification.CLOUD_OK",
            ),
            (
                '    PREM_ONLY = "prem_only"\n\n    def join',
                '    PREM_ONLY = "prem_only"\n    RESTRICTED = "restricted"\n\n    def join',
            ),
        ),
        tests_in(
            T_TYPES,
            "test_join_truth_table",
            "test_every_classification_permits_its_own_storage",
        ),
    ),
    Case(
        "T2",
        "Scale rank mapping out of order",
        TYPES,
        (("    Scale.N25: 25,", "    Scale.N25: 125,"),),
        tests_in(T_TYPES, "test_rank_orders_every_scale_finest_to_coarsest"),
    ),
    Case(
        "T3",
        "a Scale member without a rank entry",
        TYPES,
        (("    Scale.N250: 250,\n", ""),),
        tests_in(
            T_TYPES, "test_every_member_has_a_rank_and_definition_order_is_rank_order"
        ),
    ),
    Case(
        "E1",
        "an AgError subclass with a required keyword-only constructor argument",
        ERRORS,
        (
            (
                "",
                "\n\nclass _Probe(AgError):\n"
                "    def __init__(\n"
                "        self, message: str, *, code: int, "
                "context: ErrorContext | None = None\n"
                "    ) -> None:\n"
                "        super().__init__(message, context=context)\n"
                "        self.code = code\n",
            ),
        ),
        tests_in(T_ERRORS, "test_every_error_survives_a_pickle_round_trip"),
    ),
    Case(
        "E2",
        "fill_context overwrites instead of filling empty fields",
        ERRORS,
        (
            (
                "    return offered if current is None else current",
                "    return current if offered is None else offered",
            ),
        ),
        tests_in(
            T_ERRORS,
            "test_fill_context_fills_empty_fields_only",
            "test_fill_context_never_replaces_the_operation",
        ),
    ),
    Case(
        "E3",
        "row sample not capped on construction",
        ERRORS,
        (
            (
                '        object.__setattr__(self, "row_indices", indices[:ROW_INDEX_CAP])',
                '        object.__setattr__(self, "row_indices", indices)',
            ),
        ),
        tests_in(
            T_ERRORS,
            "test_fill_context_caps_the_row_sample_and_derives_the_count",
            "test_a_directly_constructed_context_is_capped_and_counted",
        ),
    ),
    Case(
        "E4",
        "indices and count filled independently",
        ERRORS,
        (
            (
                "    if current.row_indices or current.row_count is not None:",
                "    if current.row_indices and current.row_count is not None:",
            ),
        ),
        tests_in(T_ERRORS, "test_fill_context_keeps_indices_and_count_as_one_pair"),
    ),
    Case(
        "E5",
        "generator materialised although the count is known",
        ERRORS,
        (
            (
                "        indices = tuple(islice(offered_rows, ROW_INDEX_CAP))",
                "        indices = tuple(offered_rows)",
            ),
        ),
        tests_in(
            T_ERRORS,
            "test_fill_context_reads_a_generator_only_up_to_the_cap_when_the_count_is_given",
        ),
    ),
    Case(
        "E6",
        "truth test on an array-like argument",
        ERRORS,
        (
            (
                "    offered_rows: Iterable[int] = () if row_indices is None else row_indices",
                "    offered_rows: Iterable[int] = row_indices or ()",
            ),
        ),
        tests_in(T_ERRORS, "test_fill_context_accepts_array_like_rows_and_messages"),
    ),
    Case(
        "E7",
        "indices not normalised through operator.index",
        ERRORS,
        (
            (
                "        indices = tuple(operator.index(index) for index in self.row_indices)",
                "        indices = tuple(self.row_indices)",
            ),
        ),
        tests_in(
            T_ERRORS,
            "test_a_directly_constructed_context_normalises_its_sequences",
            "test_a_float_row_position_is_refused_rather_than_truncated",
        ),
    ),
    Case(
        "E8",
        "a bare string as tool_messages taken as its characters",
        ERRORS,
        (
            (
                "    if isinstance(value, str):\n        return (value,)",
                "    if False:\n        return (value,)",
            ),
        ),
        tests_in(T_ERRORS, "test_a_bare_string_is_one_tool_message"),
    ),
)

SUITE: tuple[str, ...] = ("tests/unit/core",)
