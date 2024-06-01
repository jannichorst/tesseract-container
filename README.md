# Tesseract Container

This repository contains a FastAPI application that uses [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) to extract text from images. The application exposes several endpoints to upload images, retrieve analysis results and check the health of the service.

## Getting Started

### Prerequisites

- [Docker](https://www.docker.com/get-started)

### Installation

1. Clone the repository:

    ```sh
    git clone https://github.com/jannichorst/tesseract-container.git
    cd tesseract-container
    ```

2. To build and run the Docker container in one step:

    ```sh
    ./scripts/build_and_run.sh
    ```
3. Access the Swagger documentation under [http://localhost:8000/docs](http://localhost:8000/docs).
4. Checkout the examples in [demo.ipynb](demo.ipynb) and install the required packages with:
    ```sh
    pip install -r requirements.txt
    ``` 
    

## Endpoints

### Upload Image for Analysis

- **URL**: `/analyzeDocument/`
- **Method**: `POST`
- **Request**: Multipart/form-data with an image file
- **Response**: JSON containing a task ID

Example using `curl`:

```sh
curl -X POST "http://localhost:8000/analyzeDocument/" -F "file=@path_to_your_image_file"
```

### Get Analysis Results

- **URL**: `/analyzeResults/{task_id}`
- **Method**: `GET`
- **Request**: Path parameter with the task ID
- **Response**: JSON containing the OCR results or the status of the task

Example using `curl`:

```sh
curl "http://localhost:8000/analyzeResults/{task_id}"
```

### Health Check

- **URL**: `/health`
- **Method**: `GET`
- **Response**: JSON indicating the health status of the application

Example using `curl`:

```sh
curl "http://localhost:8000/health"
```

### List File System Structure

- **URL**: `/fs`
- **Method**: `GET`
- **Response**: JSON representation of the file system structure

Example using `curl`:

```sh
curl "http://localhost:8000/fs"
```

### Swagger Documentation

- **URL**: `/docs`
- **Method**: `GET`
- **Response**: Autogenerated documentation & testing area


## Examples

This repository includes a Jupyter notebook called [demo.ipynb](demo.ipynb) which contains examples on how to use the provided endpoints. You can find the notebook in the root directory of the repository.

## Source Code

The main application code is located in `src/app/main.py`. The Dockerfile and scripts for building and running the container are located in the root directory and the `scripts` directory, respectively.

### Directory Structure

```
tesseract-container
├── Dockerfile
├── README.md
├── demo.ipynb
├── scripts
│   ├── build.sh
│   ├── run.sh
│   └── build_and_run.sh
└── src
    ├── requirements.txt
    └── app
        ├── main.py
        └── ...
```

## References

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract)
- [Docker Documentation](https://docs.docker.com/)
