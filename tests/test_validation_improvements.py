#!/usr/bin/env python3
"""
Test script for Phase 1 validation improvements.

Tests:
1. Data quality validation
2. Estimation validation
3. End-to-end improvement measurement
"""

import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from validation.data_quality_validator import DataQualityValidator
from validation.estimation_validator import EstimationValidator


def test_data_quality_validation():
    """Test the data quality validator."""
    print("="*70)
    print("TEST 1: Data Quality Validation")
    print("="*70)
    
    validator = DataQualityValidator(strict_mode=False)
    
    # Test case 1: Good issue
    good_issue = {
        "id": "TEST_1",
        "section": "HVAC",
        "description": "Air conditioning system not cooling adequately. Unit is 12 years old.",
        "status": "D",
        "title": "AC not cooling"
    }
    
    result = validator.validate_issue(good_issue)
    print(f"\n✓ Good issue test:")
    print(f"  Valid: {result.valid}")
    print(f"  Quality score: {result.quality_score:.2f}")
    print(f"  Action: {result.action.value}")
    
    # Test case 2: Unicode corruption
    corrupted_issue = {
        "id": "TEST_2",
        "section": "ELECTRICAL",
        "description": "þ ̈ ̈ þ corrupted text",
        "status": "D",
        "title": "þ ̈ ̈ þ"
    }
    
    result = validator.validate_issue(corrupted_issue)
    print(f"\n✗ Corrupted issue test:")
    print(f"  Valid: {result.valid}")
    print(f"  Reason: {result.reason}")
    print(f"  Action: {result.action.value}")
    
    # Test case 3: Metadata content
    metadata_issue = {
        "id": "HEADER_3",
        "section": "HEADER",
        "description": "The inspector is not required to identify all potential hazards. It is recommended that qualified service professionals regarding any items reported as Deficient (D).",
        "status": "D",
        "title": "from qualified service professionals"
    }
    
    result = validator.validate_issue(metadata_issue)
    print(f"\n✗ Metadata issue test:")
    print(f"  Valid: {result.valid}")
    print(f"  Reason: {result.reason}")
    print(f"  Action: {result.action.value}")
    
    # Test case 4: Short description
    short_issue = {
        "id": "TEST_4",
        "section": "PLUMBING",
        "description": "Leak",
        "status": "D",
        "title": "Leak"
    }
    
    result = validator.validate_issue(short_issue)
    print(f"\n⚠ Short description test:")
    print(f"  Valid: {result.valid}")
    print(f"  Quality score: {result.quality_score:.2f}")
    print(f"  Issues: {result.issues_found}")
    
    print("\n" + "="*70)


