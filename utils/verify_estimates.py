#!/usr/bin/env python3
"""
Quick validation script to check if AI estimates were successfully generated.
Run after estimation completes: python verify_estimates.py
"""

import json
import sys
from pathlib import Path

def verify_estimates(output_file: str = "cost_estimates/6-report_enhanced_estimates.json"):
    """Verify AI estimation results."""
    
    if not Path(output_file).exists():
        print(f"❌ Output file not found: {output_file}")
        print("   Run the estimation pipeline first!")
        return False
    
    with open(output_file, 'r') as f:
        data = json.load(f)
    
    summary = data.get("summary", {})
    estimates = data.get("cost_estimates", [])
    
    print("=" * 70)
    print("AI COST ESTIMATION VERIFICATION")
    print("=" * 70)
    
    # Check 1: Did AI run?
    ai_count = summary.get("ai_estimates", 0) + summary.get("hybrid_estimates", 0)
    print(f"\n✓ AI Estimates Generated: {ai_count}/{summary.get('total_issues', 0)}")
    
    # Check 2: Are estimates populated?
    null_estimates = sum(1 for e in estimates if e.get("estimated_low") is None or e.get("estimated_low") == 0)
    valid_estimates = len(estimates) - null_estimates
    print(f"✓ Valid Cost Estimates: {valid_estimates}/{len(estimates)}")
    
    if null_estimates > 0:
        print(f"⚠ WARNING: {null_estimates} estimates are missing or null!")
        print("   This means the API didn't return complete data.")
    
    # Check 3: Total cost
    total_low = summary.get("total_estimated_low", 0)
    total_high = summary.get("total_estimated_high", 0)
    print(f"\n✓ Total Cost Range: ${total_low:,.0f} - ${total_high:,.0f}")
    
    if total_low == 0 and total_high == 0:
        print("❌ FAILURE: No costs calculated!")
        print("   Check if GEMINI_API_KEY was set correctly.")
        return False
    
    # Check 4: Confidence
    avg_confidence = summary.get("average_confidence", 0)
    print(f"✓ Average Confidence: {avg_confidence:.0f}%")
    
    if avg_confidence < 60:
        print("⚠ WARNING: Low confidence scores - may need manual review")
    
    # Check 5: Quality metrics
    needs_review = summary.get("needs_review", 0)
    high_conf = summary.get("high_confidence", 0)
    print(f"\n✓ High Confidence (85+): {high_conf}/{len(estimates)}")
    print(f"✓ Needs Manual Review: {needs_review}/{len(estimates)}")
    
    review_pct = (needs_review / len(estimates) * 100) if estimates else 0
    if review_pct > 30:
        print(f"⚠ WARNING: {review_pct:.0f}% need review (target: <20%)")
    
    # Check 6: Sample estimate
    print("\n" + "=" * 70)
    print("SAMPLE ESTIMATE (First Issue)")
    print("=" * 70)
    
    if estimates:
        sample = estimates[0]
        print(f"Title: {sample.get('item', 'Unknown')}")
        print(f"Cost: ${sample.get('estimated_low', 0):,.0f} - ${sample.get('estimated_high', 0):,.0f}")
        print(f"Confidence: {sample.get('confidence_score', 0)}%")
        print(f"Reasoning: {sample.get('reasoning', 'None')[:200]}...")
        
        if sample.get('estimated_low') is None or sample.get('estimated_low') == 0:
            print("\n❌ SAMPLE HAS NULL ESTIMATES!")
            return False
    
    print("\n" + "=" * 70)
    
    # Final verdict
    if valid_estimates >= len(estimates) * 0.9 and total_low > 0:
        print("✅ VERIFICATION PASSED - AI Estimation Successful!")
        print(f"\nNext steps:")
        print(f"  1. Review flagged estimates (needs_review=true)")
        print(f"  2. Check cost reasonableness against Houston market rates")
        print(f"  3. Generate PDF report for client")
        return True
    else:
        print("❌ VERIFICATION FAILED - Issues detected")
        print(f"\nTroubleshooting:")
        print(f"  1. Check that GEMINI_API_KEY is valid")
        print(f"  2. Look for API errors in the logs")
        print(f"  3. Try running with --model gemini-1.5-flash")
        return False

if __name__ == "__main__":
    output_file = sys.argv[1] if len(sys.argv) > 1 else "cost_estimates/6-report_enhanced_estimates.json"
    success = verify_estimates(output_file)
    sys.exit(0 if success else 1)

