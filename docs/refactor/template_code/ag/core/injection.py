"""TEMPLATE — not shipped. Target module: `src/ag/core/injection.py`.

The marker that says a parameter is supplied by the runtime, not by a declaration.

THIS MODULE EXISTS TO BE IMPORTED UPWARD, which makes it the odd one out in `core/`.
`Toolbox` lives in `ports/` and `core/` may not import it (03-architecture §4.1), but
`@operation` must still recognise it as a parameter kind. Inverting the arrow settles
it: `ports.toolbox` imports this, `core.operations` asks `issubclass(hint, Injected)`,
and the name `Toolbox` never appears anywhere in `core/`. ADR-0014.

Nothing here imports anything, including from this package. It cannot: every layer
above `core/` is allowed to depend on it.
"""

from __future__ import annotations


class Injected:
    """Marker: the runtime supplies this parameter; a declaration site must not.

    Two subclasses today - `ScratchScope` (core.operations) and `Toolbox`
    (ports.toolbox). Both arrive from the pod entry point, both are rejected if
    passed at a declaration site, and both carry a sentinel default so the
    declaration site may omit them while the runtime signature still requires them.

    NO METHODS, AND NOT A PROTOCOL. There is no behaviour common to a scratch scope
    and a toolbox - one allocates files, the other holds ports. What they share is
    provenance, which is not a capability and so has nothing to structurally match
    on. A nominal base is the honest encoding: `@operation` is asking who supplies
    this, not what it can do.
    """
