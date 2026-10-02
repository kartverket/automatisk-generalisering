"""Engine-free code that more than one adapter needs.

Membership test: it imports only `ag.core`, `ag.ports` and the standard library, and at
least two adapters (or an adapter and the tests) use it. Modules are named for the
decision they compute, such as `parents_resolver`. Code that calls an engine belongs in
that adapter's `support` package instead.
"""
