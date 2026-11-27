"""Errors raised in `ag.staging`: a pod's paths and names.

What: `StagingError(AgError)`, the base every staging guard raises; `WorkspaceError
(StagingError)`, a name or path the scratch manager refuses: an illegal or over-long
name, two names the engine would treat as one, a workspace it was not asked for.

Why: a staging guard fires in a pod, not at import, so it is an `AgError` with a
context and not a builtin. It is not a `StageRunError`: only `ag.runtime` imports
`ag.staging` (import row 9), so staging cannot name runtime's errors, and a caller that
handles a run failure is not the caller that handles a bad name.
"""

from __future__ import annotations

from ag.core.errors import AgError


class StagingError(AgError):
    """A failure in naming, placing or transferring a pod's data."""


class WorkspaceError(StagingError):
    """A name or path the scratch manager refuses."""
