"""
Phase 2.2: Extract Key Attributes from Descriptions
Pulls structured data from unstructured text using NER and regex patterns.
"""

from typing import Dict, List, Optional, Any
import re
import logging

logger = logging.getLogger(__name__)


class AttributeExtractor:
    """Extracts structured attributes from unstructured text descriptions."""
    
    # Location patterns (room names, areas)
    LOCATION_PATTERNS = {
        'rooms': [
            'kitchen', 'bedroom', 'bathroom', 'living room', 'dining room', 'family room',
            'master bedroom', 'guest bedroom', 'laundry room', 'utility room', 'garage',
            'basement', 'attic', 'crawlspace', 'hallway', 'foyer', 'entry', 'den',
            'office', 'bonus room', 'media room', 'game room'
        ],
        'areas': [
            'front', 'back', 'rear', 'side', 'left', 'right', 'north', 'south', 'east', 'west',
            'exterior', 'interior', 'upstairs', 'downstairs', 'first floor', 'second floor',
            'ground level', 'upper level', 'lower level'
        ],
        'outdoor': [
            'roof', 'driveway', 'walkway', 'patio', 'deck', 'porch', 'yard', 'lawn',
            'fence', 'gate', 'foundation', 'exterior wall'
        ]
    }
    
    # Measurement patterns
    MEASUREMENT_PATTERNS = [
        # Dimensions: 2x3, 2 x 3, 2' x 3', 2ft x 3ft, etc.
        r'(\d+(?:\.\d+)?)\s*[xX×]\s*(\d+(?:\.\d+)?)\s*(?:feet|foot|ft|\'|inches|inch|in|\")?',
        # Single measurements: 5 feet, 10 inches, 3', etc.
        r'(\d+(?:\.\d+)?)\s*(?:feet|foot|ft|\'|inches|inch|in|\")',
        # Square footage: 500 sq ft, 1000 square feet
        r'(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:sq\.?\s*ft|square\s+feet|square\s+foot)',
        # Percentages
        r'(\d+(?:\.\d+)?)\s*(?:%|percent)',
    ]
    
    # Material keywords
    MATERIALS = {
        'wood': ['wood', 'wooden', 'timber', 'lumber', 'oak', 'pine', 'cedar', 'plywood', 'hardwood'],
        'metal': ['metal', 'steel', 'aluminum', 'iron', 'galvanized', 'copper', 'brass'],
        'concrete': ['concrete', 'cement', 'masonry', 'brick', 'block', 'cinder block'],
        'drywall': ['drywall', 'sheetrock', 'gypsum board', 'wallboard'],
        'plastic': ['plastic', 'pvc', 'vinyl', 'polyethylene', 'abs'],
        'glass': ['glass', 'glazing', 'window glass'],
        'shingles': ['shingles', 'asphalt shingles', 'composition shingles', 'roof shingles'],
        'tile': ['tile', 'ceramic', 'porcelain', 'tiles'],
        'carpet': ['carpet', 'carpeting', 'rug'],
        'paint': ['paint', 'painted', 'coating']
    }
    
    # Damage type keywords
    DAMAGE_TYPES = {
        'water_damage': ['water damage', 'water stain', 'moisture', 'wet', 'damp', 'leak', 'seepage'],
        'crack': ['crack', 'cracked', 'cracking', 'fracture', 'split'],
        'rust': ['rust', 'rusted', 'corrosion', 'corroded', 'oxidation'],
        'rot': ['rot', 'rotted', 'decay', 'decayed', 'deterioration'],
        'mold': ['mold', 'mildew', 'fungus', 'fungi'],
        'wear': ['wear', 'worn', 'aging', 'deteriorated', 'degraded'],
        'missing': ['missing', 'absent', 'not present', 'lacking'],
        'damaged': ['damaged', 'broken', 'defective', 'compromised'],
        'improper': ['improper', 'incorrect', 'inadequate', 'insufficient']
    }
    
    # Safety-related keywords
    SAFETY_KEYWORDS = [
        'safety', 'hazard', 'dangerous', 'risk', 'unsafe', 'fire hazard',
        'electrical hazard', 'shock hazard', 'trip hazard', 'fall hazard',
        'carbon monoxide', 'gas leak', 'structural integrity'
    ]
    
    def extract_attributes(self, description: str, title: str = None) -> Dict[str, Any]:
        """
        Extract structured attributes from description text.
        
        Args:
            description: Full description text
            title: Optional title for additional context
            
        Returns:
            Dictionary of extracted attributes
        """
        if not description:
            return {}
        
        text = ' '.join(filter(None, [title, description])).lower()
        
        attributes = {
            'locations': self._extract_locations(text),
            'measurements': self._extract_measurements(text),
            'materials': self._extract_materials(text),
            'damage_types': self._extract_damage_types(text),
            'safety_related': self._is_safety_related(text),
            'accessibility': self._extract_accessibility(text)
        }
        
        # Remove empty values
        attributes = {k: v for k, v in attributes.items() if v}
        
        return attributes
    
    def _extract_locations(self, text: str) -> List[str]:
        """Extract location mentions from text."""
        locations = []
        
        # Check all location patterns
        for category, patterns in self.LOCATION_PATTERNS.items():
            for pattern in patterns:
                if pattern in text:
                    if pattern not in locations:
                        locations.append(pattern)
        
        # Look for "in the [location]" or "at the [location]" patterns
        location_context = re.findall(r'(?:in|at|near|around|by)\s+(?:the\s+)?(\w+(?:\s+\w+)?)', text)
        for loc in location_context:
            # Check if it matches known locations
            for category, patterns in self.LOCATION_PATTERNS.items():
                if loc in patterns and loc not in locations:
                    locations.append(loc)
        
        return locations
    
    def _extract_measurements(self, text: str) -> Dict[str, List[str]]:
        """Extract measurements from text."""
        measurements = {
            'dimensions': [],
            'lengths': [],
            'areas': []
        }
        
        for pattern in self.MEASUREMENT_PATTERNS:
            matches = re.findall(pattern, text)
            
            if matches:
                for match in matches:
                    if isinstance(match, tuple):
                        if len(match) == 2 and match[0] and match[1]:
                            # It's a dimension (2x3)
                            dim = f"{match[0]}x{match[1]}"
                            measurements['dimensions'].append(dim)
                        elif len(match) == 1 or (len(match) > 1 and not match[1]):
                            # Single measurement
                            measurements['lengths'].append(str(match[0] if isinstance(match, tuple) else match))
                    else:
                        measurements['lengths'].append(str(match))
        
        # Extract square footage specifically
        sqft_matches = re.findall(r'(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:sq\.?\s*ft|square\s+feet)', text)
        if sqft_matches:
            measurements['areas'] = [f"{m} sq ft" for m in sqft_matches]
        
        # Remove empty categories
        measurements = {k: v for k, v in measurements.items() if v}
        
        return measurements
    
    def _extract_materials(self, text: str) -> List[str]:
        """Extract material mentions from text."""
        materials = []
        
        for material_category, keywords in self.MATERIALS.items():
            for keyword in keywords:
                if keyword in text:
                    if material_category not in materials:
                        materials.append(material_category)
                    break
        
        return materials
    
    def _extract_damage_types(self, text: str) -> List[str]:
        """Extract damage type mentions from text."""
        damage_types = []
        
        for damage_category, keywords in self.DAMAGE_TYPES.items():
            for keyword in keywords:
                if keyword in text:
                    if damage_category not in damage_types:
                        damage_types.append(damage_category)
                    break
        
        return damage_types
    
    def _is_safety_related(self, text: str) -> bool:
        """Check if issue is safety-related."""
        for keyword in self.SAFETY_KEYWORDS:
            if keyword in text:
                return True
        return False
    
    def _extract_accessibility(self, text: str) -> Optional[str]:
        """Extract accessibility information."""
        accessibility_patterns = {
            'difficult': ['difficult to access', 'hard to reach', 'limited access', 'not accessible'],
            'requires_equipment': ['requires ladder', 'requires scaffolding', 'needs lift', 'needs special equipment'],
            'confined_space': ['crawlspace', 'attic', 'tight space', 'confined'],
            'easy': ['easily accessible', 'readily accessible', 'easy access']
        }
        
        for access_type, patterns in accessibility_patterns.items():
            for pattern in patterns:
                if pattern in text:
                    return access_type
        
        return None
    
    def enrich_issue(self, issue: Dict) -> Dict:
        """
        Enrich an issue with extracted attributes.
        
        Args:
            issue: Issue dictionary
            
        Returns:
            Enriched issue
        """
        enriched = issue.copy()
        
        description = issue.get('description', '')
        title = issue.get('title', '')
        
        # Extract attributes
        attributes = self.extract_attributes(description, title)
        
        # Add to issue
        enriched['extracted_attributes'] = attributes
        
        # Update enrichment metadata
        if 'enrichment_metadata' not in enriched:
            enriched['enrichment_metadata'] = {}
        
        enriched['enrichment_metadata']['attributes'] = attributes
        
        # Set safety flag if safety-related
        if attributes.get('safety_related'):
            enriched['safety_flag'] = True
            logger.debug(f"Issue marked as safety-related: {title[:50]}")
        
        # Set accessibility complexity
        if 'accessibility' in attributes:
            enriched['accessibility_complexity'] = attributes['accessibility']
        
        return enriched
    
    def extract_batch(self, issues: List[Dict]) -> List[Dict]:
        """
        Extract attributes for a batch of issues.
        
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

