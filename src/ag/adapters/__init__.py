"""Implementations of the ports, and the only place a vendor library is imported.

One package per engine or service. Membership test: the code exists because a specific
library or service exists. Only `ag.runtime` and `ag.orchestrator` may import from here,
and adapter packages never import each other.
"""
