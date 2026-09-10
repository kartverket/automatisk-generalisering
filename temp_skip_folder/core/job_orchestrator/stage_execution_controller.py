"""
Responsible for orchestrating the execution of individual stages within the DAG.
Each stage operation consists of three jobs: fan out, indexed job, fan in.

These steps execute sequentially for each stage:
1. Fan out - distributes the input data
2. Indexed job - executes the actual stage processing
3. Fan in - aggregates the results
"""

import asyncio
import hashlib
import json
import re
from datetime import date, timedelta
from pathlib import Path

from temp_skip_folder.core.dag.dag_model import StageSpec


async def fan_out(stage_name: str, stage_spec: StageSpec) -> None:
    """
    Fan out phase: distribute input artifacts to workers.

    For now, prints status and sleeps for 5 seconds.

    Args:
        stage_name: Name of the stage being executed.
        stage_spec: StageSpec defining the stage's inputs/outputs.
    """
    input_artifacts = ", ".join(stage_spec.inputs) if stage_spec.inputs else "none"
    print(f"\nstarting fan out of artifacts: {input_artifacts}")
    await asyncio.sleep(10)
    print(f"\ncompleted fan out of artifacts: {input_artifacts}")


async def indexed_job(stage_name: str, stage_spec: StageSpec) -> None:
    """
    Indexed job phase: execute the actual stage processing.

    For now, prints status and sleeps for 5 seconds.

    Args:
        stage_name: Name of the stage being executed.
        stage_spec: StageSpec defining the stage's inputs/outputs.
    """
    print(f"\nstarting indexed job with stage: {stage_name}")
    await asyncio.sleep(10)
    print(f"\ncompleted indexed job with stage: {stage_name}")


async def fan_in(stage_name: str, stage_spec: StageSpec) -> None:
    """
    Fan in phase: aggregate results from workers.

    For now, prints status and sleeps for 5 seconds.

    Args:
        stage_name: Name of the stage being executed.
        stage_spec: StageSpec defining the stage's inputs/outputs.
    """
    output_artifacts = ", ".join(stage_spec.outputs) if stage_spec.outputs else "none"
    print(f"\nstarting fan in of artifacts: {output_artifacts}")
    await asyncio.sleep(10)
    print(f"\ncompleted fan in of artifacts: {output_artifacts}")

def _completion_log_path(stage_name: str) -> Path:
    """Return the completion-log path for a stage."""
    completion_log_dir = Path("/tmp/completion_log")
    completion_log_dir.mkdir(parents=True, exist_ok=True)
    file_name = f"{stage_name}.json"
    file_name = file_name.replace(":", "_")
    return completion_log_dir / file_name


def load_json(stage_name: str) -> dict:
    json_file_path = _completion_log_path(stage_name)
    if not json_file_path.exists():
        return {}

    with open(json_file_path, "r", encoding="utf-8") as file:
        return json.load(file)


def write_json(stage_name: str, data: dict) -> None:
    json_file_path = _completion_log_path(stage_name)
    json_string = json.dumps(data, indent=4)
    with open(json_file_path, "w", encoding="utf-8") as file:
        file.write(json_string)

async def update_stage_completion_date(stage_name: str, completion_log: dict) -> None:
    """
    Update the completion date of a stage.

    Args:
        stage_name: Name of the completed stage.
    """
    today = date.today().isoformat()


    completion_log[stage_name] = today

    write_json(stage_name, completion_log)


def check_completion(stage_name: str, completion_log: dict) -> bool:
    """
    Check if a stage has been completed recently.

    hard coded 1 week for now

    Args:
        stage_name: Name of the stage to check.
        json: Dictionary containing completion log.

    Returns:
        True if the stage has a completion date within a week, False otherwise.
    """
    if stage_name not in completion_log:
        return False

    completion_date = date.fromisoformat(completion_log[stage_name])
    one_week_ago = date.today() - timedelta(days=7)

    return one_week_ago <= completion_date 


async def execute_stage_operation(stage_name: str, stage_spec: StageSpec) -> None:
    """
    Execute a complete stage operation with three sequential phases.

    Executes fan_out → indexed_job → fan_in in sequence.

    Args:
        stage_name: Name of the stage being executed.
        stage_spec: StageSpec defining the stage's inputs/outputs.
    """
    completion_log = load_json(stage_name)
    complete = check_completion(stage_name, completion_log)
    if complete:
        print(f"Stage '{stage_name}' has been completed recently. Skipping execution.")
        return

    await fan_out(stage_name, stage_spec)
    await indexed_job(stage_name, stage_spec)
    await fan_in(stage_name, stage_spec)
    await update_stage_completion_date(stage_name, completion_log)