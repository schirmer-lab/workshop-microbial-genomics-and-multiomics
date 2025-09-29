#!/bin/bash
set -e

# Script to create platform-specific environment.yml files
# Auto-detect architecture if TARGETARCH not set (for local runs)
if [ -z "$TARGETARCH" ]; then
    case "$(uname -m)" in
        x86_64) DETECTED_ARCH="amd64" ;;
        aarch64|arm64) DETECTED_ARCH="arm64" ;;
        *) DETECTED_ARCH="amd64" ;;
    esac
    ARCH=${DETECTED_ARCH}
    echo "Auto-detected architecture: $ARCH (from uname -m: $(uname -m))"
else
    ARCH=${TARGETARCH}
    echo "Using Docker TARGETARCH: $ARCH"
fi

BASE_ENV="/tmp/environment.yml"
TARGET_ENV="/tmp/environment-${ARCH}.yml"

echo "Creating platform-specific environment for: $ARCH"

# Start with base environment structure
cat > "$TARGET_ENV" << 'EOF'
channels:
  - conda-forge
  - bioconda
dependencies:
EOF

# Add common packages first
cat >> "$TARGET_ENV" << 'EOF'
  # Core scientific computing (from conda-forge)
  - python=3.10
  - pip
  - numpy
  - pandas
  - matplotlib
  - seaborn
  - scipy
  - scikit-learn
  - h5py
  - tqdm

  # Jupyter (from conda-forge)
  - conda-forge::biopython
  - conda-forge::jupyter
  - conda-forge::jupyterlab
  - conda-forge::notebook
  - conda-forge::ipykernel
  - conda-forge::nbconvert
  - conda-forge::ipywidgets

  # R and R packages (from conda-forge) - let conda resolve versions
  - conda-forge::r-base=4.3.*
  - conda-forge::r-irkernel
  - conda-forge::r-tidyverse
  - conda-forge::r-devtools
  - conda-forge::r-remotes
  - conda-forge::r-biocmanager
  - conda-forge::r-ggpubr
  - conda-forge::r-vegan
  - conda-forge::r-languageserver
EOF

# Add architecture-specific packages
case "$ARCH" in
    arm64|aarch64)
        echo "Adding ARM64-compatible bioinformatics packages..."
        cat >> "$TARGET_ENV" << 'EOF'

  # Bioinformatics (ARM64-compatible subset from bioconda)
  - bioconda::samtools
  - bioconda::bcftools
  - bioconda::bedtools
  - bioconda::minimap2
  - bioconda::seqkit
  - bioconda::fastp
  - bioconda::bamtools
  - bioconda::blast
  - bioconda::nanofilt
  - bioconda::nanoplot

  # Additional packages that usually work on ARM64
  # Note: Some packages like lrge, medaka, prokka may not be available
  # They can be installed via pip if needed
EOF
        ;;

    amd64|x86_64)
        echo "Adding full x86_64 bioinformatics suite..."
        cat >> "$TARGET_ENV" << 'EOF'

  # Additional R packages (x86_64 only - not available on ARM64)
  - conda-forge::r-fossil
  - conda-forge::r-taxonomizr

  # Bioinformatics (full suite for x86_64 from bioconda)
  - bioconda::samtools
  - bioconda::bcftools
  - bioconda::bedtools
  - bioconda::minimap2
  - bioconda::seqkit
  - bioconda::flye
  - bioconda::fastani
  - bioconda::fastp
  - bioconda::bamtools
  - bioconda::blast

  # Nanopore tools (explicitly from bioconda)
  - bioconda::nanofilt
  - bioconda::nanoplot
  - bioconda::rasusa
  - bioconda::porechop_abi
  - bioconda::filtlong
  - bioconda::lrge
  - bioconda::dnaapler
  - bioconda::medaka

  # R Bioconductor packages (from bioconda)
  - bioconda::bioconductor-maaslin2
EOF
        ;;

    *)
        echo "Warning: Unknown architecture $ARCH, using minimal configuration"
        cat >> "$TARGET_ENV" << 'EOF'

  # Minimal bioinformatics packages (most likely to work)
  - bioconda::samtools
  - bioconda::bcftools
  - bioconda::minimap2
EOF
        ;;
esac

echo "Environment file for $ARCH created at $TARGET_ENV"
echo "Contents:"
cat "$TARGET_ENV"