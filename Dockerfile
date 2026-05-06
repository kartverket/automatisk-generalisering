# Use a small Python base image
FROM ghcr.io/kartverket/arcpy-linux:12.0

# Set working directory
WORKDIR /app

# Copy project files
COPY . /app


# Make the project script the container entrypoint
ENV SCALE=n100 OBJECT=road
CMD ["sh","-c","python main.py --scale ${SCALE} --object ${OBJECT}"]

