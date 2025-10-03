# Metabiome

**Metabiome** is a high-performance Python package for handling large-scale metagenomic cohort studies. Built specifically for metagenomics data, it provides a comprehensive toolkit for data integration, analysis, and visualization with extreme performance and memory efficiency.

## Installation

Install Metabiome using `uv` (recommended):

```bash
git clone https://github.com/realhexiheng/metabiome.git
cd metabiome
uv sync
```

Or install directly from the repository:

```bash
uv add git+https://github.com/realhexiheng/metabiome.git
```

## Why Metabiome Instead of AnnData?

While AnnData is excellent for single-cell genomics, **Metabiome is purpose-built for metagenomics** with significant performance advantages:

### Performance Benefits
- **10-100x faster** than AnnData using **Polars** instead of pandas
- **Lazy evaluation** with `LazyFrame`s - handle datasets larger than RAM
- **Zarr v3 + Parquet** storage backends vs HDF5 for better compression and speed
- **Sparse matrix optimizations** for typical metagenomic abundance patterns

### Metagenomics-Specific Features
- **Gene catalog integration** with hierarchical gene/cluster/pathway IDs
- **Taxonomic hierarchy support** with automated GTDB/NCBI taxonomy parsing
- **Functional annotation layers** (KEGG, COG, Pfam, etc.) with aligned indexing
- **Multi-cohort operations** for large-scale comparative studies
- **Sequence management** with integrated FASTA handling

### Memory Efficiency
- **Lazy loading** - only materialize data when needed
- **Categorical optimization** for gene IDs and taxonomic labels
- **Chunked processing** for datasets exceeding memory limits
- **Copy-free views** for efficient slicing and filtering

## Core Features

### Data Integration
- **Unified container** for metadata, abundance, taxonomy, functional annotations, and sequences
- **Automatic alignment** of all annotation layers to feature indices
- **ID mapping support** for cross-referencing between gene catalogs
- **Multi-format parsing** (JSON, TSV, Parquet, FASTA)

### High-Performance Operations
- **AnnData-style indexing** with `mds[samples, features]` syntax
- **Lazy grouping and aggregation** with `mds.groupby.obs()` and `mds.groupby.var()`
- **Conditional filtering** with Polars expressions
- **Memory-efficient concatenation** for multi-cohort studies

### Analysis Tools
- **Taxonomic visualization** with interactive Sankey diagrams
- **Diversity analysis** with alpha/beta diversity metrics
- **Differential abundance** testing with statistical methods
- **Functional enrichment** analysis with pathway databases

## Usage Examples

### Loading Data

```python
import polars as pl
import metabiome.io as mio

# Load from multiple file formats
mds = mio.from_files(
    obs="../data/input/metadata",           # Sample metadata
    abundance="../data/input/RPKM.json",   # Gene abundance profiles
    taxonomy="../data/input/taxonomy.json", # Taxonomic annotations
    functional="../data/input/FG.json",    # Functional groups
    sequences="../data/input/merged.fasta", # Gene sequences
    id_mapping="../data/input/id_mapping.tsv" # ID cross-references
)

# Check data dimensions
print(f"Data shape: {mds.shape}")  # (n_samples, n_features)
```

### Indexing and Slicing

```python
# Single sample and feature
sample_slice = mds["CSM5MCWG", "cohort_merged__MSM79HBR_k105_18694::129::153944::157684::+"]

# Multiple samples, all features
multi_samples = mds[["CSM5MCWG", "SRR7989845"], :]

# All samples, specific features
multi_features = mds[:, ["gene_1", "gene_2", "gene_3"]]

# Conditional filtering with Polars expressions
male_samples = mds[pl.col("gender") == "M", :]

# Chained indexing
filtered = mds[["CSM5MCWG", "SRR7989845"], :][
    :, ["gene_1", "gene_2"]
]
```

### Grouping and Aggregation

```python
# Group by sample metadata
grouped = mds.groupby.obs(["disease_group"])
disease_means = grouped.agg("mean")

# Group by feature annotations
genus_grouped = mds.groupby.var(["genus"])
genus_sums = genus_grouped.agg("sum")

# Simultaneous grouping on both axes
dual_grouped = mds.groupby(obs=["disease_group"], var=["genus"])
result = dual_grouped.agg("max")
```

