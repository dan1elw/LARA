"""
LARA - Local Air Route Analysis

Track, analyze, and visualize aircraft flights over your location.
"""

__version__ = "v0.1.1"
__author__ = "LARA Project"
__license__ = "MIT"

from .config import Config
from .database import FlightDatabase
from .collector import FlightCollector
from .reader import FlightReader
from . import utils
from . import constants

__all__ = [
    'Config',
    'FlightDatabase',
    'FlightCollector',
    'FlightReader',
    'utils',
    'constants',
]
