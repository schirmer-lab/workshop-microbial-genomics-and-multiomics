# Docker Setup for Course Pilot

This repository uses Docker to provide a consistent development environment with Python, R, and Jupyter support.

## Structure

```
docker/
├── Dockerfile          # Docker image definition
├── packages.txt        # Ubuntu system packages
└── environment.yml     # Python and R packages (conda)
```

## Using the Environment

This setup is designed for VS Code development with Jupyter notebooks as `.ipynb` files, not browser-based Jupyter.

### Option 1: Published Docker Image (Default)

The devcontainer is configured to use a pre-built image from Docker Hub:

1. Open the project in VS Code
2. When prompted, click "Reopen in Container"
3. VS Code will pull the published image and start the container
4. Open any `.ipynb` file in VS Code
5. Select either "Python 3.10 (course-pilot)" or "R" kernel when prompted

### Option 2: Build Locally

If you need to modify dependencies or build a custom image:

1. Edit the dependency files as needed:
   - `docker/packages.txt` - Add/remove Ubuntu packages
   - `docker/environment.yml` - Add/remove Python and R packages

2. Switch to local building by editing `.devcontainer/devcontainer.json`:
   ```json
   {
     // Comment out this line:
     // "image": "your-dockerhub-username/course-pilot:latest",
     
     // Uncomment these lines:
     "dockerFile": "../docker/Dockerfile",
     "context": "../docker",
   }
   ```

3. Rebuild the container: `Ctrl+Shift+P` → "Dev Containers: Rebuild Container"

## Building and Publishing the Docker Image

### Build the Image

From the project root:

```bash
cd docker
./docker/build.sh
```

### Push to Docker Hub 

```bash
docker push schirmerlab/biodev:1.0 
```

## Updating Dependencies

### Adding Ubuntu Packages

Edit `docker/packages.txt` and add package names (one per line):

```
# Example additions
htop
tree
nano
```

### Adding Python Packages

Edit `docker/environment.yml`:

```yaml
dependencies:
  - python=3.10
  - numpy
  - your-new-package
  - pip:
    - another-pip-package
```

#### Bioinformatics Tools Included

**Conda/Bioconda packages:**
- Assembly: flye, polypolish
- Alignment: minimap2, samtools, bcftools
- Analysis: bedtools, seqkit, fastani
- Annotation: prokka
- Quality Control: fastp, nanofilt, nanoplot, rasusa
- Libraries: biopython, bamtools

**Pip packages:**
- dnaapler, pod5, porechop_abi, trimnami, pypolca

### Adding R Packages

Edit `docker/environment.yml` and add R packages using conda-forge or bioconda channels:

```yaml
dependencies:
  # R packages from conda-forge
  - conda-forge::r-your-package
  - conda-forge::r-another-package
  
  # R Bioconductor packages from bioconda
  - bioconda::bioconductor-yourpackage
```

**Benefits of conda-managed R packages:**
- Pre-compiled binaries (no compilation errors)
- Automatic system dependency management
- Consistent dependency resolution
- Faster, more reliable installations

## Switching Between Modes

### To Published Image Mode
1. Edit `.devcontainer/devcontainer.json`
2. Uncomment the `"image"` line
3. Comment out the `"dockerFile"` and `"context"` lines
4. Rebuild container

### To Local Build Mode
1. Edit `.devcontainer/devcontainer.json`
2. Comment out the `"image"` line
3. Uncomment the `"dockerFile"` and `"context"` lines
4. Rebuild container

## Troubleshooting

- If packages fail to install, check the syntax in the respective dependency files
- For R package installation issues, check if system dependencies are available in `packages.txt`
- Use `docker logs <container-id>` to debug build issues