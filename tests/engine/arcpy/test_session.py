"""What `session.py` expects of the engine: the catch set, the drain rule and the
environment read back. ADR-0018 AR-D23, ADR-0021 ST-D25.

What: a misspelt keyword after a successful tool is a `TypeError` left unwrapped; a tool
failure after a success carries its own lines and not the earlier tool's; the
environment reads back as `ENVIRONMENT`; a cursor on a missing field or a bad clause
fails inside the guard as an exact `RuntimeError`, so the guard wraps it. An exception
of another class leaves unwrapped, and the failure then shows its type. A write cursor on
a dataset another cursor holds was tried as W3's provocation and succeeded on the engine,
so no test holds it: no `RuntimeError` after engine work has been found.
"""

from __future__ import annotations

import pytest

from ag.adapters.arcpy.session import ENVIRONMENT
from ag.adapters.arcpy.support.dataset_schema import OID_TOKEN
from ag.ports.errors import EngineError
from tests.engine.arcpy.conftest import Pro
from tests.support.cases import roads

pytestmark = pytest.mark.arcpy


def test_a_misspelt_keyword_after_a_successful_tool_is_a_type_error_unwrapped(
    pro: Pro,
) -> None:
    pro.session.run_tool(
        "management.CreateTable", out_path=pro.workspace, out_name="first_table"
    )
    with pytest.raises(TypeError):
        pro.session.run_tool(
            "management.CreateTable", out_pth=pro.workspace, out_name="second_table"
        )


def test_a_tool_failure_after_a_success_carries_its_own_messages(pro: Pro) -> None:
    pro.session.run_tool(
        "management.CreateTable", out_path=pro.workspace, out_name="first_table"
    )
    with pytest.raises(EngineError) as caught:
        pro.session.run_tool(
            "management.CreateTable",
            out_path=pro.path("no_such_workspace.gdb"),
            out_name="second_table",
        )
    assert caught.value.context.tool == "management.CreateTable"
    messages = caught.value.context.tool_messages
    assert any("ERROR" in line for line in messages), messages
    assert not any("first_table" in line for line in messages), messages


def test_the_environment_reads_back_as_applied(pro: Pro) -> None:
    assert pro.session.read_environment() == ENVIRONMENT


def test_a_cursor_on_a_missing_field_is_an_engine_error_from_an_exact_runtime_error(
    pro: Pro,
) -> None:
    seeded = pro.seed(roads())
    with pytest.raises(EngineError) as caught:
        pro.read_cells(path=str(seeded.handle.path), tokens=("no_such_field",))
    assert caught.value.context.tool == "SearchCursor"
    assert type(caught.value.__cause__) is RuntimeError, type(caught.value.__cause__)


def test_a_cursor_with_a_bad_where_clause_is_an_engine_error_from_an_exact_runtime_error(
    pro: Pro,
) -> None:
    seeded = pro.seed(roads())
    with pytest.raises(EngineError) as caught:
        pro.read_cells(
            path=str(seeded.handle.path),
            tokens=(OID_TOKEN,),
            where='"no_such_field" = 1',
        )
    assert type(caught.value.__cause__) is RuntimeError, type(caught.value.__cause__)
