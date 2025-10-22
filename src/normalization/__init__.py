"""
Normalization module for standardizing severity and action classifications.
"""

from .severity_normalizer import SeverityNormalizer
from .action_normalizer import ActionNormalizer

__all__ = ['SeverityNormalizer', 'ActionNormalizer']

