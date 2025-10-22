"""
Example Cost Estimation Usage

Demonstrates how to use the cost estimation pipeline with various configurations.

This script shows:
1. Basic usage (individual processing)
2. Batch processing for cost savings
3. Comparing different models
4. Analyzing results and quality metrics
5. Manual review workflows
"""

import os
import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from cost_estimation_pipeline import CostEstimationPipeline


def example_1_basic_usage():
    """Example 1: Basic usage with individual processing."""
    print("\n" + "="*70)
    print("EXAMPLE 1: Basic Usage (Individual Processing)")
    print("="*70)
    
    # Initialize pipeline
    pipeline = CostEstimationPipeline(
        model="gemini-2.5-flash",
        temperature=0.3,
        batch_size=1,  # Process one issue at a time
        prompt_version="v1.0-individual",
        enable_logging=True
    )
    
    # Process a report
    result = pipeline.process_report(
        enriched_data_path="enriched_data/6-report_enriched.json",
        output_path="cost_estimates/6-report_individual.json"
    )
    
    print(f"\n✓ Completed! See: {result['output_file']}")
    return result


def example_2_batch_processing():
    """Example 2: Batch processing for cost savings."""
    print("\n" + "="*70)
    print("EXAMPLE 2: Batch Processing (Lower API Costs)")
    print("="*70)
    
    # Initialize pipeline with batching
    pipeline = CostEstimationPipeline(
        model="gemini-2.5-flash",
        temperature=0.3,
        batch_size=10,  # Process 10 issues per API call
        prompt_version="v1.0-batch10",
        enable_logging=True
    )
    
    # Process a report
    result = pipeline.process_report(
        enriched_data_path="enriched_data/7-report_enriched.json",
        output_path="cost_estimates/7-report_batch.json"
    )
    
    print(f"\n✓ Completed! See: {result['output_file']}")
    return result


def example_3_compare_models():
    """Example 3: Compare different AI models."""
    print("\n" + "="*70)
    print("EXAMPLE 3: Comparing Different Models")
    print("="*70)
    
    models = ["gemini-2.5-flash", "gemini-pro"]
    results = {}
    
    for model in models:
        print(f"\n--- Testing {model} ---")
        
        try:
            pipeline = CostEstimationPipeline(
                model=model,
                temperature=0.3,
                batch_size=5,
                prompt_version=f"v1.0-{model}",
                enable_logging=True
            )
            
            result = pipeline.process_report(
                enriched_data_path="enriched_data/6-report_enriched.json",
                output_path=f"cost_estimates/6-report_{model}.json"
            )
            
            results[model] = result["statistics"]
            
        except Exception as e:
            print(f"Error with {model}: {e}")
            results[model] = {"error": str(e)}
    
    # Compare results
    print("\n" + "="*70)
    print("MODEL COMPARISON")
    print("="*70)
    for model, stats in results.items():
        if "error" not in stats:
            print(f"\n{model}:")
            print(f"  Success rate: {stats['estimated_issues']}/{stats['total_issues']}")
            print(f"  Validation passed: {stats['validation_passed']}")
            print(f"  Flagged for review: {stats['flagged_for_review']}")
    
    return results


def example_4_analyze_results():
    """Example 4: Analyze cost estimation results."""
    print("\n" + "="*70)
    print("EXAMPLE 4: Analyzing Results")
    print("="*70)
    
    # Load results
    results_file = "cost_estimates/6-report_individual.json"
    
    if not Path(results_file).exists():
        print(f"Results file not found: {results_file}")
        print("Run example_1_basic_usage() first")
        return
    
    with open(results_file, 'r') as f:
        data = json.load(f)
    
    estimates = data["cost_estimates"]
    
    # Analyze by severity
    by_severity = {}
    for est in estimates:
        severity = est.get("severity", "Unknown")
        if severity not in by_severity:
            by_severity[severity] = []
        by_severity[severity].append(est)
    
    print("\nCost Breakdown by Severity:")
    print("-" * 70)
    for severity in ["Critical", "High", "Medium", "Low"]:
        if severity in by_severity:
            issues = by_severity[severity]
            total_low = sum(e.get("estimated_low", 0) for e in issues)
            total_high = sum(e.get("estimated_high", 0) for e in issues)
            avg_conf = sum(e.get("confidence_score", 0) for e in issues) / len(issues)
            
            print(f"{severity:10} ({len(issues):2} issues): "
                  f"${total_low:8,.0f} - ${total_high:8,.0f}  "
                  f"(avg confidence: {avg_conf:.0f})")
    
    # Find issues needing review
    print("\n\nIssues Flagged for Manual Review:")
    print("-" * 70)
    review_needed = [
        e for e in estimates
        if e.get("validation", {}).get("needs_review", False)
    ]
    
    for est in review_needed[:10]:  # Show first 10
        print(f"• {est.get('item', 'Unknown')}")
        print(f"  Cost: ${est.get('estimated_low', 0):.0f} - ${est.get('estimated_high', 0):.0f}")
        print(f"  Confidence: {est.get('confidence_score', 0)}")
        print(f"  Reason: {est.get('reasoning', '')[:100]}...")
        print()
    
    if len(review_needed) > 10:
        print(f"... and {len(review_needed) - 10} more")
    
    # Highest cost items
    print("\n\nTop 5 Highest Cost Items:")
    print("-" * 70)
    sorted_by_cost = sorted(
        estimates,
        key=lambda x: x.get("estimated_high", 0),
        reverse=True
    )
    
    for est in sorted_by_cost[:5]:
        print(f"• {est.get('item', 'Unknown')}")
        print(f"  Cost: ${est.get('estimated_low', 0):,.0f} - ${est.get('estimated_high', 0):,.0f}")
        print(f"  Severity: {est.get('severity', 'Unknown')}")
        print(f"  Action: {est.get('suggested_action', 'Unknown')}")
        print()


