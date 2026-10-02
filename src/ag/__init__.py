"""The generalization framework and the cartographic domain code it runs.

The framework packages (core, ports, adapters, lineage, staging, observability, runtime,
orchestrator) change rarely and need architecture review; `generalization` holds all
cartographic domain code. Membership test: a new top-level package is an architecture
change, and the exhaustive layers contract in `.importlinter` fails until the package is
given a layer.
"""
