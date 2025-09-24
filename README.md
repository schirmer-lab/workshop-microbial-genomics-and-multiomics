# Course Pilot

A Docker-based development environment for data science courses with Python, R, and Jupyter support.

## Requirements

Before you can use this development environment, make sure you have the following installed:

### Essential Requirements
- **Docker Desktop** (v4.0+)
  - Windows: [Download Docker Desktop for Windows](https://docs.docker.com/desktop/install/windows-install/)
  - macOS: [Download Docker Desktop for Mac](https://docs.docker.com/desktop/install/mac-install/)
  - Linux: [Install Docker Engine](https://docs.docker.com/engine/install/) + [Docker Compose](https://docs.docker.com/compose/install/)

- **Visual Studio Code** (latest version)
  - [Download VS Code](https://code.visualstudio.com/download)

- **Dev Containers Extension** for VS Code
  - Install from VS Code: `Ctrl+Shift+X` → search "Dev Containers" → Install
  - Or [install directly](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)

### Platform-Specific Notes
- **Windows**: WSL2 is recommended for better Docker performance
- **macOS**: Ensure Docker Desktop has sufficient memory allocated (8GB+ recommended)
- **Linux**: User must be in the `docker` group to run Docker without sudo

### Storage Requirements
- **Available disk space**: 5-10GB for Docker images and container data
- **Data directory**: The container will create `~/biodata` on your host system for persistent storage

## Quick Start

1. Open this project in VS Code
2. When prompted, click "Reopen in Container"
3. The development environment will be ready with all dependencies installed

## Docker Setup

This project uses a modular Docker setup with separate dependency files:

- `docker/Dockerfile` - Main Docker image definition
- `docker/packages.txt` - Ubuntu system packages
- `docker/environment.yml` - Python packages (conda)
- `docker/r_packages.R` - R packages

By default, the dev container uses a pre-built image from Docker Hub for faster startup. You can switch to local building when you need to modify dependencies.

See `docker/README.md` for detailed Docker setup and usage instructions.

## Features

- **Python 3.10**: Scientific computing stack (NumPy, Pandas, Matplotlib, etc.)
- **R**: Statistical analysis packages (ggplot2, dplyr, vegan, etc.)
- **Bioinformatics Tools**: Comprehensive suite including samtools, bcftools, bedtools, minimap2, flye, prokka, and nanopore analysis tools
- **Jupyter Kernels**: Both Python and R kernels available in VS Code
- **VS Code Integration**: Pre-configured extensions and settings for notebook development
- **Ubuntu 24.04**: Clean, modern base system with micromamba for package management
