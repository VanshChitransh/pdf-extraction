"""
Phase 3.3: Assign Cost Estimation Strategy
Routes each issue to the appropriate cost prediction method.
"""

from typing import Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)


class CostStrategyAssigner:
    """Assigns cost estimation strategy to each issue."""
    
    # Standard items that can use lookup tables
    STANDARD_REPLACEMENTS = {
        # HVAC
        'hvac_furnace_replacement': {'avg_cost': 3500, 'range': (2500, 5000)},
        'hvac_ac_replacement': {'avg_cost': 4000, 'range': (3000, 6000)},
        'hvac_thermostat_replacement': {'avg_cost': 250, 'range': (150, 400)},
        
        # Plumbing
        'plumbing_water_heater_replacement': {'avg_cost': 1200, 'range': (800, 2000)},
        'plumbing_toilet_replacement': {'avg_cost': 350, 'range': (250, 500)},
        'plumbing_faucet_replacement': {'avg_cost': 300, 'range': (200, 450)},
        
        # Electrical
        'electrical_outlet_replacement': {'avg_cost': 150, 'range': (100, 250)},
        'electrical_switch_replacement': {'avg_cost': 120, 'range': (80, 200)},
        'electrical_gfci_installation': {'avg_cost': 200, 'range': (150, 300)},
        'electrical_panel_upgrade': {'avg_cost': 2000, 'range': (1500, 3500)},
        
        # Roofing
        'roofing_shingle_replacement': {'avg_cost': 8000, 'range': (5000, 12000)},
        'roofing_gutter_replacement': {'avg_cost': 1500, 'range': (1000, 2500)},
        
        # Windows/Doors
        'window_replacement': {'avg_cost': 650, 'range': (400, 1000)},
        'door_replacement': {'avg_cost': 800, 'range': (500, 1500)},
    }
    
    # Thresholds for strategy assignment
    STRATEGY_RULES = {
        'lookup_table': {
            'description': 'Standard items with known costs',
            'criteria': {
                'work_type': ['replacement'],
                'complexity': ['simple', 'moderate'],
                'standard_items': True
            }
        },
        'ml_model': {
            'description': 'Issues with structured data for ML prediction',
            'criteria': {
                'has_measurements': True,
                'has_category': True,
                'complexity': ['simple', 'moderate']
            }
        },
        'llm_reasoning': {
            'description': 'Complex issues requiring contextual understanding',
            'criteria': {
                'complexity': ['complex'],
                'or_conditions': [
                    {'description_length': '>200'},
                    {'requires_specialist': True},
                    {'multiple_components': True}
                ]
            }
        }
    }
    
    def assign_strategy(self, issue: Dict) -> Tuple[str, float, Dict]:
        """
        Assign cost estimation strategy to an issue.
        
        Args:
            issue: Issue dictionary
            
        Returns:
            Tuple of (strategy, confidence, reasoning)
        """
        # Extract relevant features
        work_type = issue.get('classification', {}).get('work_type', '')
        complexity = issue.get('classification', {}).get('complexity', '')
        category = issue.get('standard_category', '')
        trade = issue.get('classification', {}).get('trade', '')
        description = issue.get('description', '')
        description_length = len(description) if description else 0
        
        has_measurements = bool(issue.get('extracted_attributes', {}).get('measurements'))
        requires_specialist = issue.get('requires_specialized_labor', False)
        
        reasoning = {}
        
        # Check for standard replacement items (lookup table)
        if work_type == 'replacement' and complexity in ['simple', 'moderate']:
            # Try to match to standard items
            lookup_key = self._match_standard_item(trade, category, description)
            if lookup_key:
                reasoning['matched_standard_item'] = lookup_key
                reasoning['cost_data'] = self.STANDARD_REPLACEMENTS[lookup_key]
                return 'lookup_table', 0.9, reasoning
        
        # Check for complex issues (LLM reasoning)
        if complexity == 'complex':
            reasoning['reason'] = 'High complexity requires contextual reasoning'
            return 'llm_reasoning', 0.85, reasoning
        
        if description_length > 200:
            reasoning['reason'] = 'Long description requires detailed analysis'
            return 'llm_reasoning', 0.8, reasoning
        
        if requires_specialist or work_type == 'inspection':
            reasoning['reason'] = 'Requires specialist evaluation'
            return 'llm_reasoning', 0.85, reasoning
        
        # Check for ML model suitability
        if has_measurements and category != 'Unknown' and complexity in ['simple', 'moderate']:
            reasoning['reason'] = 'Has structured data for ML prediction'
            reasoning['features'] = {
                'has_measurements': True,
                'category': category,
                'complexity': complexity
            }
            return 'ml_model', 0.75, reasoning
        
        # Default to LLM reasoning for uncertain cases
        reasoning['reason'] = 'Default to LLM for general case'
        return 'llm_reasoning', 0.7, reasoning
    
    def _match_standard_item(self, trade: str, category: str, description: str) -> str:
        """
        Try to match issue to a standard replacement item.
        
        Args:
            trade: Trade category
            category: Component category
            description: Issue description
            
        Returns:
            Lookup key or empty string
        """
        description_lower = description.lower()
        
        # Build search terms
        search_terms = f"{trade} {category} {description}".lower()
        
        # Check each standard item
        for key in self.STANDARD_REPLACEMENTS.keys():
            # Extract components from key (e.g., 'hvac_furnace_replacement')
            parts = key.split('_')
            
            # Check if all parts are in search terms
            matches = all(part in search_terms for part in parts)
            
            if matches:
                logger.debug(f"Matched standard item: {key}")
                return key
        
        return ''
    
    def assign_batch(self, issues: List[Dict]) -> List[Dict]:
        """
        Assign strategies to a batch of issues.
        
        Args:
            issues: List of issue dictionaries
            
        Returns:
            Issues with strategy assignments
        """
        for issue in issues:
            strategy, confidence, reasoning = self.assign_strategy(issue)
            
            issue['cost_strategy'] = strategy
            issue['strategy_confidence'] = confidence
            issue['strategy_reasoning'] = reasoning
            
            # Update enrichment metadata
            if 'enrichment_metadata' not in issue:
                issue['enrichment_metadata'] = {}
            
            issue['enrichment_metadata']['cost_strategy'] = {
                'strategy': strategy,
                'confidence': confidence,
                'reasoning': reasoning
            }
            
            logger.debug(f"Assigned strategy '{strategy}' to issue: {issue.get('id')}")
        
        return issues
    
    def get_strategy_summary(self, issues: List[Dict]) -> Dict:
        """
        Get summary of strategy assignments.
        
        Args:
            issues: List of issues with strategies
            
        Returns:
            Summary dictionary
        """
        summary = {
            'by_strategy': {},
            'avg_confidence': {}
        }
        
        strategy_confidences = {}
        
        for issue in issues:
            strategy = issue.get('cost_strategy', 'unknown')
            confidence = issue.get('strategy_confidence', 0.0)
            
            # Count by strategy
            summary['by_strategy'][strategy] = summary['by_strategy'].get(strategy, 0) + 1
            
            # Track confidences
            if strategy not in strategy_confidences:
                strategy_confidences[strategy] = []
            strategy_confidences[strategy].append(confidence)
        
        # Calculate average confidences
        for strategy, confidences in strategy_confidences.items():
            summary['avg_confidence'][strategy] = round(sum(confidences) / len(confidences), 2)
        
        return summary
    
    def get_standard_items(self) -> Dict:
        """Get all standard replacement items with costs."""
        return self.STANDARD_REPLACEMENTS.copy()

