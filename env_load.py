###########################
# Libraries
###########################

import os

from pathlib import Path

###########################
# Functionality
###########################

def require(name: str) -> str:
    try:
        return os.environ[name]
    except KeyError:
        raise RuntimeError(
            f"Required environment variable {name} is not set!\nSee .env.example for the contract."
        ) from None

def load_env(env_path: Path=Path(".env")):
    if not env_path.exists():
        return

    for line in env_path.read_text().splitlines():
        line = line.strip()

        if not line or line.startswith("#"):
            continue

        if "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())
