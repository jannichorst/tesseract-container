# Stop and remove any existing container with the same name
docker stop tesseract-ocr || true
docker rm tesseract-ocr || true

# Run the Docker container
docker run -d --name tesseract-ocr -p 8000:8000 tesseract-ocr