"""
Phase 3 Enhancement: Calibration Database

Stores historical data comparing AI estimates to actual contractor quotes.
This enables the system to learn from real-world data and improve accuracy over time.

Database Schema:
- Estimate records (AI predictions)
- Actual quotes (contractor bids)
- Variance metrics (difference analysis)
- Calibration factors (adjustment multipliers)
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import json
from pathlib import Path
import statistics


@dataclass
class EstimateRecord:
    """Record of an estimate and actual cost."""
    record_id: str
    timestamp: str
    issue_title: str
    issue_description: str
    category: str
    complexity: str
    severity: str
    
    # Estimate data
    estimated_min: float
    estimated_max: float
    estimated_midpoint: float
    estimation_strategy: str
    confidence_score: float
    
    # Actual data (populated later)
    actual_cost: Optional[float] = None
    contractor_name: Optional[str] = None
    quote_date: Optional[str] = None
    
    # Variance analysis
    variance_pct: Optional[float] = None  # (actual - estimated_mid) / estimated_mid
    variance_dollars: Optional[float] = None
    within_range: Optional[bool] = None  # actual between min and max
    
    # Property context
    property_size_sqft: Optional[int] = None
    property_age: Optional[int] = None
    location: str = "Houston, TX"


class CalibrationDatabase:
    """
    Manages storage and retrieval of estimate calibration data.
    
    Features:
    - Store estimate vs actual cost pairs
    - Query by category, complexity, contractor
    - Calculate calibration factors
    - Track variance trends over time
    
    Usage:
        db = CalibrationDatabase("calibration_data.json")
        
        # Store estimate
        record_id = db.store_estimate(estimate, issue)
        
        # Later, add actual cost
        db.add_actual_cost(record_id, actual_cost, contractor)
        
        # Get calibration factor
        factor = db.get_calibration_factor("HVAC", "medium")
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize calibration database.
        
        Args:
            db_path: Path to JSON database file. If None, uses default location.
        """
        if db_path is None:
            db_path = Path(__file__).parent.parent.parent / "calibration_data" / "estimates.json"
        
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.records: Dict[str, EstimateRecord] = {}
        self._load_database()
        
        self.stats = {
            'total_estimates': 0,
            'estimates_with_actuals': 0,
            'average_variance_pct': 0.0,
            'within_range_pct': 0.0
        }
        self._update_stats()
    
    def store_estimate(
        self,
        estimate: Dict,
        issue: Dict,
        property_metadata: Optional[Dict] = None
    ) -> str:
        """
        Store an estimate for future calibration.
        
        Args:
            estimate: Estimate dictionary with cost breakdown
            issue: Issue dictionary with title, description, etc.
            property_metadata: Optional property context
            
        Returns:
            record_id for referencing this estimate later
        """
        # Generate unique ID
        timestamp = datetime.now().isoformat()
        record_id = f"{issue.get('id', 'unknown')}_{timestamp}"
        
        # Extract cost data
        cost = estimate.get('cost', {})
        total = cost.get('total', {})
        estimated_min = total.get('min', 0)
        estimated_max = total.get('max', 0)
        estimated_midpoint = (estimated_min + estimated_max) / 2
        
        # Create record
        record = EstimateRecord(
            record_id=record_id,
            timestamp=timestamp,
            issue_title=issue.get('title', 'Unknown'),
            issue_description=issue.get('description', ''),
            category=issue.get('category', 'General'),
            complexity=self._determine_complexity(issue, estimate),
            severity=issue.get('severity', 'Medium'),
            estimated_min=estimated_min,
            estimated_max=estimated_max,
            estimated_midpoint=estimated_midpoint,
            estimation_strategy=estimate.get('estimation_strategy', 'unknown'),
            confidence_score=estimate.get('confidence_score', 0.5),
            property_size_sqft=property_metadata.get('square_footage') if property_metadata else None,
            property_age=2025 - property_metadata.get('year_built') if property_metadata and property_metadata.get('year_built') else None,
            location=property_metadata.get('location', 'Houston, TX') if property_metadata else 'Houston, TX'
        )
        
        self.records[record_id] = record
        self._save_database()
        self._update_stats()
        
        return record_id
    
    def add_actual_cost(
        self,
        record_id: str,
        actual_cost: float,
        contractor_name: str,
        quote_date: Optional[str] = None
    ) -> bool:
        """
        Add actual cost from contractor quote to existing estimate record.
        
        Args:
            record_id: ID of estimate record
            actual_cost: Actual contractor quote amount
            contractor_name: Name of contractor who provided quote
            quote_date: Optional date of quote
            
        Returns:
            True if successful, False if record not found
        """
        if record_id not in self.records:
            return False
        
        record = self.records[record_id]
        
        # Update actual data
        record.actual_cost = actual_cost
        record.contractor_name = contractor_name
        record.quote_date = quote_date or datetime.now().isoformat()
        
        # Calculate variance
        if record.estimated_midpoint > 0:
            record.variance_dollars = actual_cost - record.estimated_midpoint
            record.variance_pct = (record.variance_dollars / record.estimated_midpoint) * 100
        
        # Check if within range
        record.within_range = record.estimated_min <= actual_cost <= record.estimated_max
        
        self._save_database()
        self._update_stats()
        
        return True
    
    def get_calibration_factor(
        self,
        category: str,
        complexity: str = None,
        min_samples: int = 3
    ) -> Optional[float]:
        """
        Calculate calibration factor for a category/complexity combination.
        
        Calibration factor = Average(actual_cost / estimated_midpoint)
        
        Args:
            category: Issue category (e.g., "HVAC", "Electrical")
            complexity: Optional complexity filter ("simple", "medium", "complex")
            min_samples: Minimum number of samples required to return factor
            
        Returns:
            Calibration factor (e.g., 1.15 means estimates are 15% too low)
            None if insufficient data
        """
        # Filter records
        relevant_records = [
            r for r in self.records.values()
            if r.actual_cost is not None
            and r.category.lower() == category.lower()
            and (complexity is None or r.complexity.lower() == complexity.lower())
        ]
        
        if len(relevant_records) < min_samples:
            return None
        
        # Calculate ratios
        ratios = []
        for record in relevant_records:
            if record.estimated_midpoint > 0:
                ratio = record.actual_cost / record.estimated_midpoint
                ratios.append(ratio)
        
        if not ratios:
            return None
        
        # Return median (more robust than mean for outliers)
        return statistics.median(ratios)
    
    def get_variance_stats(
        self,
        category: Optional[str] = None,
        complexity: Optional[str] = None,
        strategy: Optional[str] = None
    ) -> Dict:
        """
        Get variance statistics for filtered records.
        
        Args:
            category: Optional category filter
            complexity: Optional complexity filter
            strategy: Optional estimation strategy filter
            
        Returns:
            Dict with variance statistics
        """
        # Filter records with actual costs
        filtered = [
            r for r in self.records.values()
            if r.actual_cost is not None
            and (category is None or r.category.lower() == category.lower())
            and (complexity is None or r.complexity.lower() == complexity.lower())
            and (strategy is None or r.estimation_strategy == strategy)
        ]
        
        if not filtered:
            return {
                'count': 0,
                'avg_variance_pct': 0,
                'median_variance_pct': 0,
                'within_range_pct': 0,
                'avg_variance_dollars': 0
            }
        
        variances_pct = [r.variance_pct for r in filtered if r.variance_pct is not None]
        variances_dollars = [r.variance_dollars for r in filtered if r.variance_dollars is not None]
        within_range_count = sum(1 for r in filtered if r.within_range)
        
        return {
            'count': len(filtered),
            'avg_variance_pct': statistics.mean(variances_pct) if variances_pct else 0,
            'median_variance_pct': statistics.median(variances_pct) if variances_pct else 0,
            'std_dev_variance_pct': statistics.stdev(variances_pct) if len(variances_pct) > 1 else 0,
            'within_range_pct': (within_range_count / len(filtered)) * 100,
            'avg_variance_dollars': statistics.mean(variances_dollars) if variances_dollars else 0,
            'total_estimates': len(filtered)
        }
    
    def get_top_variance_categories(self, limit: int = 10) -> List[Tuple[str, float]]:
        """
        Get categories with highest variance (need most calibration).
        
        Args:
            limit: Maximum number of categories to return
            
        Returns:
            List of (category, avg_variance_pct) tuples, sorted by variance
        """
        # Group by category
        category_stats = {}
        
        for record in self.records.values():
            if record.actual_cost is None or record.variance_pct is None:
                continue
            
            cat = record.category
            if cat not in category_stats:
                category_stats[cat] = []
            
            category_stats[cat].append(abs(record.variance_pct))
        
        # Calculate average variance per category
        category_variances = [
            (cat, statistics.mean(variances))
            for cat, variances in category_stats.items()
        ]
        
        # Sort by variance (highest first)
        category_variances.sort(key=lambda x: x[1], reverse=True)
        
        return category_variances[:limit]
    
    def get_records_by_contractor(self, contractor_name: str) -> List[EstimateRecord]:
        """Get all records for a specific contractor."""
        return [
            r for r in self.records.values()
            if r.contractor_name and r.contractor_name.lower() == contractor_name.lower()
        ]
    
    def get_recent_records(self, limit: int = 50) -> List[EstimateRecord]:
        """Get most recent estimate records."""
        sorted_records = sorted(
            self.records.values(),
            key=lambda r: r.timestamp,
            reverse=True
        )
        return sorted_records[:limit]
    
    def export_for_analysis(self, output_path: str):
        """Export records to JSON for external analysis."""
        data = {
            'records': [asdict(r) for r in self.records.values()],
            'stats': self.get_stats(),
            'export_timestamp': datetime.now().isoformat()
        }
        
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def get_stats(self) -> Dict:
        """Get overall database statistics."""
        return self.stats.copy()
    
    def _determine_complexity(self, issue: Dict, estimate: Dict) -> str:
        """Determine complexity level from issue and estimate."""
        severity = issue.get('severity', '').lower()
        confidence = estimate.get('confidence_score', 0.5)
        cost = estimate.get('cost', {}).get('total', {}).get('max', 0)
        
        # High cost or low confidence = complex
        if cost > 5000 or confidence < 0.6:
            return 'complex'
        
        # Low cost and high confidence = simple
        if cost < 500 and confidence > 0.8:
            return 'simple'
        
        return 'medium'
    
    def _load_database(self):
        """Load database from file."""
        if not self.db_path.exists():
            return
        
        try:
            with open(self.db_path, 'r') as f:
                data = json.load(f)
            
            self.records = {
                record_id: EstimateRecord(**record_data)
                for record_id, record_data in data.get('records', {}).items()
            }
        except Exception as e:
            print(f"Warning: Could not load calibration database: {e}")
            self.records = {}
    
    def _save_database(self):
        """Save database to file."""
        try:
            data = {
                'records': {
                    record_id: asdict(record)
                    for record_id, record in self.records.items()
                },
                'last_updated': datetime.now().isoformat()
            }
            
            with open(self.db_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save calibration database: {e}")
    
    def _update_stats(self):
        """Update statistics cache."""
        total = len(self.records)
        with_actuals = sum(1 for r in self.records.values() if r.actual_cost is not None)
        
        if with_actuals > 0:
            variances = [
                r.variance_pct for r in self.records.values()
                if r.variance_pct is not None
            ]
            within_range = sum(
                1 for r in self.records.values()
                if r.within_range
            )
            
            self.stats = {
                'total_estimates': total,
                'estimates_with_actuals': with_actuals,
                'average_variance_pct': statistics.mean(variances) if variances else 0,
                'within_range_pct': (within_range / with_actuals) * 100 if with_actuals > 0 else 0
            }
        else:
            self.stats = {
                'total_estimates': total,
                'estimates_with_actuals': 0,
                'average_variance_pct': 0,
                'within_range_pct': 0
            }

