#!/bin/sh

# Navigate to the root directory of the repository
SCRIPT_DIR=$(dirname "$0")
cd "$SCRIPT_DIR/.."

# Build the Docker image
docker build -t tesseract-ocr .