# Use a small Python base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy project files
COPY . /app




# Make the project script the container entrypoint
ENTRYPOINT ["python", "main.py"]

