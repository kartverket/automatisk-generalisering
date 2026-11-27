FROM python:3.11-slim

RUN pip install kubernetes
RUN pip install minio

COPY pod_orchestrator.py /app/pod_orchestrator.py

CMD ["python", "/app/pod_orchestrator.py"]