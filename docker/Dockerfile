FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC
ENV MAMBA_ROOT_PREFIX=/opt/conda
ENV PATH=/opt/conda/bin:$PATH

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

# Install micromamba
RUN set -eux; \
    curl -L https://micro.mamba.pm/api/micromamba/linux-64/latest -o /tmp/micromamba.tar.bz2; \
    mkdir -p /usr/local/bin; \
    tar -xvj -C /usr/local/bin -f /tmp/micromamba.tar.bz2 bin/micromamba --strip-components=1; \
    rm /tmp/micromamba.tar.bz2

# Copy and install packages from environment.yml in base environment
COPY environment.yml /tmp/environment.yml
RUN /usr/local/bin/micromamba install -y -f /tmp/environment.yml && \
    /usr/local/bin/micromamba clean -a -y && \
    rm -rf /tmp/environment.yml

# Copy and install R packages
COPY r_packages.R /tmp/r_packages.R
RUN Rscript /tmp/r_packages.R && \
    rm -rf /tmp/r_packages.R

# Install Jupyter kernels
RUN /usr/local/bin/micromamba run python -m ipykernel install --sys-prefix && \
    R -e "IRkernel::installspec(user = FALSE)"

WORKDIR /workspace
