# Use the official Jupyter base image which includes Python and Jupyter
FROM jupyter/base-notebook:latest

# Switch to root user for installations
USER root

# Install system dependencies for R
RUN apt-get update && apt-get install -y \
    r-base \
    r-base-dev \
    libcurl4-openssl-dev \
    libssl-dev \
    libxml2-dev \
    libfontconfig1-dev \
    libharfbuzz-dev \
    libfribidi-dev \
    libfreetype6-dev \
    libpng-dev \
    libtiff5-dev \
    libjpeg-dev \
    && rm -rf /var/lib/apt/lists/*

# Install IRkernel for R in Jupyter
RUN R -e "install.packages('IRkernel', repos='https://cran.rstudio.com/')" && \
    R -e "IRkernel::installspec(user = FALSE)"

# Install the requested R packages
RUN R -e "install.packages(c('devtools', 'ggplot2', 'vegan', 'ggpubr', 'taxonomizr', 'stringr'), repos='https://cran.rstudio.com/', dependencies=TRUE)"

# Create a non-root user
RUN useradd -m -s /bin/bash vscode && \
    usermod -aG sudo vscode && \
    echo "vscode ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Set up the working directory
WORKDIR /home/vscode

# Switch back to the vscode user
USER vscode

# Expose Jupyter port
EXPOSE 8888

# Default command
CMD ["jupyter", "notebook", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root", "--NotebookApp.token=''"]