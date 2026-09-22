"""Adapters with no engine: the recording spy and the in-memory adapter.

They ship in `src` because a developer without ArcPy runs a stage against them through
`ag.runtime.local`. Membership test: it implements a port without any vendor library.
`ag.runtime.local` is the only module in `ag` allowed to import this package; tests and
tools sit outside the root package and import it freely.
"""
