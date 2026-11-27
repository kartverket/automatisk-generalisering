import os
import shutil
import sys
import time
import logging
from pathlib import Path

from kubernetes import client, config
from minio import Minio

logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO),
    format="%(asctime)s %(levelname)s: %(message)s",
)


logger = logging.getLogger(__name__)

DATA_ROOT = Path("/data")
GIS_FILES_FOLDER = "GIS_Files"
CHECKPOINTS_FOLDER = "checkpoints"
S3_DATA_FOLDERS = (GIS_FILES_FOLDER, CHECKPOINTS_FOLDER)
DATA_PVC_CLAIM_NAME = "auto-gen-scratch-pvc"
WORKER_GIS_OUTPUTS_ROOT = f"/tmp/{GIS_FILES_FOLDER}"
ROAD_RESULTS_ROOT = str(DATA_ROOT / GIS_FILES_FOLDER)


def download_s3_data_if_data_is_empty() -> None:
    if not DATA_ROOT.is_dir():
        raise FileNotFoundError(
            f"Expected PVC mount directory does not exist: {DATA_ROOT}"
        )

    """
    if next(DATA_ROOT.iterdir(), None) is not None:
        logger.info("PVC data directory is not empty; skipping initial S3 download")
        return
    """

    environment_names = (
        "SCALITY_ENDPOINT",
        "SCALITY_BUCKET",
        "scality_user",
        "scality_pass",
    )
    missing_environment = [
        name for name in environment_names if not os.environ.get(name)
    ]
    if missing_environment:
        raise RuntimeError(
            "Missing required Scality environment variables: "
            + ", ".join(missing_environment)
        )

    s3_client = Minio(
        endpoint=os.environ["SCALITY_ENDPOINT"],
        access_key=os.environ["scality_user"],
        secret_key=os.environ["scality_pass"],
    )
    bucket_name = os.environ["SCALITY_BUCKET"]

    for folder in S3_DATA_FOLDERS:
        prefix = f"{folder}/"
        downloaded_objects = 0
        for item in s3_client.list_objects(
            bucket_name=bucket_name,
            prefix=prefix,
            recursive=True,
        ):
            object_name = item.object_name
            if object_name.endswith("/"):
                continue

            relative_path = Path(object_name[len(prefix) :])
            if (
                not object_name.startswith(prefix)
                or relative_path.is_absolute()
                or ".." in relative_path.parts
                or not relative_path.parts
            ):
                raise ValueError(
                    f"Invalid object path under S3 prefix {prefix}: {object_name}"
                )

            local_path = DATA_ROOT / folder / relative_path
            local_path.parent.mkdir(parents=True, exist_ok=True)
            logger.info(
                "Downloading s3://%s/%s to %s", bucket_name, object_name, local_path
            )
            s3_client.fget_object(
                bucket_name=bucket_name,
                object_name=object_name,
                file_path=str(local_path),
            )
            downloaded_objects += 1

        if downloaded_objects == 0:
            raise FileNotFoundError(f"No objects found in s3://{bucket_name}/{prefix}")

    logger.info("Initial S3 data download to %s completed", DATA_ROOT)


NAMESPACE = os.environ.get("NAMESPACE")
RUN_ID = os.environ.get("RUN_ID")
OWNER_JOB_NAME = os.environ["OWNER_JOB_NAME"]
OWNER_JOB_UID = os.environ["OWNER_JOB_UID"]
PARTITION_COUNT = int(os.environ.get("PARTITION_COUNT"))
PARALLELISM = int(os.environ.get("PARALLELISM", "2"))
PIPELINE_CONFIGS: dict[str, tuple[str, str]] = {
    "n100_roads": ("n100", "road"),
    "n100_buildings": ("n100", "building"),
}
PIPELINE_NAME = os.environ.get("PIPELINE_NAME", "n100_roads")
try:
    PIPELINE_SCALE, PIPELINE_OBJECT = PIPELINE_CONFIGS[PIPELINE_NAME]
except KeyError:
    raise ValueError(
        f"PIPELINE_NAME must be one of {', '.join(PIPELINE_CONFIGS)}, "
        f"got {PIPELINE_NAME!r}"
    ) from None

PARTITION_JOB_NAME = f"{RUN_ID}-partitions"


# Temporary zip, extracted data and outputs coexist in /tmp.
EPHEMERAL_STORAGE = "2Gi"
WORKER_MEMORY_LIMIT = "32Gi"


