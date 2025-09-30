#!/bin/bash
set -e  # Exit on any error

echo "🔍 Testing Dev Container Environment"
echo "==================================="

echo "0. Testing Unicode/Emoji Support..."
echo "Locale: $(locale | grep LANG)"
echo "Testing emojis: ✅ ❌ 📦 🧪 🎉"
echo "Unicode test: $(echo -e '\U2705 \U274C \U1F4E6')"

echo "1. Testing R installation..."
R --version | head -1

echo -e "\n2. Testing critical R packages..."
R -e "
# Architecture-aware package testing
arch <- Sys.info()[['machine']];
cat('Testing R packages for architecture:', arch, '\n');

# Common packages available on all architectures
common_packages <- c('ggplot2', 'tidyverse', 'vegan', 'dplyr', 'stringr', 'ggpubr', 'BiocManager');

# Architecture-specific packages
arch_specific <- list();
if (arch %in% c('x86_64', 'amd64')) {
  arch_specific <- c('fossil', 'taxonomizr');
  cat('  ℹ️  x86_64 detected - testing additional packages\n');
} else {
  cat('  ℹ️  ARM64 detected - skipping packages not available on this architecture\n');
}

# Combine package lists
packages <- c(common_packages, arch_specific);
failed <- 0;

# First check ggplot2 version
if(require('ggplot2', character.only=TRUE, quietly=TRUE)) {
  ggplot_version <- packageVersion('ggplot2');
  cat(paste('  ℹ️  ggplot2 version:', ggplot_version, '\n'));
}

for(pkg in packages) {
  result <- tryCatch({
    library(pkg, character.only=TRUE, quietly=TRUE);
    version <- packageVersion(pkg);
    cat(paste('  ✅', pkg, 'v', version, '\n'));
    TRUE
  }, error = function(e) {
    cat(paste('  ❌', pkg, '- ERROR:', e\$message, '\n'));
    # For version conflicts, show what versions are available
    if(grepl('version.*required', e\$message)) {
      cat('    💡 This is a version compatibility issue\n');
    }
    failed <<- failed + 1;
    FALSE
  });
};
if(failed == 0) {
  cat('🎉 All R packages loaded successfully!\n');
} else {
  cat(paste('❌', failed, 'R packages failed to load\n'));
  quit(status=1);
}
"

echo -e "\n3. Testing ggplot2 functions (corruption check)..."
R -e "
library(ggplot2, quietly=TRUE);
tryCatch({
  funcs <- lsf.str('package:ggplot2');
  cat('✅ ggplot2 functions accessible (no corruption)\n');
}, error = function(e) {
  cat('❌ ggplot2 corruption detected:', e\$message, '\n');
  quit(status=1);
});
"

echo -e "\n4. Testing Bioconductor integration..."
R -e "
library(BiocManager, quietly=TRUE);
cat('BiocManager version:', as.character(BiocManager::version()), '\n');
# Test if we can access Bioconductor (don't install, just check connection)
tryCatch({
  available <- BiocManager::available()[1:5];  # Just check first 5
  cat('✅ BiocManager can access Bioconductor\n');
}, error = function(e) {
  cat('⚠️  BiocManager warning (may be network related):', e\$message, '\n');
});
"

echo -e "\n5. Testing Jupyter kernels..."
echo "Available kernels:"
jupyter kernelspec list

# Verify both Python and R kernels exist
if jupyter kernelspec list | grep -q python; then
    echo "✅ Python kernel found"
else
    echo "❌ Python kernel missing"
    exit 1
fi

if jupyter kernelspec list | grep -q "ir\|R"; then
    echo "✅ R kernel found"
else
    echo "❌ R kernel missing"
    exit 1
fi

