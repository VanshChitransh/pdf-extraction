"""
Cost Estimation Enhancement Module

Advanced estimation features:
- Multi-dimensional confidence scoring
- Component-level cost database
- Relationship analysis for bundled estimates
- Historical calibration

Phase 2 Enhancements:
- Cost strategy selection (lookup/formula/AI)
- Houston market multipliers
- Hybrid estimation (combining multiple strategies)
"""

from .confidence_scorer import AdvancedConfidenceScorer
from .cost_database import HoustonCostDatabase
from .relationship_analyzer import IssueRelationshipAnalyzer

# Phase 2 imports
from .cost_strategy_selector import CostStrategySelector, EstimationStrategy
from .houston_cost_multipliers import HoustonCostAdjuster, PermitType
from .hybrid_cost_estimator import HybridCostEstimator

__all__ = [
    # Original
    'AdvancedConfidenceScorer',
    'HoustonCostDatabase',
    'IssueRelationshipAnalyzer',
    # Phase 2
    'CostStrategySelector',
    'EstimationStrategy',
    'HoustonCostAdjuster',
    'PermitType',
    'HybridCostEstimator'
]

