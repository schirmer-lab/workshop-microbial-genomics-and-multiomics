# syntax=docker/dockerfile:1.7-labs
FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive TZ=UTC

# Micromamba base
ENV MAMBA_ROOT_PREFIX=/opt/conda
ENV PATH=/opt/conda/bin:$PATH
ENV MAMBA_NO_BANNER=1 MAMBA_EXTRACT_THREADS=0 MAMBA_DOWNLOAD_THREADS=8

# Bring inputs
COPY packages.txt /tmp/packages.txt
COPY environment.yml /tmp/environment.yml          # for documentation/reference
COPY conda-linux-64.lock /tmp/conda-linux-64.lock  # created on host; see commands below
COPY r_packages.R /tmp/r_packages.R                # optional

# System packages
RUN set -eux; \
    sed -i 's/\r$//' /tmp/packages.txt; \
    apt-get update; \
    apt-get install -y --no-install-recommends ca-certificates gnupg curl wget bzip2; \
    grep -vE '^\s*#|^\s*$' /tmp/packages.txt > /tmp/packages.clean; \
    xargs -a /tmp/packages.clean -r apt-get install -y --no-install-recommends; \
    rm -rf /var/lib/apt/lists/*

# Micromamba install + explicit install from lock (no solver)
RUN --mount=type=cache,target=/opt/conda/pkgs \
    --mount=type=cache,target=/root/.cache/mamba \
    set -eux; \
    curl -L https://micro.mamba.pm/api/micromamba/linux-64/latest -o /tmp/micromamba.tar.bz2; \
    mkdir -p /usr/local/bin; \
    tar -xvj -C /usr/local/bin -f /tmp/micromamba.tar.bz2 bin/micromamba --strip-components=1; \
    rm -f /tmp/micromamba.tar.bz2; \
    mkdir -p "$MAMBA_ROOT_PREFIX"; \
    printf "channels:\n  - conda-forge\n  - bioconda\nchannel_priority: strict\n" > "$MAMBA_ROOT_PREFIX/.condarc"; \
    # FIXED: Use 'micromamba create' with the lock file to skip the slow solver.
    micromamba create -y -n base --file /tmp/conda-linux-64.lock; \
    micromamba clean --all --yes

# Make the kernel show up immediately
RUN set -eux; \
    python -m ipykernel install --sys-prefix --name course-pilot --display-name "Python (course-pilot)"

WORKDIR /workspace