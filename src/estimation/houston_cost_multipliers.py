"""
Phase 2 Enhancement: Houston Market Cost Multipliers

Applies Houston-specific cost adjustments to base estimates:
- Labor rate multipliers (15% above national average)
- Material cost adjustments (10% for HVAC due to high demand)
- Permit costs (Houston requires permits for most work)
- Climate-specific factors (foundation, HVAC, humidity control)

This ensures estimates reflect the actual Houston market conditions.
"""

from typing import Dict, Optional
from dataclasses import dataclass
from enum import Enum


class PermitType(Enum):
    """Houston permit types and costs."""
    ELECTRICAL = "electrical"
    PLUMBING = "plumbing"
    MECHANICAL = "mechanical"
    STRUCTURAL = "structural"
    ROOFING = "roofing"
    NONE = "none"


@dataclass
class HoustonAdjustment:
    """Result of Houston market adjustment."""
    original_estimate: Dict
    adjusted_estimate: Dict
    labor_multiplier: float
    material_multiplier: float
    permit_cost: float
    climate_adjustment: float
    total_adjustment: float
    reasoning: str


class HoustonCostAdjuster:
    """
    Applies Houston-specific cost multipliers to base estimates.
    
    Houston Market Factors (2025):
    - Labor: 15% above national average
    - HVAC demand: 10% material premium
    - Foundation issues: Clay soil requires specialized work
    - Permits: Required for most structural/utility work
    - Climate: High humidity, hurricane preparedness
    
    Usage:
        adjuster = HoustonCostAdjuster()
        result = adjuster.adjust_estimate(base_estimate, issue)
        final_estimate = result.adjusted_estimate
    """
    
    # Labor rate multipliers by trade (Houston premium over national average)
    LABOR_MULTIPLIERS = {
        'hvac': 1.15,  # High demand, 8-9 months/year runtime
        'plumbing': 1.12,  # Cast iron replacement common
        'electrical': 1.10,  # Panel upgrades frequent
        'roofing': 1.15,  # Hurricane-rated materials, harsh sun
        'foundation': 1.25,  # Clay soil specialists required
        'structural': 1.20,  # Hurricane/foundation expertise
        'general': 1.08,  # General contractors
        'default': 1.10  # Default 10% premium
    }
    
    # Material cost multipliers by category
    MATERIAL_MULTIPLIERS = {
        'hvac': 1.10,  # High demand, specialized equipment
        'roofing': 1.08,  # Hurricane-rated shingles
        'foundation': 1.15,  # Specialized piers, drainage
        'insulation': 1.05,  # R-value requirements for climate
        'humidity_control': 1.12,  # Dehumidifiers, ventilation
        'default': 1.00  # No adjustment
    }
    
    # Houston permit costs (2025 rates)
    PERMIT_COSTS = {
        PermitType.ELECTRICAL: {'min': 150, 'max': 300},
        PermitType.PLUMBING: {'min': 125, 'max': 250},
        PermitType.MECHANICAL: {'min': 175, 'max': 350},  # HVAC
        PermitType.STRUCTURAL: {'min': 300, 'max': 600},
        PermitType.ROOFING: {'min': 200, 'max': 400},
        PermitType.NONE: {'min': 0, 'max': 0}
    }
    
    # Climate-specific adjustments
    CLIMATE_ADJUSTMENTS = {
        'foundation': {
            'drainage_factor': 1.10,  # Clay soil requires better drainage
            'pier_premium': 1.15,  # Specialized foundation piers
            'soil_testing': 500  # Soil analysis often needed
        },
        'hvac': {
            'efficiency_premium': 1.08,  # Higher SEER needed for climate
            'humidity_control': 300,  # Additional dehumidification
            'runtime_factor': 1.05  # Longer operating hours
        },
        'roofing': {
            'hurricane_rating': 1.10,  # Hurricane-rated materials
            'uv_resistance': 1.05,  # UV-resistant materials
            'ventilation': 200  # Additional attic ventilation
        },
        'exterior': {
            'moisture_resistance': 1.08,  # High humidity materials
            'uv_protection': 1.05  # UV-resistant finishes
        }
    }
    
    # Keywords for permit requirement detection
    PERMIT_KEYWORDS = {
        PermitType.ELECTRICAL: [
            'electrical', 'panel', 'circuit', 'wiring', 'breaker',
            'outlet', 'switch', 'lighting', 'electric'
        ],
        PermitType.PLUMBING: [
            'plumbing', 'pipe', 'water line', 'drain', 'sewer',
            'water heater', 'fixture', 'faucet', 'toilet'
        ],
        PermitType.MECHANICAL: [
            'hvac', 'air conditioning', 'furnace', 'heating', 'cooling',
            'ductwork', 'ventilation', 'ac unit'
        ],
        PermitType.STRUCTURAL: [
            'foundation', 'structural', 'beam', 'joist', 'load bearing',
            'pier', 'support', 'framing'
        ],
        PermitType.ROOFING: [
            'roof', 'roofing', 'shingles', 'decking', 'flashing'
        ]
    }
    
    def __init__(self):
        """Initialize Houston cost adjuster."""
        self.stats = {
            'total_adjustments': 0,
            'labor_adjustments': 0,
            'material_adjustments': 0,
            'permit_additions': 0,
            'climate_adjustments': 0
        }
    
    def adjust_estimate(
        self,
        base_estimate: Dict,
        issue: Dict,
        property_metadata: Optional[Dict] = None
    ) -> HoustonAdjustment:
        """
        Apply Houston market adjustments to base estimate.
        
        Args:
            base_estimate: Base cost estimate (before Houston adjustments)
            issue: Issue dictionary with category, description, etc.
            property_metadata: Optional property context
            
        Returns:
            HoustonAdjustment with original, adjusted estimates and reasoning
        """
        self.stats['total_adjustments'] += 1
        
        # Extract issue details
        category = issue.get('category', '').lower()
        title = issue.get('title', '').lower()
        description = issue.get('description', '').lower()
        text = f"{title} {description}"
        
        # Determine trade type
        trade_type = self._determine_trade_type(text, category)
        
        # Get base costs
        cost = base_estimate.get('cost', {})
        labor = cost.get('labor', {'min': 0, 'max': 0})
        materials = cost.get('materials', {'min': 0, 'max': 0})
        permits = cost.get('permits', {'min': 0, 'max': 0})
        
        # Apply labor multiplier
        labor_multiplier = self.LABOR_MULTIPLIERS.get(trade_type, self.LABOR_MULTIPLIERS['default'])
        adjusted_labor = {
            'min': round(labor['min'] * labor_multiplier, 2),
            'max': round(labor['max'] * labor_multiplier, 2)
        }
        
        if labor['min'] > 0 or labor['max'] > 0:
            self.stats['labor_adjustments'] += 1
        
        # Apply material multiplier
        material_multiplier = self.MATERIAL_MULTIPLIERS.get(trade_type, self.MATERIAL_MULTIPLIERS['default'])
        adjusted_materials = {
            'min': round(materials['min'] * material_multiplier, 2),
            'max': round(materials['max'] * material_multiplier, 2)
        }
        
        if material_multiplier > 1.0 and (materials['min'] > 0 or materials['max'] > 0):
            self.stats['material_adjustments'] += 1
        
        # Determine permit requirements
        permit_type = self._determine_permit_type(text)
        permit_cost = self.PERMIT_COSTS[permit_type]
        
        # Add permits if not already included
        if permit_type != PermitType.NONE and permits['max'] < permit_cost['min']:
            adjusted_permits = permit_cost.copy()
            self.stats['permit_additions'] += 1
        else:
            adjusted_permits = permits.copy()
        
        # Apply climate-specific adjustments
        climate_adjustment_amount = 0
        climate_reasoning = []
        
        for climate_category, adjustments in self.CLIMATE_ADJUSTMENTS.items():
            if climate_category in text or climate_category in category:
                self.stats['climate_adjustments'] += 1
                
                # Apply relevant climate factors
                if 'drainage_factor' in adjustments:
                    drainage_adj = (adjusted_materials['max'] * (adjustments['drainage_factor'] - 1))
                    adjusted_materials['max'] += round(drainage_adj, 2)
                    climate_reasoning.append("Clay soil drainage requirements")
                
                if 'hurricane_rating' in adjustments:
                    hurricane_adj = (adjusted_materials['max'] * (adjustments['hurricane_rating'] - 1))
                    adjusted_materials['max'] += round(hurricane_adj, 2)
                    climate_reasoning.append("Hurricane-rated materials required")
                
                if 'efficiency_premium' in adjustments:
                    efficiency_adj = (adjusted_materials['max'] * (adjustments['efficiency_premium'] - 1))
                    adjusted_materials['max'] += round(efficiency_adj, 2)
                    climate_reasoning.append("Higher SEER rating for Houston climate")
                
                # Add fixed costs if applicable
                for key in ['soil_testing', 'humidity_control', 'ventilation']:
                    if key in adjustments:
                        climate_adjustment_amount += adjustments[key]
                        climate_reasoning.append(f"{key.replace('_', ' ').title()}: ${adjustments[key]}")
        
        # Calculate totals
        adjusted_total = {
            'min': adjusted_labor['min'] + adjusted_materials['min'] + adjusted_permits['min'] + climate_adjustment_amount,
            'max': adjusted_labor['max'] + adjusted_materials['max'] + adjusted_permits['max'] + climate_adjustment_amount
        }
        
        # Round to nearest dollar
        adjusted_total['min'] = round(adjusted_total['min'], 0)
        adjusted_total['max'] = round(adjusted_total['max'], 0)
        
        # Build adjusted estimate
        adjusted_estimate = base_estimate.copy()
        adjusted_estimate['cost'] = {
            'labor': adjusted_labor,
            'materials': adjusted_materials,
            'permits': adjusted_permits,
            'total': adjusted_total
        }
        
        # Calculate total adjustment
        original_total = cost.get('total', {}).get('max', 0)
        total_adjustment = adjusted_total['max'] - original_total if original_total > 0 else 0
        adjustment_pct = (total_adjustment / original_total * 100) if original_total > 0 else 0
        
        # Build reasoning
        reasoning_parts = [
            f"Houston market adjustment: +{adjustment_pct:.1f}%",
            f"Labor ({trade_type}): {(labor_multiplier - 1) * 100:.0f}% premium"
        ]
        
        if material_multiplier > 1.0:
            reasoning_parts.append(f"Materials: {(material_multiplier - 1) * 100:.0f}% premium")
        
        if permit_type != PermitType.NONE:
            reasoning_parts.append(f"Permit ({permit_type.value}): ${adjusted_permits['min']}-${adjusted_permits['max']}")
        
        if climate_reasoning:
            reasoning_parts.extend(climate_reasoning)
        
        reasoning = "; ".join(reasoning_parts)
        
        # Add Houston adjustment metadata
        adjusted_estimate['houston_adjustment'] = {
            'labor_multiplier': labor_multiplier,
            'material_multiplier': material_multiplier,
            'permit_type': permit_type.value,
            'permit_cost': adjusted_permits,
            'climate_adjustments': climate_reasoning,
            'total_adjustment': round(total_adjustment, 2),
            'adjustment_percentage': round(adjustment_pct, 1)
        }
        
        return HoustonAdjustment(
            original_estimate=base_estimate,
            adjusted_estimate=adjusted_estimate,
            labor_multiplier=labor_multiplier,
            material_multiplier=material_multiplier,
            permit_cost=adjusted_permits['max'],
            climate_adjustment=climate_adjustment_amount,
            total_adjustment=total_adjustment,
            reasoning=reasoning
        )
    
    def _determine_trade_type(self, text: str, category: str) -> str:
        """Determine the trade type for labor multiplier."""
        trade_keywords = {
            'hvac': ['hvac', 'air conditioning', 'heating', 'cooling', 'furnace', 'ac'],
            'plumbing': ['plumb', 'pipe', 'water', 'drain', 'sewer', 'faucet', 'toilet'],
            'electrical': ['electric', 'wiring', 'panel', 'circuit', 'outlet', 'switch'],
            'roofing': ['roof', 'shingle', 'flashing', 'gutter'],
            'foundation': ['foundation', 'pier', 'slab', 'crawlspace'],
            'structural': ['structural', 'beam', 'joist', 'support', 'framing']
        }
        
        text_lower = text.lower()
        category_lower = category.lower()
        
        for trade, keywords in trade_keywords.items():
            if any(keyword in text_lower or keyword in category_lower for keyword in keywords):
                return trade
        
        return 'general'
    
    def _determine_permit_type(self, text: str) -> PermitType:
        """Determine if permit is required and what type."""
        text_lower = text.lower()
        
        # Check each permit type
        for permit_type, keywords in self.PERMIT_KEYWORDS.items():
            if any(keyword in text_lower for keyword in keywords):
                # Check if it's a minor repair that doesn't need permit
                no_permit_phrases = [
                    'replace filter', 'change filter', 'battery', 
                    'light bulb', 'outlet cover', 'switch plate',
                    'minor', 'small repair', 'touch up'
                ]
                
                if not any(phrase in text_lower for phrase in no_permit_phrases):
                    return permit_type
        
        return PermitType.NONE
    
    def get_stats(self) -> Dict:
        """Get adjustment statistics."""
        return self.stats.copy()
    
    def reset_stats(self):
        """Reset statistics."""
        self.stats = {
            'total_adjustments': 0,
            'labor_adjustments': 0,
            'material_adjustments': 0,
            'permit_additions': 0,
            'climate_adjustments': 0
        }