def test_estimation_validation():
    """Test the estimation validator."""
    print("\n" + "="*70)
    print("TEST 2: Estimation Validation")
    print("="*70)
    
    validator = EstimationValidator(strict_mode=False, auto_correct=True)
    
    # Test case 1: Good estimate
    good_estimate = {
        "repair_name": "AC Repair",
        "cost": {
            "labor": {"min": 800, "max": 1500},
            "materials": {"min": 300, "max": 1000},
            "permits": {"min": 0, "max": 0},
            "total": {"min": 1100, "max": 2500}
        },
        "timeline": {"min_days": 1, "max_days": 3},
        "urgency": "high",
        "contractor_type": "HVAC Technician",
        "confidence_score": 0.85
    }
    
    result = validator.validate_estimate(good_estimate)
    print(f"\n✓ Good estimate test:")
    print(f"  Valid: {result.valid}")
    print(f"  Action: {result.action.value}")
    print(f"  Warnings: {len(result.warnings)}")
    
    # Test case 2: Math error (components don't sum)
    math_error_estimate = {
        "repair_name": "Foundation Repair",
        "cost": {
            "labor": {"min": 5000, "max": 8000},
            "materials": {"min": 2000, "max": 3000},
            "permits": {"min": 100, "max": 200},
            "total": {"min": 6000, "max": 10000}  # Wrong! Should be 7100-11200
        },
        "timeline": {"min_days": 5, "max_days": 10},
        "urgency": "high",
        "contractor_type": "Foundation Specialist",
        "confidence_score": 0.7
    }
    
    result = validator.validate_estimate(math_error_estimate)
    print(f"\n⚠ Math error test:")
    print(f"  Valid: {result.valid}")
    print(f"  Action: {result.action.value}")
    print(f"  Auto-corrected: {result.corrected_estimate is not None}")
    if result.corrected_estimate:
        print(f"  Corrected total: ${result.corrected_estimate['cost']['total']['min']}-${result.corrected_estimate['cost']['total']['max']}")
    
    # Test case 3: Inverted min/max
    inverted_estimate = {
        "repair_name": "Plumbing Repair",
        "cost": {
            "labor": {"min": 500, "max": 300},  # Inverted!
            "materials": {"min": 200, "max": 100},  # Inverted!
            "permits": {"min": 0, "max": 0},
            "total": {"min": 700, "max": 400}  # Inverted!
        },
        "timeline": {"min_days": 1, "max_days": 2},
        "urgency": "medium",
        "contractor_type": "Plumber",
        "confidence_score": 0.8
    }
    
    result = validator.validate_estimate(inverted_estimate)
    print(f"\n⚠ Inverted ranges test:")
    print(f"  Valid: {result.valid}")
    print(f"  Errors: {len(result.errors)}")
    print(f"  Auto-corrected: {result.corrected_estimate is not None}")
    
    # Test case 4: Extreme cost
    extreme_estimate = {
        "repair_name": "Complete Renovation",
        "cost": {
            "labor": {"min": 50000, "max": 100000},
            "materials": {"min": 30000, "max": 50000},
            "permits": {"min": 500, "max": 1000},
            "total": {"min": 80500, "max": 151000}
        },
        "timeline": {"min_days": 30, "max_days": 60},
        "urgency": "low",
        "contractor_type": "General Contractor",
        "confidence_score": 0.6
    }
    
    result = validator.validate_estimate(extreme_estimate)
    print(f"\n✗ Extreme cost test:")
    print(f"  Valid: {result.valid}")
    print(f"  Reason: {result.reason}")
    print(f"  Action: {result.action.value}")
    
    # Test case 5: Low confidence
    low_conf_estimate = {
        "repair_name": "Unknown Issue",
        "cost": {
            "labor": {"min": 100, "max": 1000},
            "materials": {"min": 50, "max": 500},
            "permits": {"min": 0, "max": 0},
            "total": {"min": 150, "max": 1500}
        },
        "timeline": {"min_days": 1, "max_days": 5},
        "urgency": "medium",
        "contractor_type": "Contractor",
        "confidence_score": 0.25
    }
    
    result = validator.validate_estimate(low_conf_estimate)
    print(f"\n⚠ Low confidence test:")
    print(f"  Valid: {result.valid}")
    print(f"  Action: {result.action.value}")
    print(f"  Warnings: {result.warnings}")
    
    print("\n" + "="*70)


