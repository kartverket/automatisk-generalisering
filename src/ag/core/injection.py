"""The marker that says a parameter is supplied by the runtime, not by a declaration.

What: `Injected`, a nominal base with no behaviour. A class that subclasses it is a kind
of parameter the pod entry point supplies and a declaration site must not.

Why: this module exists to be imported upward, which makes it the odd one out in `core`.
The toolbox lives in `ports` and `core` may not import it, yet `@operation` must recognise
it as a parameter kind. Inverting the arrow settles it: the toolbox module imports this,
`@operation` asks `issubclass(hint, Injected)`, and the toolbox's name never appears in
`core`. Nothing here imports anything, because every layer above `core` is allowed to
depend on it. ADR-0014.
"""

from __future__ import annotations


class Injected:
    """Marker: the runtime supplies this parameter; a declaration site must not.

    Why: no methods and not a Protocol. A scratch scope allocates files and a toolbox
    holds ports; what they share is provenance, which is not a capability and so has
    nothing to structurally match on. A nominal base is the honest encoding: `@operation`
    is asking who supplies this, not what it can do. Each subclass carries a sentinel
    default, an instance of the subclass, so the declaration signature may omit the
    parameter while the runtime signature still requires it.
    """
