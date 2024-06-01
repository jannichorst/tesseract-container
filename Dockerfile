# Use the official Python image from the Docker Hub (Alpine version)
FROM python:3.9-alpine

# Set environment variables to prevent Python from writing .pyc files to disk
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory in the container
WORKDIR /code

# Install dependencies
COPY ./src/requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# Install Tesseract dependencies and Tesseract itself
RUN apk update && \
    apk add --no-cache tesseract-ocr tesseract-ocr-data-eng

# Copy the rest of the application code to the working directory
COPY ./src/app /code/app

# Expose the port the app runs on
EXPOSE 8000

# Run the FastAPI application using Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
