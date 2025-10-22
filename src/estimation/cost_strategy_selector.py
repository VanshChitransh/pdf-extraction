"""
Phase 2 Enhancement: Cost Strategy Selector

Determines the optimal estimation strategy for each repair issue:
- Lookup Table: Simple, standardized repairs with known costs
- Formula-Based: Standard repairs with calculable costs
- Hybrid: Moderate complexity requiring formula + AI verification
- LLM Reasoning: Complex/uncertain repairs requiring expert analysis

This prevents using expensive AI calls for simple repairs like "replace outlet cover"
and ensures appropriate estimation methods for each complexity level.
"""

from typing import Dict, List, Tuple, Optional
from enum import Enum
from dataclasses import dataclass
import re


class EstimationStrategy(Enum):
    """Estimation strategy types."""
    LOOKUP_TABLE = "lookup_table"  # Simple repairs with fixed costs
    FORMULA_BASED = "formula_based"  # Calculable repairs (e.g., material cost * qty)
    HYBRID = "hybrid"  # Formula + AI verification
    LLM_REASONING = "llm_reasoning"  # Complex repairs requiring AI


@dataclass
class StrategyResult:
    """Result of strategy selection."""
    strategy: EstimationStrategy
    confidence: float  # 0.0-1.0
    reasoning: str
    cost_estimate: Optional[Dict] = None  # For lookup/formula strategies


