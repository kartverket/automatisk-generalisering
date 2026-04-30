import argparse
import os
import sys
import logging
from typing import Callable, Dict, Tuple

logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO),
    format="%(asctime)s %(levelname)s: %(message)s",
)


logger = logging.getLogger(__name__)

#pipeline imports
def pipeline_n100_road(args: argparse.Namespace) -> None:
    #from generalization.n100.road.data_preparation_2 import run as run_n100_road
    logger.info("Starting pipeline for %s", args)
    #run_n100_road()


def pipeline_n10_arealdekke(args: argparse.Namespace) -> None:
    #from generalization.n10.arealdekke.orchestrator.arealdekke_orchestrator import run as run_n10_arealdekke
    logger.info("Starting pipeline for %s", args)
    #run_n10_arealdekke()


DISPATCH: Dict[Tuple[str, str], Callable[[argparse.Namespace], None]] = {
    ("n100", "road"): pipeline_n100_road,
    ("n10", "arealdekke"): pipeline_n10_arealdekke,
}


def print_available() -> None:
    logger.info("Available pipelines:")
    for scale, obj in DISPATCH.keys():
        logger.info(f"  - scale={scale} object={obj}")

def parse_args():
    parser = argparse.ArgumentParser(description="Dispatch to pipelines")
    parser.add_argument("--scale", type=str, default=os.getenv("SCALE"), help="Scale to run (env SCALE)")
    parser.add_argument("--object", dest="obj", type=str, default=os.getenv("OBJECT"), help="Object to process (env OBJECT)")
    return parser.parse_args()

def main():
    args = parse_args()

    if not args.scale or not args.obj:
        logger.error("Error: --scale and --object required (or set SCALE/OBJECT env)")
        print_available()
        sys.exit()

    key = (args.scale, args.obj)
    handler = DISPATCH.get(key)
    if handler is None:
        logger.error(f"No pipeline for scale={args.scale} object={args.obj}")
        print_available()
        sys.exit()

    handler(args)

if __name__ == "__main__":
    main()