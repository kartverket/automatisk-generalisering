"""TEMPLATE — not shipped. Target module: `src/ag/ports/graph_ops.py`.

Graph algorithms over abstract topology. ~8 methods. Wraps networkx.

Q-C IS STILL OPEN. THIS FILE IS ONE CANDIDATE ANSWER, NOT THE ANSWER.

The question (03-architecture §9): does `GraphOps` know about datasets? Either graph
construction is a `GraphOps` method taking a `ScratchHandle`, or it is a helper that
calls `read_rows` and hands plain edges to a pure `GraphOps`. The document prefers the
second and asks for confirmation against the strahler code first.

This port takes the second form. Nothing here mentions a `ScratchHandle`, a workspace
or a geometry - it is edges in, structure out. Two properties follow, and they are
what the eventual confirmation is against:

  the adapter is a THIN networkx wrapper with no IO, so it is testable with tuples
  and its contract suite needs no fixtures at all.

  reading the dataset is somebody else's job. A helper does `read_rows`, builds the
  edge list, calls this, and writes the result back - so the "which fields are the
  node ids" question stays in the domain layer where the answer is known, rather
  than becoming a port parameter every adapter has to honour.

WHY IT IS NOT CLOSED, STATED PLAINLY SO IT DOES NOT BECOME SETTLED-BY-IMPLEMENTATION.
The worked pipelines exercise this port from exactly ONE call site - `_build_topology`
in `operations/road`, called twice - reaching TWO of the six methods below. One caller
is not evidence about a port's shape; it is evidence that one caller was writable. And
the evidence 03-architecture §9 actually asks for is the strahler code, which lives in
the real codebase and has not been read.

If that code turns out to want the graph and the geometry together in a way this form
makes clumsy, the dataset-aware form is still available and NO OPERATION SIGNATURE
CHANGES - only `_build_topology` does. That is the property that makes deferring cheap,
and it is the reason deferring is the right call rather than a dodge.

FOUR METHODS HERE HAVE NO CALLER IN THIS PACKAGE, which breaks the rule `geometry_ops`
states - a method with no caller is not shipped. They are kept because they are not
invented: 03-architecture §2.5 names connected components, shortest path, MST and
cycle detection as what networkx is used for in the current codebase. Each is marked
below with where its caller is.

The current homes of this logic: `custom_tools/general_tools/graph.py`, `_UnionFind`
inside `line_topology.py`, and the river strahler modules.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Protocol, TypeAlias

NodeId: TypeAlias = int
"""A node identity, opaque to this port.

An int rather than a str because these come from feature OIDs and from synthesized
junction ids, both integral, and because a graph over hundreds of thousands of
segments pays real memory for string keys.
"""

Edge: TypeAlias = tuple[NodeId, NodeId]
Weight: TypeAlias = float


class GraphOps(Protocol):
    """Graph algorithms over abstract topology. No datasets, no geometry.

    UNDIRECTED THROUGHOUT. Every current caller is a road or river network treated as
    undirected; direction matters for routing, which this system does not do. When it
    does, that is a second set of methods rather than a `directed: bool` flag, because
    the flag would change the return type's meaning without changing its type.
    """

    def connected_components(
        self, *, edges: Iterable[Edge]
    ) -> tuple[frozenset[NodeId], ...]:
        """CALLER: `_build_topology` here; `_UnionFind` in `line_topology.py` today.

        The one method with a caller in both this package and the real codebase."""
        ...

    def shortest_path(
        self,
        *,
        edges: Iterable[Edge],
        source: NodeId,
        target: NodeId,
        weights: Mapping[Edge, Weight] | None = None,
    ) -> Sequence[NodeId] | None:
        """CALLER: none here. 03-architecture §2.5, from the real codebase.

        None when no path exists - not an exception. Disconnection is an ordinary
        outcome in a partitioned network, not an error."""
        ...

    def minimum_spanning_tree(
        self, *, edges: Iterable[Edge], weights: Mapping[Edge, Weight] | None = None
    ) -> tuple[Edge, ...]:
        """CALLER: none here. 03-architecture §2.5, from the real codebase."""
        ...

    def cycles(self, *, edges: Iterable[Edge]) -> tuple[tuple[NodeId, ...], ...]:
        """CALLER: none here. 03-architecture §2.5, from the real codebase."""
        ...

    def degree(self, *, edges: Iterable[Edge]) -> Mapping[NodeId, int]:
        """CALLER: `_build_topology` here.

        Degree per node. Degree 1 is a dangle, which is what the topology helpers are
        looking for."""
        ...

    def articulation_points(self, *, edges: Iterable[Edge]) -> frozenset[NodeId]:
        """CALLER: none anywhere yet - the one method here that IS speculative.

        Nodes whose removal disconnects a component. The structural reason a segment must survive thinning regardless of its
        length or class - and the check `select_network` cannot make for itself once
        the network has been handed to a vendor tool.
        """
        ...
