"""Cases for the ADR citation check, `tests/static/test_adr_citations.py`: a number with
no ADR, an id missing from its ADR, a retired number, and an ADR body citing a staging id.
"""

from __future__ import annotations

from ..engine import Case, tests_in

COLUMNS = "src/ag/ports/columns.py"
ADR_ARCHITECTURE = "docs/decisions/0018-architecture.md"
T_CITATIONS = "tests/static/test_adr_citations.py"

CITATION = "the port's native indices at the port; the layer above maps them to ids. ADR-0017 RS-6.\n"

CASES: tuple[Case, ...] = (
    Case(
        "C1",
        "a citation to a number with no ADR",
        COLUMNS,
        ((CITATION, CITATION.replace("ADR-0017", "ADR-0099")),),
        tests_in(T_CITATIONS, "test_rule_holds[number-resolves]"),
    ),
    Case(
        "C2",
        "an id missing from its ADR",
        COLUMNS,
        ((CITATION, CITATION.replace("RS-6", "RS-D99")),),
        tests_in(T_CITATIONS, "test_rule_holds[id-exists]"),
    ),
    Case(
        "C3",
        "a retired number cited",
        COLUMNS,
        ((CITATION, CITATION.replace("ADR-0017", "ADR-0016")),),
        tests_in(T_CITATIONS, "test_rule_holds[no-retired-number]"),
    ),
    Case(
        "C4",
        "an ADR body cites a staging id",
        ADR_ARCHITECTURE,
        (("- **AR-D3** Fakes over mocks:", "- **AR-D3** Fakes over mocks (A1.3):"),),
        tests_in(T_CITATIONS, "test_rule_holds[body-cites-no-staging-id]"),
    ),
)

SUITE: tuple[str, ...] = (T_CITATIONS,)
