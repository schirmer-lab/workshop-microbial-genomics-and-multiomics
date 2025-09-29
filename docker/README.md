# Multi-Architecture Docker Setup for Course Pilot

This repository provides a consistent bioinformatics development environment with Python, R, and Jupyter support that works reliably across different architectures (Intel/AMD x86_64 and Apple Silicon ARM64).

## 🏗️ Architecture Support

This DevContainer now supports:
- **Intel/AMD x86_64** (Linux, Windows, older Macs)
- **Apple Silicon ARM64** (M1/M2/M3 Macs)

The build system automatically detects the target architecture and installs compatible packages.

## Structure

```
docker/
├── Dockerfile              # Multi-arch Docker image definition
├── packages.txt           # Ubuntu system packages
├── environment.yml        # Base Python and R packages
├── create_platform_env.sh # Platform-specific package handler
├── environment-config.yml # Architecture-specific package lists
├── build.sh              # Smart build script
├── build-multiarch.sh    # Multi-platform build script
├── docker-compose.yml    # Container orchestration
└── test_environment.sh   # Comprehensive environment testing
```

## 🚀 Quick Start

### Option 1: Use Pre-built Multi-Arch Image (Recommended)

1. Open the project in VS Code
2. When prompted, click "Reopen in Container"
3. VS Code will pull the appropriate image for your architecture
4. Open any `.ipynb` file and select the Python or R kernel

### Option 2: Build Locally

#### Single Architecture (Current Platform)
```bash
cd docker
./build.sh
```

#### Multi-Architecture Build
```bash
cd docker
./build.sh --multi-arch
# or use the dedicated script
./build-multiarch.sh
```

#### Using Docker Compose
```bash
# Start development environment
docker-compose up biodev

# Test the environment
docker-compose run --rm biodev-test
```

## 🔧 Building and Publishing

### Prerequisites for Multi-Arch Builds

1. **Docker Buildx** (included in Docker Desktop 19.03+)
2. **QEMU emulation** (automatically set up by Docker Desktop)

### Build Commands

#### Local Development Build
```bash
./build.sh                    # Single arch (faster for development)
./build.sh --multi-arch      # Multi-arch (for publishing)
```

#### Publishing Multi-Arch Images
```bash
./build-multiarch.sh
# Follow the prompts to push to registry
```

### Manual Multi-Arch Build
```bash
# Create buildx builder
docker buildx create --name biodev-builder --driver docker-container --bootstrap
docker buildx use biodev-builder

# Build and push
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --tag schirmerlab/biodev:1.0 \
  --push \
  .
```

## 📦 Architecture-Specific Packages

### What Changes Between Architectures?

#### x86_64 (Full Suite)
- Complete bioconda package collection
- All nanopore tools (medaka, lrge, dnaapler)
- Full prokka annotation suite
- All R Bioconductor packages

#### ARM64 (Compatible Subset)
- Core bioinformatics tools (samtools, bcftools, bedtools)
- Most alignment and analysis tools
- Limited nanopore tool availability
- Some packages installed via pip fallback

### Bioinformatics Tools Included

#### Available on Both Architectures
- **Alignment**: minimap2, samtools, bcftools
- **Analysis**: bedtools, seqkit
- **Quality Control**: fastp, nanofilt, nanoplot
- **Libraries**: biopython, bamtools, blast

#### x86_64 Only (ARM64 may use alternatives)
- **Advanced Assembly**: flye, medaka
- **Specialized Tools**: lrge, dnaapler, prokka
- **Nanopore Suite**: rasusa, porechop_abi, filtlong

### Adding Dependencies

#### System Packages (`packages.txt`)
```bash
# Add Ubuntu packages (architecture-agnostic)
htop
tree
nano
```

#### Conda Packages (`environment.yml`)
```yaml
dependencies:
  - python=3.10
  - numpy
  - your-new-package

  # Bioconda packages (check ARM64 availability)
  - bioconda::your-bio-package
```

#### Architecture-Specific Packages
Modify `create_platform_env.sh` to handle architecture-specific packages:

```bash
case "$ARCH" in
    arm64|aarch64)
        # ARM64-specific handling
        echo "  - alternative-package-for-arm64" >> "$TARGET_ENV"
        ;;
    amd64|x86_64)
        # Full x86_64 package set
        echo "  - full-feature-package" >> "$TARGET_ENV"
        ;;
esac
```

## 🐛 Troubleshooting

### Common Architecture Issues

#### ARM64 Package Unavailable
```bash
# Error: PackagesNotFoundError: The following packages are not available from current channels: package-name
```
**Solution**: The package isn't available for ARM64. Options:
1. Find an alternative package
2. Install via pip if available
3. Use the x86_64 image with emulation (slower)

#### Emulation Performance
If you need x86_64-only packages on ARM64:
```bash
docker run --platform linux/amd64 schirmerlab/biodev:1.0
```
**Note**: This runs with emulation and will be significantly slower.

#### Build Failures
```bash
# Check build logs
docker buildx build --progress=plain --platform linux/arm64 .

# Test specific architecture
docker run --rm --platform linux/arm64 ubuntu:24.04 uname -m
```

### Development Workflow

#### Testing Both Architectures Locally
```bash
# Build for specific platforms
docker buildx build --platform linux/amd64 -t biodev:amd64 .
docker buildx build --platform linux/arm64 -t biodev:arm64 .

# Test each
docker run --rm biodev:amd64 ./test_environment.sh
docker run --rm biodev:arm64 ./test_environment.sh
```

#### DevContainer Configuration

##### Use Multi-Arch Published Image
```json
{
  "image": "schirmerlab/biodev:1.0",
  "customizations": {
    "vscode": {
      "extensions": ["ms-python.python", "ms-toolsai.jupyter"]
    }
  }
}
```

##### Local Development Build
```json
{
  "dockerFile": "../docker/Dockerfile",
  "context": "../docker",
  "build": {
    "args": {
      "BUILDKIT_INLINE_CACHE": "1"
    }
  }
}
```

### Performance Tips

1. **Use Native Architecture**: Always prefer native builds when possible
2. **Layer Caching**: Use `BUILDKIT_INLINE_CACHE=1` for better build caching
3. **Parallel Builds**: Use Docker Buildx for faster multi-platform builds
4. **Registry Caching**: Push intermediate layers to speed up subsequent builds

### Verification Commands

```bash
# Check image architecture
docker inspect schirmerlab/biodev:1.0 | grep Architecture

# Verify multi-platform manifest
docker buildx imagetools inspect schirmerlab/biodev:1.0

# Test environment in container
docker run --rm schirmerlab/biodev:1.0 ./test_environment.sh
```

## 🔄 CI/CD Integration

For automated multi-arch builds in GitHub Actions:

```yaml
- name: Set up Docker Buildx
  uses: docker/setup-buildx-action@v2

- name: Build and push multi-arch image
  uses: docker/build-push-action@v4
  with:
    context: docker/
    platforms: linux/amd64,linux/arm64
    push: true
    tags: schirmerlab/biodev:1.0
    cache-from: type=gha
    cache-to: type=gha,mode=max
```