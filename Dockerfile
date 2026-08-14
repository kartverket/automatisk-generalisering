# Use a small Python base image
FROM ghcr.io/kartverket/arcpy-linux:12.0 AS base

# Set working directory
WORKDIR /app

# Copy project files
COPY . /app

ENV PYTHONPATH=/app

#install dependencies
RUN python -m pip install --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r requirements.txt
#Change where arcpy writes temp files to avoid read-only issues
#After changing environment variable for the server it needs to be restarted for the change to take effect
ENV SERVER_TEMP_DIR=/tmp
RUN /arcgis/server/startserver.sh

# Make the project script the container entrypoint
ENV SCALE=scale OBJECT=object


# Define separate entrypoints for on-prem and on-cloud modes
# Build image with --target on_prem/on_cloud and tag on_prem/on_cloud accordingly
FROM base AS on_prem
CMD ["python", "main_on_prem.py"]

FROM base AS on_cloud
CMD ["python", "main_on_cloud.py"]

FROM base AS run_partition
CMD ["python", "temp_skip_folder/core/pipelines/run_partition.py"]