![CI Worklfow](https://github.com/jannichorst/tesseract-container/actions/workflows/ci.yml/badge.svg)

# Tesseract Container

This repository contains a FastAPI application that uses [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) to extract text from images and PDFs. The application exposes several endpoints to upload files, retrieve analysis results, generate searchable PDFs, and check the health of the service.

## ✨ Features
- ✅ OCR on Images and PDFs
- ✅ REST Endpoints
- ✅ Sync / Async Support
- ✅ Create searchable PDFs
- ✅ Add more languages with ease

## 📖 Contents
- [👩‍💻 Getting Started](#getting-started)
- [🔗 Endpoints](#endpoints)
- [🐳 Build Your Own Image](#build-image)
- [🛠️ About this Repository](#about)
- [📚 References](#references)

 <a name="getting-started"/> 

## 👩‍💻 Getting Started

### 1. Pull Image
```sh
docker pull jannichorst/tesseract-ocr:latest
```

### 2. Run Container
```sh
docker run -d -p 8000:8000 jannichorst/tesseract-ocr:latest
```

### 3. Usage
Access the Swagger documentation under [http://localhost:8000/docs](http://localhost:8000/docs).

```python
import requests

url = "http://localhost:8000/ocr/"
file_path = "path_to_your_image_or_pdf.jpg"

with open(file_path, "rb") as file:
    files = {"file": file}
    response = requests.post(url, files=files)

print("OCR Result:", response.json())
```

> [!NOTE]
> **Check out more examples in the [demo.iypnb](examples/demo.ipynb) notebook**

 <a name="endpoints"/> 

## 🔗 Endpoints

### Perform OCR [SYNC]

- **URL**: `/ocr/`
- **Method**: `POST`
- **Request**: Multipart/form-data with a file, language (default: "eng"), DPI (optional), config (optional), and PSM (default: 3)
- **Response**: JSON containing OCR results and job information

Example using `curl`:

```sh
curl -X POST "http://localhost:8000/ocr/" -F "file=@path_to_your_file"
```

### Start OCR Processing [ASYNC]

- **URL**: `/start_ocr/`
- **Method**: `POST`
- **Request**: Multipart/form-data with a file, language (default: "eng"), DPI (optional), config (optional), and PSM (default: 3)
- **Response**: JSON containing a task ID

Example using `curl`:

```sh
curl -X POST "http://localhost:8000/start_ocr/" -F "file=@path_to_your_file"
```

### Get OCR Results

- **URL**: `/results/{task_id}`
- **Method**: `GET`
- **Request**: Path parameter with the task ID
- **Response**: JSON containing the OCR results or the status of the task

Example using `curl`:

```sh
curl "http://localhost:8000/results/{task_id}"
```

### Create Searchable PDF [SYNC]

- **URL**: `/create_searchable/`
- **Method**: `POST`
- **Request**: Multipart/form-data with a file, language (default: "eng"), DPI (optional), PSM (default: 3), and config (optional)
- **Response**: Searchable PDF file

Example using `curl`:

```sh
curl -X POST "http://localhost:8000/create_searchable/" -F "file=@path_to_your_file" --output output_ocr.pdf
```

### Get Jobs

- **URL**: `/jobs`
- **Method**: `GET`
- **Request**: Query parameter for status (default: "pending")
- **Response**: JSON containing job information

Example using `curl`:

```sh
curl "http://localhost:8000/jobs?status=all"
```

### Get System Information

- **URL**: `/info`
- **Method**: `GET`
- **Response**: JSON containing system information

Example using `curl`:

```sh
curl "http://localhost:8000/info"
```

### Health Check

- **URL**: `/health`
- **Method**: `GET`
- **Response**: JSON indicating the health status of the application

Example using `curl`:

```sh
curl "http://localhost:8000/health"
```

### Swagger Documentation

- **URL**: `/docs`
- **Method**: `GET`
- **Response**: Autogenerated documentation & testing area

 <a name="build-image"/> 

## 🐳 Build Image Yourself
>[!NOTE]
>For the full guide on how to add more languages see: [How to add lmore anguages](docs/Install-different-language.md)

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

4. Check out the examples in [demo.ipynb](demo.ipynb) and install the required packages with:

    ```sh
    pip install -r requirements.txt
    ```

 <a name="about"/> 

## About this Repository

The main application code is located in `src/app/main.py`. The Dockerfile and scripts for building and running the container are located in the root directory and the `scripts` directory, respectively. Under `tests` you find a Postman collection that can be run with `run-postman-collection.sh` (needs [Newman CLI](https://github.com/postmanlabs/newman)). 

### Directory Structure

```
tesseract-container
├── Dockerfile
├── README.md
├── requirements.txt
├── examples
│   └── demo.ipynb
├── scripts
│   ├── build.sh
│   ├── run.sh
│   ├── build_and_run.sh
│   └── run-postman-collection.sh
├── src
│   ├── requirements.txt
│   └── app
│       ├── main.py
│       └── ...
└── tests
    ├── postman_collection.json
    ├── test-image.jpg
    └── ...
```
 <a name="references"/> 

## References

- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract)
- [Improve Tesseract Performance (Guide)](https://tesseract-ocr.github.io/tessdoc/ImproveQuality.html)
- [Tesseract Page Segmentation Modes (PSM) Exaplaind](https://pyimagesearch.com/2021/11/15/tesseract-page-segmentation-modes-psms-explained-how-to-improve-your-ocr-accuracy/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Docker Documentation](https://docs.docker.com/)
