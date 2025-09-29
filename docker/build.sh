#!/bin/bash

# Build script for the biodev Docker image
# This script supports both single-platform and multi-platform builds

set -e

IMAGE_NAME="schirmerlab/biodev"
IMAGE_TAG="1.0"
FULL_IMAGE="${IMAGE_NAME}:${IMAGE_TAG}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🔧 Docker Build for Bioinformatics DevContainer${NC}"
echo "============================================="

# Check command line arguments
MULTI_ARCH=false
if [[ "$1" == "--multi-arch" || "$1" == "-m" ]]; then
    MULTI_ARCH=true
    echo -e "${YELLOW}📦 Multi-architecture build requested${NC}"
else
    echo -e "${YELLOW}📦 Single-architecture build (current platform)${NC}"
    echo -e "${YELLOW}💡 Use --multi-arch or -m for multi-platform build${NC}"
fi

if [ "$MULTI_ARCH" = true ]; then
    # Use the multi-arch build script
    echo -e "${GREEN}🔄 Switching to multi-architecture build...${NC}"
    exec ./docker/build-multiarch.sh
else
    # Single platform build
    echo -e "${GREEN}🏗️  Building for current platform...${NC}"
    echo -e "${GREEN}🏷️  Image: $FULL_IMAGE${NC}"

    # Build the image
    docker build -t "$FULL_IMAGE" -f docker/Dockerfile docker/

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Build completed successfully!${NC}"

        # Test the container
        echo -e "${GREEN}🧪 Testing the container...${NC}"
        docker run --rm "$FULL_IMAGE" bash -c "
            echo 'Container architecture:' && uname -m &&
            echo 'Python version:' && python --version &&
            echo 'Available Jupyter kernels:' &&
            jupyter kernelspec list
        "

        echo ""
        echo -e "${GREEN}🎯 Usage examples:${NC}"
        echo "  docker run -p 8888:8888 $FULL_IMAGE"
        echo "  docker run -it $FULL_IMAGE bash"
        echo "  docker-compose up biodev"

    else
        echo -e "${RED}❌ Build failed!${NC}"
        exit 1
    fi
fi