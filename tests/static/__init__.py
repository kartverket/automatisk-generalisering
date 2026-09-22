"""Contract tests: checks over the code base rather than over behaviour.

Membership test: the test inspects source, configuration or documents (import contracts,
source scans, the row-shape check, the port matrix, the document checkers) and runs no
pipeline code. Runs in pre-commit and in CI on both runners.
"""
