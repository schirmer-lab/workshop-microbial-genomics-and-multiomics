"""
Type stubs for optimized.constants Cython module.

This file provides type hints for genetic code constants used by
the sequence analysis functions.
"""

from typing import Dict, List

GENETIC_CODE: Dict[int, List[int]]
"""
Dictionary mapping genetic code table numbers to amino acid translation arrays.

Each table maps 64 codon indices (0-63) to amino acid ASCII codes.
Common tables:
- 1: Standard genetic code
- 11: Bacterial/archaeal genetic code  
- 4: Mold/mitochondrial genetic code
"""
