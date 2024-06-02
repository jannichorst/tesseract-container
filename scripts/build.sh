#!/bin/sh

# Navigate to the root directory of the repository
SCRIPT_DIR=$(dirname "$0")
cd "$SCRIPT_DIR/.."

# Build the Docker image
# To add more languages, add them to the TESS_LANGS argument like: --build-arg TESS_LANGS="eng deu spa fra ..."
# See the list of available languages and language codes at: https://tesseract-ocr.github.io/tessdoc/Data-Files

docker build --build-arg TESS_LANGS="eng" -t tesseract-ocr .
