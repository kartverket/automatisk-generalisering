"""The ArcPy session on a fake engine: construction, `run_tool` and `guard`.

What: the environment is applied once on construction and a failure there is an
`EngineError`; a tool resolves by dotted name and passes keyword arguments and its result
through; a tool failure and a guarded engine failure leave as `EngineError` from the
original, with the tool and its messages; the buffer is drained on the vendor class only;
an `AgError`, an adapter defect and a `RuntimeError` subclass pass through (ADR-0018
AR-D23). Blank message lines are dropped on both paths.

How: `FakeEngine` subclasses `ModuleType`, as the real engine is one, declaring the names
the session resolves on it. No test here is marked: nothing touches ArcPy.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from types import ModuleType, SimpleNamespace

import pytest

from ag.adapters.arcpy.session import ENVIRONMENT, ArcpySession
from ag.core.errors import AgError
from ag.ports.errors import EngineError, PortContractError

LOGGER = "ag.adapters.arcpy.session"


class FakeExecuteError(Exception):
    """Stands in for `arcpy.ExecuteError`."""


class FakeResult:
    """Stands in for the engine's result object."""

    def __init__(self, messages: str) -> None:
        self._messages = messages

    def getMessages(self) -> str:
        return self._messages


class RefusingEnv:
    """An `env` whose every assignment fails as the engine's exact `RuntimeError`."""

    def __setattr__(self, name: str, value: object) -> None:
        raise RuntimeError(f"refused {name}")


class FakeEngine(ModuleType):
    """The names the session resolves on the engine, plus what each test inspects."""

    env: object
    ExecuteError: type[Exception]
    buffer: str
    reads: int
    spatial_references: list[int]

    def __init__(
        self,
        *,
        tools: Mapping[str, object] | None = None,
        buffer: str = "",
        env: object | None = None,
    ) -> None:
        super().__init__("arcpy")
        self.env = SimpleNamespace() if env is None else env
        self.ExecuteError = FakeExecuteError
        self.buffer = buffer
        self.reads = 0
        self.spatial_references = []
        for name, namespace in (tools or {}).items():
            setattr(self, name, namespace)

    def GetMessages(self) -> str:
        self.reads += 1
        return self.buffer

    def SpatialReference(self, epsg: int) -> tuple[str, int]:
        self.spatial_references.append(epsg)
        return ("sr", epsg)


class Delete:
    """A tool that records its keyword arguments and returns, or raises, as scripted."""

    def __init__(self, *, result: FakeResult, raises: Exception | None = None) -> None:
        self.calls: list[dict[str, object]] = []
        self._result = result
        self._raises = raises

    def __call__(self, *, in_data: str) -> FakeResult:
        self.calls.append({"in_data": in_data})
        if self._raises is not None:
            raise self._raises
        return self._result


def engine_with(delete: Delete, *, buffer: str = "") -> FakeEngine:
    return FakeEngine(
        tools={"management": SimpleNamespace(Delete=delete)}, buffer=buffer
    )


def test_construction_applies_the_environment_once() -> None:
    env = SimpleNamespace()
    engine = FakeEngine(env=env)

    session = ArcpySession(engine=engine)

    assert session.environment is ENVIRONMENT
    assert env.overwriteOutput is True
    assert env.outputCoordinateSystem == ("sr", 25833)
    assert env.XYTolerance == "0.1 Meters"
    assert env.XYResolution == "0.01 Meters"
    assert engine.spatial_references == [25833]


def test_an_environment_failure_on_construction_is_an_engine_error() -> None:
    engine = FakeEngine(env=RefusingEnv(), buffer="stale")

    with pytest.raises(EngineError) as info:
        ArcpySession(engine=engine)

    assert info.value.context.tool == "environment"
    assert info.value.context.tool_messages == ("refused overwriteOutput",)
    assert isinstance(info.value.__cause__, RuntimeError)
    assert engine.reads == 0


