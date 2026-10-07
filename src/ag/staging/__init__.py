"""Pod-local paths and transfer: workspace naming, the scratch manager and the scratch
dump.

Membership test: the code knows where data sits on a pod's disk. It imports `ag.core`
and `ag.ports` and no engine, and only `ag.runtime` imports it.
"""