def load_kube_config():
    """
    Loads Kubernetes config from inside the cluster.

    This assumes the script is running in a Kubernetes pod with a ServiceAccount.
    """
    config.load_incluster_config()


def create_indexed_job(batch_api):
    """
    Creates a Kubernetes Indexed Job.

    Each completion gets a unique JOB_COMPLETION_INDEX, which we use as the
    partition index.
    """
    logger.info(f"Creating indexed Job: {PARTITION_JOB_NAME}")
    logger.info(f"Namespace: {NAMESPACE}")
    logger.info(f"Parallelism: {PARALLELISM}")

    job = client.V1Job(
        api_version="batch/v1",
        kind="Job",
        metadata=client.V1ObjectMeta(
            name=PARTITION_JOB_NAME,
            labels={
                "app": "partitioned-pipeline",
                "run-id": RUN_ID,
                "pipeline-role": "partition-worker",
            },
            owner_references=[
                client.V1OwnerReference(
                    api_version="batch/v1",
                    kind="Job",
                    name=OWNER_JOB_NAME,
                    uid=OWNER_JOB_UID,
                    controller=False,
                    block_owner_deletion=False,
                )
            ],
            annotations={
                "argocd.argoproj.io/tracking-id": f"{os.environ.get('ARGOTRACKING')}{PARTITION_JOB_NAME}",
                "argocd.argoproj.io/sync-options": "Prune=false",
            },
        ),
        spec=client.V1JobSpec(
            completion_mode="Indexed",
            completions=PARTITION_COUNT,
            parallelism=PARALLELISM,
            backoff_limit=3,
            ttl_seconds_after_finished=604800,
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(
                    labels={
                        "app": "partitioned-pipeline",
                        "run-id": RUN_ID,
                        "pipeline-role": "partition-worker",
                    }
                ),
                spec=client.V1PodSpec(
                    containers=[
                        client.V1Container(
                            name="worker",
                            image="ghcr.io/kartverket/automatisk-generalisering:on_prem_test",
                            image_pull_policy="Always",
                            env=[
                                client.V1EnvVar(
                                    name="RUN_ID",
                                    value=RUN_ID,
                                ),
                                client.V1EnvVar(
                                    name="JOB_COMPLETION_INDEX",
                                    value_from=client.V1EnvVarSource(
                                        field_ref=client.V1ObjectFieldSelector(
                                            field_path="metadata.annotations['batch.kubernetes.io/job-completion-index']"
                                        )
                                    ),
                                ),
                                client.V1EnvVar(
                                    name="ENVIRONMENT",
                                    value="on_prem",
                                ),
                                client.V1EnvVar(
                                    name="SCALE",
                                    value=PIPELINE_SCALE,
                                ),
                                client.V1EnvVar(
                                    name="OBJECT",
                                    value=PIPELINE_OBJECT,
                                ),
                                client.V1EnvVar(
                                    name="SELECT_STUDY_AREA",
                                    value="Partition",
                                ),
                                client.V1EnvVar(
                                    name="PIPELINE_NAME",
                                    value=PIPELINE_NAME,
                                ),
                                client.V1EnvVar(
                                    name="GIS_FILES_ROOT",
                                    value=str(
                                        DATA_ROOT / GIS_FILES_FOLDER / "ag_inputs"
                                    ),
                                ),
                                client.V1EnvVar(
                                    name="GIS_OUTPUTS_ROOT",
                                    value=WORKER_GIS_OUTPUTS_ROOT,
                                ),
                                client.V1EnvVar(
                                    name="GIS_ROAD_RESULTS_ROOT",
                                    value=ROAD_RESULTS_ROOT,
                                ),
                            ],
                            env_from=[
                                client.V1EnvFromSource(
                                    config_map_ref=client.V1ConfigMapEnvSource(
                                        name="on-prem-config"
                                    )
                                ),
                                client.V1EnvFromSource(
                                    secret_ref=client.V1SecretEnvSource(
                                        name="scality-credentials"
                                    )
                                ),
                            ],
                            volume_mounts=[
                                client.V1VolumeMount(
                                    name="tmp",
                                    mount_path="/tmp",
                                ),
                                client.V1VolumeMount(
                                    name="data",
                                    mount_path=str(DATA_ROOT),
                                ),
                            ],
                            resources=client.V1ResourceRequirements(
                                requests={
                                    "ephemeral-storage": EPHEMERAL_STORAGE,
                                },
                                limits={
                                    "memory": WORKER_MEMORY_LIMIT,
                                    "ephemeral-storage": EPHEMERAL_STORAGE,
                                },
                            ),
                            security_context=client.V1SecurityContext(
                                allow_privilege_escalation=False,
                                capabilities=client.V1Capabilities(drop=["ALL"]),
                                privileged=False,
                                read_only_root_filesystem=True,
                                run_as_group=150,
                                run_as_non_root=True,
                                run_as_user=150,
                                seccomp_profile=client.V1SeccompProfile(
                                    type="RuntimeDefault"
                                ),
                            ),
                            termination_message_path="/dev/termination-log",
                            termination_message_policy="File",
                        )
                    ],
                    dns_policy="ClusterFirst",
                    image_pull_secrets=[
                        client.V1LocalObjectReference(name="github-auth")
                    ],
                    priority_class_name="skip-medium",
                    restart_policy="Never",
                    scheduler_name="default-scheduler",
                    security_context=client.V1PodSecurityContext(
                        fs_group=150,
                        seccomp_profile=client.V1SeccompProfile(type="RuntimeDefault"),
                        supplemental_groups=[150],
                    ),
                    termination_grace_period_seconds=30,
                    topology_spread_constraints=[
                        client.V1TopologySpreadConstraint(
                            label_selector=client.V1LabelSelector(
                                match_expressions=[
                                    client.V1LabelSelectorRequirement(
                                        key="app",
                                        operator="In",
                                        values=["partitioned-pipeline"],
                                    )
                                ]
                            ),
                            max_skew=1,
                            topology_key="kubernetes.io/hostname",
                            when_unsatisfiable="DoNotSchedule",
                        ),
                        client.V1TopologySpreadConstraint(
                            label_selector=client.V1LabelSelector(
                                match_expressions=[
                                    client.V1LabelSelectorRequirement(
                                        key="app",
                                        operator="In",
                                        values=["partitioned-pipeline"],
                                    )
                                ]
                            ),
                            match_label_keys=["pod-template-hash"],
                            max_skew=1,
                            topology_key="onprem.gke.io/failure-domain-name",
                            when_unsatisfiable="ScheduleAnyway",
                        ),
                    ],
                    volumes=[
                        client.V1Volume(
                            name="tmp",
                            empty_dir=client.V1EmptyDirVolumeSource(
                                size_limit=EPHEMERAL_STORAGE
                            ),
                        ),
                        client.V1Volume(
                            name="data",
                            persistent_volume_claim=client.V1PersistentVolumeClaimVolumeSource(
                                claim_name=DATA_PVC_CLAIM_NAME,
                            ),
                        ),
                    ],
                ),
            ),
        ),
    )

    try:
        created_job = batch_api.create_namespaced_job(
            namespace=NAMESPACE,
            body=job,
        )
        logger.info(
            f"Created Job successfully: "
            f"name={created_job.metadata.name}, "
            f"namespace={created_job.metadata.namespace}, "
            f"uid={created_job.metadata.uid}"
        )
    except client.exceptions.ApiException as e:
        raise RuntimeError(
            "Failed to create indexed Job "
            f"name={PARTITION_JOB_NAME} namespace={NAMESPACE}. "
            f"status={e.status}, reason={e.reason}, body={e.body}"
        ) from e
    except Exception as e:
        raise RuntimeError(
            "Unexpected error while creating indexed Job "
            f"name={PARTITION_JOB_NAME} namespace={NAMESPACE}: {e}"
        ) from e


