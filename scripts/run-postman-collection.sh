#!/bin/sh

# Run Postman Collection using Newman CLI Tool
newman run tests/full-api-test.postman_collection.json --delay-request 1000