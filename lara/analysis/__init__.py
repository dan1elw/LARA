"""
LARA Analysis Component
Advanced analytics and pattern detection for flight data.
"""

__version__ = "v0.1.1"

from .analyzer import FlightAnalyzer
from .corridor_detector import CorridorDetector
from .pattern_matcher import PatternMatcher
from .statistics import StatisticsEngine
from .reporter import ReportGenerator

__all__ = [
    'FlightAnalyzer',
    'CorridorDetector',
    'PatternMatcher',
    'StatisticsEngine',
    'ReportGenerator',
]
