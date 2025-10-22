"""
Output Validator

Validates AI-generated cost estimates to ensure they meet requirements,
catch hallucinations, and flag issues for manual review.
"""

from typing import Dict, List, Any, Optional, Tuple
import json
import re


class OutputValidator:
    """
    Validates AI cost estimation outputs.
    
    Features:
    - Schema validation (required fields present)
    - Value range validation (costs, confidence scores)
    - Consistency checks (severity vs action, cost ranges)
    - Hallucination detection
    - Quality scoring
    - Manual review flagging
    
    Usage:
        validator = OutputValidator()
        
        result = validator.validate_estimate(ai_response)
        if result["valid"]:
            # Save estimate
        else:
            # Log errors and flag for review
    """
    
    def __init__(
        self,
        min_cost: float = 0,
        max_cost: float = 50000,
        min_confidence: int = 0,
        max_confidence: int = 100,
        max_cost_ratio: float = 5.0,
        manual_review_threshold: int = 60
    ):
        """
        Initialize validator with constraints.
        
        Args:
            min_cost: Minimum acceptable cost estimate
            max_cost: Maximum cost before flagging for review
            min_confidence: Minimum confidence score
            max_confidence: Maximum confidence score
            max_cost_ratio: Maximum ratio of high/low estimate
            manual_review_threshold: Flag estimates below this confidence for review
        """
        self.min_cost = min_cost
        self.max_cost = max_cost
        self.min_confidence = min_confidence
        self.max_confidence = max_confidence
        self.max_cost_ratio = max_cost_ratio
        self.manual_review_threshold = manual_review_threshold
        
        self.required_fields = [
            'item',
            'issue_description',
            'severity',
            'suggested_action',
            'estimated_low',
            'estimated_high',
            'confidence_score',
            'reasoning'
        ]
        
        self.optional_fields = [
            'assumptions',
            'risk_factors',
            'category',
            'location'
        ]
        
        self.stats = {
            "total_validated": 0,
            "valid_count": 0,
            "invalid_count": 0,
            "flagged_for_review": 0,
            "errors_by_type": {}
        }
    
    def validate_estimate(
        self,
        estimate: Dict[str, Any],
        strict: bool = True
    ) -> Dict[str, Any]:
        """
        Validate a single cost estimate.
        
        Args:
            estimate: Estimate dict from AI
            strict: If True, fail on any error; if False, return warnings
        
        Returns:
            Dict with validation results:
            {
                "valid": bool,
                "errors": List[str],
                "warnings": List[str],
                "needs_review": bool,
                "quality_score": int (0-100),
                "cleaned_estimate": Dict (with any fixes applied)
            }
        """
        self.stats["total_validated"] += 1
        
        errors = []
        warnings = []
        needs_review = False
        
        # 1. Check required fields
        missing_fields = self._check_required_fields(estimate)
        if missing_fields:
            errors.append(f"Missing required fields: {', '.join(missing_fields)}")
        
        # 2. Validate field values
        field_errors = self._validate_field_values(estimate)
        errors.extend(field_errors)
        
        # 3. Check cost ranges
        cost_errors, cost_warnings = self._validate_cost_ranges(estimate)
        errors.extend(cost_errors)
        warnings.extend(cost_warnings)
        
        # 4. Check consistency
        consistency_warnings = self._check_consistency(estimate)
        warnings.extend(consistency_warnings)
        
        # 5. Detect potential hallucinations
        hallucination_warnings = self._detect_hallucinations(estimate)
        warnings.extend(hallucination_warnings)
        
        # 6. Calculate quality score
        quality_score = self._calculate_quality_score(estimate, errors, warnings)
        
        # 7. Determine if manual review needed
        needs_review = self._needs_manual_review(estimate, errors, warnings, quality_score)
        if needs_review:
            self.stats["flagged_for_review"] += 1
        
        # 8. Clean/fix estimate if possible
        cleaned_estimate = self._clean_estimate(estimate)
        
        # Update stats
        is_valid = len(errors) == 0 if strict else len(errors) == 0 or not needs_review
        if is_valid:
            self.stats["valid_count"] += 1
        else:
            self.stats["invalid_count"] += 1
        
        for error in errors:
            error_type = error.split(':')[0]
            self.stats["errors_by_type"][error_type] = \
                self.stats["errors_by_type"].get(error_type, 0) + 1
        
        return {
            "valid": is_valid,
            "errors": errors,
            "warnings": warnings,
            "needs_review": needs_review,
            "quality_score": quality_score,
            "cleaned_estimate": cleaned_estimate
        }
    
    def validate_batch(
        self,
        estimates: List[Dict[str, Any]],
        strict: bool = True
    ) -> Dict[str, Any]:
        """
        Validate a batch of estimates.
        
        Args:
            estimates: List of estimate dicts
            strict: If True, fail on any error
        
        Returns:
            Dict with batch validation results
        """
        results = []
        for estimate in estimates:
            result = self.validate_estimate(estimate, strict)
            results.append(result)
        
        valid_count = sum(1 for r in results if r["valid"])
        review_count = sum(1 for r in results if r["needs_review"])
        
        return {
            "total": len(estimates),
            "valid": valid_count,
            "invalid": len(estimates) - valid_count,
            "needs_review": review_count,
            "results": results,
            "success_rate": valid_count / len(estimates) if estimates else 0
        }
    
    def _check_required_fields(self, estimate: Dict[str, Any]) -> List[str]:
        """Check if all required fields are present."""
        missing = []
        for field in self.required_fields:
            if field not in estimate or estimate[field] is None or estimate[field] == "":
                missing.append(field)
        return missing
    
    def _validate_field_values(self, estimate: Dict[str, Any]) -> List[str]:
        """Validate individual field values."""
        errors = []
        
        # Check severity
        valid_severities = ["Low", "Medium", "High", "Critical", "Informational"]
        if "severity" in estimate:
            if estimate["severity"] not in valid_severities:
                errors.append(f"Invalid severity: {estimate['severity']} (must be one of {valid_severities})")
        
        # Check confidence score
        if "confidence_score" in estimate:
            score = estimate["confidence_score"]
            if not isinstance(score, (int, float)):
                errors.append(f"confidence_score must be numeric, got {type(score)}")
            elif not (self.min_confidence <= score <= self.max_confidence):
                errors.append(f"confidence_score {score} out of range [{self.min_confidence}, {self.max_confidence}]")
        
        # Check costs
        if "estimated_low" in estimate:
            low = estimate["estimated_low"]
            if not isinstance(low, (int, float)):
                errors.append(f"estimated_low must be numeric, got {type(low)}")
            elif low < self.min_cost:
                errors.append(f"estimated_low {low} below minimum {self.min_cost}")
        
        if "estimated_high" in estimate:
            high = estimate["estimated_high"]
            if not isinstance(high, (int, float)):
                errors.append(f"estimated_high must be numeric, got {type(high)}")
            elif high > self.max_cost:
                errors.append(f"estimated_high {high} exceeds maximum {self.max_cost} (flag for manual review)")
        
        # Check reasoning length
        if "reasoning" in estimate:
            reasoning = estimate["reasoning"]
            if not isinstance(reasoning, str):
                errors.append("reasoning must be a string")
            elif len(reasoning) < 50:
                errors.append("reasoning is too short (minimum 50 characters)")
        
        return errors
    
    def _validate_cost_ranges(
        self,
        estimate: Dict[str, Any]
    ) -> Tuple[List[str], List[str]]:
        """Validate cost ranges and relationships."""
        errors = []
        warnings = []
        
        if "estimated_low" not in estimate or "estimated_high" not in estimate:
            return errors, warnings
        
        low = estimate["estimated_low"]
        high = estimate["estimated_high"]
        
        # Check low < high
        if low >= high:
            errors.append(f"estimated_low ({low}) must be less than estimated_high ({high})")
        
        # Check minimum spread
        if high - low < 100 and low > 0:
            warnings.append(f"Cost range very narrow ({low}-{high}). Consider wider range for uncertainty.")
        
        # Check maximum ratio
        if low > 0 and high / low > self.max_cost_ratio:
            warnings.append(
                f"Cost range very wide (ratio {high/low:.1f}:1). "
                f"Indicates high uncertainty or insufficient information."
            )
        
        # Check for round numbers (possible lazy estimation)
        if low % 1000 == 0 and high % 1000 == 0:
            warnings.append("Both estimates are round thousands. Consider more precise estimates.")
        
        return errors, warnings
    
    def _check_consistency(self, estimate: Dict[str, Any]) -> List[str]:
        """Check for internal consistency issues."""
        warnings = []
        
        severity = estimate.get("severity", "").lower()
        action = estimate.get("suggested_action", "").lower()
        confidence = estimate.get("confidence_score", 100)
        
        # Critical severity should not have "monitor" action
        if severity == "critical" and "monitor" in action:
            warnings.append("Inconsistency: Critical severity with 'monitor' action")
        
        # Low severity should not have very high costs
        if severity == "low" and estimate.get("estimated_high", 0) > 5000:
            warnings.append("Inconsistency: Low severity with high cost estimate")
        
        # High confidence should not have very wide ranges
        if confidence > 85:
            low = estimate.get("estimated_low", 0)
            high = estimate.get("estimated_high", 0)
            if low > 0 and high / low > 3:
                warnings.append("Inconsistency: High confidence with wide cost range")
        
        # Immediate action should have higher severity
        if "immediate" in action and severity in ["low", "informational"]:
            warnings.append("Inconsistency: Immediate action with low severity")
        
        # Check if reasoning mentions uncertainty but confidence is high
        reasoning = estimate.get("reasoning", "").lower()
        uncertainty_keywords = ["uncertain", "unclear", "unknown", "depends", "may vary", "estimate"]
        if any(keyword in reasoning for keyword in uncertainty_keywords) and confidence > 80:
            warnings.append("Inconsistency: Reasoning mentions uncertainty but confidence is high")
        
        return warnings
    
    def _detect_hallucinations(self, estimate: Dict[str, Any]) -> List[str]:
        """Detect potential AI hallucinations."""
        warnings = []
        
        reasoning = estimate.get("reasoning", "")
        description = estimate.get("issue_description", "")
        
        # Check for generic/template-like responses
        generic_phrases = [
            "as mentioned earlier",
            "as discussed",
            "according to the document",
            "based on the inspection report",
            "the inspector noted"
        ]
        
        for phrase in generic_phrases:
            if phrase in reasoning.lower():
                warnings.append(f"Possible hallucination: Generic phrase '{phrase}' in reasoning")
        
        # Check for unrealistic precision
        if "estimated_low" in estimate and "estimated_high" in estimate:
            low = estimate["estimated_low"]
            high = estimate["estimated_high"]
            
            # Very specific estimates (not rounded) might be hallucinated
            if low % 10 != 0 and high % 10 != 0 and low != high:
                if low % 5 != 0 or high % 5 != 0:
                    warnings.append("Unusual precision in estimates (not rounded to $5 or $10)")
        
        # Check for excessive detail without justification
        if len(reasoning) > 500 and estimate.get("confidence_score", 0) < 70:
            warnings.append("Very detailed reasoning despite low confidence")
        
        # Check for contradictions between description and reasoning
        if "replace" in description.lower() and "repair" in reasoning.lower() and "replace" not in reasoning.lower():
            warnings.append("Possible contradiction: Description mentions replace but reasoning focuses on repair")
        
        return warnings
    
    def _calculate_quality_score(
        self,
        estimate: Dict[str, Any],
        errors: List[str],
        warnings: List[str]
    ) -> int:
        """Calculate overall quality score (0-100)."""
        score = 100
        
        # Deduct for errors
        score -= len(errors) * 20
        
        # Deduct for warnings
        score -= len(warnings) * 5
        
        # Bonus for having optional fields
        if "assumptions" in estimate and estimate["assumptions"]:
            score += 5
        if "risk_factors" in estimate and estimate["risk_factors"]:
            score += 5
        
        # Bonus for detailed reasoning
        reasoning_len = len(estimate.get("reasoning", ""))
        if reasoning_len > 200:
            score += 5
        
        # Deduct for low confidence
        confidence = estimate.get("confidence_score", 100)
        if confidence < 50:
            score -= 10
        
        return max(0, min(100, score))
    
    def _needs_manual_review(
        self,
        estimate: Dict[str, Any],
        errors: List[str],
        warnings: List[str],
        quality_score: int
    ) -> bool:
        """Determine if estimate needs manual review."""
        
        # Always review if there are errors
        if errors:
            return True
        
        # Review if quality score is low
        if quality_score < 60:
            return True
        
        # Review if confidence is low
        confidence = estimate.get("confidence_score", 100)
        if confidence < self.manual_review_threshold:
            return True
        
        # Review if cost is very high
        high_cost = estimate.get("estimated_high", 0)
        if high_cost > self.max_cost:
            return True
        
        # Review if multiple warnings
        if len(warnings) >= 3:
            return True
        
        # Review if cost range is very wide (high uncertainty)
        low = estimate.get("estimated_low", 0)
        high = estimate.get("estimated_high", 0)
        if low > 0 and high / low > 4:
            return True
        
        return False
    
    def _clean_estimate(self, estimate: Dict[str, Any]) -> Dict[str, Any]:
        """Clean and normalize estimate data."""
        cleaned = estimate.copy()
        
        # Ensure numeric fields are proper type
        for field in ["estimated_low", "estimated_high"]:
            if field in cleaned:
                try:
                    cleaned[field] = float(cleaned[field])
                except (ValueError, TypeError):
                    pass
        
        if "confidence_score" in cleaned:
            try:
                cleaned["confidence_score"] = int(float(cleaned["confidence_score"]))
            except (ValueError, TypeError):
                pass
        
        # Capitalize severity
        if "severity" in cleaned:
            cleaned["severity"] = cleaned["severity"].capitalize()
        
        # Strip whitespace from strings
        for field in ["item", "issue_description", "suggested_action", "reasoning"]:
            if field in cleaned and isinstance(cleaned[field], str):
                cleaned[field] = cleaned[field].strip()
        
        # Ensure lists are lists
        for field in ["assumptions", "risk_factors"]:
            if field in cleaned and not isinstance(cleaned[field], list):
                if isinstance(cleaned[field], str):
                    # Try to parse as JSON array
                    try:
                        parsed = json.loads(cleaned[field])
                        if isinstance(parsed, list):
                            cleaned[field] = parsed
                    except json.JSONDecodeError:
                        # Split by common delimiters
                        cleaned[field] = [
                            item.strip()
                            for item in re.split(r'[;\n]', cleaned[field])
                            if item.strip()
                        ]
        
        return cleaned
    
    def get_stats(self) -> Dict[str, Any]:
        """Get validation statistics."""
        return {
            **self.stats,
            "success_rate": (
                self.stats["valid_count"] / self.stats["total_validated"]
                if self.stats["total_validated"] > 0
                else 0
            ),
            "review_rate": (
                self.stats["flagged_for_review"] / self.stats["total_validated"]
                if self.stats["total_validated"] > 0
                else 0
            )
        }
    
    def reset_stats(self):
        """Reset statistics counters."""
        self.stats = {
            "total_validated": 0,
            "valid_count": 0,
            "invalid_count": 0,
            "flagged_for_review": 0,
            "errors_by_type": {}
        }

