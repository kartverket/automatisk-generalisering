"""TEMPLATE — PARTIAL. Target package: `src/ag/adapters/fakes/`.

Test doubles for the ports.

ONE DOUBLE SO FAR, AND IT IS A SPY, NOT A FAKE. `recording_toolbox` records the port
calls an operation makes and computes nothing. That is deliberately not what
03-architecture §7.6 means by `adapters/fakes/` - the contract-test suites need
in-memory implementations that genuinely buffer, intersect and dissolve, so that one
suite can be run against every adapter and actually compare results.

The spy came first because it answers a question the in-memory fake does not: does the
port surface let an operation express what it needs to do? An operation that cannot be
written against these Protocols is a design error, and it is cheaper to find by
running every operation in the two worked pipelines than by writing a geometry engine.
`tools/run_example.py` does exactly that.

Still to write: in-memory `GeometryOps`, `TableOps`, `CartographicOps` and `GraphOps`
with real semantics, and the per-port contract suites in `tests/contract/`.
"""
