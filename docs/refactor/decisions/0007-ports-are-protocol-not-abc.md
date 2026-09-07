# ADR-0007: Ports are `typing.Protocol`, not `ABC`

**Status:** Accepted

## Context

The existing `temp_skip_folder/core/infrastructure/archive/interface.py` declares a six-method
`ArchiveClient` ABC, of which only `read` and `write` have callers anywhere.

## Decision

Every port is a `typing.Protocol`. Conformance is asserted by an `if TYPE_CHECKING:`
assignment at the bottom of each adapter module, plus one central adapter × port matrix in
`tests/static/` covering the fakes.

## Consequences

With an ABC the adapter must import and subclass the port, so the dependency arrow points
from adapter to port and back. With a Protocol nothing is imported and satisfaction is
structural, so the arrow only ever points one way.

Ports stay narrow. An ABC produces one interface everybody inherits, which is how a
two-method need became six abstract methods.

Third-party clients and plain dataclass test doubles satisfy a Protocol with no wrapper.

No runtime enforcement at instantiation: `@runtime_checkable` plus `isinstance` checks method
*names* only, not signatures. Hence the static conformance convention above.

PEP 544 cautions that large, implementation-oriented interfaces are impractical as protocols.
`GeometryOps` at 25–35 methods is that shape. This is the substance of Q-B, and is accepted
knowingly rather than overlooked.
