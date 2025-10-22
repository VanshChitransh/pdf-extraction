"""
Phase 3.1: Multi-level Issue Classification
Assigns issues to cost estimation categories with hierarchical structure.
"""

from typing import Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)


class IssueClassifier:
    """Classifies issues into multi-level hierarchy for cost estimation."""
    
    # Trade category classification rules
    TRADE_CLASSIFICATION = {
        'plumbing': {
            'keywords': ['plumbing', 'pipe', 'drain', 'water', 'sewer', 'faucet', 'toilet', 
                        'sink', 'tub', 'shower', 'water heater', 'leak', 'drainage'],
            'categories': ['Plumbing', 'Water_Heater']
        },
        'electrical': {
            'keywords': ['electrical', 'electric', 'wiring', 'outlet', 'switch', 'panel', 
                        'breaker', 'gfci', 'afci', 'lighting', 'fixture', 'circuit'],
            'categories': ['Electrical']
        },
        'hvac': {
            'keywords': ['hvac', 'heating', 'cooling', 'furnace', 'air conditioner', 'ac', 
                        'heat pump', 'ductwork', 'thermostat', 'ventilation', 'air handler'],
            'categories': ['HVAC']
        },
        'structural': {
            'keywords': ['structural', 'foundation', 'framing', 'beam', 'joist', 'support', 
                        'load bearing', 'structural integrity', 'settling', 'slab'],
            'categories': ['Structural', 'Foundation']
        },
        'roofing': {
            'keywords': ['roof', 'shingles', 'flashing', 'gutter', 'downspout', 'roofing', 
                        'roof covering', 'ridge', 'roof deck'],
            'categories': ['Roofing']
        },
        'carpentry': {
            'keywords': ['door', 'window', 'trim', 'cabinet', 'deck', 'porch', 'framing',
                        'wood', 'siding', 'fence'],
            'categories': ['Windows_Doors', 'Exterior', 'Interior']
        },
        'masonry': {
            'keywords': ['masonry', 'brick', 'concrete', 'block', 'chimney', 'fireplace',
                        'foundation', 'retaining wall'],
            'categories': ['Structural', 'Fireplace', 'Exterior']
        },
        'painting': {
            'keywords': ['paint', 'painted', 'coating', 'finish', 'stain'],
            'categories': ['Interior', 'Exterior']
        },
        'flooring': {
            'keywords': ['floor', 'flooring', 'carpet', 'tile', 'hardwood', 'laminate', 'vinyl'],
            'categories': ['Interior']
        },
        'general': {
            'keywords': ['repair', 'maintenance', 'general', 'misc', 'miscellaneous'],
            'categories': ['Interior', 'Exterior', 'Unknown']
        }
    }
    
    # Work type classification
    WORK_TYPE_KEYWORDS = {
        'repair': ['repair', 'fix', 'correct', 'patch', 'seal', 'address'],
        'replacement': ['replace', 'replacement', 'install new', 'remove and replace'],
        'inspection': ['inspect', 'evaluate', 'assess', 'investigation', 'specialist'],
        'maintenance': ['maintain', 'service', 'clean', 'maintenance', 'upkeep'],
        'monitoring': ['monitor', 'observe', 'watch', 'track']
    }
    
    # Complexity tiers
    COMPLEXITY_FACTORS = {
        'simple': {
            'max_cost_range': 500,
            'indicators': ['minor', 'small', 'simple', 'quick fix', 'easy']
        },
        'moderate': {
            'max_cost_range': 3000,
            'indicators': ['moderate', 'typical', 'standard', 'normal']
        },
        'complex': {
            'max_cost_range': float('inf'),
            'indicators': ['major', 'extensive', 'significant', 'complex', 'structural']
        }
    }
    
    def classify_trade(self, issue: Dict) -> Tuple[str, float]:
        """
        Classify issue by trade category.
        
        Args:
            issue: Issue dictionary
            
        Returns:
            Tuple of (trade, confidence)
        """
        # Get relevant text
        category = issue.get('standard_category', '')
        description = issue.get('description', '').lower()
        title = issue.get('title', '').lower()
        section = issue.get('section', '').lower()
        
        combined_text = f"{category} {description} {title} {section}".lower()
        
        # Score each trade
        trade_scores = {}
        
        for trade, config in self.TRADE_CLASSIFICATION.items():
            score = 0
            
            # Check keywords
            for keyword in config['keywords']:
                if keyword in combined_text:
                    score += 1
            
            # Boost score if category matches
            for cat in config['categories']:
                if cat.lower() in category.lower():
                    score += 5
            
            if score > 0:
                trade_scores[trade] = score
        
        # Get best match
        if not trade_scores:
            return 'general', 0.3
        
        best_trade = max(trade_scores, key=trade_scores.get)
        max_score = trade_scores[best_trade]
        
        # Calculate confidence (normalize to 0-1)
        confidence = min(0.95, 0.5 + (max_score / 10))
        
        return best_trade, confidence
    
    def classify_work_type(self, issue: Dict) -> Tuple[str, float]:
        """
        Classify issue by work type.
        
        Args:
            issue: Issue dictionary
            
        Returns:
            Tuple of (work_type, confidence)
        """
        # Get action
        action = issue.get('standard_action', '')
        description = issue.get('description', '').lower()
        
        # Direct mapping from standard action
        action_mapping = {
            'immediate_repair': 'repair',
            'replacement': 'replacement',
            'further_inspection': 'inspection',
            'monitoring': 'monitoring',
            'maintenance': 'maintenance',
            'no_action': 'monitoring'
        }
        
        if action in action_mapping:
            return action_mapping[action], 0.9
        
        # Fall back to keyword matching
        combined_text = f"{action} {description}".lower()
        
        work_scores = {}
        for work_type, keywords in self.WORK_TYPE_KEYWORDS.items():
            score = sum(1 for keyword in keywords if keyword in combined_text)
            if score > 0:
                work_scores[work_type] = score
        
        if not work_scores:
            return 'repair', 0.5  # Default to repair
        
        best_work = max(work_scores, key=work_scores.get)
        confidence = min(0.85, 0.6 + (work_scores[best_work] / 5))
        
        return best_work, confidence
    
    def classify_complexity(self, issue: Dict) -> Tuple[str, float]:
        """
        Classify issue complexity tier.
        
        Args:
            issue: Issue dictionary
            
        Returns:
            Tuple of (complexity, confidence)
        """
        description = issue.get('description', '').lower()
        complexity_factor = issue.get('complexity_factor', 5.0)
        
        # Use complexity factor as primary indicator
        if complexity_factor >= 7:
            complexity = 'complex'
            confidence = 0.8
        elif complexity_factor >= 4:
            complexity = 'moderate'
            confidence = 0.75
        else:
            complexity = 'simple'
            confidence = 0.7
        
        # Check description for complexity indicators
        for tier, config in self.COMPLEXITY_FACTORS.items():
            for indicator in config['indicators']:
                if indicator in description:
                    # If description agrees with complexity_factor, boost confidence
                    if tier == complexity:
                        confidence = min(0.95, confidence + 0.1)
                    # If strong disagreement, trust description more
                    elif confidence < 0.8:
                        complexity = tier
                        confidence = 0.8
                    break
        
        return complexity, confidence
    
    def classify_issue(self, issue: Dict) -> Dict:
        """
        Perform complete multi-level classification.
        
        Args:
            issue: Issue dictionary
            
        Returns:
            Issue with classification added
        """
        classified = issue.copy()
        
        # Classify on all three levels
        trade, trade_conf = self.classify_trade(issue)
        work_type, work_conf = self.classify_work_type(issue)
        complexity, complexity_conf = self.classify_complexity(issue)
        
        # Add classification
        classification = {
            'trade': trade,
            'trade_confidence': trade_conf,
            'work_type': work_type,
            'work_type_confidence': work_conf,
            'complexity': complexity,
            'complexity_confidence': complexity_conf
        }
        
        classified['classification'] = classification
        
        # Update enrichment metadata
        if 'enrichment_metadata' not in classified:
            classified['enrichment_metadata'] = {}
        
        classified['enrichment_metadata']['classification'] = classification
        
        logger.debug(f"Classified: trade={trade}, work={work_type}, complexity={complexity}")
        
        return classified
    
    def classify_batch(self, issues: List[Dict]) -> List[Dict]:
        """
        Classify a batch of issues.
        
        Args:
            issues: List of issue dictionaries
            
        Returns:
            Classified issues
        """
        classified_issues = []
        
        for issue in issues:
            classified = self.classify_issue(issue)
            classified_issues.append(classified)
        
        return classified_issues
    
    def get_classification_summary(self, issues: List[Dict]) -> Dict:
        """
        Generate summary of classifications.
        
        Args:
            issues: List of classified issues
            
        Returns:
            Summary dictionary
        """
        summary = {
            'by_trade': {},
            'by_work_type': {},
            'by_complexity': {}
        }
        
        for issue in issues:
            classification = issue.get('classification', {})
            
            # Count by trade
            trade = classification.get('trade', 'unknown')
            summary['by_trade'][trade] = summary['by_trade'].get(trade, 0) + 1
            
            # Count by work type
            work_type = classification.get('work_type', 'unknown')
            summary['by_work_type'][work_type] = summary['by_work_type'].get(work_type, 0) + 1
            
            # Count by complexity
            complexity = classification.get('complexity', 'unknown')
            summary['by_complexity'][complexity] = summary['by_complexity'].get(complexity, 0) + 1
        
        return summary