echo -e "\n6. Testing Python packages..."
python -c "
import sys
# Map package names to their import names
packages = {
    'numpy': 'numpy',
    'pandas': 'pandas',
    'matplotlib': 'matplotlib',
    'seaborn': 'seaborn',
    'scipy': 'scipy',
    'sklearn': 'sklearn',
    'biopython': 'Bio'  # biopython package imports as Bio
}
failed = []
print('Testing Python packages:')
for pkg_name, import_name in packages.items():
    try:
        __import__(import_name)
        print(f'  ✅ {pkg_name}')
    except ImportError as e:
        print(f'  ❌ {pkg_name} - ERROR: {e}')
        failed.append(pkg_name)
if failed:
    print(f'❌ {len(failed)} Python packages failed')
    sys.exit(1)
else:
    print('🎉 All Python packages OK!')
"

echo -e "\n7. Testing bioinformatics tools..."
tools=("samtools" "bcftools" "minimap2" "fastp" "seqkit")
for tool in "${tools[@]}"; do
    if command -v "$tool" &> /dev/null; then
        version=$(${tool} --version 2>&1 | head -1 || echo "version info unavailable")
        echo "  ✅ $tool: $version"
    else
        echo "  ❌ $tool: not found"
        exit 1
    fi
done

echo -e "\n8. Testing file system permissions..."
# Test write permissions in common directories
test_dirs=("/tmp" "/opt/conda")
for dir in "${test_dirs[@]}"; do
    if [ -d "$dir" ] && [ -w "$dir" ]; then
        # Try to create and remove a test file
        if touch "$dir/test_file_$$" 2>/dev/null && rm "$dir/test_file_$$" 2>/dev/null; then
            echo "  ✅ $dir: writable"
        else
            echo "  ❌ $dir: write test failed"
            exit 1
        fi
    else
        echo "  ❌ $dir: not writable or doesn't exist"
        exit 1
    fi
done

# Test that we can create the workspace directory
echo "  Testing workspace directory creation..."
if mkdir -p /workspace && [ -d "/workspace" ]; then
    echo "  ✅ /workspace: can be created"
    rmdir /workspace  # Clean up for the WORKDIR instruction
else
    echo "  ❌ /workspace: cannot be created"
    exit 1
fi

echo -e "\n9. Testing R data processing capabilities..."
R -e "
# Test basic data manipulation that students will use
library(dplyr, quietly=TRUE);
library(ggplot2, quietly=TRUE);

# Create test data
test_data <- data.frame(
  sample = paste0('S', 1:10),
  value1 = rnorm(10),
  value2 = runif(10),
  group = rep(c('A', 'B'), 5)
);

# Test dplyr operations
result <- test_data %>%
  filter(group == 'A') %>%
  summarise(mean_val = mean(value1));

# Test ggplot2 (create plot but don't display)
p <- ggplot(test_data, aes(x=value1, y=value2, color=group)) +
     geom_point() +
     theme_minimal();

cat('✅ R data processing pipeline working\n');
cat('✅ dplyr and ggplot2 integration working\n');
"

echo -e "\n10. Architecture-specific validation..."
ARCH=$(uname -m)
echo "Running on architecture: $ARCH"

# Check if we're missing any expected tools based on architecture
case "$ARCH" in
    x86_64|amd64)
        echo "  ✅ Running on x86_64 - full toolset expected"
        # Check for tools that should be available on x86_64
        if command -v lrge &> /dev/null; then
            echo "  ✅ lrge: available"
        else
            echo "  ⚠️  lrge: not found (may be expected on some platforms)"
        fi
        ;;
    aarch64|arm64)
        echo "  ✅ Running on ARM64 - some tools may be unavailable"
        echo "  💡 This is expected - ARM64 has limited bioconda package availability"
        ;;
    *)
        echo "  ⚠️  Unknown architecture: $ARCH"
        ;;
esac

echo -e "\n🎉 All tests passed! Environment is ready for the course."
echo "Container build completed successfully! 🚀"
echo "Architecture: $ARCH"
echo "Build platform: ${TARGETPLATFORM:-unknown}"
