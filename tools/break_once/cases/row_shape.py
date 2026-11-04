"""Cases for the row-shape grammar: `ports/row_shape.py`, the three Protocol methods,
the check over the surface, the typing guard on the decorator, and row 5 of
`.importlinter` for the two new modules.
"""

from __future__ import annotations

from ..engine import Case, tests_in

ROW_SHAPE = "src/ag/ports/row_shape.py"
GEOMETRY_OPS = "src/ag/ports/geometry_ops.py"
COLUMNS = "src/ag/ports/columns.py"
T_UNIT = "tests/unit/ports/test_row_shape.py"
T_STATIC = "tests/static/test_row_shape.py"
T_TYPING = "tests/static/test_row_shape_typing.py"
T_CONTRACTS = "tests/static/test_import_contracts.py"
ROW_5 = f"{T_CONTRACTS}::test_contract_is_kept[row-05-port-layers]"

SELECT_ROW = (
    '    @row_shape(output=Rows(Cardinality.ONE, Ids.CARRY, subject="input"))\n'
)
EXPLODE_ROW = (
    '    @row_shape(output=Rows(Cardinality.MANY, Ids.MINT, subject="input"))\n'
)
HANDLES_IMPORT = "from ag.core.handles import In, Out, ParentsOut\n"

CASES: tuple[Case, ...] = (
    Case(
        "R1",
        "GROUP + CARRY and GROUP + FOREIGN accepted",
        ROW_SHAPE,
        (
            (
                "        if self.cardinality is Cardinality.GROUP and self.ids is not Ids.MINT:",
                "        if False:",
            ),
        ),
        tests_in(
            T_UNIT,
            "test_group_with_carry_or_foreign_is_refused_because_a_scalar_cannot_hold_a_set",
        ),
    ),
    Case(
        "R2",
        "MANY + CARRY accepted",
        ROW_SHAPE,
        (
            (
                "        if self.cardinality is Cardinality.MANY and self.ids is Ids.CARRY:",
                "        if False:",
            ),
        ),
        tests_in(T_UNIT, "test_many_with_carry_is_refused_as_the_inheritance_model"),
    ),
    Case(
        "R3",
        "CARRY or MINT accepted without a subject",
        ROW_SHAPE,
        (("            if self.subject is None:", "            if False:"),),
        tests_in(T_UNIT, "test_carry_and_mint_need_a_subject_and_take_no_refs"),
    ),
    Case(
        "R4",
        "CARRY or MINT accepted with refs",
        ROW_SHAPE,
        (
            (
                "            if self.refs:\n                raise ValueError(\n"
                '                    f"a {self.ids.name} output carries',
                "            if False:\n                raise ValueError(\n"
                '                    f"a {self.ids.name} output carries',
            ),
        ),
        tests_in(T_UNIT, "test_carry_and_mint_need_a_subject_and_take_no_refs"),
    ),
    Case(
        "R5",
        "FOREIGN accepted without refs",
        ROW_SHAPE,
        (("            if not self.refs:", "            if False:"),),
        tests_in(T_UNIT, "test_foreign_needs_refs_and_has_no_subject"),
    ),
    Case(
        "R6",
        "FOREIGN accepted with a subject",
        ROW_SHAPE,
        (("            if self.subject is not None:", "            if False:"),),
        tests_in(T_UNIT, "test_foreign_needs_refs_and_has_no_subject"),
    ),
    Case(
        "R7",
        "an axis given a default",
        ROW_SHAPE,
        (("    ids: Ids\n", "    ids: Ids = Ids.CARRY\n"),),
        tests_in(T_UNIT, "test_both_axes_are_required"),
    ),
    Case(
        "R8",
        "the decorator returns a plain wrapper instead of the function",
        ROW_SHAPE,
        (
            (
                "from typing import Any, TypeVar\n",
                "from typing import Any, TypeVar, cast\n",
            ),
            (
                '        setattr(fn, "__row_shape__", MappingProxyType(dict(outputs)))\n'
                "        return fn\n",
                "        def wrapper(*args: Any, **kwargs: Any) -> Any:\n"
                "            return fn(*args, **kwargs)\n\n"
                '        setattr(wrapper, "__row_shape__", MappingProxyType(dict(outputs)))\n'
                "        return cast(F, wrapper)\n",
            ),
        ),
        tests_in(T_UNIT, "test_the_decorator_leaves_signature_and_hints_unchanged"),
    ),
    Case(
        "R9",
        "the decorator returns a functools.wraps wrapper instead of the function",
        ROW_SHAPE,
        (
            (
                "from __future__ import annotations\n\n",
                "from __future__ import annotations\n\nimport functools\n",
            ),
            (
                "from typing import Any, TypeVar\n",
                "from typing import Any, TypeVar, cast\n",
            ),
            (
                '        setattr(fn, "__row_shape__", MappingProxyType(dict(outputs)))\n'
                "        return fn\n",
                "        @functools.wraps(fn)\n"
                "        def wrapper(*args: Any, **kwargs: Any) -> Any:\n"
                "            return fn(*args, **kwargs)\n\n"
                '        setattr(wrapper, "__row_shape__", MappingProxyType(dict(outputs)))\n'
                "        return cast(F, wrapper)\n",
            ),
        ),
        tests_in(T_UNIT, "test_the_decorator_returns_the_function_itself"),
    ),
    Case(
        "R10",
        "the decorator erases the method's type",
        ROW_SHAPE,
        (
            (
                "def row_shape(**outputs: Rows) -> Callable[[F], F]:",
                "def row_shape(**outputs: Rows) -> Callable[[Any], Any]:",
            ),
            ("    def attach(fn: F) -> F:", "    def attach(fn: Any) -> Any:"),
        ),
        tests_in(T_TYPING, "test_the_decorated_protocol_still_refuses_a_non_conformer"),
    ),
    Case(
        "R11",
        "an Out with no row",
        GEOMETRY_OPS,
        ((SELECT_ROW, ""),),
        (f"{T_STATIC}::test_rule_holds[out-without-row]",),
    ),
    Case(
        "R12",
        "a row naming the ParentsOut parameter instead of the Out",
        GEOMETRY_OPS,
        ((EXPLODE_ROW, EXPLODE_ROW.replace("output=", "parents=")),),
        (f"{T_STATIC}::test_rule_holds[row-names-non-out]",),
    ),
    Case(
        "R13",
        "a subject naming a parameter that is not an In",
        GEOMETRY_OPS,
        ((SELECT_ROW, SELECT_ROW.replace('subject="input"', 'subject="where"')),),
        (f"{T_STATIC}::test_rule_holds[input-names-non-in]",),
    ),
    Case(
        "R14",
        "an output annotated as a bare ScratchHandle",
        GEOMETRY_OPS,
        (
            (
                HANDLES_IMPORT,
                "from ag.core.handles import In, Out, ParentsOut, ScratchHandle\n",
            ),
            (
                "    def select(self, *, input: In, where: Predicate, output: Out) -> None:",
                "    def select(\n"
                "        self, *, input: In, where: Predicate, output: ScratchHandle\n"
                "    ) -> None:",
            ),
        ),
        (f"{T_STATIC}::test_rule_holds[unmarked-handle]",),
    ),
    Case(
        "R15",
        "a method with no Out that is not in the query list",
        GEOMETRY_OPS,
        (
            (
                "",
                "\n\nclass Probe(Protocol):  # probe\n"
                "    def count(self, *, input: In) -> int: ...\n",
            ),
        ),
        (f"{T_STATIC}::test_rule_holds[unlisted-query]",),
    ),
    Case(
        "R16",
        "a Mutates parameter on the surface",
        GEOMETRY_OPS,
        (
            (
                "",
                "\n\nfrom ag.core.handles import Mutates  # probe\n\n\n"
                "class Probe(Protocol):  # probe\n"
                "    def touch(self, *, input: Mutates) -> None: ...\n",
            ),
        ),
        (f"{T_STATIC}::test_rule_holds[mutates-fails-closed]",),
    ),
    Case(
        "R17",
        "row 5: columns imports its sibling predicates",
        COLUMNS,
        (("", "\nimport ag.ports.predicates  # probe\n"),),
        (ROW_5,),
    ),
)

SUITE: tuple[str, ...] = ("tests/unit/ports", "tests/static")
