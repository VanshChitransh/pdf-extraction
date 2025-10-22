"""
Phase 2.3: Add Contextual Metadata
Enriches issues with contextual metadata for cost estimation.
"""

from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


class MetadataEnricher:
    """Enriches issues with contextual metadata."""
    
    def __init__(self, property_data: Optional[Dict] = None):
        """
        Initialize enricher with optional property data.
        
        Args:
            property_data: Dictionary containing property information
        """
        self.property_data = property_data or {}
    
    def enrich_issue(self, issue: Dict) -> Dict:
        """
        Enrich a single issue with metadata.
        
        Args:
            issue: Issue dictionary
            
        Returns:
            Enriched issue
        """
        enriched = issue.copy()
        
        # Initialize enrichment_metadata if not present
        if 'enrichment_metadata' not in enriched:
            enriched['enrichment_metadata'] = {}
        
        # Add property context if available
        if self.property_data:
            enriched['enrichment_metadata']['property'] = self.property_data
        
        # Calculate urgency score
        urgency_score = self._calculate_urgency_score(enriched)
        enriched['urgency_score'] = urgency_score
        enriched['enrichment_metadata']['urgency_score'] = urgency_score
        
        # Calculate complexity factor
        complexity_factor = self._calculate_complexity_factor(enriched)
        enriched['complexity_factor'] = complexity_factor
        enriched['enrichment_metadata']['complexity_factor'] = complexity_factor
        
        # Determine if specialized labor is needed
        specialized_labor = self._requires_specialized_labor(enriched)
        enriched['requires_specialized_labor'] = specialized_labor
        enriched['enrichment_metadata']['specialized_labor'] = specialized_labor
        
        # Estimate affected area size
        affected_area = self._estimate_affected_area(enriched)
        if affected_area:
            enriched['estimated_affected_area'] = affected_area
            enriched['enrichment_metadata']['affected_area'] = affected_area
        
        return enriched
    
    def _calculate_urgency_score(self, issue: Dict) -> float:
        """
        Calculate urgency score (0-10) based on severity, action, and safety.
        
        Args:
            issue: Issue dictionary
            
        Returns:
            Urgency score
        """
        score = 5.0  # Base score
        
        # Severity contribution (0-4 points)
        severity = issue.get('standard_severity', issue.get('severity', '')).lower()
        severity_scores = {
            'critical': 4.0,
            'high': 3.0,
            'medium': 2.0,
            'low': 1.0,
            'unknown': 0.0
        }
        score += severity_scores.get(severity, 0.0)
        
        # Action type contribution (0-3 points)
        action = issue.get('standard_action', issue.get('suggested_action', '')).lower()
        if 'immediate' in action:
            score += 3.0
        elif 'replacement' in action or 'replace' in action:
            score += 2.0
        elif 'repair' in action:
            score += 1.5
        elif 'inspect' in action or 'evaluat' in action:
            score += 1.0
        elif 'monitor' in action:
            score += 0.5
        
        # Safety flag contribution (0-3 points)
        if issue.get('safety_flag') or issue.get('safety_related'):
            score += 3.0
        
        # Damage type contribution
        damage_types = issue.get('extracted_attributes', {}).get('damage_types', [])
        if 'water_damage' in damage_types or 'leak' in str(issue.get('description', '')).lower():
            score += 1.0  # Water damage needs quick attention
        if 'mold' in damage_types:
            score += 1.5  # Mold is health hazard
        
        # Cap at 10
        score = min(10.0, score)
        
        return round(score, 2)
    
    def _calculate_complexity_factor(self, issue: Dict) -> float:
        """
        Calculate complexity factor (0-10) based on various factors.
        
        Args:
            issue: Issue dictionary
            
        Returns:
            Complexity factor
        """
        complexity = 5.0  # Base complexity
        
        # Component category complexity
        category = issue.get('standard_category', '')
        category_complexity = {
            'Structural': 3.0,
            'HVAC': 2.5,
            'Electrical': 2.5,
            'Plumbing': 2.0,
            'Roofing': 2.0,
            'Foundation': 3.0,
        }
        complexity += category_complexity.get(category, 0.0)
        
        # Accessibility impact
        accessibility = issue.get('accessibility_complexity', '')
        if accessibility == 'difficult':
            complexity += 2.0
        elif accessibility == 'requires_equipment':
            complexity += 2.5
        elif accessibility == 'confined_space':
            complexity += 1.5
        elif accessibility == 'easy':
            complexity -= 1.0
        
        # Specialized labor increases complexity
        if issue.get('requires_specialized_labor'):
            complexity += 1.5
        
        # Multiple locations increase complexity
        locations = issue.get('extracted_attributes', {}).get('locations', [])
        if len(locations) > 2:
            complexity += 1.0
        
        # Multiple damage types increase complexity
        damage_types = issue.get('extracted_attributes', {}).get('damage_types', [])
        if len(damage_types) > 2:
            complexity += 1.0
        
        # Cap at 10
        complexity = min(10.0, complexity)
        
        return round(complexity, 2)
    
    def _requires_specialized_labor(self, issue: Dict) -> bool:
        """
        Determine if specialized/licensed labor is required.
        
        Args:
            issue: Issue dictionary
            
        Returns:
            True if specialized labor needed
        """
        # Categories that typically require licensed professionals
        specialized_categories = {
            'Electrical', 'HVAC', 'Plumbing', 'Structural', 'Roofing'
        }
        
        category = issue.get('standard_category', '')
        if category in specialized_categories:
            return True
        
        # Check for keywords in description
        description = issue.get('description', '').lower()
        specialized_keywords = [
            'licensed', 'electrician', 'plumber', 'hvac tech', 'structural engineer',
            'contractor', 'specialist', 'professional', 'certified', 'qualified'
        ]
        
        for keyword in specialized_keywords:
            if keyword in description:
                return True
        
        # Check action type
        action = issue.get('standard_action', '')
        if action == 'further_inspection':
            return True
        
        return False
    
    def _estimate_affected_area(self, issue: Dict) -> Optional[Dict[str, Any]]:
        """
        Estimate the affected area size from measurements.
        
        Args:
            issue: Issue dictionary
            
        Returns:
            Dictionary with area estimate or None
        """
        attributes = issue.get('extracted_attributes', {})
        measurements = attributes.get('measurements', {})
        
        if not measurements:
            return None
        
        area_info = {}
        
        # Check for square footage
        if 'areas' in measurements and measurements['areas']:
            # Extract numeric value
            area_str = measurements['areas'][0]
            try:
                area_value = float(area_str.split()[0].replace(',', ''))
                area_info['square_feet'] = area_value
                area_info['size_category'] = self._categorize_size(area_value)
            except ValueError:
                pass
        
        # Check for dimensions
        elif 'dimensions' in measurements and measurements['dimensions']:
            # Try to calculate area from dimensions
            dim_str = measurements['dimensions'][0]
            try:
                parts = dim_str.split('x')
                if len(parts) == 2:
                    length = float(parts[0])
                    width = float(parts[1])
                    area_value = length * width
                    area_info['square_feet'] = area_value
                    area_info['dimensions'] = dim_str
                    area_info['size_category'] = self._categorize_size(area_value)
            except ValueError:
                pass
        
        return area_info if area_info else None
    
    def _categorize_size(self, square_feet: float) -> str:
        """Categorize area size."""
        if square_feet < 10:
            return 'small'
        elif square_feet < 50:
            return 'medium'
        elif square_feet < 200:
            return 'large'
        else:
            return 'very_large'
    
    def enrich_batch(self, issues: List[Dict]) -> List[Dict]:
        """
        Enrich a batch of issues.
        
        Args:
            issues: List of issue dictionaries
            
        Returns:
            Enriched issues
        """
        enriched_issues = []
        
        for issue in issues:
            enriched = self.enrich_issue(issue)
            enriched_issues.append(enriched)
        
        return enriched_issues
    
    def set_property_data(self, property_data: Dict):
        """
        Update property data for enrichment.
        
        Args:
            property_data: Property information dictionary
        """
        self.property_data = property_data
        logger.info(f"Updated property data: {property_data}")

