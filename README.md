## Building and Running the Docker Container

To build and run the Docker container, you can use the provided shell script. Ensure you have Docker installed and running on your system.

1. Open a terminal and navigate to the root directory of this repository.
2. Run the following command:

    ```sh
    ./build_and_run.sh
    ```

This script will:
- Build the Docker image with the tag `tesseract-39alpine`.
- Stop and remove any existing container named `tesseract-smal`.
- Run a new container named `tesseract-smal` and map port 8000 on your host to port 8000 on the container.

Your FastAPI application should now be accessible at `http://localhost:8000`.
