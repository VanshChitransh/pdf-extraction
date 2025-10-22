"""
Test Phase 3 Improvements: Learning Loop

Tests the Phase 3 learning and calibration system:
1. Calibration database storage and retrieval
2. Feedback loop calculation and application
3. Variance analysis and trend tracking
4. Learning effectiveness measurement

Expected Outcomes:
- Accurate storage of estimate vs actual cost pairs
- Calibration factors calculated from historical data
- Estimates adjusted based on calibration
- 20% additional variance reduction (beyond Phase 1+2's 70%)
"""

import sys
import tempfile
from pathlib import Path
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.learning.calibration_database import CalibrationDatabase, EstimateRecord
from src.learning.feedback_loop import FeedbackLoop
from src.learning.variance_analyzer import VarianceAnalyzer


def test_calibration_database():
    """Test 1: Calibration database storage and retrieval"""
    print("\n" + "="*70)
    print("TEST 1: Calibration Database")
    print("="*70)
    
    # Use temporary database
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        db_path = f.name
    
    db = CalibrationDatabase(db_path)
    
    # Test estimate storage
    test_estimates = [
        {
            'estimate': {
                'cost': {
                    'labor': {'min': 200, 'max': 400},
                    'materials': {'min': 100, 'max': 200},
                    'total': {'min': 300, 'max': 600}
                },
                'estimation_strategy': 'lookup_table',
                'confidence_score': 0.9
            },
            'issue': {
                'id': 'test_1',
                'title': 'Outlet Cover Replacement',
                'description': 'Replace outlet cover',
                'category': 'Electrical',
                'severity': 'Low'
            },
            'actual_cost': 35,
            'contractor': 'ABC Electric'
        },
        {
            'estimate': {
                'cost': {
                    'labor': {'min': 500, 'max': 1000},
                    'materials': {'min': 300, 'max': 600},
                    'total': {'min': 800, 'max': 1600}
                },
                'estimation_strategy': 'llm_reasoning',
                'confidence_score': 0.65
            },
            'issue': {
                'id': 'test_2',
                'title': 'HVAC Repair',
                'description': 'Repair AC unit',
                'category': 'HVAC',
                'severity': 'High'
            },
            'actual_cost': 1400,
            'contractor': 'Cool Air HVAC'
        },
        {
            'estimate': {
                'cost': {
                    'labor': {'min': 150, 'max': 300},
                    'materials': {'min': 50, 'max': 100},
                    'total': {'min': 200, 'max': 400}
                },
                'estimation_strategy': 'formula_based',
                'confidence_score': 0.8
            },
            'issue': {
                'id': 'test_3',
                'title': 'Door Repair',
                'description': 'Fix interior door',
                'category': 'Interior',
                'severity': 'Medium'
            },
            'actual_cost': 280,
            'contractor': 'Home Handyman'
        }
    ]
    
    print("\n📦 Testing Data Storage:")
    print("-" * 70)
    
    record_ids = []
    for test_case in test_estimates:
        record_id = db.store_estimate(
            test_case['estimate'],
            test_case['issue']
        )
        record_ids.append(record_id)
        print(f"✓ Stored estimate: {test_case['issue']['title']}")
    
    print(f"\n📊 Database Stats:")
    stats = db.get_stats()
    print(f"  Total estimates: {stats['total_estimates']}")
    print(f"  Estimates with actuals: {stats['estimates_with_actuals']}")
    
    # Add actual costs
    print("\n💰 Adding Actual Costs:")
    print("-" * 70)
    
    for i, test_case in enumerate(test_estimates):
        success = db.add_actual_cost(
            record_ids[i],
            test_case['actual_cost'],
            test_case['contractor']
        )
        
        record = db.records[record_ids[i]]
        status = "✓" if success else "✗"
        print(f"{status} {test_case['issue']['title']}:")
        print(f"  Estimated: ${record.estimated_min:.0f}-${record.estimated_max:.0f}")
        print(f"  Actual: ${record.actual_cost:.0f}")
        print(f"  Variance: {record.variance_pct:+.1f}%")
        print(f"  Within range: {'Yes' if record.within_range else 'No'}")
    
    # Test calibration factor calculation
    print("\n🎯 Testing Calibration Factors:")
    print("-" * 70)
    
    factor = db.get_calibration_factor('Electrical')
    print(f"Electrical calibration: {factor:.3f}x" if factor else "Electrical: Insufficient data")
    
    factor = db.get_calibration_factor('HVAC')
    print(f"HVAC calibration: {factor:.3f}x" if factor else "HVAC: Insufficient data")
    
    # Calculate success
    stats = db.get_stats()
    success = (
        stats['total_estimates'] == 3 and
        stats['estimates_with_actuals'] == 3 and
        len(db.records) == 3
    )
    
    print(f"\n🎯 Database Test: {'✅ PASS' if success else '❌ FAIL'}")
    
    # Cleanup
    Path(db_path).unlink(missing_ok=True)
    
    return success


