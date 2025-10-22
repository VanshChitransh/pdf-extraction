#!/usr/bin/env python3
"""
Test script to verify the 5 critical fixes:
1. AI response rejection if incomplete
2. Unicode normalization
3. Fallback estimate field preservation
4. Confidence scorer logging
5. Stricter prompts

Tests with FIRST 3 ISSUES ONLY to save API quota.
"""

import os
import sys
import json
from pathlib import Path

# Set API key
os.environ['GEMINI_API_KEY'] = 'AIzaSyC6cbjbrjZQE1VkzZQ83Mbfym8PN09wV6k'

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from enhanced_cost_estimator import EnhancedCostEstimator

def test_fixes():
    """Test the fixes with a small sample."""
    
    print("="*70)
    print("TESTING FIXES - Processing FIRST 3 ISSUES ONLY")
    print("="*70)
    
    # Load enriched data
    enriched_path = "enriched_data/6-report_enriched.json"
    print(f"\nLoading: {enriched_path}")
    
    with open(enriched_path, 'r') as f:
        data = json.load(f)
    
    # Take ONLY first 3 issues to save API quota
    original_count = len(data.get('issues', []))
    data['issues'] = data['issues'][:3]
    
    print(f"Original issue count: {original_count}")
    print(f"Testing with: {len(data['issues'])} issues (to save quota)")
    
    # Initialize estimator
    print("\nInitializing enhanced estimator...")
    estimator = EnhancedCostEstimator(
        model="gemini-2.5-flash",  # Using 2.5 Flash as requested
        enable_database_lookup=True,
        enable_relationship_analysis=True,
        enable_specialist_prompts=True
    )
    
    # Process each issue
    print("\n" + "="*70)
    print("TESTING EACH FIX:")
    print("="*70)
    
    results = []
    
    for idx, issue in enumerate(data['issues'], 1):
        print(f"\n{'='*70}")
        print(f"ISSUE #{idx}: {issue.get('title', issue.get('item', 'Unknown'))}")
        print(f"{'='*70}")
        
        try:
            # Estimate
            estimate = estimator._estimate_issue(
                issue,
                data.get('metadata', {}),
                data['issues'],
                None
            )
            
            if estimate:
                print(f"\n✅ SUCCESS!")
                print(f"   Estimated: ${estimate.get('estimated_low', 0):.0f} - ${estimate.get('estimated_high', 0):.0f}")
                print(f"   Method: {estimate.get('estimation_method', 'unknown')}")
                
                # CHECK FIX #1: Are costs present?
                low = estimate.get('estimated_low', 0)
                high = estimate.get('estimated_high', 0)
                reasoning = estimate.get('reasoning', '')
                
                print(f"\n   FIX #1 CHECK (AI response validation):")
                if low > 0 and high > low:
                    print(f"   ✅ Costs present: ${low} < ${high}")
                else:
                    print(f"   ❌ FAILED: low={low}, high={high}")
                
                print(f"\n   FIX #3 CHECK (Fallback field preservation):")
                if reasoning:
                    print(f"   ✅ Reasoning present: {len(reasoning)} chars")
                else:
                    print(f"   ❌ FAILED: No reasoning")
                
                # CHECK FIX #4: Confidence scores
                confidence = estimate.get('confidence', {})
                breakdown = confidence.get('breakdown', {})
                
                print(f"\n   FIX #4 CHECK (Confidence scores):")
                print(f"   - estimate_range_quality: {breakdown.get('estimate_range_quality', 0)}")
                print(f"   - reasoning_quality: {breakdown.get('reasoning_quality', 0)}")
                
                if breakdown.get('estimate_range_quality', 0) > 0:
                    print(f"   ✅ Range quality scored")
                else:
                    print(f"   ⚠️  Range quality is 0 (check logs)")
                
                if breakdown.get('reasoning_quality', 0) > 0:
                    print(f"   ✅ Reasoning quality scored")
                else:
                    print(f"   ⚠️  Reasoning quality is 0 (check logs)")
                
                results.append(estimate)
            else:
                print(f"❌ FAILED: No estimate generated")
                
        except Exception as e:
            print(f"❌ ERROR: {str(e)}")
            import traceback
            traceback.print_exc()
    
    # Print summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"Issues tested: {len(data['issues'])}")
    print(f"Estimates generated: {len(results)}")
    print(f"\nData Quality Stats:")
    print(f"  Excluded: {estimator.stats.get('data_quality_excluded', 0)}")
    print(f"  Flagged: {estimator.stats.get('data_quality_flagged', 0)}")
    
    # CHECK FIX #2: Unicode normalization (should have LOW exclusion rate)
    exclusion_rate = estimator.stats.get('data_quality_excluded', 0) / len(data['issues']) * 100
    print(f"\n  FIX #2 CHECK (Unicode normalization):")
    if exclusion_rate < 50:
        print(f"  ✅ Exclusion rate: {exclusion_rate:.1f}% (good, <50%)")
    else:
        print(f"  ❌ Exclusion rate: {exclusion_rate:.1f}% (too high, >50%)")
    
    # Save test results
    output_path = "cost_estimates/test_fixes_results.json"
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump({
            'test_metadata': {
                'issues_tested': len(data['issues']),
                'estimates_generated': len(results),
                'stats': estimator.stats
            },
            'estimates': results
        }, f, indent=2)
    
    print(f"\n✅ Test results saved to: {output_path}")
    print("\n" + "="*70)

if __name__ == "__main__":
    test_fixes()
