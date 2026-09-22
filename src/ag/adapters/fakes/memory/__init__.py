"""The in-memory adapter, in the same package shape as the ArcPy adapter.

The root holds `store.py`, `_base.py`, `support/` and the port packages, and nothing
else. Membership test: the code reads and writes rows only through the `MemoryStore` it
is handed, and computes no geometry.
"""