def example_5_manual_review_workflow():
    """Example 5: Manual review workflow for flagged estimates."""
    print("\n" + "="*70)
    print("EXAMPLE 5: Manual Review Workflow")
    print("="*70)
    
    # Load results
    results_file = "cost_estimates/6-report_individual.json"
    
    if not Path(results_file).exists():
        print(f"Results file not found: {results_file}")
        return
    
    with open(results_file, 'r') as f:
        data = json.load(f)
    
    estimates = data["cost_estimates"]
    
    # Filter issues needing review
    review_needed = [
        e for e in estimates
        if e.get("validation", {}).get("needs_review", False)
    ]
    
    print(f"\nFound {len(review_needed)} estimates flagged for review")
    
    # Categorize by reason
    low_confidence = [e for e in review_needed if e.get("confidence_score", 100) < 60]
    high_cost = [e for e in review_needed if e.get("estimated_high", 0) > 10000]
    validation_failed = [
        e for e in review_needed
        if not e.get("validation", {}).get("valid", True)
    ]
    
    print("\nReview Categories:")
    print(f"  Low confidence (<60): {len(low_confidence)}")
    print(f"  High cost (>$10k): {len(high_cost)}")
    print(f"  Validation failed: {len(validation_failed)}")
    
    # Export for manual review
    review_file = "cost_estimates/manual_review_needed.json"
    review_data = {
        "generated_at": data["metadata"]["generated_at"],
        "total_flagged": len(review_needed),
        "categories": {
            "low_confidence": low_confidence,
            "high_cost": high_cost,
            "validation_failed": validation_failed
        }
    }
    
    with open(review_file, 'w') as f:
        json.dump(review_data, f, indent=2)
    
    print(f"\n✓ Manual review file saved: {review_file}")


def example_6_version_comparison():
    """Example 6: Compare prompt versions."""
    print("\n" + "="*70)
    print("EXAMPLE 6: Prompt Version Comparison")
    print("="*70)
    
    from prompting.version_control import PromptVersionControl
    
    # Load different versions
    versions = ["v1.0-individual", "v1.0-batch10"]
    
    for version in versions:
        try:
            pvc = PromptVersionControl.load_version(version)
            summary = pvc.get_version_summary()
            
            print(f"\n{version}:")
            print(f"  Interactions: {summary['interaction_count']}")
            print(f"  Success rate: {summary['success_rate']:.1%}")
            print(f"  Avg confidence: {summary['metrics']['avg_confidence']:.1f}")
            print(f"  Avg quality: {summary['metrics']['avg_response_quality']:.1f}")
            
            # Confidence distribution
            dist = pvc.analyze_confidence_distribution()
            if "distribution" in dist:
                print("  Confidence distribution:")
                for level, data in dist["distribution"].items():
                    print(f"    {level}: {data['count']} ({data['percent']:.1f}%)")
        
        except Exception as e:
            print(f"\n{version}: Not found or error - {e}")


def run_all_examples():
    """Run all examples in sequence."""
    print("\n" + "="*70)
    print("RUNNING ALL COST ESTIMATION EXAMPLES")
    print("="*70)
    
    # Check for API key
    if not os.environ.get("GEMINI_API_KEY"):
        print("\n⚠ Warning: GEMINI_API_KEY not set")
        print("Set it with: export GEMINI_API_KEY='your-key-here'")
        print("\nRunning in demo mode (will show errors)...\n")
    
    # Check for input files
    if not Path("enriched_data/6-report_enriched.json").exists():
        print("\n⚠ Warning: enriched_data/6-report_enriched.json not found")
        print("Run enrich_data.py first to create enriched data")
        return
    
    try:
        # Run examples
        example_1_basic_usage()
        
        input("\nPress Enter to continue to Example 2 (batch processing)...")
        example_2_batch_processing()
        
        input("\nPress Enter to continue to Example 3 (model comparison)...")
        # example_3_compare_models()  # Uncomment if you have multiple models
        
        input("\nPress Enter to continue to Example 4 (analyze results)...")
        example_4_analyze_results()
        
        input("\nPress Enter to continue to Example 5 (manual review)...")
        example_5_manual_review_workflow()
        
        input("\nPress Enter to continue to Example 6 (version comparison)...")
        example_6_version_comparison()
        
        print("\n" + "="*70)
        print("ALL EXAMPLES COMPLETED!")
        print("="*70)
    
    except KeyboardInterrupt:
        print("\n\nExamples interrupted by user")
    except Exception as e:
        print(f"\n\nError running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        example_num = sys.argv[1]
        
        examples = {
            "1": example_1_basic_usage,
            "2": example_2_batch_processing,
            "3": example_3_compare_models,
            "4": example_4_analyze_results,
            "5": example_5_manual_review_workflow,
            "6": example_6_version_comparison,
            "all": run_all_examples
        }
        
        if example_num in examples:
            examples[example_num]()
        else:
            print(f"Unknown example: {example_num}")
            print(f"Available: {', '.join(examples.keys())}")
    else:
        print("\nUsage:")
        print("  python example_cost_estimation.py 1    # Run example 1")
        print("  python example_cost_estimation.py 2    # Run example 2")
        print("  python example_cost_estimation.py all  # Run all examples")
        print("\nAvailable examples:")
        print("  1. Basic usage (individual processing)")
        print("  2. Batch processing for cost savings")
        print("  3. Compare different models")
        print("  4. Analyze results")
        print("  5. Manual review workflow")
        print("  6. Version comparison")

