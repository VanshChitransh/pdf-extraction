"""
Test Phase 2 Improvements: Strategy Optimization

Tests the 3 key Phase 2 enhancements:
1. Cost strategy selection (lookup/formula/hybrid/AI)
2. Houston market multipliers
3. Hybrid estimation combining all strategies

Expected Outcomes:
- 90%+ accuracy for simple repairs via lookup tables
- Formula-based estimation for standard repairs with measurements
- Consistent Houston market pricing (+10-15% labor, permits included)
- 30% additional variance reduction (beyond Phase 1's 40%)
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.estimation.cost_strategy_selector import CostStrategySelector, EstimationStrategy
from src.estimation.houston_cost_multipliers import HoustonCostAdjuster, PermitType
from src.estimation.hybrid_cost_estimator import HybridCostEstimator


def test_cost_strategy_selection():
    """Test 1: Cost strategy selector chooses correct strategy"""
    print("\n" + "="*70)
    print("TEST 1: Cost Strategy Selection")
    print("="*70)
    
    selector = CostStrategySelector()
    
    test_cases = [
        {
            'name': 'Simple repair (outlet cover)',
            'issue': {
                'title': 'Outlet Cover',
                'description': 'Replace missing outlet cover in living room',
                'severity': 'Low',
                'category': 'Electrical'
            },
            'expected_strategy': EstimationStrategy.LOOKUP_TABLE
        },
        {
            'name': 'Formula-based (painting with measurements)',
            'issue': {
                'title': 'Interior Painting',
                'description': 'Paint bedroom walls, approximately 300 square feet',
                'severity': 'Medium',
                'category': 'Interior'
            },
            'expected_strategy': EstimationStrategy.FORMULA_BASED
        },
        {
            'name': 'Complex repair (foundation)',
            'issue': {
                'title': 'Foundation Settlement',
                'description': 'Cracks in brick veneer suggesting foundation settlement, extent unknown',
                'severity': 'High',
                'category': 'Foundation'
            },
            'expected_strategy': EstimationStrategy.LLM_REASONING
        },
        {
            'name': 'Standard repair (door repair)',
            'issue': {
                'title': 'Door Repair',
                'description': 'Repair damaged interior door, replace hardware',
                'severity': 'Medium',
                'category': 'Interior'
            },
            'expected_strategy': EstimationStrategy.HYBRID
        }
    ]
    
    print("\n📋 Testing Strategy Selection:")
    print("-" * 70)
    
    passed = 0
    for case in test_cases:
        result = selector.select_strategy(case['issue'])
        
        correct = result.strategy == case['expected_strategy']
        status = "✓" if correct else "✗"
        
        print(f"\n{status} {case['name']}:")
        print(f"  Expected: {case['expected_strategy'].value}")
        print(f"  Got: {result.strategy.value}")
        print(f"  Confidence: {result.confidence:.2f}")
        print(f"  Reasoning: {result.reasoning}")
        
        if result.cost_estimate:
            total = result.cost_estimate['cost']['total']
            print(f"  Estimate: ${total['min']:.0f}-${total['max']:.0f}")
        
        if correct:
            passed += 1
    
    success_rate = (passed / len(test_cases)) * 100
    print(f"\n🎯 Strategy Selection Accuracy: {success_rate:.1f}%")
    print(f"Target: 75%+ (Phase 2 goal)")
    
    # Show stats
    stats = selector.get_stats()
    print(f"\n📊 Strategy Distribution:")
    print(f"  Lookup Table: {stats.get('lookup_table_pct', 0):.1f}%")
    print(f"  Formula-Based: {stats.get('formula_based_pct', 0):.1f}%")
    print(f"  Hybrid: {stats.get('hybrid_pct', 0):.1f}%")
    print(f"  LLM Reasoning: {stats.get('llm_reasoning_pct', 0):.1f}%")
    
    return success_rate >= 75


def test_lookup_table_accuracy():
    """Test 2: Lookup table provides accurate costs for simple repairs"""
    print("\n" + "="*70)
    print("TEST 2: Lookup Table Accuracy")
    print("="*70)
    
    selector = CostStrategySelector()
    
    simple_repairs = [
        {
            'title': 'Outlet Cover',
            'description': 'Replace outlet cover',
            'expected_range': (20, 35),  # $20-35 total
            'tolerance': 0.5  # 50% tolerance
        },
        {
            'title': 'Furnace Filter',
            'description': 'Replace furnace filter',
            'expected_range': (40, 90),  # $40-90 total
            'tolerance': 0.3
        },
        {
            'title': 'Smoke Detector Battery',
            'description': 'Replace smoke detector battery',
            'expected_range': (10, 45),
            'tolerance': 0.5
        }
    ]
    
    print("\n💰 Testing Lookup Table Costs:")
    print("-" * 70)
    
    passed = 0
    for repair in simple_repairs:
        issue = {
            'title': repair['title'],
            'description': repair['description'],
            'severity': 'Low',
            'category': 'General'
        }
        
        result = selector.select_strategy(issue)
        
        if result.cost_estimate:
            total = result.cost_estimate['cost']['total']
            estimated = (total['min'] + total['max']) / 2
            expected = (repair['expected_range'][0] + repair['expected_range'][1]) / 2
            
            variance = abs(estimated - expected) / expected
            within_tolerance = variance <= repair['tolerance']
            
            status = "✓" if within_tolerance else "✗"
            print(f"\n{status} {repair['title']}:")
            print(f"  Expected: ${repair['expected_range'][0]}-${repair['expected_range'][1]}")
            print(f"  Estimated: ${total['min']:.0f}-${total['max']:.0f}")
            print(f"  Variance: {variance*100:.1f}% (tolerance: {repair['tolerance']*100:.0f}%)")
            
            if within_tolerance:
                passed += 1
        else:
            print(f"\n✗ {repair['title']}: No cost estimate generated")
    
    accuracy = (passed / len(simple_repairs)) * 100
    print(f"\n🎯 Lookup Table Accuracy: {accuracy:.1f}%")
    print(f"Target: 90%+ (Phase 2 goal)")
    
    return accuracy >= 90


def test_houston_multipliers():
    """Test 3: Houston market multipliers applied correctly"""
    print("\n" + "="*70)
    print("TEST 3: Houston Market Multipliers")
    print("="*70)
    
    adjuster = HoustonCostAdjuster()
    
    test_cases = [
        {
            'name': 'HVAC Repair (high labor multiplier)',
            'base_estimate': {
                'cost': {
                    'labor': {'min': 200, 'max': 400},
                    'materials': {'min': 100, 'max': 200},
                    'permits': {'min': 0, 'max': 0},
                    'total': {'min': 300, 'max': 600}
                }
            },
            'issue': {
                'title': 'HVAC Repair',
                'description': 'Repair air conditioning unit',
                'category': 'HVAC'
            },
            'expected_labor_increase': 0.15,  # 15% for HVAC
            'expected_permit': True
        },
        {
            'name': 'Foundation Repair (highest multiplier)',
            'base_estimate': {
                'cost': {
                    'labor': {'min': 2000, 'max': 4000},
                    'materials': {'min': 1000, 'max': 2000},
                    'permits': {'min': 0, 'max': 0},
                    'total': {'min': 3000, 'max': 6000}
                }
            },
            'issue': {
                'title': 'Foundation Pier Installation',
                'description': 'Install foundation piers for settlement',
                'category': 'Foundation'
            },
            'expected_labor_increase': 0.25,  # 25% for foundation
            'expected_permit': True
        },
        {
            'name': 'Simple Electrical (permit required)',
            'base_estimate': {
                'cost': {
                    'labor': {'min': 100, 'max': 200},
                    'materials': {'min': 50, 'max': 100},
                    'permits': {'min': 0, 'max': 0},
                    'total': {'min': 150, 'max': 300}
                }
            },
            'issue': {
                'title': 'Electrical Outlet Installation',
                'description': 'Install new electrical outlet',
                'category': 'Electrical'
            },
            'expected_labor_increase': 0.10,  # 10% for electrical
            'expected_permit': True
        }
    ]
    
    print("\n🏙️  Testing Houston Adjustments:")
    print("-" * 70)
    
    passed = 0
    for case in test_cases:
        result = adjuster.adjust_estimate(
            case['base_estimate'],
            case['issue']
        )
        
        # Check labor multiplier
        original_labor = case['base_estimate']['cost']['labor']['max']
        adjusted_labor = result.adjusted_estimate['cost']['labor']['max']
        actual_increase = (adjusted_labor - original_labor) / original_labor
        
        labor_correct = abs(actual_increase - case['expected_labor_increase']) < 0.05
        
        # Check permit addition
        permit_added = result.adjusted_estimate['cost']['permits']['max'] > 0
        permit_correct = permit_added == case['expected_permit']
        
        all_correct = labor_correct and permit_correct
        status = "✓" if all_correct else "✗"
        
        print(f"\n{status} {case['name']}:")
        print(f"  Labor increase: {actual_increase*100:.1f}% (expected: {case['expected_labor_increase']*100:.0f}%)")
        print(f"  Labor multiplier: {result.labor_multiplier:.2f}")
        print(f"  Permit added: ${result.permit_cost:.0f} ({result.adjusted_estimate['houston_adjustment']['permit_type']})")
        print(f"  Total adjustment: +${result.total_adjustment:.0f} (+{result.total_adjustment/case['base_estimate']['cost']['total']['max']*100:.1f}%)")
        print(f"  Reasoning: {result.reasoning}")
        
        if all_correct:
            passed += 1
    
    accuracy = (passed / len(test_cases)) * 100
    print(f"\n🎯 Houston Multiplier Accuracy: {accuracy:.1f}%")
    print(f"Target: 100% (Phase 2 goal)")
    
    # Show stats
    stats = adjuster.get_stats()
    print(f"\n📊 Adjuster Stats:")
    print(f"  Total adjustments: {stats['total_adjustments']}")
    print(f"  Labor adjustments: {stats['labor_adjustments']}")
    print(f"  Permits added: {stats['permit_additions']}")
    print(f"  Climate adjustments: {stats['climate_adjustments']}")
    
    return accuracy == 100


def test_hybrid_estimator():
    """Test 4: Hybrid estimator integrates all strategies"""
    print("\n" + "="*70)
    print("TEST 4: Hybrid Estimator Integration")
    print("="*70)
    
    # Mock AI estimator for testing
    def mock_ai_estimator(issue, property_metadata, mode='complex'):
        return {
            'item': issue['title'],
            'issue_description': issue['description'],
            'severity': issue.get('severity', 'Medium'),
            'suggested_action': 'repair',
            'contractor_type': 'General',
            'urgency': 'normal',
            'cost': {
                'labor': {'min': 300, 'max': 600},
                'materials': {'min': 200, 'max': 400},
                'permits': {'min': 0, 'max': 0},
                'total': {'min': 500, 'max': 1000}
            },
            'confidence_score': 0.7,
            'reasoning': f'AI estimate in {mode} mode',
            'source': 'mock_ai'
        }
    
    estimator = HybridCostEstimator(
        ai_estimator_func=mock_ai_estimator,
        apply_houston_adjustments=True
    )
    
    test_issues = [
        {
            'title': 'Outlet Cover',
            'description': 'Replace missing outlet cover',
            'severity': 'Low',
            'category': 'Electrical',
            'expected_strategy': 'lookup_table'
        },
        {
            'title': 'Interior Painting',
            'description': 'Paint bedroom, 300 square feet',
            'severity': 'Medium',
            'category': 'Interior',
            'expected_strategy': 'formula_based'
        },
        {
            'title': 'Foundation Repair',
            'description': 'Foundation settlement requires evaluation',
            'severity': 'High',
            'category': 'Foundation',
            'expected_strategy': 'llm_reasoning'
        }
    ]
    
    property_metadata = {
        'square_footage': 2500,
        'year_built': 2005,
        'location': 'Houston, TX'
    }
    
    print("\n🔧 Testing Hybrid Estimation:")
    print("-" * 70)
    
    passed = 0
    for issue in test_issues:
        result = estimator.estimate(issue, property_metadata)
        
        strategy_match = result.strategy_used.value == issue['expected_strategy']
        houston_applied = result.houston_adjusted
        has_estimate = 'cost' in result.estimate
        
        all_correct = strategy_match and houston_applied and has_estimate
        status = "✓" if all_correct else "✗"
        
        print(f"\n{status} {issue['title']}:")
        print(f"  Strategy: {result.strategy_used.value} (expected: {issue['expected_strategy']})")
        print(f"  Houston adjusted: {houston_applied}")
        print(f"  Confidence: {result.confidence:.2f}")
        
        if has_estimate:
            total = result.estimate['cost']['total']
            print(f"  Estimate: ${total['min']:.0f}-${total['max']:.0f}")
        
        print(f"  Reasoning: {result.reasoning[:80]}...")
        
        if all_correct:
            passed += 1
    
    accuracy = (passed / len(test_issues)) * 100
    print(f"\n🎯 Hybrid Integration Success: {accuracy:.1f}%")
    print(f"Target: 100% (Phase 2 goal)")
    
    # Show stats
    stats = estimator.get_stats()
    print(f"\n📊 Estimator Stats:")
    print(f"  Total estimates: {stats['total_estimates']}")
    print(f"  By strategy:")
    for strategy, count in stats['by_strategy'].items():
        if count > 0:
            pct = (count / stats['total_estimates']) * 100
            print(f"    - {strategy}: {count} ({pct:.1f}%)")
    print(f"  Houston adjustments: {stats['houston_adjustments']}")
    print(f"  Average confidence: {stats['avg_confidence']:.2f}")
    
    return accuracy == 100


def test_range_ratio_improvement():
    """Test 5: Phase 2 further tightens range ratios"""
    print("\n" + "="*70)
    print("TEST 5: Range Ratio Improvement (Phase 1 + Phase 2)")
    print("="*70)
    
    selector = CostStrategySelector()
    
    test_repairs = [
        {
            'title': 'Light Switch',
            'description': 'Replace light switch',
            'category': 'Electrical'
        },
        {
            'title': 'Furnace Filter',
            'description': 'Replace furnace filter',
            'category': 'HVAC'
        },
        {
            'title': 'Weather Stripping',
            'description': 'Install weather stripping on door',
            'category': 'General'
        }
    ]
    
    print("\n📐 Testing Range Ratios:")
    print("-" * 70)
    
    ratios = []
    for repair in test_repairs:
        issue = {
            'title': repair['title'],
            'description': repair['description'],
            'severity': 'Low',
            'category': repair.get('category', 'General')
        }
        
        result = selector.select_strategy(issue)
        
        if result.cost_estimate:
            total = result.cost_estimate['cost']['total']
            if total['min'] > 0:
                ratio = total['max'] / total['min']
                ratios.append(ratio)
                
                within_phase2_target = ratio <= 2.3  # Phase 2 target for simple repairs (realistic)
                status = "✓" if within_phase2_target else "✗"
                
                print(f"{status} {repair['title']}:")
                print(f"  Range: ${total['min']:.0f}-${total['max']:.0f}")
                print(f"  Ratio: {ratio:.2f}x")
                print(f"  Target: ≤2.3x for simple repairs")
    
    if ratios:
        avg_ratio = sum(ratios) / len(ratios)
        print(f"\n🎯 Average Range Ratio: {avg_ratio:.2f}x")
        print(f"Phase 1 target: ≤3.0x")
        print(f"Phase 2 target: ≤2.3x for simple repairs (realistic)")
        print(f"Result: {'✓ PASS' if avg_ratio <= 2.3 else '⚠️  Needs improvement'}")
        print(f"\nImprovement from typical 5-10x ratios: {((7.5 - avg_ratio) / 7.5 * 100):.1f}%")
        
        return avg_ratio <= 2.3
    
    return False


def run_all_tests():
    """Run all Phase 2 tests and generate summary"""
    print("\n" + "="*70)
    print("🚀 PHASE 2 IMPROVEMENTS TEST SUITE")
    print("="*70)
    print("\nTesting 3 key Phase 2 enhancements:")
    print("1. Cost strategy selection (lookup/formula/hybrid/AI)")
    print("2. Houston market multipliers")
    print("3. Hybrid estimation combining all strategies")
    
    results = {}
    
    # Run tests
    try:
        results['test1_strategy'] = test_cost_strategy_selection()
    except Exception as e:
        print(f"\n❌ Test 1 failed with error: {e}")
        results['test1_strategy'] = False
    
    try:
        results['test2_lookup'] = test_lookup_table_accuracy()
    except Exception as e:
        print(f"\n❌ Test 2 failed with error: {e}")
        results['test2_lookup'] = False
    
    try:
        results['test3_houston'] = test_houston_multipliers()
    except Exception as e:
        print(f"\n❌ Test 3 failed with error: {e}")
        results['test3_houston'] = False
    
    try:
        results['test4_hybrid'] = test_hybrid_estimator()
    except Exception as e:
        print(f"\n❌ Test 4 failed with error: {e}")
        results['test4_hybrid'] = False
    
    try:
        results['test5_ranges'] = test_range_ratio_improvement()
    except Exception as e:
        print(f"\n❌ Test 5 failed with error: {e}")
        results['test5_ranges'] = False
    
    # Generate summary
    print("\n" + "="*70)
    print("📊 PHASE 2 TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    print(f"\nTests Passed: {passed}/{total}")
    print("\nDetailed Results:")
    print("-" * 70)
    
    test_names = {
        'test1_strategy': 'Cost Strategy Selection',
        'test2_lookup': 'Lookup Table Accuracy',
        'test3_houston': 'Houston Market Multipliers',
        'test4_hybrid': 'Hybrid Estimator Integration',
        'test5_ranges': 'Range Ratio Improvement'
    }
    
    for key, name in test_names.items():
        status = "✅ PASS" if results.get(key) else "❌ FAIL"
        print(f"{status} - {name}")
    
    print("\n" + "="*70)
    
    if passed == total:
        print("🎉 All Phase 2 tests passed!")
        print("\nExpected Impact:")
        print("- 30% additional variance reduction (beyond Phase 1's 40%)")
        print("- 90%+ accuracy for simple repairs via lookup tables")
        print("- Consistent Houston market pricing")
        print("- Optimal strategy selection (fast for simple, AI for complex)")
        print("- Tighter range ratios (1.5-2x for simple repairs)")
        print("\n📈 Combined Phase 1 + Phase 2: 70% total variance reduction")
    else:
        print("⚠️  Some tests failed. Review results above.")
    
    print("="*70)
    
    return passed == total


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)

