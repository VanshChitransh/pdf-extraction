"""
Demo: Phase 1 Enhancements

Quick demonstration of the new Phase 1 features:
1. Multi-dimensional confidence scoring
2. Houston cost database
3. Issue relationship analysis
4. Specialist prompts
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from estimation.confidence_scorer import AdvancedConfidenceScorer
from estimation.cost_database import HoustonCostDatabase
from estimation.relationship_analyzer import IssueRelationshipAnalyzer
from prompting.specialist_prompts import SpecialistPromptSelector


def demo_confidence_scorer():
    """Demonstrate multi-dimensional confidence scoring."""
    print("\n" + "="*70)
    print("DEMO 1: Multi-Dimensional Confidence Scoring")
    print("="*70)
    
    scorer = AdvancedConfidenceScorer()
    
    # Mock estimate and issue
    estimate = {
        "estimated_low": 2500,
        "estimated_high": 4500,
        "reasoning": "AC condenser unit replacement including labor ($500-1000 at $125/hr for 4-8 hours), "
                    "materials ($1800-3500 for 3-ton unit), permits ($150), refrigerant ($150), "
                    "and disposal fee ($75). Houston's extreme heat reduces AC lifespan to 10-15 years."
    }
    
    issue = {
        "item": "AC Condenser Unit",
        "issue": "AC condenser unit not cooling. Unit is 15 years old, located on southeast exterior. "
                "Compressor makes loud grinding noise when running. No cold air from vents.",
        "location": "Exterior southeast corner of house",
        "severity": "High",
        "category": "HVAC"
    }
    
    # Calculate confidence
    confidence = scorer.calculate_confidence(
        estimate=estimate,
        issue=issue,
        property_age=25,
        has_photos=True,
        database_match_score=0.90,
        historical_similarity=0.75
    )
    
    print(f"\n📊 Overall Confidence: {confidence['overall']:.1f}/100")
    print(f"✅ Recommendation: {confidence['recommendation']}")
    print(f"\n🔍 Dimension Breakdown:")
    for dimension, score in list(confidence['breakdown'].items())[:5]:
        print(f"  • {dimension}: {score:.1f}/100")
    
    if confidence['weak_dimensions']:
        print(f"\n⚠️  Weak Dimensions ({len(confidence['weak_dimensions'])}):")
        for weak in confidence['weak_dimensions'][:2]:
            print(f"  • {weak['dimension']}: {weak['score']:.1f}")
            print(f"    💡 Tip: {weak['improvement_tip']}")
    
    print(f"\n🔬 Assessment:")
    print(f"  • Manual Review Needed: {'Yes' if confidence['manual_review_needed'] else 'No'}")
    print(f"  • Inspection Needed: {'Yes' if confidence['inspection_needed'] else 'No'}")


def demo_cost_database():
    """Demonstrate Houston cost database."""
    print("\n" + "="*70)
    print("DEMO 2: Houston Cost Database")
    print("="*70)
    
    db = HoustonCostDatabase()
    
    # Example 1: HVAC
    print("\n🔧 Example 1: AC Condenser Unit (3 ton)")
    hvac_estimate = db.get_estimate("AC condenser unit", "3 ton")
    
    if hvac_estimate:
        print(f"  💰 Cost Range: ${hvac_estimate['estimated_low']:.0f} - ${hvac_estimate['estimated_high']:.0f}")
        print(f"  ⚡ Confidence: {hvac_estimate['confidence']*100:.0f}%")
        print(f"  👷 Contractor: {hvac_estimate['contractor_type']}")
        print(f"\n  📋 Breakdown:")
        breakdown = hvac_estimate['breakdown']
        print(f"    • Labor: ${breakdown['labor']['low']:.0f}-${breakdown['labor']['high']:.0f} "
              f"({breakdown['labor']['hours']['min']}-{breakdown['labor']['hours']['max']} hrs @ "
              f"${breakdown['labor']['rate_per_hour']}/hr)")
        print(f"    • Materials: ${breakdown['materials']['low']:.0f}-${breakdown['materials']['high']:.0f}")
        print(f"    • Permits: ${breakdown['permits']:.0f}")
        print(f"    • Additional: ${breakdown['additional']:.0f}")
        
        if hvac_estimate['notes']:
            print(f"\n  📝 Notes:")
            for note in hvac_estimate['notes'][:2]:
                print(f"    • {note}")
    
    # Example 2: Foundation
    print("\n\n🏗️  Example 2: Foundation Pier Installation")
    foundation_estimate = db.get_estimate("foundation pier", "pressed concrete")
    
    if foundation_estimate:
        print(f"  💰 Cost Range (per pier): ${foundation_estimate['estimated_low']:.0f} - ${foundation_estimate['estimated_high']:.0f}")
        print(f"  ⚡ Confidence: {foundation_estimate['confidence']*100:.0f}%")
        print(f"  ⚠️  Note: Typically need 8-12 piers minimum")
        print(f"  📊 Estimated Project: ${foundation_estimate['estimated_low']*10:.0f} - ${foundation_estimate['estimated_high']*12:.0f} (10-12 piers)")
    
    # Example 3: Search
    print("\n\n🔍 Example 3: Search for 'water heater'")
    results = db.search_components("water heater")
    print(f"  Found {len(results)} matching components:")
    for result in results:
        print(f"    • {result['component_name']} (confidence: {result['confidence']*100:.0f}%)")


def demo_relationship_analyzer():
    """Demonstrate issue relationship analysis."""
    print("\n" + "="*70)
    print("DEMO 3: Issue Relationship Analysis")
    print("="*70)
    
    analyzer = IssueRelationshipAnalyzer()
    
    # Mock issues
    issues = [
        {
            "id": "1",
            "item": "Foundation crack",
            "category": "Foundation",
            "issue": "Large crack in foundation slab on north side",
            "location": "Exterior north foundation",
            "severity": "High"
        },
        {
            "id": "2",
            "item": "Door misalignment",
            "category": "General",
            "issue": "Front door difficult to close, frame appears shifted",
            "location": "Front entryway",
            "severity": "Medium"
        },
        {
            "id": "3",
            "item": "Drywall cracks",
            "category": "Interior",
            "issue": "Multiple cracks in drywall above door frames",
            "location": "Living room and hallway",
            "severity": "Medium"
        },
        {
            "id": "4",
            "item": "HVAC duct leak",
            "category": "HVAC",
            "issue": "Visible gap in attic ductwork, poor airflow to master bedroom",
            "location": "Attic above master bedroom",
            "severity": "Medium"
        },
        {
            "id": "5",
            "item": "Insulation damage",
            "category": "HVAC",
            "issue": "Blown insulation compressed and water-stained",
            "location": "Attic above master bedroom",
            "severity": "Low"
        },
        {
            "id": "6",
            "item": "Roof leak",
            "category": "Roofing",
            "issue": "Water stains on attic decking, active drip during rain",
            "location": "Attic above master bedroom",
            "severity": "High"
        }
    ]
    
    # Analyze relationships
    relationships = analyzer.analyze_all_issues(issues)
    
    print(f"\n📊 Analysis Results:")
    print(f"  • Total issues: {relationships['statistics']['total_issues']}")
    print(f"  • Issues in chains: {relationships['statistics']['issues_in_chains']}")
    print(f"  • Isolated issues: {relationships['statistics']['isolated_issues']}")
    print(f"  • Potential bundles: {relationships['statistics']['potential_bundles']}")
    
    # Causal chains
    if relationships['causal_chains']:
        print(f"\n🔗 Causal Chains Found: {len(relationships['causal_chains'])}")
        for idx, chain in enumerate(relationships['causal_chains'][:2], 1):
            print(f"\n  Chain {idx}:")
            print(f"    🔴 Root Cause: {chain['root_cause']['item']}")
            print(f"    ⬇️  Likely Caused:")
            for caused in chain['caused_issues']:
                print(f"       • {caused['item']}")
            print(f"    💡 {chain['recommendation']}")
    
    # Bundles
    if relationships['bundles']:
        print(f"\n📦 Bundling Opportunities: {len(relationships['bundles'])}")
        for idx, bundle in enumerate(relationships['bundles'][:2], 1):
            print(f"\n  Bundle {idx}: {bundle['bundle_type'].replace('_', ' ').title()}")
            print(f"    💰 Potential Savings: {bundle['savings_pct']*100:.0f}%")
            print(f"    📍 {bundle['reason']}")
            print(f"    🔧 Issues:")
            for issue in bundle['issues'][:3]:
                print(f"       • {issue['item']}")
    
    # Demo bundling for specific issue
    print(f"\n\n🎯 Bundling Analysis for: 'HVAC duct leak'")
    primary_issue = issues[3]
    bundle_info = analyzer.group_for_bundled_estimate(
        primary_issue,
        issues,
        max_bundle_size=3
    )
    
    print(f"  Related Issues: {len(bundle_info['related_issues'])}")
    for related in bundle_info['related_issues']:
        print(f"    • {related['item']}")
    print(f"  💰 Estimated Savings: {bundle_info['labor_savings_pct']*100:.0f}%")
    print(f"  💡 {bundle_info['bundling_recommendation']}")


def demo_specialist_prompts():
    """Demonstrate specialist prompts."""
    print("\n" + "="*70)
    print("DEMO 4: Specialist Prompts")
    print("="*70)
    
    selector = SpecialistPromptSelector()
    
    # HVAC example
    print("\n🔧 HVAC Specialist Context (excerpt):")
    hvac_context = selector.get_specialist_context(
        category="HVAC",
        issue_data={"item": "AC condenser unit"},
        property_age=15
    )
    # Print first 500 characters
    print(hvac_context[:600] + "\n    [...more specialist guidance...]")
    
    # Foundation example
    print("\n\n🏗️  Foundation Specialist Context (excerpt):")
    foundation_context = selector.get_specialist_context(
        category="Foundation",
        issue_data={"item": "Foundation crack"},
        property_age=25
    )
    print(foundation_context[:600] + "\n    [...more specialist guidance...]")
    
    print("\n📚 Available Specialists:")
    specialists = [
        "HVAC (heating/cooling systems)",
        "Plumbing (water systems, slab leaks)",
        "Electrical (panels, wiring, safety)",
        "Roofing (shingles, leaks, hurricane ratings)",
        "Foundation (piers, settlement, Houston soil)",
        "Structural (safety-critical issues)",
        "Pest Control (termites, treatments)"
    ]
    for specialist in specialists:
        print(f"  • {specialist}")


def main():
    """Run all demos."""
    print("\n" + "="*70)
    print("🚀 PHASE 1 ENHANCEMENTS DEMONSTRATION")
    print("="*70)
    print("\nThis demo showcases the 4 major Phase 1 improvements:")
    print("  1. Multi-dimensional confidence scoring")
    print("  2. Houston component cost database")
    print("  3. Issue relationship analysis")
    print("  4. Trade specialist prompts")
    
    # Run demos
    demo_confidence_scorer()
    demo_cost_database()
    demo_relationship_analyzer()
    demo_specialist_prompts()
    
    # Summary
    print("\n" + "="*70)
    print("✅ DEMO COMPLETE")
    print("="*70)
    print("\nNext Steps:")
    print("  1. Run enhanced estimator on your data:")
    print("     python enhanced_cost_estimator.py --input enriched_data/6-report_enriched.json")
    print("\n  2. Review the comprehensive output in cost_estimates/")
    print("\n  3. Check PHASE1_ENHANCEMENTS.md for detailed documentation")
    print("\n  4. Integrate these modules into your existing pipeline")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()

