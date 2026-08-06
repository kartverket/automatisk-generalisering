import os
import sys
import time
from kubernetes import client, config


NAMESPACE = os.environ.get("NAMESPACE", "default")
RUN_ID = os.environ.get("RUN_ID", "test-run-001")

PARTITION_COUNT = int(os.environ.get("PARTITION_COUNT", "5"))
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
    print(f"Creating indexed Job: {PARTITION_JOB_NAME}")
    print(f"Namespace: {NAMESPACE}")
    print(f"Partitions: {PARTITION_COUNT}")
    print(f"Parallelism: {PARALLELISM}")

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
        ),
        spec=client.V1JobSpec(
            completion_mode="Indexed",
            completions=PARTITION_COUNT,
            parallelism=PARALLELISM,
            backoff_limit=2,
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
                    restart_policy="Never",
                    containers=[
                        client.V1Container(
                            name="worker",
                            image="alpine:3.20",
                            command=["sh", "-c"],
                            args=[
                                """
                                echo "Processing partition index: ${JOB_COMPLETION_INDEX}"
                                echo "Run ID: ${RUN_ID}"
                                sleep 10
                                echo "Finished partition index: ${JOB_COMPLETION_INDEX}"
                                """
                            ],
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
                            ],
                        )
                    ],
                ),
            ),
        ),
    )

    batch_api.create_namespaced_job(
        namespace=NAMESPACE,
        body=job,
    )


def wait_for_job(batch_api):
    """
    Waits until the indexed Job has completed all partitions.
    """
    print(f"Waiting for Job to complete: {PARTITION_JOB_NAME}")

    while True:
        job = batch_api.read_namespaced_job(
            name=PARTITION_JOB_NAME,
            namespace=NAMESPACE,
        )

        status = job.status

        succeeded = status.succeeded or 0
        failed = status.failed or 0
        active = status.active or 0

        print(
            f"Job status: active={active}, "
            f"succeeded={succeeded}, "
            f"failed={failed}, "
            f"expected={PARTITION_COUNT}"
        )

        if succeeded >= PARTITION_COUNT:
            print("Indexed Job completed successfully")
            return

        if status.conditions:
            for condition in status.conditions:
                if condition.type == "Failed" and condition.status == "True":
                    raise RuntimeError(
                        f"Job failed: {condition.reason} - {condition.message}"
                    )

        time.sleep(5)


def main():
    print("Pipeline driver started")
    print(f"Namespace: {NAMESPACE}")
    print(f"Run ID: {RUN_ID}")

    load_kube_config()

    batch_api = client.BatchV1Api()

    create_indexed_job(batch_api)
    wait_for_job(batch_api)

    print("Pipeline driver completed successfully")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"Driver failed: {error}", file=sys.stderr)
        sys.exit(1)