def test_a_dotted_name_resolves_and_keyword_arguments_and_result_pass_through() -> None:
    expected = FakeResult("Done")
    delete = Delete(result=expected)
    session = ArcpySession(engine=engine_with(delete))

    result = session.run_tool("management.Delete", in_data="x")

    assert result is expected
    assert delete.calls == [{"in_data": "x"}]


def test_a_successful_tool_logs_its_own_messages(
    caplog: pytest.LogCaptureFixture,
) -> None:
    delete = Delete(result=FakeResult("Start\n\nDone\n"))
    session = ArcpySession(engine=engine_with(delete, buffer="stale"))
    caplog.set_level(logging.DEBUG, logger=LOGGER)

    session.run_tool("management.Delete", in_data="x")

    assert "management.Delete: ('Start', 'Done')" in caplog.text
    assert "stale" not in caplog.text


def test_a_vendor_failure_from_a_tool_is_an_engine_error_from_the_original() -> None:
    failure = FakeExecuteError("boom")
    delete = Delete(result=FakeResult(""), raises=failure)
    session = ArcpySession(engine=engine_with(delete))

    with pytest.raises(EngineError) as info:
        session.run_tool("management.Delete", in_data="x")

    assert info.value.__cause__ is failure


def test_a_tool_failure_carries_the_tool_and_the_drained_lines() -> None:
    delete = Delete(result=FakeResult(""), raises=FakeExecuteError("boom"))
    engine = engine_with(delete, buffer="ERROR 000732: x\n\nFailed\n")
    session = ArcpySession(engine=engine)

    with pytest.raises(EngineError) as info:
        session.run_tool("management.Delete", in_data="x")

    assert str(info.value) == "arcpy: management.Delete failed: boom"
    assert info.value.context.tool == "management.Delete"
    assert info.value.context.tool_messages == ("boom", "ERROR 000732: x", "Failed")


def test_a_misspelt_tool_raises_attribute_error() -> None:
    delete = Delete(result=FakeResult(""))
    session = ArcpySession(engine=engine_with(delete))

    with pytest.raises(AttributeError):
        session.run_tool("management.Delet", in_data="x")
    with pytest.raises(AttributeError):
        session.run_tool("managment.Delete", in_data="x")
    assert delete.calls == []


def test_a_misspelt_keyword_raises_type_error_unwrapped() -> None:
    delete = Delete(result=FakeResult(""))
    engine = engine_with(delete, buffer="stale")
    session = ArcpySession(engine=engine)

    with pytest.raises(TypeError):
        session.run_tool("management.Delete", in_dat="x")

    assert delete.calls == []
    assert engine.reads == 0


def test_a_vendor_failure_in_the_guard_is_an_engine_error_from_the_original() -> None:
    session = ArcpySession(engine=FakeEngine(buffer="cursor said\n"))
    failure = FakeExecuteError("bad")

    with pytest.raises(EngineError) as info:
        with session.guard("cursor"):
            raise failure

    assert info.value.__cause__ is failure
    assert info.value.context.tool == "cursor"
    assert info.value.context.tool_messages == ("bad", "cursor said")


def test_a_runtime_error_inside_the_guard_carries_no_stale_buffer() -> None:
    engine = FakeEngine(buffer="stale")
    session = ArcpySession(engine=engine)

    with pytest.raises(EngineError) as info:
        with session.guard("cursor"):
            raise RuntimeError("locked")

    assert info.value.context.tool_messages == ("locked",)
    assert engine.reads == 0


def test_an_ag_error_inside_the_guard_passes_through() -> None:
    session = ArcpySession(engine=FakeEngine())
    error = PortContractError("unknown field")

    with pytest.raises(AgError) as info:
        with session.guard("cursor"):
            raise error

    assert info.value is error


def test_an_adapter_defect_inside_the_guard_passes_through() -> None:
    session = ArcpySession(engine=FakeEngine())

    with pytest.raises(KeyError):
        with session.guard("cursor"):
            raise KeyError("shape")


def test_a_runtime_error_subclass_inside_the_guard_passes_through() -> None:
    session = ArcpySession(engine=FakeEngine())

    with pytest.raises(NotImplementedError):
        with session.guard("cursor"):
            raise NotImplementedError("later")
