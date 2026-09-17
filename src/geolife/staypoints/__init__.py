"""CP1 trajectory cleaning and stay-point detection."""

from geolife.staypoints.cleaning import CleaningConfig, clean_trajectory
from geolife.staypoints.detector import detect_staypoints

__all__ = ["CleaningConfig", "clean_trajectory", "detect_staypoints"]
