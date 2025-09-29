#!/bin/bash

# Multi-platform build script using Docker Buildx
# This script builds the Docker image for multiple architectures

set -e

IMAGE_NAME="schirmerlab/biodev"
IMAGE_TAG="1.0"
FULL_IMAGE="${IMAGE_NAME}:${IMAGE_TAG}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🔧 Multi-Platform Docker Build for Bioinformatics DevContainer${NC}"
echo "================================================="

# Check if docker buildx is available
if ! docker buildx version > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker Buildx is not available. Please ensure Docker Desktop is updated.${NC}"
    exit 1
fi

# Create a new builder instance if it doesn't exist
BUILDER_NAME="biodev-builder"
if ! docker buildx ls | grep -q "$BUILDER_NAME"; then
    echo -e "${YELLOW}📦 Creating new buildx builder: $BUILDER_NAME${NC}"
    docker buildx create --name "$BUILDER_NAME" --driver docker-container --bootstrap
fi

# Use the builder
echo -e "${YELLOW}🔄 Using buildx builder: $BUILDER_NAME${NC}"
docker buildx use "$BUILDER_NAME"

# Build options
PLATFORMS="linux/amd64,linux/arm64"
BUILD_DIR="docker"

echo -e "${GREEN}🏗️  Building for platforms: $PLATFORMS${NC}"
echo -e "${GREEN}📁 Build context: $BUILD_DIR${NC}"
echo -e "${GREEN}🏷️  Image: $FULL_IMAGE${NC}"

# Check if user wants to push to registry
read -p "Do you want to push to registry? [y/N]: " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    PUSH_FLAG="--push"
    echo -e "${YELLOW}📤 Will push to registry after build${NC}"
else
    PUSH_FLAG="--load"
    echo -e "${YELLOW}💾 Will load image locally (single platform only)${NC}"
    # For local loading, we need to choose one platform
    PLATFORMS="linux/amd64"
fi

# Build the image
echo -e "${GREEN}🔨 Starting multi-platform build...${NC}"
docker buildx build \
    --platform "$PLATFORMS" \
    --tag "$FULL_IMAGE" \
    --file "$BUILD_DIR/Dockerfile" \
    $PUSH_FLAG \
    "$BUILD_DIR/"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Build completed successfully!${NC}"

    if [[ $PUSH_FLAG == "--load" ]]; then
        echo -e "${GREEN}🧪 Testing the locally built image...${NC}"
        docker run --rm "$FULL_IMAGE" bash -c "echo 'Container architecture:' && uname -m && echo 'Python version:' && python --version"
    else
        echo -e "${GREEN}📤 Image pushed to registry for platforms: $PLATFORMS${NC}"
    fi

    echo ""
    echo -e "${GREEN}🎯 Usage examples:${NC}"
    echo "  docker run -p 8888:8888 $FULL_IMAGE"
    echo "  docker run -it $FULL_IMAGE bash"
    echo "  docker run --rm $FULL_IMAGE jupyter kernelspec list"

else
    echo -e "${RED}❌ Build failed!${NC}"
    exit 1
fi