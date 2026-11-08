"""Cases for the ArcPy adapter's first methods: the described schema, the WKB codec, the
predicate compiler, the write side's builders, the three group modules and the
capability record.

The session's own guards are in `arcpy_session.py`; the scan and stub rules there cover
the adapter root as a whole and are not repeated. The memory adapter's case on the
shared `distinct_paths` body (`memory_adapter.py`, M15) covers it for both adapters.
"""

from __future__ import annotations

from ..engine import Case, tests_in

ROOT_INIT = "src/ag/adapters/arcpy/__init__.py"
SCHEMA = "src/ag/adapters/arcpy/support/dataset_schema.py"
CODEC = "src/ag/adapters/arcpy/support/geometry_values.py"
COMPILER = "src/ag/adapters/arcpy/support/predicate_compiler.py"
WRITER = "src/ag/adapters/arcpy/support/dataset_writer.py"
SELECTION = "src/ag/adapters/arcpy/geometry_ops/selection.py"
SHAPE = "src/ag/adapters/arcpy/geometry_ops/shape.py"
ROW_IO = "src/ag/adapters/arcpy/table_ops/row_io.py"

UNIT = "tests/unit/adapters/arcpy"
T_SCHEMA = f"{UNIT}/test_dataset_schema.py"
T_CODEC = f"{UNIT}/test_geometry_values.py"
T_COMPILER = f"{UNIT}/test_predicate_compiler.py"
T_WRITER = f"{UNIT}/test_dataset_writer.py"
T_GEOMETRY = f"{UNIT}/test_geometry_ops.py"
T_TABLE = f"{UNIT}/test_table_ops.py"
T_CAPABILITIES = "tests/static/test_capabilities.py"
T_SCANS = "tests/static/test_source_scans.py"

REFUSES = f"{T_COMPILER}::test_check_refuses_before_anything_compiles"
CLAUSE = f"{T_COMPILER}::test_the_clause"
DESCRIBE_REFUSES = f"{T_SCHEMA}::test_describe_refuses_before_any_row"
CODEC_REFUSES = f"{T_CODEC}::test_what_the_port_cannot_hold_is_refused_naming_the_row"