def wait_for_job(batch_api):
    """
    Waits until the indexed Job has completed all partitions.
    """
    logger.info(f"Waiting for Job to complete: {PARTITION_JOB_NAME}")

    while True:
        job = batch_api.read_namespaced_job(
            name=PARTITION_JOB_NAME,
            namespace=NAMESPACE,
        )

        status = job.status

        succeeded = status.succeeded or 0
        failed = status.failed or 0
        active = status.active or 0

        logger.info(
            f"Job status: active={active}, "
            f"succeeded={succeeded}, "
            f"failed={failed}, "
            f"expected={PARTITION_COUNT}"
        )

        if succeeded >= PARTITION_COUNT:
            logger.info("Indexed Job completed successfully")
            return

        if status.conditions:
            for condition in status.conditions:
                if condition.type == "Failed" and condition.status == "True":
                    raise RuntimeError(
                        f"Job failed: {condition.reason} - {condition.message}"
                    )

        time.sleep(120)


def delete_partition_job(batch_api, wait: bool = True, timeout_seconds: int = 120):
    """
    Deletes the partition Job and optionally waits until it is fully removed.

    Requires RBAC permission:
    - verbs: get, delete
    - resource: jobs
    - apiGroup: batch
    """
    logger.info(f"Deleting Job: {PARTITION_JOB_NAME} (namespace={NAMESPACE})")

    try:
        batch_api.delete_namespaced_job(
            name=PARTITION_JOB_NAME,
            namespace=NAMESPACE,
            body=client.V1DeleteOptions(
                propagation_policy="Background",
                grace_period_seconds=0,
            ),
        )
        logger.info(f"Delete request accepted for Job: {PARTITION_JOB_NAME}")
    except client.exceptions.ApiException as e:
        if e.status == 404:
            logger.info(f"Job already absent: {PARTITION_JOB_NAME}")
            return
        raise RuntimeError(
            "Failed to delete indexed Job "
            f"name={PARTITION_JOB_NAME} namespace={NAMESPACE}. "
            f"status={e.status}, reason={e.reason}, body={e.body}"
        ) from e
    except Exception as e:
        raise RuntimeError(
            "Unexpected error while deleting indexed Job "
            f"name={PARTITION_JOB_NAME} namespace={NAMESPACE}: {e}"
        ) from e

    if not wait:
        return

    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            batch_api.read_namespaced_job(
                name=PARTITION_JOB_NAME,
                namespace=NAMESPACE,
            )
            logger.info(f"Waiting for Job deletion: {PARTITION_JOB_NAME}")
            time.sleep(2)
        except client.exceptions.ApiException as e:
            if e.status == 404:
                logger.info(f"Job deleted: {PARTITION_JOB_NAME}")
                return
            raise RuntimeError(
                "Error while verifying Job deletion "
                f"name={PARTITION_JOB_NAME} namespace={NAMESPACE}. "
                f"status={e.status}, reason={e.reason}, body={e.body}"
            ) from e

    raise TimeoutError(
        f"Timed out waiting for Job deletion: {PARTITION_JOB_NAME} "
        f"(timeout_seconds={timeout_seconds})"
    )


