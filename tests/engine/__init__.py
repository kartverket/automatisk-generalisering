"""The adapters' expectations of their engines, checked on the engine.

Membership test: the test needs an engine and asserts something the adapter's docstrings
state as expected of it, or a claim only that engine's half of a conformance case can
make; it is not a port contract every adapter must hold, which is `tests/conformance/`.
One package per engine; every test carries that engine's marker and runs under its
interpreter, never in CI. A module here reaches the engine through the adapter's session
and the builders in `tests/support/<engine>/` and never imports the engine itself, so it
type-checks and collects where the engine is absent.
"""
