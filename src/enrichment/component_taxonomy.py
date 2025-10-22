"""
Phase 2.1: Component/Item Standardization
Maps free-text item names to a standard taxonomy using fuzzy matching.
"""

from typing import Dict, List, Tuple, Optional
from difflib import SequenceMatcher
import re
import logging

logger = logging.getLogger(__name__)


class ComponentTaxonomy:
    """Standardizes component/item names to a master taxonomy."""
    
    # Master component taxonomy with hierarchical structure
    TAXONOMY = {
        'HVAC': {
            'subcategories': ['furnace', 'air_conditioner', 'heat_pump', 'ductwork', 'thermostat', 'air_handler', 'condenser'],
            'aliases': ['heating', 'cooling', 'hvac system', 'climate control', 'ac', 'a/c', 'heat', 
                       'air conditioning', 'central air', 'hvac unit', 'heating system', 'cooling system']
        },
        'Roofing': {
            'subcategories': ['shingles', 'flashing', 'gutters', 'downspouts', 'chimney', 'skylights', 'vents', 'ridge'],
            'aliases': ['roof', 'rooftop', 'roof covering', 'roofing system', 'roof shingles', 
                       'roof membrane', 'roof surface', 'gutter system']
        },
        'Plumbing': {
            'subcategories': ['water_heater', 'pipes', 'drains', 'fixtures', 'water_supply', 'sewer', 'faucets', 'toilets'],
            'aliases': ['plumbing system', 'water system', 'piping', 'drain system', 'water lines',
                       'supply lines', 'waste lines', 'plumbing fixtures', 'hot water heater']
        },
        'Electrical': {
            'subcategories': ['panel', 'wiring', 'outlets', 'switches', 'gfci', 'afci', 'breakers', 'lighting'],
            'aliases': ['electrical system', 'electric', 'electrical panel', 'breaker box', 'wiring system',
                       'electrical outlets', 'power', 'circuit breaker', 'service panel']
        },
        'Structural': {
            'subcategories': ['foundation', 'framing', 'walls', 'floors', 'beams', 'joists', 'supports'],
            'aliases': ['structure', 'structural system', 'framing system', 'load bearing', 
                       'structural support', 'foundation system', 'slab', 'concrete foundation']
        },
        'Exterior': {
            'subcategories': ['siding', 'trim', 'doors', 'windows', 'decks', 'porches', 'driveway', 'walkways'],
            'aliases': ['exterior walls', 'outside', 'exterior surfaces', 'facade', 'exterior finish',
                       'exterior components', 'outdoor features']
        },
        'Interior': {
            'subcategories': ['walls', 'ceilings', 'floors', 'doors', 'windows', 'trim', 'stairs'],
            'aliases': ['interior walls', 'inside', 'interior surfaces', 'interior finish', 
                       'interior components', 'indoor features', 'drywall', 'sheetrock']
        },
        'Appliances': {
            'subcategories': ['dishwasher', 'range', 'oven', 'microwave', 'refrigerator', 'disposal', 'hood'],
            'aliases': ['kitchen appliances', 'appliance', 'built-in appliances', 'cooking appliances']
        },
        'Insulation': {
            'subcategories': ['attic_insulation', 'wall_insulation', 'crawlspace_insulation', 'ventilation'],
            'aliases': ['insulation system', 'thermal barrier', 'attic insulation', 'weatherization']
        },
        'Windows_Doors': {
            'subcategories': ['windows', 'doors', 'glass', 'frames', 'screens', 'weatherstripping'],
            'aliases': ['windows and doors', 'entry doors', 'window system', 'door system', 'glazing']
        },
        'Fireplace': {
            'subcategories': ['firebox', 'chimney', 'damper', 'hearth', 'flue'],
            'aliases': ['fireplace system', 'wood burning', 'gas fireplace', 'fireplace insert']
        },
        'Garage': {
            'subcategories': ['garage_door', 'opener', 'floor', 'walls'],
            'aliases': ['garage system', 'garage door system', 'carport']
        },
        'Grounds': {
            'subcategories': ['grading', 'drainage', 'retaining_walls', 'fencing', 'landscaping'],
            'aliases': ['site', 'yard', 'property grounds', 'exterior grounds', 'landscape']
        }
    }
    
    def __init__(self):
        """Initialize the taxonomy with lookup indices."""
        self._build_lookup_index()
    
    def _build_lookup_index(self):
        """Build fast lookup index for matching."""
        self.lookup = {}
        
        for category, config in self.TAXONOMY.items():
            # Add category itself
            self.lookup[category.lower()] = (category, None, 1.0)
            
            # Add subcategories
            for subcat in config['subcategories']:
                key = subcat.lower().replace('_', ' ')
                self.lookup[key] = (category, subcat, 0.95)
            
            # Add aliases
            for alias in config['aliases']:
                key = alias.lower()
                self.lookup[key] = (category, None, 0.9)
    
    def standardize(self, item_name: str) -> Tuple[str, Optional[str], float]:
        """
        Standardize an item name to taxonomy.
        
        Args:
            item_name: Raw item/component name
            
        Returns:
            Tuple of (standard_category, subcategory, confidence)
        """
        if not item_name:
            return 'Unknown', None, 0.0
        
        # Clean and normalize
        cleaned = item_name.lower().strip()
        cleaned = re.sub(r'[^\w\s/-]', '', cleaned)
        
        # Try exact lookup first
        if cleaned in self.lookup:
            category, subcat, confidence = self.lookup[cleaned]
            logger.debug(f"Exact match: '{item_name}' -> {category}/{subcat}")
            return category, subcat, confidence
        
        # Try fuzzy matching
        best_match = self._fuzzy_match(cleaned)
        
        if best_match[2] > 0.6:  # Confidence threshold
            logger.debug(f"Fuzzy match: '{item_name}' -> {best_match[0]}/{best_match[1]} (confidence: {best_match[2]:.2f})")
            return best_match
        
        # No good match found
        logger.debug(f"No match found for: '{item_name}'")
        return 'Unknown', None, 0.0
    
    def _fuzzy_match(self, text: str) -> Tuple[str, Optional[str], float]:
        """
        Perform fuzzy matching against taxonomy.
        
        Args:
            text: Normalized text to match
            
        Returns:
            Tuple of (category, subcategory, confidence)
        """
        best_match = ('Unknown', None, 0.0)
        
        for key, (category, subcat, base_confidence) in self.lookup.items():
            # Calculate similarity
            similarity = SequenceMatcher(None, text, key).ratio()
            
            # Check if key is contained in text or vice versa
            if key in text or text in key:
                similarity = max(similarity, 0.75)
            
            # Adjust confidence based on similarity
            confidence = similarity * base_confidence
            
            if confidence > best_match[2]:
                best_match = (category, subcat, confidence)
        
        return best_match
    
    def standardize_from_context(self, item_name: str, section: str = None, description: str = None) -> Tuple[str, Optional[str], float]:
        """
        Standardize using additional context from section and description.
        
        Args:
            item_name: Raw item name
            section: Section name for context
            description: Description for context
            
        Returns:
            Tuple of (standard_category, subcategory, confidence)
        """
        # First try standard matching
        category, subcat, confidence = self.standardize(item_name)
        
        # Create a comprehensive context text for analysis
        context_text = ' '.join(filter(None, [item_name, section, description])).lower()
        
        # ENHANCED: Expanded roof indicators with more comprehensive terms
        roof_indicators = [
            'roof', 'shingle', 'flashing', 'gutter', 'downspout', 'roofing', 
            'roof covering', 'ridge', 'roof deck', 'roof surface', 'roof leak',
            'roof damage', 'roof repair', 'roof replacement', 'roof vent',
            'roof material', 'roof structure', 'roof system', 'roof area',
            'rooftop', 'roof edge', 'roof drainage', 'roof inspection'
        ]
        
        # ENHANCED: Check for roof indicators with higher priority
        # This addresses the specific issue of roof items being misclassified
        for indicator in roof_indicators:
            if indicator in context_text:
                logger.debug(f"Found roof indicator in context: {indicator}")
                # Increased confidence for roof matches to ensure they take precedence
                return 'Roofing', None, 0.9
        
        # If confidence is low, try extracting from context
        if confidence < 0.75:  # ENHANCED: Increased threshold
            # Look for category keywords in context
            for cat_name, config in self.TAXONOMY.items():
                # Check category name
                if cat_name.lower() in context_text:
                    if confidence < 0.75:  # ENHANCED: Increased threshold
                        logger.debug(f"Found category in context: {cat_name}")
                        return cat_name, None, 0.75
                
                # Check aliases
                for alias in config['aliases']:
                    if alias in context_text:
                        if confidence < 0.8:  # ENHANCED: Increased threshold
                            logger.debug(f"Found alias in context: {alias} -> {cat_name}")
                            return cat_name, None, 0.8
                
                # Check subcategories
                for sub in config['subcategories']:
                    sub_normalized = sub.replace('_', ' ')
                    if sub_normalized in context_text:
                        if confidence < 0.85:  # ENHANCED: Increased threshold
                            logger.debug(f"Found subcategory in context: {sub} -> {cat_name}")
                            return cat_name, sub, 0.85
        
        # ENHANCED: Improved section name analysis with stronger confidence
        if section and confidence < 0.7:  # Increased threshold
            section_lower = section.lower()
            if 'roof' in section_lower or 'roofing' in section_lower:
                return 'Roofing', None, 0.85  # ENHANCED: Higher confidence for roof sections
            elif 'structural' in section_lower:
                return 'Structural', None, 0.75
            elif 'plumbing' in section_lower:
                return 'Plumbing', None, 0.75
            elif 'electrical' in section_lower:
                return 'Electrical', None, 0.75
            elif any(term in section_lower for term in ['hvac', 'heating', 'cooling', 'air conditioning']):
                return 'HVAC', None, 0.75
        
        # ENHANCED: More comprehensive description analysis with expanded terms
        if confidence < 0.5:  # Check description even with moderate confidence
            if description:
                desc_lower = description.lower()
                # ENHANCED: More comprehensive roof terms with higher confidence
                if any(term in desc_lower for term in ['roof', 'shingle', 'flashing', 'gutter', 'downspout', 'roofing']):
                    return 'Roofing', None, 0.8
                elif any(term in desc_lower for term in ['hvac', 'furnace', 'air conditioning', 'heat', 'cooling']):
                    return 'HVAC', None, 0.75
                elif any(term in desc_lower for term in ['plumbing', 'water', 'pipe', 'leak', 'drain', 'toilet', 'faucet']):
                    return 'Plumbing', None, 0.75
                elif any(term in desc_lower for term in ['electrical', 'wiring', 'outlet', 'circuit', 'breaker', 'panel']):
                    return 'Electrical', None, 0.75
        
        return category, subcat, confidence
    
    def get_category_info(self, category: str) -> Optional[Dict]:
        """
        Get information about a category.
        
        Args:
            category: Standard category name
            
        Returns:
            Dictionary with category info or None
        """
        return self.TAXONOMY.get(category)
    
    def get_all_categories(self) -> List[str]:
        """Get list of all standard categories."""
        return list(self.TAXONOMY.keys())
    
    def get_subcategories(self, category: str) -> List[str]:
        """Get subcategories for a category."""
        if category in self.TAXONOMY:
            return self.TAXONOMY[category]['subcategories']
        return []
    
    def enrich_issue(self, issue: Dict) -> Dict:
        """
        Enrich an issue with standardized component information.
        
        Args:
            issue: Issue dictionary
            
        Returns:
            Enriched issue
        """
        enriched = issue.copy()
        
        # Extract item name from various possible fields
        item_name = (
            issue.get('item', '') or 
            issue.get('title', '') or 
            issue.get('subsection', '') or
            issue.get('section', '')
        )
        
        # Get context
        section = issue.get('section', '')
        description = issue.get('description', '')
        
        # Standardize
        category, subcategory, confidence = self.standardize_from_context(
            item_name, section, description
        )
        
        # Add to issue
        enriched['standard_category'] = category
        enriched['standard_subcategory'] = subcategory
        enriched['category_confidence'] = confidence
        
        # Add category metadata
        if 'enrichment_metadata' not in enriched:
            enriched['enrichment_metadata'] = {}
        
        enriched['enrichment_metadata']['component_taxonomy'] = {
            'category': category,
            'subcategory': subcategory,
            'confidence': confidence,
            'original_item': item_name
        }
        
        return enriched

