"""CP1 trajectory cleaning and stay-point detection."""

from geolife.staypoints.cleaning import (
    CleaningConfig,
    clean_trajectory,
    clean_trajectory_with_audit,
)
from geolife.staypoints.detector import detect_staypoints

__all__ = [
    "CleaningConfig",
    "clean_trajectory",
    "clean_trajectory_with_audit",
    "detect_staypoints",
]
