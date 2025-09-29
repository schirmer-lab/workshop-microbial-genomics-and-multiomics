# Use Ubuntu 24.04 as base
FROM ubuntu:24.04

# Get build platform information for architecture-specific handling
ARG TARGETPLATFORM
ARG TARGETOS
ARG TARGETARCH
ARG BUILDPLATFORM

# Set environment variables to prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC
ENV MAMBA_ROOT_PREFIX=/opt/conda
ENV PATH=/opt/conda/bin:$PATH

# Store architecture info for runtime use
ENV TARGETARCH=${TARGETARCH}
ENV TARGETPLATFORM=${TARGETPLATFORM}

# Architecture detection for conditional package installation
RUN echo "Building for platform: ${TARGETPLATFORM:-linux/amd64}" && \
    echo "Target architecture: ${TARGETARCH:-amd64}" && \
    echo "Build platform: ${BUILDPLATFORM:-linux/amd64}"

# Install base system packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends ca-certificates curl bzip2 && \
    rm -rf /var/lib/apt/lists/*

# Copy and install system packages from packages.txt
COPY packages.txt /tmp/packages.txt
RUN set -eux; \
    sed -i 's/\r$//' /tmp/packages.txt || true; \
    if [ -s /tmp/packages.txt ]; then \
        apt-get update; \
        grep -vE '^\s*#|^\s*$' /tmp/packages.txt | xargs apt-get install -y --no-install-recommends; \
        rm -rf /var/lib/apt/lists/*; \
    fi; \
    rm -rf /tmp/packages.txt

# Install micromamba with architecture detection
RUN set -eux; \
    case "${TARGETARCH:-amd64}" in \
        amd64|x86_64) MAMBA_ARCH="linux-64" ;; \
        arm64|aarch64) MAMBA_ARCH="linux-aarch64" ;; \
        *) echo "Unsupported architecture: ${TARGETARCH}" && exit 1 ;; \
    esac; \
    echo "Installing micromamba for architecture: $MAMBA_ARCH"; \
    curl -L "https://micro.mamba.pm/api/micromamba/$MAMBA_ARCH/latest" -o /tmp/micromamba.tar.bz2; \
    mkdir -p /usr/local/bin; \
    tar -xvj -C /usr/local/bin -f /tmp/micromamba.tar.bz2 bin/micromamba --strip-components=1; \
    rm /tmp/micromamba.tar.bz2

# Copy architecture-specific environment file
COPY environment-${TARGETARCH:-amd64}.yml /tmp/environment.yml

# Install conda packages
RUN echo "Installing conda packages for ${TARGETARCH:-amd64}..." && \
    /usr/local/bin/micromamba install -y -f /tmp/environment.yml || { \
        echo "Some packages failed to install, trying with --strict-channel-priority=false"; \
        /usr/local/bin/micromamba install -y -f /tmp/environment.yml --strict-channel-priority=false; \
    } && \
    /usr/local/bin/micromamba clean -a -y && \
    rm -rf /tmp/environment.yml

# Install Jupyter kernels
RUN /usr/local/bin/micromamba run python -m ipykernel install --sys-prefix && \
    R -e "IRkernel::installspec(user = FALSE)"

# Copy and run comprehensive environment test
COPY test_environment.sh /tmp/test_environment.sh
RUN chmod +x /tmp/test_environment.sh && \
    /tmp/test_environment.sh && \
    rm /tmp/test_environment.sh

WORKDIR /workspace