CASES: tuple[Case, ...] = (
    Case(
        "D1",
        "Z and M not refused",
        SCHEMA,
        (("    if raw.has_z or raw.has_m:\n", "    if False:\n"),),
        (f"{DESCRIBE_REFUSES}[z]", f"{DESCRIBE_REFUSES}[m]"),
    ),
    Case(
        "D2",
        "an unrepresentable field dropped instead of recorded",
        SCHEMA,
        (("            unrepresentable[name] = engine_type\n", "            pass\n"),),
        tests_in(
            T_SCHEMA,
            "test_an_unrepresentable_field_is_recorded_not_refused_until_named",
        ),
    ),
    Case(
        "D3",
        "an unmapped shape type described as a feature class with no family",
        SCHEMA,
        (
            (
                '        family = SHAPE_TYPES.get(raw.shape_type or "")\n'
                "        if family is None:\n",
                '        family = SHAPE_TYPES.get(raw.shape_type or "", GeometryFamily.LINE)\n'
                "        if False:\n",
            ),
        ),
        (f"{DESCRIBE_REFUSES}[unknown-shape-type]",),
    ),
    Case(
        "D4",
        "the family read from a fixed shape type instead of the described one",
        SCHEMA,
        (
            (
                "            shape_type = described.shapeType\n",
                '            shape_type = "Polyline"\n',
            ),
        ),
        (
            f"{T_SCHEMA}::test_describe_reads_the_family_from_the_shape_type[points]",
            f"{T_SCHEMA}::test_describe_reads_the_family_from_the_shape_type[multipoints]",
            f"{T_SCHEMA}::test_describe_reads_the_family_from_the_shape_type[polygons]",
        ),
    ),
    Case(
        "V1",
        "a non-planar type code accepted",
        CODEC,
        (("        if code not in _KINDS:\n", "        if False:\n"),),
        (f"{CODEC_REFUSES}[z]", f"{CODEC_REFUSES}[circular-string]"),
    ),
    Case(
        "V2",
        "a multipolygon member with holes flattened instead of refused",
        CODEC,
        (("            if len(member) > 1:\n", "            if False:\n"),),
        (f"{CODEC_REFUSES}[member-with-hole]",),
    ),
    Case(
        "P1",
        "the value check against the field removed",
        COMPILER,
        (
            (
                "    reason = type_mismatch(value=value, field=field)\n",
                "    reason = None\n",
            ),
        ),
        (f"{REFUSES}[wrong-type]", f"{REFUSES}[long-overflow]"),
    ),
    Case(
        "P2",
        "LIKE allowed on a non-text field",
        COMPILER,
        (
            (
                "            if field.type is not FieldType.TEXT:\n",
                "            if False:\n",
            ),
        ),
        (f"{REFUSES}[like-on-number]",),
    ),
    Case(
        "P3",
        "the empty IsIn compiled as IN ()",
        COMPILER,
        (("            if not values:\n", "            if False:\n"),),
        (f"{CLAUSE}[empty-in]", f"{CLAUSE}[not-empty-in]"),
    ),
    Case(
        "P4",
        "the compiler's literal drops a date's fraction silently",
        COMPILER,
        (
            (
                '        fraction = f".{value.microsecond:06d}" if value.microsecond else ""\n',
                '        fraction = ""\n',
            ),
        ),
        (f"{CLAUSE}[date-with-fraction]",),
    ),
    Case(
        "D5",
        "a date field's precision not read, so no field is a whole-second store",
        SCHEMA,
        (
            (
                "            if field_type is FieldType.DATE and precision == WHOLE_SECOND_PRECISION:\n",
                "            if False:\n",
            ),
        ),
        (
            f"{T_SCHEMA}::test_describe_names_the_date_fields_whose_store_holds_whole_seconds",
        ),
    ),
    Case(
        "W1",
        "a date field added without the migration, so the adapter's own store rounds",
        WRITER,
        (
            (
                "        if field.type is FieldType.DATE:\n",
                "        if False:\n",
            ),
        ),
        (f"{T_WRITER}::test_create_table_adds_every_field_and_migrates_the_date_ones",),
    ),
    Case(
        "S1",
        "select compiles without checking the predicate",
        SELECTION,
        (("        check(where, dataset=dataset)\n", "        pass\n"),),
        tests_in(T_GEOMETRY, "test_a_bad_predicate_is_refused_before_any_tool_runs"),
    ),
    Case(
        "S2",
        "select does not check its paths",
        SELECTION,
        (("        distinct_paths(handles=(input, output))\n", "        pass\n"),),
        tests_in(T_GEOMETRY, "test_select_refuses_an_output_on_the_input_path"),
    ),
    Case(
        "X1",
        "a null shape reaches the tool",
        SHAPE,
        (
            (
                "        _refuse_null_shapes(self._session, path=source)\n",
                "        pass\n",
            ),
        ),
        tests_in(
            T_GEOMETRY,
            "test_explode_refuses_a_null_shape_before_the_tool_whether_or_not_parents_asked",
            "test_an_empty_shape_counts_as_null",
        ),
    ),
    Case(
        "X2",
        "a table input and shared paths accepted",
        SHAPE,
        (
            ("        distinct_paths(handles=handles)\n", "        pass\n"),
            (
                "        if before.schema.data_type is not DataType.FEATURE_CLASS:\n",
                "        if False:\n",
            ),
        ),
        tests_in(T_GEOMETRY, "test_explode_refuses_a_table_and_handles_on_one_path"),
    ),
    Case(
        "X6",
        "an input that already has the reference field accepted",
        SHAPE,
        (
            (
                "        if REFERENCE_FIELD in before.all_fields:\n",
                "        if False:\n",
            ),
        ),
        tests_in(
            T_GEOMETRY,
            "test_explode_refuses_an_input_that_already_has_the_reference_field",
        ),
    ),
    Case(
        "X3",
        "the reference field assumed instead of found: any added field accepted",
        SHAPE,
        (("    if len(added) != 1:\n", "    if not added:\n"),),
        tests_in(T_GEOMETRY, "test_a_tool_that_adds_two_fields_is_an_engine_error"),
    ),
    Case(
        "X4",
        "the output's own engine fields counted as added",
        SHAPE,
        (
            (
                "        if name not in before.all_fields and name not in after.engine_fields\n",
                "        if name not in before.all_fields\n",
            ),
        ),
        tests_in(
            T_GEOMETRY, "test_the_reference_diff_ignores_the_output_engine_fields"
        ),
    ),
    Case(
        "X5",
        "the reference field kept on the output",
        SHAPE,
        (
            (
                "        self._session.run_tool("
                "DELETE_FIELD_TOOL, in_table=target, drop_field=reference)\n",
                "        pass\n",
            ),
        ),
        tests_in(
            T_GEOMETRY,
            "test_explode_without_parents_runs_the_tool_and_drops_the_reference",
        ),
    ),
    Case(
        "R1",
        "read_rows opens the cursor on an unchecked field",
        ROW_IO,
        (("            declared_field(dataset, name)\n", "            pass\n"),),
        (
            f"{T_TABLE}::test_read_rows_refuses_a_field_before_the_cursor_opens[undeclared]",
            f"{T_TABLE}::test_read_rows_refuses_a_field_before_the_cursor_opens[unrepresentable]",
        ),
    ),
    Case(
        "R2",
        "the cursor iterated outside the guard",
        ROW_IO,
        (('    with session.guard("SearchCursor"):\n', "    if True:\n"),),
        (
            f"{T_TABLE}::test_a_cursor_failure_mid_read_leaves_as_an_engine_error",
            f"{T_SCANS}::test_tree_is_clean[adapters-arcpy]",
        ),
    ),
    Case(
        "R3",
        "a whole-second store's encoding noise read through as a fraction",
        ROW_IO,
        (
            (
                "        if whole_second and value.microsecond:\n",
                "        if False:\n",
            ),
        ),
        (
            f"{T_TABLE}::test_a_date_from_a_whole_second_store_is_read_to_its_nearest_second[just-over]",
            f"{T_TABLE}::test_a_date_from_a_whole_second_store_is_read_to_its_nearest_second[just-under]",
        ),
    ),
    Case(
        "R4",
        "a whole-second store's value truncated instead of rounded, a second off",
        ROW_IO,
        (
            (
                "            return (value + _HALF_SECOND).replace(microsecond=0)\n",
                "            return value.replace(microsecond=0)\n",
            ),
        ),
        (
            f"{T_TABLE}::test_a_date_from_a_whole_second_store_is_read_to_its_nearest_second[just-under]",
            f"{T_TABLE}::test_a_date_from_a_whole_second_store_is_read_to_its_nearest_second[over-midnight]",
        ),
    ),
    Case(
        "C1",
        "the record leaves out a method the adapter honours parents for",
        ROOT_INIT,
        (
            (
                "frozenset({GeometryOps.explode_multipart})",
                "frozenset[PortMethod]()",
            ),
            (
                "from ag.ports.capabilities import AdapterCapabilities\n",
                "from ag.ports.capabilities import AdapterCapabilities, PortMethod\n",
            ),
        ),
        (
            f"{T_CAPABILITIES}::"
            "test_the_record_names_every_mint_method_the_adapter_implements_and_no_other[arcpy]",
        ),
    ),
)

SUITE: tuple[str, ...] = ("tests/unit/adapters/arcpy", "tests/static")
