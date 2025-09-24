# Use Ubuntu 24.04 as base
FROM ubuntu:24.04

# Set environment variables to prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

# Copy dependency files
COPY packages.txt /tmp/packages.txt
COPY environment.yml /tmp/environment.yml
COPY r_packages.R /tmp/r_packages.R

# System packages (APT) — keep Ubuntu's default repo config; ignore comments in packages.txt
RUN set -eux; \
    # Normalize CRLF if any
    sed -i 's/\r$//' /tmp/packages.txt; \
    apt-get update; \
    # Base tools needed early
    apt-get install -y --no-install-recommends ca-certificates gnupg curl wget bzip2; \
    # Filter comments/blank lines, then install
    grep -vE '^\s*#|^\s*$' /tmp/packages.txt > /tmp/packages.clean; \
    xargs -a /tmp/packages.clean -r apt-get install -y --no-install-recommends; \
    rm -rf /var/lib/apt/lists/*

# ----- Micromamba install & make env immediately available -----
ENV MAMBA_ROOT_PREFIX=/opt/conda
ENV PATH=/opt/conda/bin:$PATH

RUN set -eux; \
    # Install micromamba (static binary)
    curl -L https://micro.mamba.pm/api/micromamba/linux-64/latest -o /tmp/micromamba.tar.bz2; \
    mkdir -p /usr/local/bin; \
    tar -xvj -C /usr/local/bin -f /tmp/micromamba.tar.bz2 bin/micromamba --strip-components=1; \
    rm -f /tmp/micromamba.tar.bz2; \
    # Prepare root prefix and strict channels
    mkdir -p "${MAMBA_ROOT_PREFIX}"; \
    printf "channels:\n  - conda-forge\n  - bioconda\n  - defaults\nchannel_priority: strict\n" > "${MAMBA_ROOT_PREFIX}/.condarc"; \
    # IMPORTANT: install into the base env at the root prefix (do NOT 'create -p $MAMBA_ROOT_PREFIX')
    micromamba install -y -r "${MAMBA_ROOT_PREFIX}" -n base -f /tmp/environment.yml; \
    # Clean caches
    micromamba clean --all --yes

# Register a Jupyter kernel for the env (immediately available)
RUN set -eux; \
    python -m ipykernel install --sys-prefix --name course-pilot --display-name "Python (course-pilot)"

# (Optional) Install R packages
# RUN Rscript /tmp/r_packages.R

# Default workdir
WORKDIR /workspace
