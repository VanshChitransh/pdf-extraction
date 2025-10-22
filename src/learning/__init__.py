"""
Phase 3 Enhancement: Learning Loop Module

Machine learning and calibration for continuous improvement:
- Store actual contractor quotes vs AI estimates
- Calculate calibration factors by category/complexity
- Adjust future estimates based on historical performance
- Track variance reduction over time

This creates a self-improving estimation system.
"""

from .calibration_database import CalibrationDatabase, EstimateRecord
from .feedback_loop import FeedbackLoop, CalibrationFactor
from .variance_analyzer import VarianceAnalyzer, VarianceMetrics

__all__ = [
    'CalibrationDatabase',
    'EstimateRecord',
    'FeedbackLoop',
    'CalibrationFactor',
    'VarianceAnalyzer',
    'VarianceMetrics'
]

