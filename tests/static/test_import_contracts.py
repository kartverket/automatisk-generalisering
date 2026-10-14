"""The import contracts of `.importlinter`, as tests, one per contract.

What: one import-linter run per module, with its cache off, parsed into a verdict per
contract; each contract is one parametrised test, so a break-it case can name the one it
breaks. The hook runs the same contracts; this is the form a case table can target.

Why: a contract over a nearly empty tree passes whether or not its names are right, and a
contract that has never been seen to fail is not known to work. The row-5 cases in the
ports set append one import to a port module and expect the matching test here to fail.
"""

from __future__ import annotations

import configparser
import contextlib
import io
import re
from pathlib import Path

import pytest
from importlinter import cli

REPO = Path(__file__).resolve().parents[2]
CONFIG = REPO / ".importlinter"
PREFIX = "importlinter:contract:"


def _contracts() -> dict[str, str]:
    """Contract id to the name import-linter prints for it."""
    parser = configparser.ConfigParser()
    parser.read(CONFIG, encoding="utf-8")
    return {
        section.removeprefix(PREFIX): parser[section]["name"]
        for section in parser.sections()
        if section.startswith(PREFIX)
    }


CONTRACTS = _contracts()


@pytest.fixture(scope="module")
def verdicts() -> dict[str, str]:
    """Contract name to `KEPT` or `BROKEN`, from one run over every contract."""
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        cli.lint_imports(config_filename=str(CONFIG), no_cache=True, no_logo=True)
    # A contract line reads `<name> KEPT`, `<name> BROKEN`, or `<name> KEPT (n ignored
    # imports)`, so the verdict is matched as a word after the name, not as the line's end.
    pattern = re.compile(r"^(?P<name>.+?) (?P<verdict>KEPT|BROKEN)(?: \(.*\))?$")
    found: dict[str, str] = {}
    for line in output.getvalue().splitlines():
        match = pattern.match(line.strip())
        if match is not None:
            found[match["name"]] = match["verdict"]
    return found


def test_every_contract_is_reported(verdicts: dict[str, str]) -> None:
    assert sorted(verdicts) == sorted(CONTRACTS.values())


@pytest.mark.parametrize("contract", sorted(CONTRACTS), ids=sorted(CONTRACTS))
def test_contract_is_kept(contract: str, verdicts: dict[str, str]) -> None:
    assert verdicts[CONTRACTS[contract]] == "KEPT", contract
