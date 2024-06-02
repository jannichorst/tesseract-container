# Use the official Python image from the Docker Hub (Alpine version)
FROM python:3.11-alpine

# Set environment variables to prevent Python from writing .pyc files to disk
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory in the container
WORKDIR /code

# Update pip and setuptools to the latest version
RUN pip install --no-cache-dir --upgrade pip setuptools

# Install dependencies
COPY ./src/requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# Default Tesseract languages (can be overridden at build time like "--build-arg TESS_LANGS="eng deu ...")
ARG TESS_LANGS="eng"
ENV TESS_LANGS=${TESS_LANGS}

# Install Tesseract dependencies and Tesseract itself along with specified languages
RUN apk update && \
    apk add --no-cache tesseract-ocr && \
    for lang in $(echo $TESS_LANGS | tr "," " "); do \
        apk add --no-cache tesseract-ocr-data-$lang; \
    done

# Install Poppler utilities for PDF processing
RUN apk add --no-cache poppler-utils

# Copy the rest of the application code to the working directory
COPY ./src/app /code/app

# Expose the port the app runs on
EXPOSE 8000

# Run the FastAPI application using Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