def test_feedback_loop():
    """Test 2: Feedback loop calculates and applies calibration"""
    print("\n" + "="*70)
    print("TEST 2: Feedback Loop")
    print("="*70)
    
    # Create database with sample data
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        db_path = f.name
    
    db = CalibrationDatabase(db_path)
    
    # Add several estimates with consistent underestimation pattern
    # Simulate historical data showing estimates are 15% too low for HVAC
    # Need 8+ samples for high confidence calibration
    hvac_estimates = [
        {'estimated_mid': 1000, 'actual': 1150},  # +15%
        {'estimated_mid': 2000, 'actual': 2300},  # +15%
        {'estimated_mid': 1500, 'actual': 1725},  # +15%
        {'estimated_mid': 800, 'actual': 920},     # +15%
        {'estimated_mid': 1200, 'actual': 1380},  # +15%
        {'estimated_mid': 900, 'actual': 1035},    # +15%
        {'estimated_mid': 1800, 'actual': 2070},  # +15%
        {'estimated_mid': 1100, 'actual': 1265},  # +15%
    ]
    
    print("\n📈 Simulating Historical HVAC Estimates:")
    print("-" * 70)
    
    for i, data in enumerate(hvac_estimates):
        mid = data['estimated_mid']
        estimate = {
            'cost': {
                'labor': {'min': mid * 0.6, 'max': mid * 0.6},
                'materials': {'min': mid * 0.4, 'max': mid * 0.4},
                'total': {'min': mid * 0.85, 'max': mid * 1.15}
            },
            'estimation_strategy': 'llm_reasoning',
            'confidence_score': 0.7
        }
        issue = {
            'id': f'hvac_{i}',
            'title': 'HVAC Repair',
            'description': 'HVAC system repair',
            'category': 'HVAC',
            'severity': 'Medium'
        }
        
        record_id = db.store_estimate(estimate, issue)
        db.add_actual_cost(record_id, data['actual'], 'Test Contractor')
        
        variance = ((data['actual'] - mid) / mid) * 100
        print(f"  Estimate {i+1}: ${mid:.0f} → ${data['actual']:.0f} ({variance:+.1f}%)")
    
    # Initialize feedback loop
    feedback = FeedbackLoop(db, min_samples_for_adjustment=3)
    
    # Test calibration factor calculation
    print("\n🔧 Testing Calibration Calculation:")
    print("-" * 70)
    
    new_issue = {
        'category': 'HVAC',
        'severity': 'Medium',
        'title': 'New HVAC Repair'
    }
    
    new_estimate = {
        'cost': {
            'labor': {'min': 600, 'max': 1200},
            'materials': {'min': 400, 'max': 800},
            'total': {'min': 1000, 'max': 2000}
        },
        'estimation_strategy': 'llm_reasoning',
        'confidence_score': 0.7
    }
    
    # Apply calibration
    adjusted_estimate = feedback.adjust_estimate(new_estimate, new_issue)
    
    original_mid = (new_estimate['cost']['total']['min'] + new_estimate['cost']['total']['max']) / 2
    adjusted_mid = (adjusted_estimate['cost']['total']['min'] + adjusted_estimate['cost']['total']['max']) / 2
    
    print(f"Original estimate: ${new_estimate['cost']['total']['min']:.0f}-${new_estimate['cost']['total']['max']:.0f}")
    print(f"Adjusted estimate: ${adjusted_estimate['cost']['total']['min']:.0f}-${adjusted_estimate['cost']['total']['max']:.0f}")
    print(f"Calibration factor: {adjusted_mid / original_mid:.3f}x")
    print(f"Calibration status: {adjusted_estimate.get('calibration', {}).get('status')}")
    print(f"Sample count: {adjusted_estimate.get('calibration', {}).get('sample_count')}")
    
    # Test should show calibration was applied
    calibration_applied = adjusted_estimate.get('calibration', {}).get('status') == 'applied'
    factor_reasonable = 1.10 <= adjusted_mid / original_mid <= 1.20  # Should be ~1.15
    
    print(f"\n🎯 Feedback Loop Test: {'✅ PASS' if (calibration_applied and factor_reasonable) else '❌ FAIL'}")
    
    # Cleanup
    Path(db_path).unlink(missing_ok=True)
    
    return calibration_applied and factor_reasonable


