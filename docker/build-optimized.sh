#!/bin/bash

# Optimized build script for the biodev Docker image
# Uses the optimized multi-stage Dockerfile for smaller image sizes
# Usage: ./build-optimized.sh [--multi-arch|-m] [--tag|-t TAG]

set -e

IMAGE_NAME="schirmerlab/biodev"

# Generate default tag in YY.MM.DD format
DEFAULT_TAG=$(date +%y.%m.%d)
IMAGE_TAG="${DEFAULT_TAG}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Optimized Docker Build for Bioinformatics DevContainer${NC}"
echo "======================================================="
echo -e "${BLUE}Expected size reduction: 30-40% (target: ~7-8GB vs original ~11GB)${NC}"
echo ""

# Parse command line arguments
MULTI_ARCH=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --multi-arch|-m)
            MULTI_ARCH=true
            shift
            ;;
        --tag|-t)
            IMAGE_TAG="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  --multi-arch, -m    Build for multiple architectures (linux/amd64,linux/arm64)"
            echo "  --tag, -t TAG       Set image tag (default: YY.MM.DD format, today: $DEFAULT_TAG)"
            echo "  --help, -h          Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                           # Single arch build with date tag"
            echo "  $0 --tag 1.2.0              # Single arch build with custom tag"
            echo "  $0 --multi-arch              # Multi arch build with date tag"
            echo "  $0 -m -t latest              # Multi arch build with custom tag"
            exit 0
            ;;
        *)
            echo -e "${RED}❌ Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Set final image name
FULL_IMAGE="${IMAGE_NAME}:${IMAGE_TAG}"

# Display build configuration
if [ "$MULTI_ARCH" = true ]; then
    echo -e "${YELLOW}📦 Multi-architecture build requested${NC}"
else
    echo -e "${YELLOW}📦 Single-architecture build (current platform)${NC}"
    echo -e "${YELLOW}💡 Use --multi-arch or -m for multi-platform build${NC}"
fi
echo -e "${BLUE}🏷️  Image tag: ${IMAGE_TAG}${NC}"

if [ "$MULTI_ARCH" = true ]; then
    # Multi-arch build
    echo -e "${GREEN}🔄 Multi-architecture build...${NC}"
    echo -e "${GREEN}🏷️  Building: $FULL_IMAGE${NC}"

    # Create buildx builder if it doesn't exist
    docker buildx create --name biodev-builder --use 2>/dev/null || docker buildx use biodev-builder 2>/dev/null || true

    # Build and push multi-arch image
    docker buildx build \
        --platform linux/amd64,linux/arm64 \
        --tag "$FULL_IMAGE" \
        --file docker/Dockerfile.optimized \
        --push \
        docker/

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Multi-arch build completed successfully!${NC}"
        echo -e "${GREEN}📊 Image pushed to registry with both amd64 and arm64 support${NC}"
    else
        echo -e "${RED}❌ Multi-arch build failed!${NC}"
        exit 1
    fi
else
    # Single platform build
    echo -e "${GREEN}🏗️  Building for current platform...${NC}"
    echo -e "${GREEN}🏷️  Building: $FULL_IMAGE${NC}"

    # Build the optimized image
    docker build -t "$FULL_IMAGE" -f docker/Dockerfile.optimized docker/

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Build completed successfully!${NC}"

        # Show image size comparison
        echo -e "${GREEN}📊 Image size information:${NC}"
        docker images | grep -E "(biodev|schirmerlab)" | head -5

        # Test the container
        echo -e "${GREEN}🧪 Testing the optimized container...${NC}"
        docker run --rm "$FULL_IMAGE" bash -c "
            echo 'Container architecture:' && uname -m &&
            echo 'Python version:' && python --version &&
            echo 'R version:' && R --version | head -1 &&
            echo 'Available Jupyter kernels:' &&
            jupyter kernelspec list &&
            echo 'MMSeqs2 available:' && mmseqs version | head -1 &&
            echo 'Sample bioinformatics tools:' &&
            samtools --version | head -1 &&
            echo 'Conda environment size:' && du -sh /opt/conda
        "

        echo ""
        echo -e "${GREEN}🎯 Usage examples:${NC}"
        echo "  docker run -p 8888:8888 $FULL_IMAGE"
        echo "  docker run -it $FULL_IMAGE bash"
        echo ""
        echo -e "${BLUE}💡 Optimization summary:${NC}"
        echo "  ✅ Multi-stage build (separates build/runtime)"
        echo "  ✅ Removed development packages from runtime"
        echo "  ✅ Aggressive conda cache cleanup"
        echo "  ✅ Optimized system package selection"
        echo "  ✅ Binary installation for select tools"

    else
        echo -e "${RED}❌ Build failed!${NC}"
        exit 1
    fi
fi