"""
Phase 3 Enhancement: Feedback Loop

Uses historical calibration data to adjust future estimates.
Implements continuous learning from actual contractor quotes.

Key Features:
- Apply calibration factors based on historical performance
- Adjust estimates by category, complexity, and strategy
- Track improvement over time
- Provide confidence intervals based on historical accuracy
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import statistics
import logging

from .calibration_database import CalibrationDatabase

logger = logging.getLogger(__name__)


@dataclass
class CalibrationFactor:
    """Calibration factor with metadata."""
    category: str
    complexity: str
    strategy: str
    factor: float  # Multiplier (e.g., 1.15 = increase estimates by 15%)
    sample_count: int
    confidence: float  # 0-1, based on sample size and variance
    avg_variance_pct: float
    reasoning: str


class FeedbackLoop:
    """
    Implements learning loop to improve estimates based on actual costs.
    
    Phase 3 Learning Process:
    1. Collect actual contractor quotes
    2. Compare to AI estimates
    3. Calculate calibration factors
    4. Apply factors to future estimates
    5. Track accuracy improvement
    
    Usage:
        feedback = FeedbackLoop(calibration_db)
        
        # Adjust estimate based on historical data
        adjusted_estimate = feedback.adjust_estimate(
            base_estimate,
            issue
        )
        
        # Track learning progress
        improvement = feedback.get_improvement_metrics()
    """
    
    def __init__(
        self,
        calibration_db: CalibrationDatabase,
        min_samples_for_adjustment: int = 5,
        confidence_threshold: float = 0.6
    ):
        """
        Initialize feedback loop.
        
        Args:
            calibration_db: Calibration database with historical data
            min_samples_for_adjustment: Minimum samples needed to apply calibration
            confidence_threshold: Minimum confidence to apply adjustment
        """
        self.db = calibration_db
        self.min_samples = min_samples_for_adjustment
        self.confidence_threshold = confidence_threshold
        
        self.stats = {
            'total_adjustments': 0,
            'adjustments_applied': 0,
            'adjustments_skipped': 0,
            'avg_adjustment_factor': 1.0
        }
    
    def adjust_estimate(
        self,
        base_estimate: Dict,
        issue: Dict,
        property_metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Adjust estimate based on historical calibration data.
        
        Args:
            base_estimate: Base estimate from estimation system
            issue: Issue dictionary
            property_metadata: Optional property context
            
        Returns:
            Adjusted estimate with calibration applied
        """
        self.stats['total_adjustments'] += 1
        
        # Extract issue characteristics
        category = issue.get('category', 'General')
        severity = issue.get('severity', 'Medium')
        
        # Determine complexity
        complexity = self._determine_complexity(issue, base_estimate)
        
        # Get estimation strategy
        strategy = base_estimate.get('estimation_strategy', 'unknown')
        
        # Get calibration factor
        calibration = self._get_best_calibration_factor(
            category,
            complexity,
            strategy
        )
        
        if calibration is None:
            logger.info(f"No calibration data for {category}/{complexity}/{strategy}")
            self.stats['adjustments_skipped'] += 1
            return self._add_calibration_metadata(base_estimate, None, "insufficient_data")
        
        # Check if we should apply calibration
        if not self._should_apply_calibration(calibration):
            logger.info(f"Calibration confidence too low: {calibration.confidence:.2f}")
            self.stats['adjustments_skipped'] += 1
            return self._add_calibration_metadata(base_estimate, calibration, "low_confidence")
        
        # Apply calibration
        adjusted_estimate = self._apply_calibration_factor(
            base_estimate,
            calibration.factor
        )
        
        self.stats['adjustments_applied'] += 1
        
        # Track adjustment factors
        adjustment_factors = self.stats.get('adjustment_factors', [])
        adjustment_factors.append(calibration.factor)
        self.stats['adjustment_factors'] = adjustment_factors
        self.stats['avg_adjustment_factor'] = statistics.mean(adjustment_factors)
        
        logger.info(
            f"Applied calibration {calibration.factor:.3f}x to {category}/{complexity} "
            f"(confidence: {calibration.confidence:.2f}, samples: {calibration.sample_count})"
        )
        
        return self._add_calibration_metadata(adjusted_estimate, calibration, "applied")
    
    def _get_best_calibration_factor(
        self,
        category: str,
        complexity: str,
        strategy: str
    ) -> Optional[CalibrationFactor]:
        """
        Get best calibration factor for the given characteristics.
        
        Tries in order of specificity:
        1. Category + Complexity + Strategy
        2. Category + Complexity
        3. Category only
        4. Complexity only (across all categories)
        """
        # Try most specific first
        factor = self._calculate_calibration_factor(
            category=category,
            complexity=complexity,
            strategy=strategy
        )
        if factor:
            return factor
        
        # Try category + complexity
        factor = self._calculate_calibration_factor(
            category=category,
            complexity=complexity
        )
        if factor:
            return factor
        
        # Try category only
        factor = self._calculate_calibration_factor(
            category=category
        )
        if factor:
            return factor
        
        # Try complexity only (fallback)
        factor = self._calculate_calibration_factor(
            complexity=complexity
        )
        return factor
    
    def _calculate_calibration_factor(
        self,
        category: Optional[str] = None,
        complexity: Optional[str] = None,
        strategy: Optional[str] = None
    ) -> Optional[CalibrationFactor]:
        """Calculate calibration factor for given filters."""
        # Get variance stats
        stats = self.db.get_variance_stats(
            category=category,
            complexity=complexity,
            strategy=strategy
        )
        
        sample_count = stats['count']
        
        if sample_count < self.min_samples:
            return None
        
        # Calculate factor from average variance
        # If estimates are consistently 10% low, factor = 1.10
        avg_variance_pct = stats['avg_variance_pct']
        factor = 1.0 + (avg_variance_pct / 100)
        
        # Cap factor to reasonable range (0.7 to 1.5)
        factor = max(0.7, min(1.5, factor))
        
        # Calculate confidence based on sample size and variance consistency
        confidence = self._calculate_confidence(
            sample_count,
            stats['std_dev_variance_pct']
        )
        
        # Build reasoning
        reasoning_parts = []
        if category:
            reasoning_parts.append(f"Category: {category}")
        if complexity:
            reasoning_parts.append(f"Complexity: {complexity}")
        if strategy:
            reasoning_parts.append(f"Strategy: {strategy}")
        reasoning_parts.append(f"Based on {sample_count} historical quotes")
        reasoning_parts.append(f"Avg variance: {avg_variance_pct:+.1f}%")
        
        reasoning = "; ".join(reasoning_parts)
        
        return CalibrationFactor(
            category=category or "any",
            complexity=complexity or "any",
            strategy=strategy or "any",
            factor=factor,
            sample_count=sample_count,
            confidence=confidence,
            avg_variance_pct=avg_variance_pct,
            reasoning=reasoning
        )
    
    def _calculate_confidence(
        self,
        sample_count: int,
        std_dev: float
    ) -> float:
        """
        Calculate confidence in calibration factor.
        
        Confidence increases with:
        - More samples
        - Lower variance (more consistent)
        
        Returns: 0.0 to 1.0
        """
        # Sample size component (asymptotic to 1.0)
        sample_confidence = min(1.0, sample_count / 20)  # Full confidence at 20+ samples
        
        # Consistency component (lower std dev = higher confidence)
        # Std dev of 10% = 0.9 confidence, 20% = 0.8, etc.
        if std_dev > 0:
            consistency_confidence = max(0.5, 1.0 - (std_dev / 100))
        else:
            consistency_confidence = 1.0
        
        # Combined confidence (geometric mean)
        return (sample_confidence * consistency_confidence) ** 0.5
    
    def _should_apply_calibration(self, calibration: CalibrationFactor) -> bool:
        """Determine if calibration should be applied."""
        # Don't apply if confidence too low
        if calibration.confidence < self.confidence_threshold:
            return False
        
        # Don't apply extreme adjustments (likely outliers)
        if calibration.factor < 0.75 or calibration.factor > 1.35:
            return False
        
        # Don't apply tiny adjustments (not worth it)
        if 0.98 <= calibration.factor <= 1.02:
            return False
        
        return True
    
    def _apply_calibration_factor(
        self,
        base_estimate: Dict,
        factor: float
    ) -> Dict:
        """Apply calibration factor to estimate."""
        adjusted = base_estimate.copy()
        cost = adjusted.get('cost', {}).copy()
        
        # Apply factor to all cost components
        for component in ['labor', 'materials', 'total']:
            if component in cost and isinstance(cost[component], dict):
                comp = cost[component].copy()
                comp['min'] = round(comp.get('min', 0) * factor, 2)
                comp['max'] = round(comp.get('max', 0) * factor, 2)
                cost[component] = comp
        
        # Don't adjust permits (fixed costs)
        
        adjusted['cost'] = cost
        
        return adjusted
    
    def _add_calibration_metadata(
        self,
        estimate: Dict,
        calibration: Optional[CalibrationFactor],
        status: str
    ) -> Dict:
        """Add calibration metadata to estimate."""
        estimate = estimate.copy()
        
        estimate['calibration'] = {
            'status': status,  # "applied", "low_confidence", "insufficient_data"
            'factor': calibration.factor if calibration else 1.0,
            'confidence': calibration.confidence if calibration else 0.0,
            'sample_count': calibration.sample_count if calibration else 0,
            'reasoning': calibration.reasoning if calibration else "No historical data available"
        }
        
        return estimate
    
    def _determine_complexity(self, issue: Dict, estimate: Dict) -> str:
        """Determine complexity level."""
        severity = issue.get('severity', '').lower()
        confidence = estimate.get('confidence_score', 0.5)
        cost = estimate.get('cost', {}).get('total', {}).get('max', 0)
        
        if cost > 5000 or confidence < 0.6:
            return 'complex'
        elif cost < 500 and confidence > 0.8:
            return 'simple'
        else:
            return 'medium'
    
    def get_improvement_metrics(self) -> Dict:
        """
        Get metrics showing estimation improvement over time.
        
        Compares early estimates vs recent estimates to show learning effect.
        """
        all_records = list(self.db.records.values())
        
        if len(all_records) < 10:
            return {
                'insufficient_data': True,
                'message': 'Need at least 10 estimates with actuals to measure improvement'
            }
        
        # Split into early and recent
        sorted_records = sorted(all_records, key=lambda r: r.timestamp)
        split_point = len(sorted_records) // 2
        
        early_records = [r for r in sorted_records[:split_point] if r.actual_cost is not None]
        recent_records = [r for r in sorted_records[split_point:] if r.actual_cost is not None]
        
        if len(early_records) < 3 or len(recent_records) < 3:
            return {
                'insufficient_data': True,
                'message': 'Need more actuals in both periods'
            }
        
        # Calculate variance for each period
        early_variances = [abs(r.variance_pct) for r in early_records if r.variance_pct is not None]
        recent_variances = [abs(r.variance_pct) for r in recent_records if r.variance_pct is not None]
        
        early_avg = statistics.mean(early_variances) if early_variances else 0
        recent_avg = statistics.mean(recent_variances) if recent_variances else 0
        
        improvement_pct = ((early_avg - recent_avg) / early_avg * 100) if early_avg > 0 else 0
        
        return {
            'insufficient_data': False,
            'early_period': {
                'count': len(early_records),
                'avg_variance_pct': early_avg,
                'median_variance_pct': statistics.median(early_variances) if early_variances else 0
            },
            'recent_period': {
                'count': len(recent_records),
                'avg_variance_pct': recent_avg,
                'median_variance_pct': statistics.median(recent_variances) if recent_variances else 0
            },
            'improvement_pct': improvement_pct,
            'learning_effective': improvement_pct > 5  # 5%+ improvement indicates learning
        }
    
    def get_stats(self) -> Dict:
        """Get feedback loop statistics."""
        stats = self.stats.copy()
        
        # Add database stats
        stats['database'] = self.db.get_stats()
        
        return stats

