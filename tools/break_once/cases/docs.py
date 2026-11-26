"""Cases for the user guides: `tests/unit/docs/test_scratch_user_guide.py` holds the page
`docs/user_guide/scratch.md` to the code it documents, so each way the two can part is
broken once here: a rendered name, an error message, a sample block, and the links the
page and the modules carry to each other.
"""

from __future__ import annotations

from ..engine import Case, tests_in

SCRATCH = "src/ag/staging/scratch.py"
HANDLES = "src/ag/core/handles.py"
SAMPLES = "tests/unit/docs/scratch_samples.py"
T_GUIDE = "tests/unit/docs/test_scratch_user_guide.py"

CASES: tuple[Case, ...] = (
    Case(
        "D1",
        "a workspace name the page shows no longer matches what the code renders",
        SCRATCH,
        (('STEM_SEPARATOR = "__"', 'STEM_SEPARATOR = "_"'),),
        tests_in(T_GUIDE, "test_the_layout_is_as_shown"),
    ),
    Case(
        "D2",
        "a layer name the page shows no longer matches what the code renders",
        HANDLES,
        (
            (
                '            segment = f"{key}_{count}"',
                '            segment = f"{key}{count}"',
            ),
        ),
        tests_in(T_GUIDE, "test_a_naming_case_renders_the_names_shown[case_suffix]"),
    ),
    Case(
        "D3",
        "an error message in the source no longer matches the page's block",
        SCRATCH,
        (
            (
                'raise StagingError(f"call identity {call!r} is given twice.")',
                'raise StagingError(f"call identity {call!r} is given twice")',
            ),
        ),
        tests_in(
            T_GUIDE,
            "test_an_error_sample_raises_the_message_shown[error_repeated_call]",
        ),
    ),
    Case(
        "D4",
        "a sample block on the page no longer equals its block in the samples module",
        SAMPLES,
        (
            (
                '    singlepart = scratch("singlepart")\n'
                "    tb.geometry.explode_multipart(input=source, output=singlepart)",
                '    singlepart = scratch("single_part")\n'
                "    tb.geometry.explode_multipart(input=source, output=singlepart)",
            ),
        ),
        tests_in(T_GUIDE, "test_every_sample_block_is_on_the_page_and_equal"),
    ),
    Case(
        "D5",
        "a documented module no longer names the page",
        HANDLES,
        (
            (
                "developer's guide to scratch is `docs/user_guide/scratch.md`;",
                "developer's guide to scratch is the user guide;",
            ),
        ),
        tests_in(T_GUIDE, "test_the_page_and_the_modules_name_each_other"),
    ),
)

SUITE: tuple[str, ...] = ("tests/unit/docs",)
