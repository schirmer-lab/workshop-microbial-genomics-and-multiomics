#!/bin/bash

# Build script for the biodev Docker image
# This script builds the Docker image with proper tagging

set -e

echo "Building schirmerlab/biodev:1.0 Docker image..."

# Build the image
docker build -t schirmerlab/biodev:1.0 -f docker/Dockerfile docker/

echo "Build completed successfully!"

# Optionally test the container
echo "Testing the container (optional)..."
echo "Run: docker run -p 8888:8888 schirmerlab/biodev:1.0"
echo "Or run interactively: docker run -it schirmerlab/biodev:1.0 bash"

# Show available kernels
echo "Checking available Jupyter kernels in the container..."
docker run --rm schirmerlab/biodev:1.0 bash -c "eval \"\$(micromamba shell hook -s bash)\" && micromamba activate base && jupyter kernelspec list"