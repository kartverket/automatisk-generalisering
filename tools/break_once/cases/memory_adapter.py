"""Cases for the in-memory adapter: the store, the shared field rule, the predicate
evaluator, the two geometry groups, the row IO group, and the group rules in
`tests/static/test_adapter_groups.py`.

Two guards have no case here because no text edit reaches them: the root-contents rule
needs a stray file in the adapter root, and the static matrix is checked by pyright, not
pytest. Both are broken by hand and recorded in the evidence file.
"""

from __future__ import annotations

from ..engine import Case

FIELD_VALUES = "src/ag/adapters/_shared/field_values.py"
STORE = "src/ag/adapters/fakes/memory/store.py"
PRECONDITIONS = "src/ag/adapters/fakes/memory/support/preconditions.py"
PREDICATE_EVAL = "src/ag/adapters/fakes/memory/support/predicate_eval.py"
SELECTION = "src/ag/adapters/fakes/memory/geometry_ops/selection.py"
SHAPE = "src/ag/adapters/fakes/memory/geometry_ops/shape.py"
GEOMETRY_INIT = "src/ag/adapters/fakes/memory/geometry_ops/__init__.py"
CARTOGRAPHIC_INIT = "src/ag/adapters/fakes/memory/cartographic_ops/__init__.py"
ROW_IO = "src/ag/adapters/fakes/memory/table_ops/row_io.py"

UNIT = "tests/unit/adapters/fakes/memory"
T_STORE = f"{UNIT}/test_store.py"
T_EVAL = f"{UNIT}/test_predicate_eval.py"
T_GEOMETRY = f"{UNIT}/test_geometry_ops.py"
T_TABLE = f"{UNIT}/test_table_ops.py"
T_GROUPS = "tests/static/test_adapter_groups.py"

ROW_REFUSED = f"{T_STORE}::test_a_row_that_does_not_fit_the_schema_is_refused"
CHECK_REFUSES = f"{T_EVAL}::test_check_refuses_what_the_adapter_cannot_evaluate"
EMPTY_RAISES = f"{T_GEOMETRY}::test_a_bad_predicate_on_an_empty_dataset_raises"
ONE_GROUP = f"{T_GROUPS}::test_every_protocol_method_is_implemented_by_one_group"

SELECT_DEF = (
    "    def select(\n"
    "        self, *, input: ScratchHandle, where: Predicate, output: ScratchHandle\n"
    "    ) -> None:\n"
)
EXPLODE_DEF = "    def explode_multipart(\n"
READ_ROWS_DEF = "    def read_rows(\n"
COMPOSED_DOC = '    """`GeometryOps` over the in-memory store, composed from its method groups."""\n'
RAW_CASE = (
    "        case RawAttr(cql=cql):\n"
    "            raise PortContractError(\n"
    '                f"Attr.raw({cql!r}) cannot run under the in-memory adapter, which "\n'
    '                "compiles no CQL; a raw expression runs only under an engine."\n'
    "            )\n"
)
SPATIAL_CASE = (
    "        case Spatial():\n"
    "            raise PortContractError(\n"
    '                f"{predicate!r} cannot run under the in-memory adapter, which computes "\n'
    '                "no geometry; a spatial predicate runs only under an engine."\n'
    "            )\n"
)
DECLARED_RAISE = (
    "    raise PortContractError(\n"
    '        f"{name!r} is not a field of the dataset, whose fields are "\n'
    '        f"{[field.name for field in schema.fields]}."\n'
    "    )\n"
)

