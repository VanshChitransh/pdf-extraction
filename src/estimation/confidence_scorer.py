"""
Advanced Multi-Dimensional Confidence Scorer

Calculates confidence scores across multiple dimensions:
- Data quality (description completeness, measurements, photos)
- Estimation factors (database match, historical similarity, market data)
- Risk factors (age uncertainty, access difficulty, hidden damage risk)
"""

from typing import Dict, Any, List, Optional
from datetime import datetime


class AdvancedConfidenceScorer:
    """
    Multi-dimensional confidence scoring system.
    
    Usage:
        scorer = AdvancedConfidenceScorer()
        
        confidence = scorer.calculate_confidence(
            estimate=ai_estimate,
            issue=issue_data,
            property_age=25,
            has_photos=True
        )
        
        print(f"Overall confidence: {confidence['overall']}")
        print(f"Breakdown: {confidence['breakdown']}")
    """
    
    def __init__(self):
        """Initialize confidence scorer with default weights."""
        self.weights = {
            # Data quality dimensions (40% of total)
            "description_completeness": 0.15,
            "has_measurements": 0.10,
            "has_photos": 0.10,
            "has_location": 0.05,
            
            # Estimation factors (40% of total)
            "database_match": 0.15,
            "market_data_availability": 0.10,
            "estimate_range_quality": 0.10,
            "reasoning_quality": 0.05,
            
            # Risk factors (20% of total)
            "age_uncertainty": 0.07,
            "access_difficulty": 0.07,
            "hidden_damage_risk": 0.06
        }
        
        # Thresholds for recommendations
        self.thresholds = {
            "excellent": 85,
            "good": 70,
            "fair": 55,
            "poor": 40
        }
    
    def calculate_confidence(
        self,
        estimate: Dict[str, Any],
        issue: Dict[str, Any],
        property_age: Optional[int] = None,
        has_photos: bool = False,
        database_match_score: Optional[float] = None,
        historical_similarity: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Calculate multi-dimensional confidence score.
        
        Args:
            estimate: AI-generated estimate with reasoning
            issue: Issue data from enriched JSON
            property_age: Age of property in years
            has_photos: Whether photos are available
            database_match_score: Score from cost database lookup (0-1)
            historical_similarity: Score from historical data matching (0-1)
        
        Returns:
            Dict with overall confidence, breakdown, and recommendation
        """
        scores = {}
        
        # === DATA QUALITY DIMENSIONS ===
        
        # Description completeness (0-100)
        scores["description_completeness"] = self._score_description(
            issue.get("issue", issue.get("description", ""))
        )
        
        # Measurements available (0-100)
        scores["has_measurements"] = self._score_measurements(issue)
        
        # Photos available (0-100)
        scores["has_photos"] = 100.0 if has_photos else 60.0
        
        # Location specified (0-100)
        scores["has_location"] = self._score_location(issue.get("location", ""))
        
        # === ESTIMATION FACTORS ===
        
        # Database match quality (0-100)
        scores["database_match"] = (database_match_score * 100) if database_match_score else 50.0
        
        # Market data availability (0-100)
        scores["market_data_availability"] = self._score_market_data(
            issue.get("category", ""),
            issue.get("item", "")
        )
        
        # Estimate range quality (0-100)
        scores["estimate_range_quality"] = self._score_range_quality(estimate)
        
        # Reasoning quality (0-100)
        scores["reasoning_quality"] = self._score_reasoning(
            estimate.get("reasoning", "")
        )
        
        # === RISK FACTORS ===
        
        # Age uncertainty (0-100, higher = less uncertainty)
        scores["age_uncertainty"] = self._score_age_factor(
            property_age,
            issue.get("item", "")
        )
        
        # Access difficulty (0-100, higher = easier access)
        scores["access_difficulty"] = self._score_access(
            issue.get("location", ""),
            issue.get("issue", "")
        )
        
        # Hidden damage risk (0-100, higher = less risk)
        scores["hidden_damage_risk"] = self._assess_hidden_damage(
            issue.get("issue", ""),
            issue.get("severity", "")
        )
        
        # Calculate weighted overall score
        overall_confidence = sum(
            scores[dimension] * self.weights[dimension]
            for dimension in scores
        )
        
        # Get recommendation
        recommendation = self._get_recommendation(overall_confidence)
        
        # Identify weak dimensions
        weak_dimensions = self._identify_weak_dimensions(scores)
        
        return {
            "overall": round(overall_confidence, 1),
            "breakdown": {k: round(v, 1) for k, v in scores.items()},
            "recommendation": recommendation,
            "weak_dimensions": weak_dimensions,
            "inspection_needed": overall_confidence < self.thresholds["fair"],
            "manual_review_needed": overall_confidence < self.thresholds["good"]
        }
    
    def _score_description(self, description: str) -> float:
        """Score description completeness (0-100)."""
        if not description:
            return 0.0
        
        score = 0.0
        desc_lower = description.lower()
        
        # Base score on length
        if len(description) < 20:
            score = 30.0
        elif len(description) < 50:
            score = 50.0
        elif len(description) < 100:
            score = 70.0
        else:
            score = 85.0
        
        # Bonus for specific details
        detail_keywords = [
            "crack", "leak", "damaged", "worn", "corrosion", "rust",
            "missing", "broken", "deteriorated", "sagging", "stain"
        ]
        details_found = sum(1 for kw in detail_keywords if kw in desc_lower)
        score += min(15, details_found * 3)
        
        # Bonus for measurements
        has_measurements = any(unit in desc_lower for unit in ["inch", "foot", "ft", '"', "'", "cm", "mm"])
        if has_measurements:
            score += 10
        
        return min(100.0, score)
    
    def _score_measurements(self, issue: Dict[str, Any]) -> float:
        """Score whether measurements are included (0-100)."""
        description = issue.get("issue", "") + " " + issue.get("description", "")
        
        # Check for explicit measurement fields
        if "measurements" in issue or "dimensions" in issue:
            return 100.0
        
        # Check for measurements in description
        measurement_patterns = [
            r'\d+\s*(inch|foot|ft|cm|mm)',
            r'\d+\s*["\']',
            r'\d+x\d+',
            r'\d+\s*(sq|square)\s*(ft|feet)',
        ]
        
        import re
        for pattern in measurement_patterns:
            if re.search(pattern, description.lower()):
                return 90.0
        
        return 50.0  # No measurements found
    
    def _score_location(self, location: str) -> float:
        """Score location specificity (0-100)."""
        if not location or location.lower() in ["not specified", "unknown", "n/a"]:
            return 30.0
        
        location_lower = location.lower()
        
        # Very specific location
        specific_keywords = [
            "northeast", "northwest", "southeast", "southwest",
            "front", "rear", "side", "left", "right",
            "bedroom", "bathroom", "kitchen", "garage",
            "attic", "basement", "crawl space"
        ]
        
        if any(kw in location_lower for kw in specific_keywords):
            return 100.0
        
        # General location
        general_keywords = ["exterior", "interior", "roof", "foundation", "wall"]
        if any(kw in location_lower for kw in general_keywords):
            return 70.0
        
        # Has something but vague
        return 50.0
    
    def _score_market_data(self, category: str, item: str) -> float:
        """Score market data availability for this type of work (0-100)."""
        # Common repairs with abundant market data
        high_data_categories = [
            "hvac", "plumbing", "electrical", "roofing", "painting"
        ]
        
        # Specialized work with less market data
        low_data_categories = [
            "structural", "foundation", "specialty"
        ]
        
        category_lower = category.lower()
        
        if any(cat in category_lower for cat in high_data_categories):
            return 90.0
        elif any(cat in category_lower for cat in low_data_categories):
            return 60.0
        else:
            return 75.0  # Medium availability
    
    def _score_range_quality(self, estimate: Dict[str, Any]) -> float:
        """Score quality of cost range (0-100)."""
        low = estimate.get("estimated_low", 0)
        high = estimate.get("estimated_high", 0)
        
        if low <= 0 or high <= 0:
            # Log warning - this indicates upstream problem
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Confidence scorer: estimate_range_quality=0.0 because estimated_low={low}, estimated_high={high}. Check AI response parsing.")
            return 0.0
        
        if low >= high:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Confidence scorer: Invalid range (low >= high): {low} >= {high}")
            return 0.0
        
        # Calculate range ratio
        ratio = high / low if low > 0 else 10.0
        
        # Ideal range: 1.3x to 2.5x
        if 1.3 <= ratio <= 2.5:
            return 100.0
        elif 1.2 <= ratio <= 3.0:
            return 85.0
        elif 1.1 <= ratio <= 4.0:
            return 70.0
        elif ratio < 1.1:
            return 40.0  # Too narrow (overconfident)
        else:
            return 50.0  # Too wide (high uncertainty)
    
    def _score_reasoning(self, reasoning: str) -> float:
        """Score quality of reasoning (0-100)."""
        if not reasoning:
            # Log warning - this indicates upstream problem
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Confidence scorer: reasoning_quality=0.0 because reasoning field is empty. Check AI response parsing.")
            return 0.0
        
        score = 0.0
        reasoning_lower = reasoning.lower()
        
        # Base score on length
        if len(reasoning) < 50:
            score = 20.0
        elif len(reasoning) < 150:
            score = 60.0
        elif len(reasoning) < 300:
            score = 80.0
        else:
            score = 90.0
        
        # Bonus for specific elements
        if "labor" in reasoning_lower or "hours" in reasoning_lower:
            score += 5
        if "material" in reasoning_lower or "supplies" in reasoning_lower:
            score += 5
        if "houston" in reasoning_lower or "market" in reasoning_lower:
            score += 5
        
        # Penalty for vague language
        vague_phrases = ["depends", "varies", "uncertain", "unclear", "unknown"]
        vague_count = sum(1 for phrase in vague_phrases if phrase in reasoning_lower)
        score -= vague_count * 5
        
        return max(0.0, min(100.0, score))
    
    def _score_age_factor(self, property_age: Optional[int], item: str) -> float:
        """Score age-related uncertainty (0-100, higher = less uncertainty)."""
        if property_age is None:
            return 60.0  # Unknown age = moderate uncertainty
        
        item_lower = item.lower()
        
        # For certain items, age is critical
        age_critical_items = {
            "hvac": (15, 20),      # (typical lifespan, high uncertainty age)
            "water heater": (10, 15),
            "roof": (20, 25),
            "electrical panel": (30, 40),
            "foundation": (50, 70)
        }
        
        for key, (typical_life, uncertain_age) in age_critical_items.items():
            if key in item_lower:
                if property_age <= typical_life:
                    return 90.0  # Young, low uncertainty
                elif property_age <= uncertain_age:
                    return 70.0  # Middle age, moderate uncertainty
                else:
                    return 50.0  # Old, high uncertainty (may need replacement)
        
        # Default: age is less critical
        return 80.0
    
    def _score_access(self, location: str, issue_description: str) -> float:
        """Score access difficulty (0-100, higher = easier access)."""
        text = (location + " " + issue_description).lower()
        
        # Difficult access locations
        difficult_keywords = [
            "attic", "crawl space", "under slab", "behind wall",
            "inaccessible", "difficult access", "hard to reach",
            "underground", "buried"
        ]
        
        if any(kw in text for kw in difficult_keywords):
            return 50.0  # Difficult access
        
        # Easy access locations
        easy_keywords = [
            "visible", "accessible", "exposed", "open",
            "exterior", "garage"
        ]
        
        if any(kw in text for kw in easy_keywords):
            return 95.0  # Easy access
        
        return 75.0  # Moderate access (default)
    
    def _assess_hidden_damage(self, issue_description: str, severity: str) -> float:
        """Assess risk of hidden damage (0-100, higher = less risk)."""
        desc_lower = issue_description.lower()
        severity_lower = severity.lower()
        
        # High risk indicators
        high_risk_keywords = [
            "leak", "water damage", "moisture", "mold",
            "foundation crack", "structural", "termite",
            "extensive", "severe"
        ]
        
        high_risk_found = sum(1 for kw in high_risk_keywords if kw in desc_lower)
        
        if high_risk_found >= 2 or severity_lower == "critical":
            return 40.0  # High risk of hidden damage
        elif high_risk_found == 1 or severity_lower == "high":
            return 60.0  # Moderate risk
        else:
            return 85.0  # Low risk
    
    def _get_recommendation(self, overall_score: float) -> str:
        """Get recommendation based on overall confidence score."""
        if overall_score >= self.thresholds["excellent"]:
            return "Excellent - Estimate is highly reliable"
        elif overall_score >= self.thresholds["good"]:
            return "Good - Estimate is reliable with minor uncertainties"
        elif overall_score >= self.thresholds["fair"]:
            return "Fair - Estimate has moderate uncertainties; consider professional inspection"
        elif overall_score >= self.thresholds["poor"]:
            return "Poor - High uncertainty; professional inspection strongly recommended"
        else:
            return "Very Poor - Insufficient data; on-site inspection required"
    
    def _identify_weak_dimensions(
        self,
        scores: Dict[str, float],
        threshold: float = 60.0
    ) -> List[Dict[str, Any]]:
        """Identify dimensions with low scores."""
        weak = []
        
        for dimension, score in scores.items():
            if score < threshold:
                weak.append({
                    "dimension": dimension,
                    "score": round(score, 1),
                    "improvement_tip": self._get_improvement_tip(dimension)
                })
        
        return sorted(weak, key=lambda x: x["score"])
    
    def _get_improvement_tip(self, dimension: str) -> str:
        """Get tip for improving a specific dimension."""
        tips = {
            "description_completeness": "Request more detailed description with specific observations",
            "has_measurements": "Include measurements (length, width, area affected)",
            "has_photos": "Take photos of the issue from multiple angles",
            "has_location": "Specify exact location (e.g., 'southeast corner of bedroom 2')",
            "database_match": "Need more specific component identification",
            "market_data_availability": "Limited market data for this type of work",
            "estimate_range_quality": "Cost range may be too wide or too narrow",
            "reasoning_quality": "Reasoning lacks specific cost breakdown details",
            "age_uncertainty": "Property age affects component lifespan; consider replacement vs repair",
            "access_difficulty": "Difficult access may increase labor costs significantly",
            "hidden_damage_risk": "High risk of discovering additional issues during repair"
        }
        
        return tips.get(dimension, "Consider gathering more information")
    
    def get_confidence_summary(
        self,
        estimates: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Get summary statistics across multiple estimates.
        
        Args:
            estimates: List of estimates with confidence scores
        
        Returns:
            Summary statistics
        """
        if not estimates:
            return {}
        
        confidences = [e.get("confidence", {}).get("overall", 0) for e in estimates]
        
        return {
            "average_confidence": round(sum(confidences) / len(confidences), 1),
            "min_confidence": min(confidences),
            "max_confidence": max(confidences),
            "excellent_count": sum(1 for c in confidences if c >= self.thresholds["excellent"]),
            "good_count": sum(1 for c in confidences if self.thresholds["good"] <= c < self.thresholds["excellent"]),
            "fair_count": sum(1 for c in confidences if self.thresholds["fair"] <= c < self.thresholds["good"]),
            "poor_count": sum(1 for c in confidences if c < self.thresholds["fair"]),
            "needs_inspection": sum(1 for c in confidences if c < self.thresholds["fair"])
        }

