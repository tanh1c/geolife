"""Synthetic-first, private destination-ranking research.

No historical GeoLife participant linkage or semantic HOME/OFFICE truth.
"""
from .destination import Visit, suggest_destinations, evaluate_first_heldout

__all__ = ["Visit", "suggest_destinations", "evaluate_first_heldout"]