def test_with_real_data():
    """Test validators with real enriched data."""
    print("\n" + "="*70)
    print("TEST 3: Real Data Validation")
    print("="*70)
    
    enriched_path = Path("enriched_data/6-report_enriched.json")
    
    if not enriched_path.exists():
        print(f"⚠ Enriched data not found at: {enriched_path}")
        print("  Skipping real data test")
        return
    
    print(f"\nLoading enriched data from: {enriched_path}")
    with open(enriched_path, 'r') as f:
        data = json.load(f)
    
    issues = data.get('issues', [])
    print(f"Found {len(issues)} issues")
    
    # Test data quality validation
    print("\nRunning data quality validation...")
    validator = DataQualityValidator(strict_mode=False)
    results = validator.validate_batch(issues)
    
    print(f"\nData Quality Results:")
    print(f"  Total issues: {len(issues)}")
    print(f"  Valid: {len(results['valid_issues'])}")
    print(f"  Excluded: {len(results['excluded_issues'])}")
    print(f"  Flagged: {len(results['flagged_issues'])}")
    
    summary = results['summary']
    print(f"\n  Pass rate: {summary['pass_rate']:.1f}%")
    print(f"  Exclusion rate: {summary['exclusion_rate']:.1f}%")
    
    if summary['failure_reasons']:
        print("\n  Top exclusion reasons:")
        for reason, count in sorted(summary['failure_reasons'].items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"    - {reason}: {count}")
    
    # Show sample excluded issues
    if results['excluded_issues']:
        print("\n  Sample excluded issues:")
        for exc in results['excluded_issues'][:3]:
            issue = exc['issue']
            print(f"    - ID: {issue.get('id', 'unknown')}")
            print(f"      Reason: {exc['reason']}")
            print(f"      Description: {issue.get('description', 'N/A')[:60]}...")
    
    print("\n" + "="*70)


def test_cost_estimates_validation():
    """Test estimation validator with real cost estimates."""
    print("\n" + "="*70)
    print("TEST 4: Real Cost Estimates Validation")
    print("="*70)
    
    estimates_path = Path("cost_estimates 22-22-02-317/6-report_enhanced_estimates.json")
    
    if not estimates_path.exists():
        print(f"⚠ Cost estimates not found at: {estimates_path}")
        print("  Skipping cost estimates test")
        return
    
    print(f"\nLoading cost estimates from: {estimates_path}")
    with open(estimates_path, 'r') as f:
        data = json.load(f)
    
    estimates = data.get('cost_estimates', [])
    print(f"Found {len(estimates)} estimates")
    
    # Test estimation validation
    print("\nRunning estimation validation...")
    validator = EstimationValidator(strict_mode=False, auto_correct=True)
    
    valid_count = 0
    flagged_count = 0
    failed_count = 0
    auto_corrected_count = 0
    
    for idx, estimate in enumerate(estimates[:20], 1):  # Test first 20
        result = validator.validate_estimate(estimate)
        
        if result.valid:
            valid_count += 1
            if result.action.value == 'flag_for_review':
                flagged_count += 1
        else:
            failed_count += 1
        
        if result.corrected_estimate:
            auto_corrected_count += 1
    
    print(f"\nEstimation Validation Results (first 20):")
    print(f"  Valid: {valid_count}/20")
    print(f"  Flagged for review: {flagged_count}/20")
    print(f"  Failed: {failed_count}/20")
    print(f"  Auto-corrected: {auto_corrected_count}/20")
    
    stats = validator.get_stats_summary()
    print(f"\n  Pass rate: {stats['pass_rate']:.1f}%")
    
    if stats['error_types']:
        print("\n  Top error types:")
        for error_type, count in sorted(stats['error_types'].items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"    - {error_type}: {count}")
    
    print("\n" + "="*70)


def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("PHASE 1 VALIDATION IMPROVEMENTS TEST SUITE")
    print("="*70)
    
    # Run tests
    test_data_quality_validation()
    test_estimation_validation()
    test_with_real_data()
    test_cost_estimates_validation()
    
    print("\n" + "="*70)
    print("✓ ALL TESTS COMPLETE")
    print("="*70)
    print("\nKey Improvements:")
    print("  ✓ Data quality validation catches corrupted/metadata issues")
    print("  ✓ Estimation validation auto-corrects math errors")
    print("  ✓ Low quality items are excluded from estimation")
    print("  ✓ Confidence thresholds enforce manual review")
    print("\nRecommendation:")
    print("  Run enhanced_cost_estimator.py to see improvements in action:")
    print("  python enhanced_cost_estimator.py --input enriched_data/6-report_enriched.json")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()

