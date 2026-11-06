"""What `dataset_schema.py` expects of the engine beyond what the conformance round trip
pins: the class Describe raises for a path that does not exist. The type names of the
five field types, the empty length and area names, and the `dataType` strings are pinned
by the conformance suite's round trips and the memory-workspace module. ADR-0018 AR-D23.
"""

from __future__ import annotations

import pytest

from ag.adapters.arcpy.support.dataset_schema import describe
from ag.ports.errors import EngineError
from tests.engine.arcpy.conftest import Pro

pytestmark = pytest.mark.arcpy


def test_describe_of_a_missing_dataset_is_an_engine_error(pro: Pro) -> None:
    with pytest.raises(EngineError) as caught:
        describe(pro.session, pro.path("no_such_dataset"))
    assert caught.value.context.tool == "Describe"
