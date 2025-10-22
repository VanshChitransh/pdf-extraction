#!/usr/bin/env python3
"""
Test script to verify the component classification fix for roof-related issues.
"""

import sys
import os
import json
from src.enrichment.component_taxonomy import ComponentTaxonomy

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