"""Benchmark dataset package: items plus their ground-truth checkers.

Import `ALL_ITEMS`, `GOVERNED_ITEMS`, and `dataset_stats` from here. The act of importing runs
the dataset's integrity gate (`items.self_check`), so a bad label cannot reach the runner.
"""

from .checkers import get_checker  # noqa: F401
from .items import (  # noqa: F401
    ALL_ITEMS,
    GOVERNED_ITEMS,
    Item,
    dataset_stats,
    self_check,
)
