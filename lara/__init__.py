"""
LARA - Local Air Route Analysis

A comprehensive system for tracking, analyzing, and visualizing aircraft
flight routes over your location using ADS-B data from OpenSky Network.

Components:
    - tracking: Real-time flight data collection and storage
    - analysis: Pattern detection and statistical analysis
    - visualization: Interactive map generation and dashboards

Example:
    >>> from lara.tracking import Config, FlightCollector
    >>> config = Config()
    >>> collector = FlightCollector(config)
    >>> collector.run()
"""

__version__ = "v0.1.1"
__author__ = "LARA Project"
__license__ = "MIT"

# Component imports for easy access
from . import tracking
from . import analysis
from . import visualization

__all__ = [
    "tracking",
    "analysis",
    "visualization",
]
