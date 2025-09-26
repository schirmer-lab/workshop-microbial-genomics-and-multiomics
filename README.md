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

> **Note**: If you're updating from a previous version, you may need to rebuild the container to get the latest improvements. Use `Ctrl+Shift+P` → "Dev Containers: Rebuild Container" to ensure you have the latest setup.

## Docker Setup

This project uses a modular Docker setup with separate dependency files:

- `docker/Dockerfile` - Main Docker image definition
- `docker/packages.txt` - Ubuntu system packages
- `docker/environment.yml` - Python packages (conda)
- `docker/r_packages.R` - R packages

By default, the dev container uses a pre-built image from Docker Hub for faster startup. You can switch to local building when you need to modify dependencies.

See `docker/README.md` for detailed Docker setup and usage instructions.

## Working with R Notebooks

### First Time Setup - Selecting the R Kernel

When you first open an R notebook (like `hello-world-r.ipynb`), you'll need to select the appropriate kernel:

1. **Open the R notebook** file in VS Code
2. **Click "Select Kernel"** button in the top-right corner of the notebook interface
3. **Choose "Jupyter Kernel..."** from the dropdown menu
4. **Look for the R kernel** - it will be listed under "Jupyter Kernels" section as **"R"**

> **Important**: The R kernel appears under the "Jupyter Kernels" section, not under language-specific kernels. Look for an entry simply labeled "R".

### R Language Server

The first time you work with R files, you might see a popup asking about installing the R `languageserver` package. This has been **pre-installed** in the container to provide enhanced R features like:
- Code completion and IntelliSense
- Function signatures and documentation
- Error detection and linting

If you still see this popup, simply click "Yes" or "No" based on your preference - the package is already available.

### Troubleshooting

**Can't find the R kernel?**
- Ensure you're looking in the "Jupyter Kernels" section, not other categories
- Try refreshing the kernel list or restarting VS Code
- Verify the dev container has fully loaded (check the bottom-left corner for "Dev Container" indicator)

**R code not executing?**
- Make sure you've selected the R kernel (see instructions above)
- Check that the cell type is set to "Code" not "Markdown"

## Features

- **Python 3.10**: Scientific computing stack (NumPy, Pandas, Matplotlib, etc.)
- **R**: Statistical analysis packages (ggplot2, dplyr, vegan, etc.) with pre-configured language server
- **Bioinformatics Tools**: Comprehensive suite including samtools, bcftools, bedtools, minimap2, flye, prokka, and nanopore analysis tools
- **Jupyter Kernels**: Both Python and R kernels available in VS Code with seamless integration
- **VS Code Integration**: Pre-configured extensions and settings for notebook development
- **Ubuntu 24.04**: Clean, modern base system with micromamba for package management
