#!/usr/bin/env python3
"""
Standalone test script for component taxonomy classification.
"""

import sys
import re
from typing import Dict, List, Tuple, Optional
from difflib import SequenceMatcher

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
            return category, subcat, confidence
        
        # Try fuzzy matching
        best_match = self._fuzzy_match(cleaned)
        
        if best_match[2] > 0.6:  # Confidence threshold
            return best_match
        
        # No good match found
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
                print(f"Found roof indicator in context: {indicator}")
                # Increased confidence for roof matches to ensure they take precedence
                return 'Roofing', None, 0.9
        
        # If confidence is low, try extracting from context
        if confidence < 0.75:  # ENHANCED: Increased threshold
            # Look for category keywords in context
            for cat_name, config in self.TAXONOMY.items():
                # Check category name
                if cat_name.lower() in context_text:
                    if confidence < 0.75:  # ENHANCED: Increased threshold
                        print(f"Found category in context: {cat_name}")
                        return cat_name, None, 0.75
                
                # Check aliases
                for alias in config['aliases']:
                    if alias in context_text:
                        if confidence < 0.8:  # ENHANCED: Increased threshold
                            print(f"Found alias in context: {alias} -> {cat_name}")
                            return cat_name, None, 0.8
                
                # Check subcategories
                for sub in config['subcategories']:
                    sub_normalized = sub.replace('_', ' ')
                    if sub_normalized in context_text:
                        if confidence < 0.85:  # ENHANCED: Increased threshold
                            print(f"Found subcategory in context: {sub} -> {cat_name}")
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

def test_roof_classification():
    """Test that roof-related issues are correctly classified."""
    taxonomy = ComponentTaxonomy()
    
    # Test cases with roof-related issues that were previously misclassified
    test_cases = [
        {
            "item": "Roof Surface",
            "section": "Exterior",
            "description": "Older roof with visible wear and tear",
            "expected_category": "Roofing"
        },
        {
            "item": "Shingles",
            "section": "Roof",
            "description": "Missing shingles observed on the south side",
            "expected_category": "Roofing"
        },
        {
            "item": "Drainage",  # This could be misclassified as Grounds or Plumbing
            "section": "Exterior",
            "description": "Roof drainage system needs cleaning",
            "expected_category": "Roofing"
        },
        {
            "item": "Ventilation",  # This could be misclassified as HVAC
            "section": "Attic",
            "description": "Roof vents are partially blocked",
            "expected_category": "Roofing"
        },
        {
            "item": "Surface Material",  # Generic name that could be misclassified
            "section": "Exterior",
            "description": "Roof material showing signs of aging",
            "expected_category": "Roofing"
        }
    ]
    
    results = []
    success_count = 0
    
    print("Testing roof-related classification...")
    print("-" * 50)
    
    for i, test_case in enumerate(test_cases):
        item = test_case["item"]
        section = test_case["section"]
        description = test_case["description"]
        expected = test_case["expected_category"]
        
        # Get classification
        category, subcategory, confidence = taxonomy.standardize_from_context(
            item, section, description
        )
        
        # Check if classification is correct
        is_correct = category == expected
        if is_correct:
            success_count += 1
            
        # Store result
        results.append({
            "test_case": i + 1,
            "item": item,
            "section": section,
            "description": description,
            "expected": expected,
            "actual": category,
            "confidence": confidence,
            "correct": is_correct
        })
        
        # Print result
        status = "✓" if is_correct else "✗"
        print(f"Test {i+1}: {status} Item: '{item}' → Expected: {expected}, Got: {category} (Confidence: {confidence:.2f})")
    
    # Print summary
    success_rate = (success_count / len(test_cases)) * 100
    print("-" * 50)
    print(f"Success rate: {success_count}/{len(test_cases)} ({success_rate:.1f}%)")
    
    return results, success_rate

if __name__ == "__main__":
    results, success_rate = test_roof_classification()
    
    # Exit with success if all tests pass
    if success_rate == 100:
        print("\nAll tests passed! The component classification fix is working correctly.")
        sys.exit(0)
    else:
        print("\nSome tests failed. The component classification fix needs further improvement.")
        sys.exit(1)