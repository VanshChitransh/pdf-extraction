"""
Phase 3 Enhancement: Variance Analyzer

Advanced statistical analysis of estimate variance.
Tracks accuracy trends, identifies problem areas, and measures learning effectiveness.

Features:
- Variance trend analysis over time
- Category-specific accuracy metrics  
- Contractor comparison
- Confidence calibration
- Learning effectiveness measurement
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import statistics
import json


@dataclass
class VarianceMetrics:
    """Comprehensive variance metrics."""
    sample_count: int
    avg_variance_pct: float
    median_variance_pct: float
    std_dev_variance_pct: float
    within_range_pct: float
    avg_variance_dollars: float
    accuracy_score: float  # 0-100, higher is better
    
    # Breakdown by range
    overestimated_count: int  # actual < estimated_min
    underestimated_count: int  # actual > estimated_max
    within_range_count: int
    
    # Confidence calibration
    avg_confidence_score: float
    confidence_accuracy_correlation: float


class VarianceAnalyzer:
    """
    Analyzes estimation variance and accuracy patterns.
    
    Phase 3 Analytics:
    - Track variance trends over time
    - Identify categories needing improvement
    - Measure learning effectiveness
    - Calibrate confidence scores
    - Compare contractor reliability
    
    Usage:
        analyzer = VarianceAnalyzer(calibration_db)
        
        # Get overall metrics
        metrics = analyzer.get_overall_metrics()
        
        # Analyze trends
        trends = analyzer.analyze_trends()
        
        # Find problem areas
        problems = analyzer.identify_problem_areas()
    """
    
    def __init__(self, calibration_db):
        """Initialize analyzer with calibration database."""
        self.db = calibration_db
    
    def get_overall_metrics(self) -> VarianceMetrics:
        """Get overall variance metrics across all estimates."""
        records_with_actuals = [
            r for r in self.db.records.values()
            if r.actual_cost is not None
        ]
        
        if not records_with_actuals:
            return self._empty_metrics()
        
        return self._calculate_metrics(records_with_actuals)
    
    def get_metrics_by_category(self) -> Dict[str, VarianceMetrics]:
        """Get variance metrics broken down by category."""
        categories = {}
        
        for record in self.db.records.values():
            if record.actual_cost is None:
                continue
            
            cat = record.category
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(record)
        
        return {
            cat: self._calculate_metrics(records)
            for cat, records in categories.items()
        }
    
    def get_metrics_by_strategy(self) -> Dict[str, VarianceMetrics]:
        """Get variance metrics broken down by estimation strategy."""
        strategies = {}
        
        for record in self.db.records.values():
            if record.actual_cost is None:
                continue
            
            strat = record.estimation_strategy
            if strat not in strategies:
                strategies[strat] = []
            strategies[strat].append(record)
        
        return {
            strat: self._calculate_metrics(records)
            for strat, records in strategies.items()
        }
    
    def get_metrics_by_complexity(self) -> Dict[str, VarianceMetrics]:
        """Get variance metrics broken down by complexity."""
        complexities = {}
        
        for record in self.db.records.values():
            if record.actual_cost is None:
                continue
            
            comp = record.complexity
            if comp not in complexities:
                complexities[comp] = []
            complexities[comp].append(record)
        
        return {
            comp: self._calculate_metrics(records)
            for comp, records in complexities.items()
        }
    
    def analyze_trends(
        self,
        period_days: int = 30
    ) -> Dict:
        """
        Analyze variance trends over time.
        
        Args:
            period_days: Number of days per period
            
        Returns:
            Dict with trend analysis
        """
        records_with_actuals = [
            r for r in self.db.records.values()
            if r.actual_cost is not None
        ]
        
        if len(records_with_actuals) < 10:
            return {
                'insufficient_data': True,
                'message': 'Need at least 10 estimates with actuals'
            }
        
        # Sort by timestamp
        sorted_records = sorted(records_with_actuals, key=lambda r: r.timestamp)
        
        # Group into periods
        first_timestamp = datetime.fromisoformat(sorted_records[0].timestamp)
        last_timestamp = datetime.fromisoformat(sorted_records[-1].timestamp)
        total_days = (last_timestamp - first_timestamp).days
        
        if total_days < period_days:
            return {
                'insufficient_data': True,
                'message': f'Need at least {period_days} days of data'
            }
        
        # Create periods
        periods = []
        current_date = first_timestamp
        
        while current_date <= last_timestamp:
            period_end = current_date + timedelta(days=period_days)
            period_records = [
                r for r in sorted_records
                if current_date <= datetime.fromisoformat(r.timestamp) < period_end
            ]
            
            if period_records:
                metrics = self._calculate_metrics(period_records)
                periods.append({
                    'start_date': current_date.isoformat(),
                    'end_date': period_end.isoformat(),
                    'metrics': metrics,
                    'count': len(period_records)
                })
            
            current_date = period_end
        
        if len(periods) < 2:
            return {
                'insufficient_data': True,
                'message': 'Need at least 2 periods'
            }
        
        # Calculate trend
        variances = [p['metrics'].avg_variance_pct for p in periods]
        trend_direction = self._calculate_trend(variances)
        
        return {
            'insufficient_data': False,
            'periods': periods,
            'trend_direction': trend_direction,  # 'improving', 'declining', 'stable'
            'variance_change': variances[-1] - variances[0],
            'improvement_pct': ((variances[0] - variances[-1]) / variances[0] * 100) if variances[0] > 0 else 0
        }
    
    def identify_problem_areas(
        self,
        variance_threshold: float = 20.0
    ) -> List[Dict]:
        """
        Identify categories/complexity levels with high variance.
        
        Args:
            variance_threshold: Variance % threshold for flagging
            
        Returns:
            List of problem areas sorted by severity
        """
        problems = []
        
        # Check by category
        for category, metrics in self.get_metrics_by_category().items():
            if metrics.avg_variance_pct > variance_threshold:
                problems.append({
                    'type': 'category',
                    'name': category,
                    'avg_variance_pct': metrics.avg_variance_pct,
                    'sample_count': metrics.sample_count,
                    'severity': self._calculate_severity(metrics.avg_variance_pct)
                })
        
        # Check by complexity
        for complexity, metrics in self.get_metrics_by_complexity().items():
            if metrics.avg_variance_pct > variance_threshold:
                problems.append({
                    'type': 'complexity',
                    'name': complexity,
                    'avg_variance_pct': metrics.avg_variance_pct,
                    'sample_count': metrics.sample_count,
                    'severity': self._calculate_severity(metrics.avg_variance_pct)
                })
        
        # Check by strategy
        for strategy, metrics in self.get_metrics_by_strategy().items():
            if metrics.avg_variance_pct > variance_threshold:
                problems.append({
                    'type': 'strategy',
                    'name': strategy,
                    'avg_variance_pct': metrics.avg_variance_pct,
                    'sample_count': metrics.sample_count,
                    'severity': self._calculate_severity(metrics.avg_variance_pct)
                })
        
        # Sort by severity
        problems.sort(key=lambda x: x['avg_variance_pct'], reverse=True)
        
        return problems
    
    def compare_contractors(self) -> Dict[str, Dict]:
        """Compare accuracy by contractor."""
        contractors = {}
        
        for record in self.db.records.values():
            if record.actual_cost is None or not record.contractor_name:
                continue
            
            contractor = record.contractor_name
            if contractor not in contractors:
                contractors[contractor] = []
            contractors[contractor].append(record)
        
        return {
            contractor: {
                'count': len(records),
                'avg_quote': statistics.mean([r.actual_cost for r in records]),
                'median_quote': statistics.median([r.actual_cost for r in records]),
                'avg_variance_from_estimate': statistics.mean([
                    abs(r.variance_pct) for r in records if r.variance_pct is not None
                ]),
                'reliability_score': self._calculate_reliability_score(records)
            }
            for contractor, records in contractors.items()
            if len(records) >= 3  # Need minimum samples
        }
    
    def calibrate_confidence_scores(self) -> Dict:
        """
        Analyze how well confidence scores correlate with actual accuracy.
        
        Returns:
            Dict with confidence calibration analysis
        """
        records_with_actuals = [
            r for r in self.db.records.values()
            if r.actual_cost is not None and r.confidence_score > 0
        ]
        
        if len(records_with_actuals) < 10:
            return {
                'insufficient_data': True,
                'message': 'Need at least 10 estimates with actuals'
            }
        
        # Group by confidence ranges
        ranges = [
            (0.0, 0.5, 'low'),
            (0.5, 0.7, 'medium'),
            (0.7, 0.9, 'high'),
            (0.9, 1.0, 'very_high')
        ]
        
        confidence_analysis = {}
        
        for min_conf, max_conf, label in ranges:
            range_records = [
                r for r in records_with_actuals
                if min_conf <= r.confidence_score < max_conf
            ]
            
            if not range_records:
                continue
            
            variances = [abs(r.variance_pct) for r in range_records if r.variance_pct is not None]
            within_range = sum(1 for r in range_records if r.within_range)
            
            confidence_analysis[label] = {
                'confidence_range': (min_conf, max_conf),
                'count': len(range_records),
                'avg_variance_pct': statistics.mean(variances) if variances else 0,
                'within_range_pct': (within_range / len(range_records)) * 100,
                'calibrated': None  # Will be calculated below
            }
        
        # Check if confidence is well-calibrated
        # (higher confidence should mean lower variance)
        for label, data in confidence_analysis.items():
            if data['count'] >= 5:
                # Well-calibrated if high confidence = low variance
                if label == 'very_high' and data['avg_variance_pct'] < 10:
                    data['calibrated'] = True
                elif label == 'high' and data['avg_variance_pct'] < 15:
                    data['calibrated'] = True
                elif label == 'medium' and data['avg_variance_pct'] < 25:
                    data['calibrated'] = True
                else:
                    data['calibrated'] = False
        
        return {
            'insufficient_data': False,
            'by_confidence_range': confidence_analysis,
            'overall_correlation': self._calculate_confidence_correlation(records_with_actuals)
        }
    
    def generate_report(self) -> Dict:
        """Generate comprehensive variance analysis report."""
        return {
            'timestamp': datetime.now().isoformat(),
            'overall_metrics': self._metrics_to_dict(self.get_overall_metrics()),
            'by_category': {
                cat: self._metrics_to_dict(metrics)
                for cat, metrics in self.get_metrics_by_category().items()
            },
            'by_strategy': {
                strat: self._metrics_to_dict(metrics)
                for strat, metrics in self.get_metrics_by_strategy().items()
            },
            'by_complexity': {
                comp: self._metrics_to_dict(metrics)
                for comp, metrics in self.get_metrics_by_complexity().items()
            },
            'trends': self.analyze_trends(),
            'problem_areas': self.identify_problem_areas(),
            'contractor_comparison': self.compare_contractors(),
            'confidence_calibration': self.calibrate_confidence_scores()
        }
    
    def export_report(self, output_path: str):
        """Export analysis report to JSON file."""
        report = self.generate_report()
        
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
    
    def _calculate_metrics(self, records: List) -> VarianceMetrics:
        """Calculate metrics for a list of records."""
        if not records:
            return self._empty_metrics()
        
        variances_pct = [r.variance_pct for r in records if r.variance_pct is not None]
        variances_dollars = [r.variance_dollars for r in records if r.variance_dollars is not None]
        confidences = [r.confidence_score for r in records if r.confidence_score > 0]
        
        overestimated = sum(1 for r in records if r.actual_cost < r.estimated_min)
        underestimated = sum(1 for r in records if r.actual_cost > r.estimated_max)
        within_range = sum(1 for r in records if r.within_range)
        
        # Calculate accuracy score (0-100)
        # Based on within-range % and average variance
        within_range_pct = (within_range / len(records)) * 100 if records else 0
        avg_abs_variance = statistics.mean([abs(v) for v in variances_pct]) if variances_pct else 0
        
        # Accuracy score: 50% from being in range, 50% from low variance
        accuracy_score = (within_range_pct * 0.5) + ((100 - min(100, avg_abs_variance)) * 0.5)
        
        return VarianceMetrics(
            sample_count=len(records),
            avg_variance_pct=statistics.mean(variances_pct) if variances_pct else 0,
            median_variance_pct=statistics.median(variances_pct) if variances_pct else 0,
            std_dev_variance_pct=statistics.stdev(variances_pct) if len(variances_pct) > 1 else 0,
            within_range_pct=within_range_pct,
            avg_variance_dollars=statistics.mean(variances_dollars) if variances_dollars else 0,
            accuracy_score=accuracy_score,
            overestimated_count=overestimated,
            underestimated_count=underestimated,
            within_range_count=within_range,
            avg_confidence_score=statistics.mean(confidences) if confidences else 0,
            confidence_accuracy_correlation=self._calculate_confidence_correlation(records)
        )
    
    def _empty_metrics(self) -> VarianceMetrics:
        """Return empty metrics."""
        return VarianceMetrics(
            sample_count=0,
            avg_variance_pct=0,
            median_variance_pct=0,
            std_dev_variance_pct=0,
            within_range_pct=0,
            avg_variance_dollars=0,
            accuracy_score=0,
            overestimated_count=0,
            underestimated_count=0,
            within_range_count=0,
            avg_confidence_score=0,
            confidence_accuracy_correlation=0
        )
    
    def _metrics_to_dict(self, metrics: VarianceMetrics) -> Dict:
        """Convert metrics to dictionary."""
        return {
            'sample_count': metrics.sample_count,
            'avg_variance_pct': round(metrics.avg_variance_pct, 2),
            'median_variance_pct': round(metrics.median_variance_pct, 2),
            'std_dev_variance_pct': round(metrics.std_dev_variance_pct, 2),
            'within_range_pct': round(metrics.within_range_pct, 2),
            'avg_variance_dollars': round(metrics.avg_variance_dollars, 2),
            'accuracy_score': round(metrics.accuracy_score, 2),
            'overestimated_count': metrics.overestimated_count,
            'underestimated_count': metrics.underestimated_count,
            'within_range_count': metrics.within_range_count,
            'avg_confidence_score': round(metrics.avg_confidence_score, 2),
            'confidence_accuracy_correlation': round(metrics.confidence_accuracy_correlation, 2)
        }
    
    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate trend direction from values."""
        if len(values) < 2:
            return 'unknown'
        
        # Simple linear trend
        first_half_avg = statistics.mean(values[:len(values)//2])
        second_half_avg = statistics.mean(values[len(values)//2:])
        
        change_pct = ((second_half_avg - first_half_avg) / first_half_avg * 100) if first_half_avg > 0 else 0
        
        if change_pct < -5:
            return 'improving'  # Variance decreasing
        elif change_pct > 5:
            return 'declining'  # Variance increasing
        else:
            return 'stable'
    
    def _calculate_severity(self, variance_pct: float) -> str:
        """Calculate problem severity."""
        abs_variance = abs(variance_pct)
        
        if abs_variance > 40:
            return 'critical'
        elif abs_variance > 25:
            return 'high'
        elif abs_variance > 15:
            return 'medium'
        else:
            return 'low'
    
    def _calculate_reliability_score(self, records: List) -> float:
        """Calculate contractor reliability score (0-100)."""
        if not records:
            return 0
        
        # Based on consistency (low variance) and competitiveness (not too high)
        variances = [abs(r.variance_pct) for r in records if r.variance_pct is not None]
        quotes = [r.actual_cost for r in records]
        
        if not variances:
            return 0
        
        # Consistency score (lower variance = better)
        avg_variance = statistics.mean(variances)
        consistency_score = max(0, 100 - avg_variance)
        
        # Competitiveness score (check if quotes are reasonable, not too high)
        # This is complex, simplified here
        competitiveness_score = 75  # Placeholder
        
        return (consistency_score * 0.6) + (competitiveness_score * 0.4)
    
    def _calculate_confidence_correlation(self, records: List) -> float:
        """
        Calculate correlation between confidence scores and accuracy.
        
        Returns: -1 to 1 (1 = perfect positive correlation)
        """
        if len(records) < 5:
            return 0
        
        # Get confidence and accuracy pairs
        pairs = [
            (r.confidence_score, 100 - abs(r.variance_pct))  # Higher = more accurate
            for r in records
            if r.confidence_score > 0 and r.variance_pct is not None
        ]
        
        if len(pairs) < 5:
            return 0
        
        # Simple correlation coefficient
        try:
            confidences = [p[0] for p in pairs]
            accuracies = [p[1] for p in pairs]
            
            correlation = statistics.correlation(confidences, accuracies) if len(pairs) >= 3 else 0
            return correlation
        except:
            return 0

