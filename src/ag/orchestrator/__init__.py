"""The composition root for a run: the dispatch registry and minter counter, and later
execution, jobs, metadata and log merge.

Membership test: the code schedules pods and never touches a pod's disk. It may not
import `ag.generalization.operations`, `ag.adapters.arcpy` or `ag.staging`, and among
the ports it uses only `cluster` and `archive`.
"""
