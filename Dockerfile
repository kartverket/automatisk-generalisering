# Use a small Python base image
FROM ghcr.io/kartverket/arcpy-linux:12.0

# Set working directory
WORKDIR /app

# Copy project files
COPY . /app

#install dependencies
RUN python -m pip install --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r requirements.txt
#Change where arcpy writes temp files to avoid read-only issues
#After changing environment variable for the server it needs to be restarted for the change to take effect
ENV SERVER_TEMP_DIR=/tmp
RUN /arcgis/server/startserver.sh

# Make the project script the container entrypoint
ENV SCALE=scale OBJECT=object
CMD ["sh","-c","python main.py --scale ${SCALE} --object ${OBJECT}"]

