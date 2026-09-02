"""TEMPLATE — not shipped. Target: `tests/unit/`.

how an operation is tested.

THIS IS THE DESIGN'S STRONGEST INTERNAL SELLING POINT and it fits on a page. An
operation takes ScratchHandles, which implement __fspath__, so a test materializes
them against a local directory of gdbs and calls the function directly.

    no cluster, no credentials, no plan, no orchestrator, no partition, no run id,
    no mocking of a file manager, no arcpy monkeypatching

That is not a happy accident of the test setup - it is the whole reason an operation
is forbidden from seeing a DataObject, a URI, a client, a partition index or a
context radius. Everything an operation needs arrives as an argument.

RUN IT: pytest test_example_road_operations.py

The arcpy-dependent test is skipped without arcpy, so the declaration tests - which
are the ones that catch a broken pipeline module - run in CI on any machine.
"""

from __future__ import annotations

import importlib.util
import posixpath
from dataclasses import replace

import pytest

import ag.pipelines.road.n100 as pipeline
from ag.core.types import DataType
from ag.operations.road import ThinRoadConfig, thin_road_network
from ag.core.operations import ScratchHandle, ScratchScope

# ---------------------------------------------------------------------------
# The fake workspace: nine lines, and it is the whole harness
# ---------------------------------------------------------------------------


def local_scope(root: str) -> ScratchScope:
    """A ScratchScope backed by a plain directory instead of a ScratchFileManager.

    The real manager adds workspaces, a name budget and a collision manifest. None of
    that is what an operation depends on - it depends on getting a handle whose
    __fspath__ returns a path - so a test can supply the two-line version.
    """

    def materialize(
        trail: tuple[str, ...], leaf: str, data_type: DataType
    ) -> ScratchHandle:
        name = "__".join((*trail, leaf))
        return ScratchHandle(name=name, data_type=data_type).materialize(
            posixpath.join(root, f"{name}.shp")
        )

    return ScratchScope(trail=(), materialize=materialize)


def local(handle: ScratchHandle, root: str) -> ScratchHandle:
    """Point a DECLARED handle at a local file. The stage entry point's job, done by
    hand in three lines because that is all it is."""
    return handle.materialize(posixpath.join(root, f"{handle.name}.shp"))


# ---------------------------------------------------------------------------
# Declaration tests - no arcpy, no filesystem, run everywhere
# ---------------------------------------------------------------------------


def test_declaration_records_the_signature() -> None:
    """Calling a decorated operation builds an OperationCall from its signature.

    This is what CI evaluates to build the dependency graph, so it must be safe with
    no data and no arcpy: the wrapper never touches the function body.
    """
    call = thin_road_network(
        roads=pipeline.Network.merged,
        ranks=pipeline.Network.ranks,
        merge_report=pipeline.Network.merge_report,
        output=pipeline.Network.thinned,
        dropped=pipeline.Network.dropped,
        config=ThinRoadConfig(
            minimum_length_m=400.0, weights=pipeline.tuning.NETWORK_WEIGHTS
        ),
    )
    assert call.operation == "thin_road_network"
    assert set(call.inputs) == {"roads", "ranks", "merge_report"}
    assert set(call.outputs) == {"output", "dropped"}
    assert set(call.parameters) == {"config"}
    assert call.wants_scratch is True


def test_a_misspelled_keyword_fails_at_declaration() -> None:
    """The failure this whole mechanism exists to move earlier.

    Before @operation the parameter name was retyped as a dict key in a hand-written
    factory, so a rename produced `TypeError: unexpected keyword argument` inside a
    pod, after fan-out had already moved the data. Now it fails while the pipeline
    module is being imported - and pyright flags it before that.
    """
    with pytest.raises(TypeError, match="roads"):
        thin_road_network(
            road=pipeline.Network.merged,  # pyright: ignore[reportCallIssue]
            output=pipeline.Network.thinned,
        )


def test_an_undeclared_handle_is_rejected() -> None:
    """handle() outside a class body has no name, and would render a path ending in
    a separator. Rejected at the choke point rather than discovered as a bad path."""
    from ag.core.operations import handle

    with pytest.raises(TypeError, match="undeclared handle"):
        thin_road_network(
            roads=handle(),
            ranks=pipeline.Network.ranks,
            merge_report=pipeline.Network.merge_report,
            output=pipeline.Network.thinned,
            dropped=pipeline.Network.dropped,
            config=pipeline.tuning.THIN_ROAD,
        )


def test_a_scratch_scope_may_not_be_passed_at_declaration() -> None:
    with pytest.raises(TypeError, match="declaration site"):
        thin_road_network(
            roads=pipeline.Network.merged,
            ranks=pipeline.Network.ranks,
            merge_report=pipeline.Network.merge_report,
            output=pipeline.Network.thinned,
            dropped=pipeline.Network.dropped,
            config=pipeline.tuning.THIN_ROAD,
            scratch=local_scope("/tmp"),
        )


def test_config_validates_itself() -> None:
    """__post_init__ on a frozen config is the first place in the design with
    anywhere to put a constraint on a VALUE."""
    with pytest.raises(ValueError, match="minimum_length_m"):
        replace(pipeline.tuning.THIN_ROAD, minimum_length_m=-1.0)


# ---------------------------------------------------------------------------
# The real thing - one operation, one local workspace
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    importlib.util.find_spec("arcpy") is None, reason="arcpy not installed"
)
def test_thin_road_network_against_local_gdbs(tmp_path: object) -> None:
    """The shape of every operation test in the project.

    Three lines of setup, one call, assertions on the outputs. Note what is NOT
    here: no RunPlan, no PinnedInput, no ScratchFileManager, no ArchiveClient, no
    partition index, no Kubernetes. The operation cannot tell this from a pod.
    """
    root = str(tmp_path)
    call = thin_road_network(
        roads=pipeline.Network.merged,
        ranks=pipeline.Network.ranks,
        merge_report=pipeline.Network.merge_report,
        output=pipeline.Network.thinned,
        dropped=pipeline.Network.dropped,
        config=pipeline.tuning.THIN_ROAD,
    )
    call.fn(
        roads=local(pipeline.Network.merged, root),
        ranks=local(pipeline.Network.ranks, root),
        merge_report=local(pipeline.Network.merge_report, root),
        output=local(pipeline.Network.thinned, root),
        dropped=local(pipeline.Network.dropped, root),
        config=pipeline.tuning.THIN_ROAD,
        scratch=local_scope(root),
    )
    # assert on the two outputs: feature counts, that every dropped segment is absent
    # from output, that no segment appears in both.