def test_variance_analysis():
    """Test 3: Variance analyzer provides insights"""
    print("\n" + "="*70)
    print("TEST 3: Variance Analysis")
    print("="*70)
    
    # Create database with varied data
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        db_path = f.name
    
    db = CalibrationDatabase(db_path)
    
    # Add estimates across different categories with varying accuracy
    test_data = [
        # Electrical - high accuracy
        {'category': 'Electrical', 'estimated_mid': 100, 'actual': 105, 'confidence': 0.9},
        {'category': 'Electrical', 'estimated_mid': 200, 'actual': 195, 'confidence': 0.85},
        {'category': 'Electrical', 'estimated_mid': 150, 'actual': 160, 'confidence': 0.88},
        
        # HVAC - moderate variance
        {'category': 'HVAC', 'estimated_mid': 1000, 'actual': 1200, 'confidence': 0.65},
        {'category': 'HVAC', 'estimated_mid': 1500, 'actual': 1650, 'confidence': 0.70},
        {'category': 'HVAC', 'estimated_mid': 2000, 'actual': 2100, 'confidence': 0.60},
        
        # Foundation - high variance
        {'category': 'Foundation', 'estimated_mid': 5000, 'actual': 7000, 'confidence': 0.45},
        {'category': 'Foundation', 'estimated_mid': 8000, 'actual': 10500, 'confidence': 0.50},
        {'category': 'Foundation', 'estimated_mid': 6000, 'actual': 8200, 'confidence': 0.40},
    ]
    
    print("\n📊 Adding Test Data:")
    print("-" * 70)
    
    for i, data in enumerate(test_data):
        mid = data['estimated_mid']
        estimate = {
            'cost': {
                'total': {'min': mid * 0.85, 'max': mid * 1.15}
            },
            'estimation_strategy': 'llm_reasoning',
            'confidence_score': data['confidence']
        }
        issue = {
            'id': f'test_{i}',
            'title': f"{data['category']} Repair",
            'description': f"{data['category']} work",
            'category': data['category'],
            'severity': 'Medium'
        }
        
        record_id = db.store_estimate(estimate, issue)
        db.add_actual_cost(record_id, data['actual'], 'Test Contractor')
    
    print(f"✓ Added {len(test_data)} estimates with actuals")
    
    # Create analyzer
    analyzer = VarianceAnalyzer(db)
    
    # Test overall metrics
    print("\n📈 Overall Metrics:")
    print("-" * 70)
    
    metrics = analyzer.get_overall_metrics()
    print(f"  Sample count: {metrics.sample_count}")
    print(f"  Avg variance: {metrics.avg_variance_pct:.1f}%")
    print(f"  Within range: {metrics.within_range_pct:.1f}%")
    print(f"  Accuracy score: {metrics.accuracy_score:.1f}/100")
    
    # Test category breakdown
    print("\n📊 By Category:")
    print("-" * 70)
    
    by_category = analyzer.get_metrics_by_category()
    for category, cat_metrics in by_category.items():
        print(f"  {category}:")
        print(f"    Samples: {cat_metrics.sample_count}")
        print(f"    Avg variance: {cat_metrics.avg_variance_pct:.1f}%")
        print(f"    Accuracy: {cat_metrics.accuracy_score:.1f}/100")
    
    # Test problem area identification
    print("\n⚠️  Problem Areas:")
    print("-" * 70)
    
    problems = analyzer.identify_problem_areas(variance_threshold=15.0)
    for problem in problems:
        print(f"  {problem['type'].upper()}: {problem['name']}")
        print(f"    Variance: {problem['avg_variance_pct']:.1f}%")
        print(f"    Severity: {problem['severity']}")
    
    # Validate results
    success = (
        metrics.sample_count == 9 and
        len(by_category) == 3 and
        len(problems) > 0 and
        'Foundation' in [p['name'] for p in problems]  # Foundation should be flagged
    )
    
    print(f"\n🎯 Variance Analysis Test: {'✅ PASS' if success else '❌ FAIL'}")
    
    # Cleanup
    Path(db_path).unlink(missing_ok=True)
    
    return success