def is_job_running(batch_api, job_name: str) -> bool:
    """
    True while the Job exists and has not reached a Complete or Failed condition.

    A Job whose pods are still pending counts as running, so its data is kept.
    """
    try:
        job = batch_api.read_namespaced_job(name=job_name, namespace=NAMESPACE)
    except client.exceptions.ApiException as e:
        if e.status == 404:
            return False
        raise RuntimeError(
            f"Failed to read Job name={job_name} namespace={NAMESPACE}. "
            f"status={e.status}, reason={e.reason}, body={e.body}"
        ) from e

    for condition in job.status.conditions or []:
        if condition.type in ("Complete", "Failed") and condition.status == "True":
            return False
    return True


def delete_s3_data_if_other_orchestrator_finished(batch_api) -> None:
    """
    Deletes the downloaded data from /data unless the other orchestrator still uses it.
    """
    """
    other_job_name = os.environ.get("OTHER_ORCHESTRATOR_JOB_NAME")
    if not other_job_name:
        logger.warning(
            "OTHER_ORCHESTRATOR_JOB_NAME is not set; keeping data in %s", DATA_ROOT
        )
        return

    if is_job_running(batch_api, other_job_name):
        logger.info(
            "Other orchestrator Job %s is still running; keeping data in %s",
            other_job_name,
            DATA_ROOT,
        )
        return
    """

    for folder in S3_DATA_FOLDERS:
        folder_path = DATA_ROOT / folder
        if folder_path.exists():
            logger.info("Deleting %s", folder_path)
            shutil.rmtree(folder_path)

    logger.info("Data in %s deleted", DATA_ROOT)


def main():
    logger.info("Pipeline driver started")
    logger.info(f"Namespace: {NAMESPACE}")
    logger.info(f"Partition count: {PARTITION_COUNT}")
    logger.info(f"Parallelism: {PARALLELISM}")
    logger.info(f"Run ID: {RUN_ID}")

    load_kube_config()

    batch_api = client.BatchV1Api()

    delete_s3_data_if_other_orchestrator_finished(batch_api)
    download_s3_data_if_data_is_empty()

    delete_partition_job(batch_api, wait=True, timeout_seconds=60)
    create_indexed_job(batch_api)
    wait_for_job(batch_api)
    # delete_partition_job(batch_api, wait=False)
    delete_s3_data_if_other_orchestrator_finished(batch_api)

    logger.info("Pipeline driver completed successfully")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        logger.info(f"Driver failed: {error}")
        sys.exit(1)
