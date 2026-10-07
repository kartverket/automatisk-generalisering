"""Feature-level identity above the ports: minter, id map, facade, session, edges and
the work key.

Membership test: the code allocates, maps or records `lineage_id` values and never calls
an engine. Only `ag.runtime` imports this package; operations reach lineage through what
the runtime hands them.
"""
