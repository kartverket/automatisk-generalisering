"""The fake engine, installed as `arcpy` for each test and handed to the session.

The group modules import `arcpy` inside the function that reaches the engine, so a
fake placed in `sys.modules` for the test's duration is what they find, and the session
built on the same object is what they call tools through. No test here is marked.
"""

from __future__ import annotations

import sys

import pytest

from ag.adapters.arcpy.session import ArcpySession
from tests.support.fake_arcpy import FakeEngine


@pytest.fixture
def engine(monkeypatch: pytest.MonkeyPatch) -> FakeEngine:
    fake = FakeEngine()
    monkeypatch.setitem(sys.modules, "arcpy", fake)
    return fake


@pytest.fixture
def session(engine: FakeEngine) -> ArcpySession:
    return ArcpySession(engine=engine)
