"""
Phase 1 Enhancement: Post-Estimation Validation

Validates AI-generated cost estimates AFTER estimation to:
- Catch mathematical errors (cost components don't sum)
- Detect unrealistic estimates
- Enforce confidence thresholds
- Flag estimates needing review

Features:
- Cost range sanity checks
- Component math validation (labor + materials + permits = total)
- Extreme cost detection
- Confidence score validation
- Timeline reasonableness checks
- Houston market-specific validation
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class EstimationAction(Enum):
    """Actions to take based on validation results."""
    ACCEPT = "accept"
    REGENERATE = "regenerate_estimate"
    FLAG_FOR_REVIEW = "flag_for_review"
    RECALCULATE = "recalculate"
    REJECT = "reject"


@dataclass
class EstimationValidationResult:
    """Result of estimation validation."""
    valid: bool
    reason: str
    action: EstimationAction
    errors: List[str]
    warnings: List[str]
    corrected_estimate: Optional[Dict[str, Any]] = None


class EstimationValidator:
    """
    Validates AI-generated cost estimates for accuracy and reasonableness.
    
    Checks:
    1. Cost ranges are reasonable (min < max)
    2. Components sum correctly (labor + materials + permits = total)
    3. Extreme cost detection
    4. Confidence scores are meaningful
    5. Timeline makes sense
    6. Houston market reasonableness
    
    Usage:
        validator = EstimationValidator()
        result = validator.validate_estimate(ai_estimate, original_issue)
        
        if result.valid:
            # Save estimate
        elif result.action == EstimationAction.REGENERATE:
            # Retry AI estimation
        elif result.action == EstimationAction.FLAG_FOR_REVIEW:
            # Mark for manual review
    """
    
    # Cost thresholds
    MIN_COST = 0
    MAX_SINGLE_ITEM_COST = 50000  # Flag if single item > $50k
    EXTREME_COST_THRESHOLD = 100000  # Reject if > $100k
    
    # Component validation
    COMPONENT_SUM_TOLERANCE = 50  # $50 tolerance for rounding
    MAX_LABOR_RATIO = 0.9  # Labor shouldn't be >90% unless specified
    MIN_MATERIALS_RATIO = 0.05  # Most repairs need some materials
    
    # Confidence thresholds
    MIN_ACCEPTABLE_CONFIDENCE = 0.3
    REVIEW_CONFIDENCE_THRESHOLD = 0.6
    
    # Timeline thresholds (in days)
    MIN_TIMELINE_DAYS = 0.1  # ~2 hours minimum
    MAX_TIMELINE_DAYS = 365  # Anything over a year is suspicious
    
    # Houston market rates (2025)
    HOUSTON_LABOR_RATES = {
        'hvac': {'min': 85, 'max': 150},
        'plumbing': {'min': 80, 'max': 130},
        'electrical': {'min': 75, 'max': 125},
        'roofing': {'min': 70, 'max': 120},
        'foundation': {'min': 90, 'max': 140},
        'general': {'min': 50, 'max': 100}
    }
    
    def __init__(
        self,
        strict_mode: bool = False,
        auto_correct: bool = True
    ):
        """
        Initialize validator.
        
        Args:
            strict_mode: Apply stricter validation rules
            auto_correct: Attempt to auto-correct minor errors
        """
        self.strict_mode = strict_mode
        self.auto_correct = auto_correct
        
        self.stats = {
            'total_validated': 0,
            'passed': 0,
            'failed': 0,
            'auto_corrected': 0,
            'flagged_for_review': 0,
            'error_types': {}
        }
    
    def validate_estimate(
        self,
        estimate: Dict[str, Any],
        issue: Optional[Dict[str, Any]] = None
    ) -> EstimationValidationResult:
        """
        Validate a single cost estimate.
        
        Args:
            estimate: AI-generated estimate dictionary
            issue: Original issue data (optional, for context)
            
        Returns:
            EstimationValidationResult with validation outcome
        """
        self.stats['total_validated'] += 1
        
        errors = []
        warnings = []
        corrected_estimate = None
        
        # SPECIAL CASE: Simple estimates with top-level low/high (no nested 'cost')
        if 'cost' not in estimate and 'estimated_low' in estimate and 'estimated_high' in estimate:
            low = estimate.get('estimated_low', 0)
            high = estimate.get('estimated_high', 0)
            auto_corrected = False
            # Invalid range
            if isinstance(low, (int, float)) and isinstance(high, (int, float)):
                if low >= high:
                    errors.append(f"estimated_low ({low}) must be less than estimated_high ({high})")
                    if self.auto_correct:
                        estimate['estimated_low'], estimate['estimated_high'] = high, low
                        auto_corrected = True
                        errors.pop()  # treat as corrected
                        warnings.append("Auto-corrected inverted estimated_low/estimated_high")
                # Low of $0 → set to 10% of high or $100
                if low == 0 and high > 0:
                    warnings.append("estimated_low is $0 - unrealistic; auto-adjusted")
                    if self.auto_correct:
                        estimate['estimated_low'] = max(100, int(high * 0.1))
                        auto_corrected = True
                # Excessive variance (>10x) → cap at 5x
                new_low = estimate.get('estimated_low', low)
                new_high = estimate.get('estimated_high', high)
                if new_low > 0 and new_high / new_low > 10:
                    warnings.append(f"Range too wide: {new_high/new_low:.1f}x - capped to 5x")
                    if self.auto_correct:
                        estimate['estimated_high'] = int(new_low * 5)
                        auto_corrected = True
            if auto_corrected:
                corrected_estimate = estimate.copy()
                self.stats['auto_corrected'] += 1
            # Continue with remaining validations using synthesized cost dict
            cost = {
                'total': {
                    'min': estimate.get('estimated_low', 0),
                    'max': estimate.get('estimated_high', 0)
                }
            }
        else:
            # Extract cost components
            cost = estimate.get('cost', {})
            if not cost:
                return self._create_error_result(
                    "Missing cost data",
                    EstimationAction.REGENERATE,
                    ["No cost information provided"]
                )
        
        # Check 1: Cost range validity (min < max)
        range_errors = self._validate_cost_ranges(cost)
        if range_errors:
            errors.extend(range_errors)
            if self.auto_correct:
                cost = self._auto_correct_ranges(cost)
                corrected_estimate = {**estimate, 'cost': cost}
                warnings.append("Auto-corrected inverted min/max ranges")
                self.stats['auto_corrected'] += 1
            else:
                return self._create_error_result(
                    "Invalid cost ranges",
                    EstimationAction.RECALCULATE,
                    errors
                )
        
        # Check 2: Component math validation
        math_errors, math_corrected = self._validate_component_math(cost)
        if math_errors:
            if self.auto_correct and math_corrected:
                corrected_estimate = {**estimate, 'cost': math_corrected}
                warnings.append("Auto-corrected component sum")
                self.stats['auto_corrected'] += 1
            else:
                errors.extend(math_errors)
                return self._create_error_result(
                    "Cost components don't sum correctly",
                    EstimationAction.RECALCULATE,
                    errors
                )
        
        # Check 3: Extreme cost detection
        total_max = cost.get('total', {}).get('max', 0)
        if total_max > self.EXTREME_COST_THRESHOLD:
            return self._create_error_result(
                f"Extreme cost estimate (${total_max:,.0f})",
                EstimationAction.REJECT,
                [f"Cost exceeds ${self.EXTREME_COST_THRESHOLD:,.0f} threshold"]
            )
        elif total_max > self.MAX_SINGLE_ITEM_COST:
            warnings.append(f"High cost estimate (${total_max:,.0f}) - flagged for review")
        
        # Check 4: Zero or negative costs
        zero_cost_warnings = self._check_zero_costs(cost)
        warnings.extend(zero_cost_warnings)
        
        # Check 5: Component ratios
        ratio_warnings = self._validate_component_ratios(cost, issue)
        warnings.extend(ratio_warnings)
        
        # Check 6: Confidence score validation
        confidence_errors, confidence_warnings = self._validate_confidence(estimate)
        errors.extend(confidence_errors)
        warnings.extend(confidence_warnings)
        
        # Check 7: Timeline validation
        timeline_warnings = self._validate_timeline(estimate, cost)
        warnings.extend(timeline_warnings)
        
        # Check 8: Houston market rates (if category known)
        if issue:
            market_warnings = self._validate_houston_market_rates(cost, issue)
            warnings.extend(market_warnings)
        
        # Check 9: Required fields present
        missing_fields = self._check_required_fields(estimate)
        if missing_fields:
            warnings.extend([f"Missing field: {field}" for field in missing_fields])
        
        # Determine final validation status
        if errors:
            self._update_stats('failed', errors)
            return EstimationValidationResult(
                valid=False,
                reason=errors[0],
                action=EstimationAction.FLAG_FOR_REVIEW,
                errors=errors,
                warnings=warnings,
                corrected_estimate=corrected_estimate
            )
        
        # Check if should flag for review despite passing
        confidence = estimate.get('confidence_score', estimate.get('confidence', {}).get('overall', 1.0))
        should_review = (
            confidence < self.REVIEW_CONFIDENCE_THRESHOLD or
            len(warnings) > 3 or
            total_max > self.MAX_SINGLE_ITEM_COST
        )
        
        if should_review:
            self.stats['flagged_for_review'] += 1
        
        # Phase 1 Enhancement: Apply confidence-based range adjustment
        final_estimate = corrected_estimate if corrected_estimate else estimate.copy()
        if confidence < 0.75:
            final_estimate = self.adjust_range_by_confidence(final_estimate, confidence)
            warnings.append(f"Cost ranges adjusted based on confidence score ({confidence:.2f})")
        
        self._update_stats('passed', None)
        
        return EstimationValidationResult(
            valid=True,
            reason="Passed validation" + (" with warnings" if warnings else ""),
            action=EstimationAction.FLAG_FOR_REVIEW if should_review else EstimationAction.ACCEPT,
            errors=[],
            warnings=warnings,
            corrected_estimate=final_estimate
        )
    
    def _validate_cost_ranges(self, cost: Dict[str, Any]) -> List[str]:
        """Check that min < max for all cost components and enforce Phase 1 range ratio limits."""
        errors = []
        
        # Phase 1 Enhancement: Enforce 1.5-3x range ratio
        MAX_RANGE_RATIO = 3.0
        MIN_RANGE_RATIO = 1.5
        
        for component in ['labor', 'materials', 'permits', 'total']:
            if component in cost:
                comp_data = cost[component]
                if isinstance(comp_data, dict):
                    min_val = comp_data.get('min', 0)
                    max_val = comp_data.get('max', 0)
                    
                    if min_val > max_val:
                        errors.append(f"{component.title()}: min (${min_val}) > max (${max_val})")
                    
                    if min_val < 0:
                        errors.append(f"{component.title()}: negative min value (${min_val})")
                    
                    if max_val < 0:
                        errors.append(f"{component.title()}: negative max value (${max_val})")
                    
                    # Phase 1: Check range ratio for non-zero ranges
                    if min_val > 0 and max_val > 0:
                        range_ratio = max_val / min_val
                        
                        if range_ratio > MAX_RANGE_RATIO:
                            errors.append(
                                f"{component.title()}: Range ratio {range_ratio:.2f}x exceeds Phase 1 limit of {MAX_RANGE_RATIO}x "
                                f"(${min_val}-${max_val}). Reduce range or lower confidence score."
                            )
                        elif range_ratio < MIN_RANGE_RATIO and component == 'total':
                            # Only warn for total (too narrow suggests overconfidence)
                            errors.append(
                                f"{component.title()}: Range ratio {range_ratio:.2f}x is too narrow (< {MIN_RANGE_RATIO}x). "
                                f"Consider widening range or justifying high confidence."
                            )
        
        return errors
    
    def _auto_correct_ranges(self, cost: Dict[str, Any]) -> Dict[str, Any]:
        """Automatically correct inverted min/max ranges."""
        corrected = cost.copy()
        
        for component in ['labor', 'materials', 'permits', 'total']:
            if component in corrected and isinstance(corrected[component], dict):
                comp_data = corrected[component]
                min_val = comp_data.get('min', 0)
                max_val = comp_data.get('max', 0)
                
                if min_val > max_val:
                    # Swap them
                    corrected[component] = {
                        'min': max_val,
                        'max': min_val
                    }
        
        return corrected
    
    def _validate_component_math(self, cost: Dict[str, Any]) -> tuple[List[str], Optional[Dict[str, Any]]]:
        """
        Validate that labor + materials + permits = total.
        
        Returns:
            (errors, corrected_cost) - corrected_cost is None if can't correct
        """
        errors = []
        
        # Extract components
        labor = cost.get('labor', {})
        materials = cost.get('materials', {})
        permits = cost.get('permits', {})
        total = cost.get('total', {})
        
        if not total:
            errors.append("Missing total cost")
            return errors, None
        
        # Calculate expected totals
        labor_min = labor.get('min', 0) if isinstance(labor, dict) else 0
        labor_max = labor.get('max', 0) if isinstance(labor, dict) else 0
        materials_min = materials.get('min', 0) if isinstance(materials, dict) else 0
        materials_max = materials.get('max', 0) if isinstance(materials, dict) else 0
        permits_min = permits.get('min', 0) if isinstance(permits, dict) else 0
        permits_max = permits.get('max', 0) if isinstance(permits, dict) else 0
        
        expected_min = labor_min + materials_min + permits_min
        expected_max = labor_max + materials_max + permits_max
        
        actual_min = total.get('min', 0) if isinstance(total, dict) else 0
        actual_max = total.get('max', 0) if isinstance(total, dict) else 0
        
        # Check with tolerance
        if abs(expected_min - actual_min) > self.COMPONENT_SUM_TOLERANCE:
            errors.append(
                f"Total min (${actual_min}) doesn't match sum of components (${expected_min}), "
                f"difference: ${abs(expected_min - actual_min)}"
            )
        
        if abs(expected_max - actual_max) > self.COMPONENT_SUM_TOLERANCE:
            errors.append(
                f"Total max (${actual_max}) doesn't match sum of components (${expected_max}), "
                f"difference: ${abs(expected_max - actual_max)}"
            )
        
        # Auto-correct if possible
        if errors and self.auto_correct:
            corrected_cost = cost.copy()
            corrected_cost['total'] = {
                'min': expected_min,
                'max': expected_max
            }
            return errors, corrected_cost
        
        return errors, None
    
    def _check_zero_costs(self, cost: Dict[str, Any]) -> List[str]:
        """Check for suspicious zero costs."""
        warnings = []
        
        total = cost.get('total', {})
        if isinstance(total, dict):
            if total.get('min', 0) == 0 and total.get('max', 0) == 0:
                warnings.append("Total cost is $0 - likely estimation error")
            elif total.get('min', 0) == 0 and total.get('max', 0) > 0:
                warnings.append("Min total cost is $0 - may be unrealistic")
        
        return warnings
    
    def _validate_component_ratios(
        self,
        cost: Dict[str, Any],
        issue: Optional[Dict[str, Any]]
    ) -> List[str]:
        """Validate ratios between cost components."""
        warnings = []
        
        total = cost.get('total', {})
        labor = cost.get('labor', {})
        materials = cost.get('materials', {})
        
        if not isinstance(total, dict) or not isinstance(labor, dict):
            return warnings
        
        total_max = total.get('max', 0)
        if total_max == 0:
            return warnings
        
        labor_max = labor.get('max', 0) if isinstance(labor, dict) else 0
        materials_max = materials.get('max', 0) if isinstance(materials, dict) else 0
        
        labor_ratio = labor_max / total_max if total_max > 0 else 0
        materials_ratio = materials_max / total_max if total_max > 0 else 0
        
        # Check if labor is too high
        if labor_ratio > self.MAX_LABOR_RATIO:
            warnings.append(
                f"Labor cost is {labor_ratio:.0%} of total - unusually high "
                f"(${labor_max} / ${total_max})"
            )
        
        # Check if materials are suspiciously low for certain repairs
        if materials_ratio < self.MIN_MATERIALS_RATIO and total_max > 500:
            # But allow for inspection-only or purely labor items
            if issue:
                desc = issue.get('description', '').lower()
                if not any(word in desc for word in ['inspect', 'evaluation', 'assess', 'service']):
                    warnings.append(
                        f"Materials cost is only {materials_ratio:.1%} of total - "
                        f"verify if reasonable"
                    )
        
        return warnings
    
    def _validate_confidence(self, estimate: Dict[str, Any]) -> tuple[List[str], List[str]]:
        """Validate confidence scores."""
        errors = []
        warnings = []
        
        # Check for confidence field (may be nested or top-level)
        confidence = estimate.get('confidence_score')
        if confidence is None:
            confidence_obj = estimate.get('confidence', {})
            confidence = confidence_obj.get('overall') if isinstance(confidence_obj, dict) else None
        
        if confidence is None:
            warnings.append("No confidence score provided")
            return errors, warnings
        
        # Validate range
        if not 0 <= confidence <= 1:
            errors.append(f"Confidence score {confidence} out of valid range [0, 1]")
        
        # Check if too low
        if confidence < self.MIN_ACCEPTABLE_CONFIDENCE:
            warnings.append(
                f"Very low confidence ({confidence:.2f}) - estimate may be unreliable"
            )
        elif confidence < self.REVIEW_CONFIDENCE_THRESHOLD:
            warnings.append(
                f"Low confidence ({confidence:.2f}) - recommend manual review"
            )
        
        # Check for suspiciously high confidence with sparse data
        if confidence > 0.9:
            # High confidence should have good justification
            reasoning = estimate.get('confidence_reasoning', '')
            if not reasoning or len(reasoning) < 20:
                warnings.append(
                    "High confidence (>0.9) without detailed reasoning - verify accuracy"
                )
        
        return errors, warnings
    
    def _validate_timeline(self, estimate: Dict[str, Any], cost: Dict[str, Any]) -> List[str]:
        """Validate timeline reasonableness."""
        warnings = []
        
        timeline = estimate.get('timeline', {})
        if not timeline:
            warnings.append("No timeline information provided")
            return warnings
        
        min_days = timeline.get('min_days', 0)
        max_days = timeline.get('max_days', 0)
        
        # Check range validity
        if min_days > max_days:
            warnings.append(f"Timeline min ({min_days}) > max ({max_days})")
        
        # Check if too short
        if min_days < self.MIN_TIMELINE_DAYS:
            warnings.append(f"Unusually short timeline ({min_days} days)")
        
        # Check if too long
        if max_days > self.MAX_TIMELINE_DAYS:
            warnings.append(f"Unusually long timeline ({max_days} days)")
        
        # Check timeline vs cost correlation
        total_max = cost.get('total', {}).get('max', 0)
        if total_max > 10000 and max_days < 1:
            warnings.append(
                f"High cost (${total_max}) but very short timeline ({max_days} days) - verify"
            )
        
        return warnings
    
    def _validate_houston_market_rates(
        self,
        cost: Dict[str, Any],
        issue: Dict[str, Any]
    ) -> List[str]:
        """Validate labor rates against Houston market."""
        warnings = []
        
        # Try to determine category
        category = (
            issue.get('standard_category', '') or
            issue.get('category', '') or
            issue.get('section', '')
        ).lower()
        
        # Map to labor rate category
        labor_category = None
        for key in self.HOUSTON_LABOR_RATES.keys():
            if key in category:
                labor_category = key
                break
        
        if not labor_category:
            labor_category = 'general'
        
        # Get labor cost
        labor = cost.get('labor', {})
        if not isinstance(labor, dict):
            return warnings
        
        labor_min = labor.get('min', 0)
        labor_max = labor.get('max', 0)
        
        # Estimate hours (rough)
        expected_rate = self.HOUSTON_LABOR_RATES[labor_category]
        min_hourly = expected_rate['min']
        max_hourly = expected_rate['max']
        
        # If labor cost is very low, might be underestimated
        if labor_max > 0 and labor_max < min_hourly:
            warnings.append(
                f"Labor cost (${labor_max}) seems low for {labor_category} work in Houston "
                f"(typical rate: ${min_hourly}-${max_hourly}/hr)"
            )
        
        return warnings
    
    def adjust_range_by_confidence(
        self, 
        estimate: Dict[str, Any], 
        confidence: float
    ) -> Dict[str, Any]:
        """
        Adjust cost ranges based on confidence score.
        Phase 1 Enhancement: Widen ranges for low-confidence estimates.
        
        Low confidence = wide range (reflecting uncertainty)
        High confidence = tight range (reflecting certainty)
        
        Args:
            estimate: The estimate dictionary to adjust
            confidence: Confidence score (0.0-1.0)
            
        Returns:
            Adjusted estimate with modified ranges and explanatory note
        """
        adjusted = estimate.copy()
        cost = adjusted.get('cost', {})
        
        if not cost or confidence is None:
            return adjusted
        
        # Determine adjustment strategy based on confidence
        if confidence < 0.6:
            # Low confidence → widen range by 50%
            adjustment_factor = 0.5
            note = "Wide range due to insufficient information. Professional on-site inspection strongly recommended."
        elif confidence < 0.75:
            # Medium confidence → widen by 25%
            adjustment_factor = 0.25
            note = "Moderate uncertainty in estimate. Consider on-site inspection for more accurate quote."
        else:
            # High confidence → no adjustment needed
            return adjusted
        
        # Apply adjustment to each component
        for component in ['labor', 'materials', 'permits', 'total']:
            if component in cost and isinstance(cost[component], dict):
                comp_data = cost[component]
                min_val = comp_data.get('min', 0)
                max_val = comp_data.get('max', 0)
                
                if min_val > 0 or max_val > 0:
                    midpoint = (min_val + max_val) / 2
                    
                    # Widen the range symmetrically around midpoint
                    new_min = max(0, midpoint * (1 - adjustment_factor))
                    new_max = midpoint * (1 + adjustment_factor)
                    
                    # Ensure reasonable range ratio (at least 1.5x, at most 4x)
                    range_ratio = new_max / new_min if new_min > 0 else 0
                    if range_ratio < 1.5:
                        # Make sure we have at least 1.5x spread
                        new_min = midpoint * 0.75
                        new_max = midpoint * 1.25
                    elif range_ratio > 4.0:
                        # Cap at 4x spread for very uncertain estimates
                        new_min = midpoint * 0.5
                        new_max = midpoint * 2.0
                    
                    cost[component] = {
                        'min': round(new_min, 2),
                        'max': round(new_max, 2)
                    }
        
        # Add adjustment note to estimate
        if 'notes' in adjusted:
            if isinstance(adjusted['notes'], list):
                adjusted['notes'].append(note)
            else:
                adjusted['notes'] = [adjusted['notes'], note]
        else:
            adjusted['notes'] = note
        
        # Add metadata about adjustment
        adjusted['confidence_adjustment'] = {
            'original_confidence': confidence,
            'adjustment_factor': adjustment_factor,
            'reason': f"Ranges widened by {int(adjustment_factor*100)}% due to low confidence"
        }
        
        adjusted['cost'] = cost
        return adjusted
    
    def _check_required_fields(self, estimate: Dict[str, Any]) -> List[str]:
        """Check for required fields in estimate."""
        required = ['cost', 'contractor_type', 'urgency']
        missing = []
        
        for field in required:
            if field not in estimate or not estimate[field]:
                missing.append(field)
        
        return missing
    
    def _create_error_result(
        self,
        reason: str,
        action: EstimationAction,
        errors: List[str]
    ) -> EstimationValidationResult:
        """Helper to create error result."""
        self._update_stats('failed', errors)
        return EstimationValidationResult(
            valid=False,
            reason=reason,
            action=action,
            errors=errors,
            warnings=[]
        )
    
    def _update_stats(self, result: str, errors: Optional[List[str]]):
        """Update validation statistics."""
        if result in ['passed', 'failed']:
            self.stats[result] += 1
        
        if errors:
            for error in errors:
                # Extract error type from error message
                error_type = error.split(':')[0] if ':' in error else 'general'
                self.stats['error_types'][error_type] = self.stats['error_types'].get(error_type, 0) + 1
    
    def validate_batch(
        self,
        estimates: List[Dict[str, Any]],
        issues: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Validate a batch of estimates.
        
        Args:
            estimates: List of AI-generated estimates
            issues: Optional list of original issues (same order)
            
        Returns:
            Dict with validation results and statistics
        """
        results = []
        valid_estimates = []
        flagged_estimates = []
        failed_estimates = []
        
        for idx, estimate in enumerate(estimates):
            issue = issues[idx] if issues and idx < len(issues) else None
            result = self.validate_estimate(estimate, issue)
            
            results.append({
                'index': idx,
                'estimate_id': estimate.get('id', f'estimate_{idx}'),
                'result': result
            })
            
            # Use corrected estimate if available
            final_estimate = result.corrected_estimate if result.corrected_estimate else estimate
            
            # Add validation metadata
            final_estimate['validation'] = {
                'valid': result.valid,
                'action': result.action.value,
                'errors': result.errors,
                'warnings': result.warnings
            }
            
            if result.valid:
                if result.action == EstimationAction.FLAG_FOR_REVIEW:
                    flagged_estimates.append(final_estimate)
                valid_estimates.append(final_estimate)
            else:
                failed_estimates.append({
                    'estimate': final_estimate,
                    'reason': result.reason,
                    'errors': result.errors
                })
        
        summary = self.get_stats_summary()
        
        return {
            'valid_estimates': valid_estimates,
            'flagged_estimates': flagged_estimates,
            'failed_estimates': failed_estimates,
            'results': results,
            'summary': summary
        }
    
    def get_stats_summary(self) -> Dict[str, Any]:
        """Get validation statistics summary."""
        total = self.stats['total_validated']
        
        return {
            'total_validated': total,
            'passed': self.stats['passed'],
            'failed': self.stats['failed'],
            'auto_corrected': self.stats['auto_corrected'],
            'flagged_for_review': self.stats['flagged_for_review'],
            'pass_rate': (self.stats['passed'] / total * 100) if total > 0 else 0,
            'error_types': self.stats['error_types']
        }
    
    def reset_stats(self):
        """Reset validation statistics."""
        self.stats = {
            'total_validated': 0,
            'passed': 0,
            'failed': 0,
            'auto_corrected': 0,
            'flagged_for_review': 0,
            'error_types': {}
        }