def test_learning_effectiveness():
    """Test 4: System improves over time with learning"""
    print("\n" + "="*70)
    print("TEST 4: Learning Effectiveness")
    print("="*70)
    
    # Create database
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        db_path = f.name
    
    db = CalibrationDatabase(db_path)
    feedback = FeedbackLoop(db, min_samples_for_adjustment=3)
    
    # Simulate two time periods with improving accuracy
    print("\n📅 Period 1 (Early - No Calibration):")
    print("-" * 70)
    
    early_estimates = []
    base_time = datetime.now() - timedelta(days=60)
    
    for i in range(10):
        # Early estimates consistently 20% too low
        mid = 1000 + (i * 100)
        actual = mid * 1.20  # 20% underestimation
        
        estimate = {
            'cost': {
                'total': {'min': mid * 0.85, 'max': mid * 1.15}
            },
            'estimation_strategy': 'llm_reasoning',
            'confidence_score': 0.7
        }
        issue = {
            'id': f'early_{i}',
            'title': 'HVAC Repair',
            'description': 'Early estimate',
            'category': 'HVAC',
            'severity': 'Medium'
        }
        
        record_id = db.store_estimate(estimate, issue)
        record = db.records[record_id]
        # Manually set timestamp to make it "early"
        record.timestamp = (base_time + timedelta(days=i)).isoformat()
        
        db.add_actual_cost(record_id, actual, 'Test Contractor')
        early_estimates.append(record)
    
    # Calculate early variance
    early_variances = [abs(r.variance_pct) for r in early_estimates]
    early_avg = sum(early_variances) / len(early_variances)
    
    print(f"  Avg variance: {early_avg:.1f}%")
    print(f"  Estimates consistently {early_avg:.0f}% off")
    
    # Period 2: Apply calibration
    print("\n📅 Period 2 (Recent - With Calibration):")
    print("-" * 70)
    
    recent_estimates = []
    
    for i in range(10):
        mid = 1000 + (i * 100)
        actual = mid * 1.20  # Same true cost pattern
        
        # Base estimate (before calibration)
        base_estimate = {
            'cost': {
                'total': {'min': mid * 0.85, 'max': mid * 1.15}
            },
            'estimation_strategy': 'llm_reasoning',
            'confidence_score': 0.7
        }
        issue = {
            'id': f'recent_{i}',
            'title': 'HVAC Repair',
            'description': 'Recent estimate',
            'category': 'HVAC',
            'severity': 'Medium'
        }
        
        # Apply calibration
        adjusted_estimate = feedback.adjust_estimate(base_estimate, issue)
        
        # Store adjusted estimate
        record_id = db.store_estimate(adjusted_estimate, issue)
        record = db.records[record_id]
        record.timestamp = (datetime.now() - timedelta(days=i)).isoformat()
        
        db.add_actual_cost(record_id, actual, 'Test Contractor')
        recent_estimates.append(record)
    
    # Calculate recent variance
    recent_variances = [abs(r.variance_pct) for r in recent_estimates]
    recent_avg = sum(recent_variances) / len(recent_variances)
    
    print(f"  Avg variance: {recent_avg:.1f}%")
    print(f"  Improvement: {early_avg - recent_avg:.1f} percentage points")
    
    # Calculate improvement
    improvement_pct = ((early_avg - recent_avg) / early_avg) * 100
    
    print(f"\n📈 Learning Results:")
    print("-" * 70)
    print(f"  Early period variance: {early_avg:.1f}%")
    print(f"  Recent period variance: {recent_avg:.1f}%")
    print(f"  Improvement: {improvement_pct:.1f}%")
    print(f"  Target: 20%+ improvement")
    
    # Success if variance reduced by 20%+
    learning_effective = improvement_pct >= 20
    
    print(f"\n🎯 Learning Effectiveness Test: {'✅ PASS' if learning_effective else '❌ FAIL'}")
    
    # Cleanup
    Path(db_path).unlink(missing_ok=True)
    
    return learning_effective