class CostStrategySelector:
    """
    Selects optimal estimation strategy based on repair complexity and type.
    
    Phase 2 Strategy Hierarchy:
    1. Lookup Table (fastest, most accurate for simple items)
    2. Formula-Based (fast, accurate for standard repairs)
    3. Hybrid (formula + AI verification for moderate complexity)
    4. LLM Reasoning (slowest, for complex/uncertain repairs)
    
    Usage:
        selector = CostStrategySelector()
        result = selector.select_strategy(issue)
        
        if result.strategy == EstimationStrategy.LOOKUP_TABLE:
            # Use pre-defined cost
            estimate = result.cost_estimate
        elif result.strategy == EstimationStrategy.LLM_REASONING:
            # Call AI for complex estimation
            estimate = call_ai(issue)
    """
    
    # =========================================================================
    # LOOKUP TABLES - Houston Market 2025
    # =========================================================================
    
    # Simple repairs with near-fixed costs
    SIMPLE_REPAIRS = {
        # Electrical
        'outlet cover': {'labor': (15, 25), 'materials': (5, 10), 'permits': 0, 'hours': 0.25},
        'light switch': {'labor': (40, 80), 'materials': (10, 25), 'permits': 0, 'hours': 0.5},
        'light bulb': {'labor': (0, 20), 'materials': (5, 15), 'permits': 0, 'hours': 0.1},
        'smoke detector battery': {'labor': (0, 20), 'materials': (10, 25), 'permits': 0, 'hours': 0.1},
        'gfci outlet': {'labor': (80, 150), 'materials': (30, 60), 'permits': 0, 'hours': 1.0},
        
        # HVAC
        'furnace filter': {'labor': (20, 40), 'materials': (20, 50), 'permits': 0, 'hours': 0.25},
        'thermostat battery': {'labor': (0, 20), 'materials': (5, 15), 'permits': 0, 'hours': 0.1},
        'air filter': {'labor': (20, 40), 'materials': (15, 40), 'permits': 0, 'hours': 0.25},
        
        # Plumbing
        'faucet aerator': {'labor': (30, 60), 'materials': (10, 25), 'permits': 0, 'hours': 0.5},
        'toilet flapper': {'labor': (80, 120), 'materials': (15, 30), 'permits': 0, 'hours': 1.0},
        'drain stopper': {'labor': (60, 100), 'materials': (20, 40), 'permits': 0, 'hours': 0.75},
        
        # General
        'caulking': {'labor': (100, 200), 'materials': (20, 50), 'permits': 0, 'hours': 1.5},
        'weather stripping': {'labor': (80, 150), 'materials': (30, 60), 'permits': 0, 'hours': 1.0},
        'door sweep': {'labor': (40, 80), 'materials': (15, 35), 'permits': 0, 'hours': 0.5},
    }
    
    # Category-based formulas (for standard repairs)
    FORMULA_CATEGORIES = {
        'painting': {
            'labor_per_sqft': (1.5, 3.0),  # $/sq ft
            'material_per_sqft': (0.5, 1.0),
            'permits': 0,
            'min_charge': 150
        },
        'drywall_repair': {
            'labor_per_sqft': (2.0, 4.0),
            'material_per_sqft': (0.75, 1.5),
            'permits': 0,
            'min_charge': 100
        },
        'flooring': {
            'labor_per_sqft': (3.0, 6.0),
            'material_per_sqft': (2.0, 8.0),
            'permits': 0,
            'min_charge': 300
        },
        'fence_repair': {
            'labor_per_linear_ft': (15, 30),
            'material_per_linear_ft': (10, 25),
            'permits': 0,
            'min_charge': 200
        }
    }
    
    # Complex repairs that require AI analysis
    COMPLEX_CATEGORIES = [
        'foundation',
        'structural',
        'roof_replacement',
        'hvac_replacement',
        'electrical_panel',
        'plumbing_repipe',
        'mold_remediation',
        'water_damage'
    ]
    
    # Keywords for simple repairs
    SIMPLE_KEYWORDS = [
        'replace outlet cover', 'outlet cover', 'switch plate',
        'light bulb', 'bulb replacement',
        'furnace filter', 'air filter', 'filter replacement',
        'smoke detector battery', 'battery replacement',
        'thermostat battery',
        'faucet aerator',
        'toilet flapper',
        'drain stopper',
        'door sweep',
        'weather stripping'
    ]
    
    # Keywords for complex repairs
    COMPLEX_KEYWORDS = [
        'foundation', 'structural', 'pier', 'underpinning',
        'mold', 'asbestos', 'lead paint',
        'roof replacement', 'reroof',
        'hvac replacement', 'new system',
        'electrical panel', 'panel upgrade',
        'repipe', 'repiping',
        'water damage', 'flood damage'
    ]
    
    def __init__(self):
        """Initialize the cost strategy selector."""
        self.stats = {
            'lookup_table': 0,
            'formula_based': 0,
            'hybrid': 0,
            'llm_reasoning': 0,
            'total': 0
        }
    
    def select_strategy(
        self,
        issue: Dict,
        property_metadata: Optional[Dict] = None
    ) -> StrategyResult:
        """
        Select optimal estimation strategy for an issue.
        
        Args:
            issue: Issue dictionary with title, description, etc.
            property_metadata: Optional property context
            
        Returns:
            StrategyResult with strategy, confidence, and optional cost estimate
        """
        self.stats['total'] += 1
        
        title = issue.get('title', '').lower()
        description = issue.get('description', '').lower()
        category = issue.get('category', '').lower()
        severity = issue.get('severity', '').lower()
        
        text = f"{title} {description}"
        
        # Strategy 1: Check for simple lookup table match
        lookup_result = self._check_lookup_table(text)
        if lookup_result:
            self.stats['lookup_table'] += 1
            return lookup_result
        
        # Strategy 2: Check if it's a complex repair requiring AI
        if self._is_complex_repair(text, category, severity):
            self.stats['llm_reasoning'] += 1
            return StrategyResult(
                strategy=EstimationStrategy.LLM_REASONING,
                confidence=0.7,
                reasoning="Complex repair requiring expert AI analysis"
            )
        
        # Strategy 3: Check for formula-based categories
        formula_result = self._check_formula_based(text, description, property_metadata)
        if formula_result:
            self.stats['formula_based'] += 1
            return formula_result
        
        # Strategy 4: Check if hybrid approach is appropriate
        if self._is_hybrid_candidate(text, category):
            self.stats['hybrid'] += 1
            return StrategyResult(
                strategy=EstimationStrategy.HYBRID,
                confidence=0.75,
                reasoning="Standard repair with calculable base cost, AI verification recommended"
            )
        
        # Default: Use LLM reasoning
        self.stats['llm_reasoning'] += 1
        return StrategyResult(
            strategy=EstimationStrategy.LLM_REASONING,
            confidence=0.6,
            reasoning="Default to AI analysis - unclear repair type or complexity"
        )
    
    def _check_lookup_table(self, text: str) -> Optional[StrategyResult]:
        """Check if repair matches simple lookup table."""
        # Normalize text
        text_normalized = ' '.join(text.split())
        
        # Check each simple repair
        for repair_name, cost_data in self.SIMPLE_REPAIRS.items():
            # Check for exact or close match
            if repair_name in text_normalized:
                # Also check it's not part of a more complex issue
                complex_indicators = ['not working', 'damaged', 'broken', 'multiple', 'several', 'all']
                if not any(indicator in text_normalized for indicator in complex_indicators):
                    # Simple match - use lookup table
                    labor_min, labor_max = cost_data['labor']
                    mat_min, mat_max = cost_data['materials']
                    permits = cost_data['permits']
                    
                    estimate = {
                        'cost': {
                            'labor': {'min': labor_min, 'max': labor_max},
                            'materials': {'min': mat_min, 'max': mat_max},
                            'permits': {'min': permits, 'max': permits},
                            'total': {
                                'min': labor_min + mat_min + permits,
                                'max': labor_max + mat_max + permits
                            }
                        },
                        'estimated_hours': cost_data['hours'],
                        'source': 'lookup_table',
                        'matched_item': repair_name
                    }
                    
                    return StrategyResult(
                        strategy=EstimationStrategy.LOOKUP_TABLE,
                        confidence=0.95,
                        reasoning=f"Standard repair: {repair_name} - using lookup table",
                        cost_estimate=estimate
                    )
        
        return None
    
    def _is_complex_repair(self, text: str, category: str, severity: str) -> bool:
        """Determine if repair is complex and requires AI analysis."""
        # Check for complex keywords
        if any(keyword in text for keyword in self.COMPLEX_KEYWORDS):
            return True
        
        # Check category
        if any(cat in category for cat in self.COMPLEX_CATEGORIES):
            return True
        
        # High severity usually means complexity
        if severity in ['critical', 'high']:
            # But not for simple items
            if not any(keyword in text for keyword in self.SIMPLE_KEYWORDS):
                return True
        
        # Check for uncertainty indicators
        uncertainty_phrases = [
            'possible', 'potential', 'may need', 'could require',
            'extent unknown', 'further inspection', 'evaluation required'
        ]
        if any(phrase in text for phrase in uncertainty_phrases):
            return True
        
        return False
    
    def _check_formula_based(
        self,
        text: str,
        description: str,
        property_metadata: Optional[Dict]
    ) -> Optional[StrategyResult]:
        """Check if repair can be estimated using formula."""
        # Extract measurements if present
        measurements = self._extract_measurements(description)
        
        if not measurements:
            return None  # Can't use formula without measurements
        
        # Check for formula-applicable categories
        for category_name, formula in self.FORMULA_CATEGORIES.items():
            if category_name.replace('_', ' ') in text:
                # Have measurements and category match - use formula
                estimate = self._calculate_formula_estimate(
                    category_name,
                    formula,
                    measurements
                )
                
                if estimate:
                    return StrategyResult(
                        strategy=EstimationStrategy.FORMULA_BASED,
                        confidence=0.85,
                        reasoning=f"Standard {category_name} with measurements - using formula",
                        cost_estimate=estimate
                    )
        
        return None
    
    def _extract_measurements(self, description: str) -> Optional[Dict]:
        """Extract measurements from description."""
        measurements = {}
        
        # Square feet
        sqft_match = re.search(r'(\d+)\s*(?:square\s*feet|sq\.?\s*ft\.?|sf)', description, re.IGNORECASE)
        if sqft_match:
            measurements['square_feet'] = int(sqft_match.group(1))
        
        # Linear feet
        linear_match = re.search(r'(\d+)\s*(?:linear\s*feet|lf|feet|ft)', description, re.IGNORECASE)
        if linear_match and 'square_feet' not in measurements:  # Avoid confusion with sq ft
            measurements['linear_feet'] = int(linear_match.group(1))
        
        # Count/quantity
        count_match = re.search(r'(\d+)\s*(?:units?|items?|pieces?|locations?)', description, re.IGNORECASE)
        if count_match:
            measurements['quantity'] = int(count_match.group(1))
        
        return measurements if measurements else None
    
    def _calculate_formula_estimate(
        self,
        category: str,
        formula: Dict,
        measurements: Dict
    ) -> Optional[Dict]:
        """Calculate cost estimate using formula."""
        labor_min = 0
        labor_max = 0
        mat_min = 0
        mat_max = 0
        
        # Calculate based on available measurements
        if 'square_feet' in measurements:
            sqft = measurements['square_feet']
            if 'labor_per_sqft' in formula:
                labor_rate_min, labor_rate_max = formula['labor_per_sqft']
                labor_min = sqft * labor_rate_min
                labor_max = sqft * labor_rate_max
            if 'material_per_sqft' in formula:
                mat_rate_min, mat_rate_max = formula['material_per_sqft']
                mat_min = sqft * mat_rate_min
                mat_max = sqft * mat_rate_max
        
        elif 'linear_feet' in measurements:
            linear_ft = measurements['linear_feet']
            if 'labor_per_linear_ft' in formula:
                labor_rate_min, labor_rate_max = formula['labor_per_linear_ft']
                labor_min = linear_ft * labor_rate_min
                labor_max = linear_ft * labor_rate_max
            if 'material_per_linear_ft' in formula:
                mat_rate_min, mat_rate_max = formula['material_per_linear_ft']
                mat_min = linear_ft * mat_rate_min
                mat_max = linear_ft * mat_rate_max
        
        # Apply minimum charge
        min_charge = formula.get('min_charge', 0)
        total_min = max(labor_min + mat_min, min_charge)
        total_max = labor_max + mat_max
        
        # Ensure reasonable range
        if total_max < total_min:
            total_max = total_min * 1.5
        
        permits = formula.get('permits', 0)
        
        return {
            'cost': {
                'labor': {'min': round(labor_min, 2), 'max': round(labor_max, 2)},
                'materials': {'min': round(mat_min, 2), 'max': round(mat_max, 2)},
                'permits': {'min': permits, 'max': permits},
                'total': {
                    'min': round(total_min + permits, 2),
                    'max': round(total_max + permits, 2)
                }
            },
            'source': 'formula',
            'category': category,
            'measurements': measurements
        }
    
    def _is_hybrid_candidate(self, text: str, category: str) -> bool:
        """Check if repair is good candidate for hybrid estimation."""
        # Standard repairs that benefit from formula + AI verification
        hybrid_indicators = [
            'repair', 'replace', 'install',
            'service', 'maintain', 'adjust'
        ]
        
        # But not too simple (lookup table) or too complex (AI only)
        if any(keyword in text for keyword in self.SIMPLE_KEYWORDS):
            return False
        
        if any(keyword in text for keyword in self.COMPLEX_KEYWORDS):
            return False
        
        # Standard repairs benefit from hybrid
        if any(indicator in text for indicator in hybrid_indicators):
            return True
        
        return False
    
    def get_stats(self) -> Dict:
        """Get strategy selection statistics."""
        if self.stats['total'] == 0:
            return self.stats
        
        return {
            'total': self.stats['total'],
            'lookup_table': self.stats['lookup_table'],
            'formula_based': self.stats['formula_based'],
            'hybrid': self.stats['hybrid'],
            'llm_reasoning': self.stats['llm_reasoning'],
            'lookup_table_pct': (self.stats['lookup_table'] / self.stats['total']) * 100,
            'formula_based_pct': (self.stats['formula_based'] / self.stats['total']) * 100,
            'hybrid_pct': (self.stats['hybrid'] / self.stats['total']) * 100,
            'llm_reasoning_pct': (self.stats['llm_reasoning'] / self.stats['total']) * 100,
        }
    
    def reset_stats(self):
        """Reset statistics."""
        self.stats = {
            'lookup_table': 0,
            'formula_based': 0,
            'hybrid': 0,
            'llm_reasoning': 0,
            'total': 0
        }