### Filtering

```python
# Filter samples by metadata
male_samples = mds.filter.obs(pl.col("gender") == "M")

# Filter features by annotations
lactobacillus = mds.filter.var(pl.col("genus") == "Lactobacillaceae")

# Filter by abundance statistics
high_abundance = mds.filter.X("var", pl.col("mean_abundance") > 0.1)
```

### Memory Management

```python
# Check memory usage
mds.memory_info()

# Materialize lazy frames
materialized = mds.collect()

# Convert back to lazy evaluation
lazy_mds = mds.lazy()
```

### Data Persistence

```python
# Save to optimized format
mds.save("my_dataset", overwrite=True)

# Load saved dataset
loaded_mds = mio.from_space("my_dataset")
```

### Visualization

```python
from metabiome.pl import plot_sankey

# Interactive taxonomic composition
plot_sankey(mds, max_level="genus", min_abundance=0.01, height=600)
```

## Core Data Structures

### `MetabiomeDataSpace`
The main container inspired by AnnData but optimized for metagenomics:

```python
# Main attributes
mds.obs          # Sample metadata (DataFrame)
mds.var          # Feature annotations (DataFrame)
mds.X            # Abundance matrix (SparseAbundanceMatrix)
mds.sequences    # FASTA sequences (pyfaidx.Fasta)
mds.id_mapping   # ID cross-references (DataFrame)

# Computed properties
mds.shape        # (n_samples, n_features)
mds.obs_names    # Sample IDs
mds.var_names    # Feature IDs
```

### `GroupedMetabiomeDataSpace`
Specialized container for grouped operations:

```python
# Lazy aggregation
grouped = mds.groupby.obs(["disease_group"])
result = grouped.agg("mean")  # Returns new MetabiomeDataSpace
```

### `SparseAbundanceMatrix`
Efficient sparse matrix wrapper:

```python
# Scipy sparse matrix with aligned indices
matrix = mds.X
print(matrix.shape)      # Matrix dimensions
print(matrix.density)    # Sparsity information
```

## API Reference

### I/O Functions
- `mio.from_files()` - Load from multiple file formats
- `mio.from_space()` - Load saved MetabiomeDataSpace
- `mds.save()` - Save to optimized format

### Core Operations
- `mds[samples, features]` - AnnData-style indexing
- `mds.groupby.obs()` - Group by sample metadata
- `mds.groupby.var()` - Group by feature annotations
- `mds.filter.obs()` - Filter samples
- `mds.filter.var()` - Filter features
- `mds.filter.X()` - Filter by abundance

### Memory Management
- `mds.collect()` - Materialize lazy frames
- `mds.lazy()` - Convert to lazy evaluation
- `mds.memory_info()` - Display memory usage
- `mds.copy()` - Create deep copy

### Multi-Cohort Operations
- `concat_spaces()` - Concatenate multiple datasets
- `mds.to_abundance_matrix()` - Export abundance data

## Performance

Metabiome is designed for production-scale metagenomics:

- **Lazy evaluation** - Process datasets larger than RAM
- **Columnar storage** - Efficient compression and I/O
- **Categorical optimization** - Reduce memory for repeated strings
- **Sparse matrices** - Handle typical metagenomic sparsity patterns
- **Parallel processing** - Leverage multi-core systems

## Modules

- **`metabiome.core`**: Core data structures and operations
- **`metabiome.io`**: File parsers and I/O operations
- **`metabiome.annotations`**: Sequence analysis and annotation tools
- **`metabiome.analysis`**: Diversity, differential, and statistical analysis
- **`metabiome.pl`**: Plotting and visualization tools
- **`metabiome.optimized`**: Cython-compiled performance functions
- **`metabiome.utils`**: Helper functions and utilities

## Getting Started

1. **Install** with `uv sync`
2. **Load data** with `mio.from_files()`
3. **Explore** with indexing and filtering
4. **Analyze** with grouping and aggregation
5. **Visualize** with plotting functions
6. **Save** results with `mds.save()`

For detailed examples, see the `examples/` directory and documentation.