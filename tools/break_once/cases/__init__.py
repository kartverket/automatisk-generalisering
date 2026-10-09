"""The case tables, one module per mutated source package, named for it.

Each module exports `CASES`, a tuple of `Case`, and `SUITE`, the pytest targets run after
the last restore. A needle is a verbatim excerpt of the current source, so a refactor that
changes the text turns the case into a harness error, which is the signal to update it.
"""
