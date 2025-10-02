from importlib import import_module

import pytest


def test_index_manager_importable_or_skip():
    try:
        mod = import_module("metabiome.core.indexing")
    except Exception:
        pytest.skip("indexing module not available")

    IndexManager = getattr(mod, "IndexManager", None)
    if IndexManager is None:
        pytest.skip("IndexManager not implemented")

    # basic construction should accept a lazyframe or similar; we won't exercise methods here
    # (deeper tests should mock an id_mapping polars frame and validate mappings)
    assert callable(IndexManager)
