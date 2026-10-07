"""Cases for the port values: `ports/attributes.py`, `ports/geometry.py`,
`ports/table_ops.py`, `ports/predicates.py`, `ports/toolbox.py`, and the pinned count of
`Attr.raw` call sites.
"""

from __future__ import annotations

from ..engine import Case, tests_in

ATTRIBUTES = "src/ag/ports/attributes.py"
GEOMETRY = "src/ag/ports/geometry.py"
TABLE = "src/ag/ports/table_ops.py"
PREDICATES = "src/ag/ports/predicates.py"
TOOLBOX = "src/ag/ports/toolbox.py"
T_PRED = "tests/unit/ports/test_predicates.py"
T_GEOM = "tests/unit/ports/test_geometry.py"
T_TABLE = "tests/unit/ports/test_table_values.py"
T_TOOLBOX = "tests/unit/ports/test_toolbox.py"
T_RAW = "tests/static/test_attr_raw_count.py"

CASES: tuple[Case, ...] = (
    Case(
        "P1",
        "TEXT field accepted without a length",
        ATTRIBUTES,
        (
            (
                "        if self.type is FieldType.TEXT and self.length is None:",
                "        if False:",
            ),
        ),
        tests_in(
            T_TABLE, "test_a_text_field_needs_a_length_and_no_other_type_takes_one"
        ),
    ),
    Case(
        "P2",
        "non-TEXT field accepted with a length",
        ATTRIBUTES,
        (
            (
                "        if self.type is not FieldType.TEXT and self.length is not None:",
                "        if False:",
            ),
        ),
        tests_in(
            T_TABLE, "test_a_text_field_needs_a_length_and_no_other_type_takes_one"
        ),
    ),
    Case(
        "P3",
        "feature class schema accepted without a CRS",
        TABLE,
        (
            (
                "        if self.data_type is DataType.FEATURE_CLASS and self.geometry_crs is None:",
                "        if False:",
            ),
        ),
        tests_in(
            T_TABLE, "test_a_feature_class_schema_needs_a_crs_and_a_table_does_not"
        ),
    ),
    Case(
        "P4",
        "Row without slots",
        TABLE,
        (
            (
                "@dataclass(frozen=True, slots=True)\nclass Row:",
                "@dataclass(frozen=True)\nclass Row:",
            ),
        ),
        tests_in(T_TABLE, "test_a_row_is_frozen_and_uses_slots"),
    ),
    Case(
        "P5",
        "empty geometry accepted",
        GEOMETRY,
        (("        if not self.parts:", "        if False:"),),
        tests_in(T_GEOM, "test_an_empty_geometry_is_refused"),
    ),
    Case(
        "P6",
        "multi-coordinate point accepted",
        GEOMETRY,
        (
            (
                "        if self.kind is GeometryKind.POINT and (",
                "        if False and (",
            ),
        ),
        tests_in(T_GEOM, "test_a_point_is_exactly_one_coordinate"),
    ),
    Case(
        "P7",
        "comparison with NULL accepted",
        PREDICATES,
        (("        if self.value is None:", "        if False:"),),
        tests_in(T_PRED, "test_cmp_refuses_a_null_value"),
    ),
    Case(
        "P8",
        "NULL member of an IN set accepted",
        PREDICATES,
        (
            (
                "        if any(value is None for value in self.values):",
                "        if False:",
            ),
        ),
        tests_in(T_PRED, "test_in_refuses_a_null_member"),
    ),
    Case(
        "P9",
        "DWITHIN accepted without a distance",
        PREDICATES,
        (
            (
                "        if needs_distance and self.distance_m is None:",
                "        if False:",
            ),
        ),
        tests_in(T_PRED, "test_dwithin_carries_its_distance_and_the_others_refuse_one"),
    ),
    Case(
        "P10",
        "a distance accepted on a non-distance relation",
        PREDICATES,
        (
            (
                "        if not needs_distance and self.distance_m is not None:",
                "        if False:",
            ),
        ),
        tests_in(T_PRED, "test_dwithin_carries_its_distance_and_the_others_refuse_one"),
    ),
    Case(
        "P11",
        "the invert operator simplifies a double negation",
        PREDICATES,
        (
            (
                "    def __invert__(self) -> Predicate:\n        return Not(self)",
                "    def __invert__(self) -> Predicate:\n"
                "        return self.term if isinstance(self, Not) else Not(self)",
            ),
        ),
        tests_in(T_PRED, "test_the_operators_build_a_tree_and_fold_nothing"),
    ),
    Case(
        "P12",
        "the sentinel reaches a port silently",
        TOOLBOX,
        (
            (
                "    def __getattr__(self, name: str) -> object:\n        raise InjectionError(",
                "    def __getattr__(self, name: str) -> object:\n        return None\n        raise InjectionError(",
            ),
        ),
        tests_in(T_TOOLBOX, "test_the_sentinel_is_a_toolbox_that_refuses_every_port"),
    ),
    Case(
        "P13",
        "an Attr.raw call site added without touching the pin",
        PREDICATES,
        (("", '\n\n_UNPINNED = Attr.raw("1=1")\n'),),
        tests_in(T_RAW, "test_attr_raw_call_sites_are_pinned"),
    ),
)

SUITE: tuple[str, ...] = ("tests/unit/ports", "tests/static")
