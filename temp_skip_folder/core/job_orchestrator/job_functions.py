import os
import sys
import time
import logging
from kubernetes import client, config

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)



def load_kube_config():
    """
    Loads Kubernetes config from inside the cluster.

    This assumes the script is running in a Kubernetes pod with a ServiceAccount.
    """
    config.load_incluster_config()


def create_indexed_job(
    batch_api,
    namespace,
    run_id,
    partition_count,
    parallelism,
    stage_name,
    partition_job_name,
    argotracking,
):
    """
    Creates a Kubernetes Indexed Job.

    Each completion gets a unique JOB_COMPLETION_INDEX, which we use as the
    partition index.
    """
    logger.info(f"Creating indexed Job: {partition_job_name}")
    logger.info(f"Namespace: {namespace}")
    logger.info(f"Partitions: {partition_count}")
    logger.info(f"Parallelism: {parallelism}")

    job = client.V1Job(
        api_version="batch/v1",
        kind="Job",
        metadata=client.V1ObjectMeta(
            name=partition_job_name,
            labels={
                "app": "partitioned-pipeline",
                "run-id": run_id,
                "pipeline-role": "partition-worker",
            },
            annotations={
                "argocd.argoproj.io/tracking-id": f"{argotracking}{partition_job_name}",
                "argocd.argoproj.io/sync-options": "Prune=false",
            },
        ),
        spec=client.V1JobSpec(
            completion_mode="Indexed",
            completions=partition_count,
            parallelism=parallelism,
            backoff_limit=1,
            ttl_seconds_after_finished=300,
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(
                    labels={
                        "app": "partitioned-pipeline",
                        "run-id": run_id,
                        "pipeline-role": "partition-worker",
                    }
                ),
                spec=client.V1PodSpec(
                    containers=[
                        client.V1Container(
                            name="worker",
                            image="ghcr.io/kartverket/automatisk-generalisering:run_partition",
                            image_pull_policy="Always",
                            env=[
                                client.V1EnvVar(
                                    name="RUN_ID",
                                    value=run_id,
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
                                    name="PIPELINE_NAME",
                                    value="n100_roads",
                                ),
                                client.V1EnvVar(
                                    name="STAGE_NAME",
                                    value=stage_name,
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
                                )
                            ],
                            resources={},
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
                            empty_dir=client.V1EmptyDirVolumeSource(medium="Memory"),
                        )
                    ],
                ),
            ),
        ),
    )

    try:
        created_job = batch_api.create_namespaced_job(
            namespace=namespace,
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
            f"name={partition_job_name} namespace={namespace}. "
            f"status={e.status}, reason={e.reason}, body={e.body}"
        ) from e
    except Exception as e:
        raise RuntimeError(
            "Unexpected error while creating indexed Job "
            f"name={partition_job_name} namespace={namespace}: {e}"
        ) from e


def create_job(
    batch_api,
    namespace,
    run_id,
    stage_name,
    job_name,
    argotracking,
):
    """
    Creates a Kubernetes Indexed Job.

    Each completion gets a unique JOB_COMPLETION_INDEX, which we use as the
    partition index.
    """
    logger.info(f"Creating Job: {job_name}")
    logger.info(f"Namespace: {namespace}")

    job = client.V1Job(
        api_version="batch/v1",
        kind="Job",
        metadata=client.V1ObjectMeta(
            name=job_name,
            labels={
                "app": job_name,
                "run-id": run_id,
                "pipeline-role": "partition-worker",
            },
            annotations={
                "argocd.argoproj.io/tracking-id": f"{argotracking}{job_name}",
                "argocd.argoproj.io/sync-options": "Prune=false",
            },
        ),
        spec=client.V1JobSpec(
            backoff_limit=1,
            ttl_seconds_after_finished=300,
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(
                    labels={
                        "app": job_name,
                        "run-id": run_id,
                        "pipeline-role": "partition-worker",
                    }
                ),
                spec=client.V1PodSpec(
                    containers=[
                        client.V1Container(
                            name="worker",
                            image="ghcr.io/kartverket/automatisk-generalisering:hello_world",
                            image_pull_policy="Always",
                            env=[
                                client.V1EnvVar(
                                    name="RUN_ID",
                                    value=run_id,
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
                                    name="PIPELINE_NAME",
                                    value="n100_roads",
                                ),
                                client.V1EnvVar(
                                    name="STAGE_NAME",
                                    value=stage_name,
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
                                )
                            ],
                            resources={},
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
                                        values=[job_name],
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
                            empty_dir=client.V1EmptyDirVolumeSource(medium="Memory"),
                        )
                    ],
                ),
            ),
        ),
    )

    try:
        created_job = batch_api.create_namespaced_job(
            namespace=namespace,
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
            f"name={job_name} namespace={namespace}. "
            f"status={e.status}, reason={e.reason}, body={e.body}"
        ) from e
    except Exception as e:
        raise RuntimeError(
            "Unexpected error while creating indexed Job "
            f"name={job_name} namespace={namespace}: {e}"
        ) from e
