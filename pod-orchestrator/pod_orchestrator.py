import os
import sys
import time
import logging
from kubernetes import client, config

logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO),
    format="%(asctime)s %(levelname)s: %(message)s",
)


logger = logging.getLogger(__name__)


NAMESPACE = os.environ.get("NAMESPACE")
RUN_ID = os.environ.get("RUN_ID")
AREAS = os.environ.get("PARTITION_STUDY_AREAS")
AREAS_LIST = os.environ["PARTITION_STUDY_AREAS"].split(",")
PARTITION_COUNT = len(AREAS_LIST)
PARALLELISM = int(os.environ.get("PARALLELISM", "2"))

PARTITION_JOB_NAME = f"{RUN_ID}-partitions"


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
    logger.info(f"Partitions: {PARTITION_COUNT}")
    logger.info(f"Areas: {AREAS_LIST}")
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
            annotations={
                "argocd.argoproj.io/tracking-id": f"{os.environ.get('ARGOTRACKING')}{PARTITION_JOB_NAME}",
                "argocd.argoproj.io/sync-options": "Prune=false",
            }

        ),
        spec=client.V1JobSpec(
            completion_mode="Indexed",
            completions=PARTITION_COUNT,
            parallelism=PARALLELISM,
            backoff_limit=1,
            ttl_seconds_after_finished=300,
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
                            image="ghcr.io/kartverket/automatisk-generalisering:on_prem",
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
                                    name="AREAS",
                                    value=AREAS,
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
                                )
                            ],
                                    
                            resources= {},
                            security_context=client.V1SecurityContext(
                                allow_privilege_escalation=False,
                                capabilities=client.V1Capabilities(
                                    drop=[
                                        "ALL"
                                    ]
                                ),
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
                        client.V1LocalObjectReference(
                            name="github-auth"
                        )
                    ],
                    priority_class_name="skip-medium",
                    restart_policy="Never",
                    scheduler_name="default-scheduler",
                    security_context=client.V1PodSecurityContext(
                        fs_group=150,
                        seccomp_profile=client.V1SeccompProfile(
                            type="RuntimeDefault"
                        ),
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
                            match_label_keys=["pod-template-hash"],
                            max_skew=1,
                            topology_key="kubernetes.io/hostname",
                            when_unsatisfiable="ScheduleAnyway",
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
                                medium="Memory"
                            ),
                        )
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

        time.sleep(5)

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

def main():
    logger.info("Pipeline driver started")
    logger.info(f"Namespace: {NAMESPACE}")
    logger.info(f"Run ID: {RUN_ID}")

    load_kube_config()

    batch_api = client.BatchV1Api()

    delete_partition_job(batch_api, wait=True, timeout_seconds=60)
    create_indexed_job(batch_api)
    wait_for_job(batch_api)
    delete_partition_job(batch_api, wait=False)

    logger.info("Pipeline driver completed successfully")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        logger.info(f"Driver failed: {error}")
        sys.exit(1)