CASES: tuple[Case, ...] = (
    Case(
        "M1",
        "a helper method on a group class",
        SELECTION,
        ((SELECT_DEF, "    def _prepare(self) -> None: ...\n\n" + SELECT_DEF),),
        (f"{T_GROUPS}::test_rule_holds[memory-protocol-methods-only]",),
    ),
    Case(
        "M2",
        "a Protocol method defined in two groups",
        SHAPE,
        ((EXPLODE_DEF, "    def select(self) -> None: ...\n\n" + EXPLODE_DEF),),
        (
            f"{T_GROUPS}::test_rule_holds[memory-no-duplicate-method]",
            f"{ONE_GROUP}[memory-geometry_ops]",
        ),
    ),
    Case(
        "M3",
        "a self assignment in a group method",
        SELECTION,
        (
            (
                "        distinct_paths(handles=(input, output))\n",
                "        self._last = output\n"
                "        distinct_paths(handles=(input, output))\n",
            ),
        ),
        (f"{T_GROUPS}::test_rule_holds[memory-no-state-outside-base]",),
    ),
    Case(
        "M4",
        "a body on the composed class",
        GEOMETRY_INIT,
        ((COMPOSED_DOC, COMPOSED_DOC + "\n    limit = 1\n"),),
        (f"{T_GROUPS}::test_rule_holds[memory-composed-body-empty]",),
    ),
    Case(
        "M5",
        "a composed class not in the matrix",
        CARTOGRAPHIC_INIT,
        (("", "\n\nclass Extra(MemoryPortBase):  # probe\n    pass\n"),),
        (f"{T_GROUPS}::test_every_composed_class_is_in_the_matrix",),
    ),
    Case(
        "M6",
        "a Protocol method implemented by no group",
        ROW_IO,
        ((READ_ROWS_DEF, "    def read_rows_(\n"),),
        (
            f"{ONE_GROUP}[memory-table_ops]",
            f"{T_GROUPS}::test_rule_holds[memory-protocol-methods-only]",
        ),
    ),
    Case(
        "M7",
        "UNKNOWN collapsed to FALSE on a NULL comparison",
        PREDICATE_EVAL,
        (
            (
                "            actual = row.attributes[name]\n"
                "            if actual is None:\n"
                "                return Truth.UNKNOWN\n"
                "            field = _declared(schema=schema, name=name)\n",
                "            actual = row.attributes[name]\n"
                "            if actual is None:\n"
                "                return Truth.FALSE\n"
                "            field = _declared(schema=schema, name=name)\n",
            ),
        ),
        (
            f"{T_EVAL}::test_compare_is_unknown_on_a_null_field_and_so_is_its_negation",
            f"{T_GEOMETRY}::"
            "test_select_under_a_negation_excludes_the_null_row_until_is_null_is_added",
        ),
    ),
    Case(
        "M8",
        "the type check on predicate values removed",
        PREDICATE_EVAL,
        (
            (
                "    reason = type_mismatch(value=value, field=field)\n"
                "    if reason is not None:\n",
                "    reason = type_mismatch(value=value, field=field)\n    if False:\n",
            ),
        ),
        (f"{CHECK_REFUSES}[float-on-long]", f"{CHECK_REFUSES}[long-overflow-lt]"),
    ),
    Case(
        "M9",
        "RawAttr passed through the check",
        PREDICATE_EVAL,
        ((RAW_CASE, "        case RawAttr():\n            pass\n"),),
        (f"{CHECK_REFUSES}[raw]", f"{EMPTY_RAISES}[raw]"),
    ),
    Case(
        "M10",
        "LIKE accepted on a non-text field",
        PREDICATE_EVAL,
        (
            (
                "            if field.type is not FieldType.TEXT:\n",
                "            if False:\n",
            ),
        ),
        (f"{CHECK_REFUSES}[like-on-a-number]",),
    ),
    Case(
        "M11",
        "the check skipped before the rows, so an empty input hides a bad predicate",
        SELECTION,
        (("        check(where, schema=dataset.schema)\n", ""),),
        (EMPTY_RAISES,),
    ),
    Case(
        "M12",
        "pairs written under parents=None",
        SHAPE,
        (
            (
                "        if parents is None:\n            return\n",
                "        if parents is None:\n"
                "            parents = ScratchHandle(\n"
                '                name="p", data_type=DataType.TABLE, path="memory:/p"\n'
                "            )\n",
            ),
        ),
        (
            f"{T_GEOMETRY}::"
            "test_explode_without_parents_writes_the_children_and_nothing_else",
        ),
    ),
    Case(
        "M13",
        "the native index numbered 1..n per write instead of from one counter",
        STORE,
        (("        start = self._next_index\n", "        start = 1\n"),),
        (
            f"{T_STORE}::test_rewriting_a_dataset_assigns_fresh_indices",
            f"{T_STORE}::"
            "test_indices_are_dense_from_one_and_a_second_write_takes_the_next_range",
            f"{T_GEOMETRY}::"
            "test_explode_leaves_the_input_index_unchanged_and_the_next_write_reassigns_it",
        ),
    ),
    Case(
        "M14",
        "the empty-geometry guard removed",
        SHAPE,
        (
            (
                "    if nulls:\n        raise EmptyGeometryError(\n",
                "    if False:\n        raise EmptyGeometryError(\n",
            ),
        ),
        (
            f"{T_GEOMETRY}::"
            "test_explode_refuses_a_null_geometry_before_writing_whether_or_not_parents_asked",
        ),
    ),
    Case(
        "M15",
        "handles compared by name, type and namespace instead of path",
        PRECONDITIONS,
        (
            (
                "        path = os.fspath(handle)\n",
                '        path = f"{handle.name}:{handle.data_type}:{handle.namespace}"\n',
            ),
        ),
        (f"{T_GEOMETRY}::test_explode_refuses_two_handles_on_one_path",),
    ),
    Case(
        "M16",
        "the SHORT and LONG range check removed",
        FIELD_VALUES,
        (("        if not low <= value <= high:\n", "        if False:\n"),),
        (
            f"{ROW_REFUSED}[long-overflow]",
            f"{T_STORE}::test_short_overflow_and_geometry_on_a_table_are_refused",
            f"{CHECK_REFUSES}[long-overflow-lt]",
        ),
    ),
    Case(
        "M17",
        "the TEXT length check removed",
        FIELD_VALUES,
        (
            (
                "        if field.length is not None and len(value) > field.length:\n",
                "        if False:\n",
            ),
        ),
        (f"{ROW_REFUSED}[text-too-long]", f"{CHECK_REFUSES}[text-too-long]"),
    ),
    Case(
        "M18",
        "a bool accepted as a cell value",
        FIELD_VALUES,
        (("    if isinstance(value, bool):\n", "    if False:\n"),),
        (f"{ROW_REFUSED}[bool-on-long]",),
    ),
    Case(
        "M19",
        "rows stored by reference instead of as read-only copies",
        STORE,
        (
            (
                "        checked = tuple(_frozen(row) for row in rows)\n",
                "        checked = tuple(rows)\n",
            ),
        ),
        (
            f"{T_STORE}::"
            "test_mutating_the_callers_mapping_after_a_write_leaves_the_stored_row_unchanged",
        ),
    ),
    Case(
        "M20",
        "the distinct-paths check removed from select",
        SELECTION,
        (("        distinct_paths(handles=(input, output))\n", ""),),
        (f"{T_GEOMETRY}::test_select_refuses_an_output_on_the_input_path",),
    ),
    Case(
        "M21",
        "a table input accepted by explode_multipart",
        SHAPE,
        (
            (
                "    if dataset.schema.data_type is not DataType.FEATURE_CLASS:\n",
                "    if False:\n",
            ),
        ),
        (f"{T_GEOMETRY}::test_explode_refuses_a_table_input",),
    ),
    Case(
        "M22",
        "an unknown field accepted by read_rows",
        ROW_IO,
        (("        if unknown:\n", "        if False:\n"),),
        (f"{T_TABLE}::test_read_rows_refuses_a_field_the_dataset_does_not_declare",),
    ),
    Case(
        "M23",
        "an unknown field accepted by the check",
        PREDICATE_EVAL,
        ((DECLARED_RAISE, "    return Field(name, FieldType.TEXT, 100)\n"),),
        (
            f"{CHECK_REFUSES}[unknown-field]",
            f"{CHECK_REFUSES}[unknown-field-is-null]",
            f"{EMPTY_RAISES}[unknown-field]",
        ),
    ),
    Case(
        "M24",
        "a Spatial leaf passed through the check",
        PREDICATE_EVAL,
        ((SPATIAL_CASE, "        case Spatial():\n            pass\n"),),
        (f"{CHECK_REFUSES}[spatial]", f"{EMPTY_RAISES}[spatial]"),
    ),
    Case(
        "M25",
        "the field-set check on write removed",
        STORE,
        (("    if names != declared.keys():\n", "    if False:\n"),),
        (f"{ROW_REFUSED}[missing-field]",),
    ),
    Case(
        "M26",
        "a handle's DataType not checked against the schema",
        STORE,
        (
            (
                "        if handle.data_type is not schema.data_type:\n",
                "        if False:\n",
            ),
        ),
        (f"{T_STORE}::test_a_table_handle_refuses_a_feature_class_schema",),
    ),
    Case(
        "M27",
        "a geometry accepted on a table",
        STORE,
        (
            (
                "    if schema.data_type is not DataType.FEATURE_CLASS:\n",
                "    if False:\n",
            ),
        ),
        (f"{T_STORE}::test_short_overflow_and_geometry_on_a_table_are_refused",),
    ),
    Case(
        "M28",
        "the CRS check on write removed",
        STORE,
        (("    if row.geometry.crs != schema.geometry_crs:\n", "    if False:\n"),),
        (f"{ROW_REFUSED}[wrong-crs]",),
    ),
    Case(
        "M29",
        "an aware datetime accepted",
        FIELD_VALUES,
        (("    if value.tzinfo is not None:\n", "    if False:\n"),),
        (f"{ROW_REFUSED}[aware-datetime]",),
    ),
)

SUITE: tuple[str, ...] = ("tests/unit/adapters", "tests/static")