def run_all_tests():
    """Run all Phase 3 tests and generate summary"""
    print("\n" + "="*70)
    print("🚀 PHASE 3 LEARNING LOOP TEST SUITE")
    print("="*70)
    print("\nTesting 4 key Phase 3 enhancements:")
    print("1. Calibration database storage")
    print("2. Feedback loop calculation")
    print("3. Variance analysis")
    print("4. Learning effectiveness")
    
    results = {}
    
    # Run tests
    try:
        results['test1_database'] = test_calibration_database()
    except Exception as e:
        print(f"\n❌ Test 1 failed with error: {e}")
        import traceback
        traceback.print_exc()
        results['test1_database'] = False
    
    try:
        results['test2_feedback'] = test_feedback_loop()
    except Exception as e:
        print(f"\n❌ Test 2 failed with error: {e}")
        import traceback
        traceback.print_exc()
        results['test2_feedback'] = False
    
    try:
        results['test3_analysis'] = test_variance_analysis()
    except Exception as e:
        print(f"\n❌ Test 3 failed with error: {e}")
        import traceback
        traceback.print_exc()
        results['test3_analysis'] = False
    
    try:
        results['test4_learning'] = test_learning_effectiveness()
    except Exception as e:
        print(f"\n❌ Test 4 failed with error: {e}")
        import traceback
        traceback.print_exc()
        results['test4_learning'] = False
    
    # Generate summary
    print("\n" + "="*70)
    print("📊 PHASE 3 TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    print(f"\nTests Passed: {passed}/{total}")
    print("\nDetailed Results:")
    print("-" * 70)
    
    test_names = {
        'test1_database': 'Calibration Database',
        'test2_feedback': 'Feedback Loop',
        'test3_analysis': 'Variance Analysis',
        'test4_learning': 'Learning Effectiveness'
    }
    
    for key, name in test_names.items():
        status = "✅ PASS" if results.get(key) else "❌ FAIL"
        print(f"{status} - {name}")
    
    print("\n" + "="*70)
    
    if passed == total:
        print("🎉 All Phase 3 tests passed!")
        print("\nExpected Impact:")
        print("- 20% additional variance reduction (beyond Phase 1+2's 70%)")
        print("- Self-improving system that learns from actual quotes")
        print("- Calibration factors applied automatically")
        print("- Variance trends tracked over time")
        print("\n📈 Combined Phase 1+2+3: 90% total variance reduction")
        print("   (vs baseline 5-10x ranges down to 1.5-2x ranges)")
    else:
        print("⚠️  Some tests failed. Review results above.")
    
    print("="*70)
    
    return passed == total


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)

