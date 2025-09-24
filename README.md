# Course Pilot

A Docker-based development environment for data science courses with Python, R, and Jupyter support.

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
