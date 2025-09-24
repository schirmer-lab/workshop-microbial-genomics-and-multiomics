# R packages installation script
# This script installs R packages required for the course

# Set CRAN mirror
options(repos = c(CRAN = "https://cran.rstudio.com"))

# Core packages
core_packages <- c(
  "IRkernel",      # Jupyter R kernel
  "devtools",      # Development tools
  "remotes"        # For installing packages from various sources
)

# Data manipulation and visualization
data_packages <- c(
  "ggplot2",       # Grammar of graphics
  "dplyr",         # Data manipulation
  "tidyr",         # Data tidying
  "readr",         # Read rectangular data
  "stringr",       # String manipulation
  "lubridate"      # Date and time manipulation
)

# Statistical analysis packages
stats_packages <- c(
  "vegan",         # Community ecology package
  "ggpubr"         # Publication ready plots
)

# Bioinformatics packages
bio_packages <- c(
  "taxonomizr"     # Taxonomic analysis
)

# Combine all packages
all_packages <- c(core_packages, data_packages, stats_packages, bio_packages)

# Install packages
cat("Installing R packages...\n")
for (pkg in all_packages) {
  cat(paste("Installing", pkg, "...\n"))
  if (!require(pkg, character.only = TRUE, quietly = TRUE)) {
    install.packages(pkg, dependencies = TRUE)
  }
}

# Install IRkernel for Jupyter
if (require("IRkernel", quietly = TRUE)) {
  cat("Installing IRkernel for Jupyter...\n")
  # Install for the current user since we're running as vscode user
  IRkernel::installspec(user = TRUE)
  
  # Also install system-wide if possible
  tryCatch({
    IRkernel::installspec(user = FALSE)
    cat("IRkernel installed system-wide\n")
  }, error = function(e) {
    cat("Could not install IRkernel system-wide (this is normal for non-root user)\n")
  })
}

cat("R package installation completed!\n")
cat("Verifying R installation...\n")
cat(paste("R version:", R.version.string, "\n"))
cat(paste("R home:", R.home(), "\n"))