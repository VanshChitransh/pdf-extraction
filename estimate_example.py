#!/usr/bin/env python3
"""
Example script demonstrating the cost estimation pipeline.
"""
import logging
from src.estimation_pipeline import EstimationPipeline

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)


def main():
    """
    Example usage of the cost estimation pipeline.
    """
    # Your Gemini API key
    API_KEY = "AIzaSyD5fPlOw8e7fU6zKFf-lo2w65XhzSwzOSA"
    
    # Path to extracted inspection report JSON
    json_path = "extracted_data/6-report.json"
    
    print("="*70)
    print("COST ESTIMATION EXAMPLE")
    print("="*70)
    print()
    
    # Initialize the pipeline
    print("1. Initializing estimation pipeline...")
    pipeline = EstimationPipeline(
        gemini_api_key=API_KEY,
        location="Houston, TX",
        output_dir="./estimates",
        use_batch=True,  # Use batch processing for efficiency
        max_workers=3    # Max 3 concurrent API calls
    )
    print("   ✓ Pipeline initialized")
    print()
    
    # Simple progress callback
    def show_progress(current, total, message):
        percent = (current / total) * 100
        print(f"   Progress: {percent:.0f}% - {message}")
    
    # Run the full pipeline (estimates + PDF + UI data)
    print("2. Running full estimation pipeline...")
    print()
    
    result = pipeline.process_full_pipeline(
        json_path=json_path,
        progress_callback=show_progress
    )
    
    print()
    print("="*70)
    print("RESULTS")
    print("="*70)
    print()
    
    # Display summary
    estimation_result = result['result']
    print(f"Property: {estimation_result.property_address}")
    print(f"Deficient Issues Found: {estimation_result.deficient_issues}")
    print(f"Estimates Generated: {len(estimation_result.estimates)}")
    print()
    
    print(f"TOTAL ESTIMATED COST:")
    print(f"  Minimum: ${estimation_result.total_cost_min:,.0f}")
    print(f"  Maximum: ${estimation_result.total_cost_max:,.0f}")
    print()
    
    # Show cost breakdown by section
    print("COST BY SECTION:")
    for section, costs in sorted(
        estimation_result.summary_by_section.items(),
        key=lambda x: x[1]['max'],
        reverse=True
    ):
        section_name = section.split('.')[-1].strip() if '.' in section else section
        print(f"  • {section_name[:50]}: ${costs['min']:,.0f} - ${costs['max']:,.0f}")
    print()
    
    # Show top 5 priorities
    print("TOP 5 PRIORITY REPAIRS:")
    for i, estimate in enumerate(estimation_result.top_priorities[:5], 1):
        cost = f"${estimate.cost_breakdown.total_min:,.0f} - ${estimate.cost_breakdown.total_max:,.0f}"
        print(f"  {i}. [{estimate.urgency.upper()}] {estimate.repair_name[:50]}")
        print(f"     Cost: {cost}")
        print(f"     Contractor: {estimate.contractor_type}")
        print()
    
    # Show generated files
    print("GENERATED FILES:")
    print(f"  • PDF Report: {result['pdf_path']}")
    print(f"  • UI Data (JSON): {result['ui_path']}")
    print(f"  • Raw Result (JSON): {result['result_path']}")
    print()
    
    # API usage stats
    print("API USAGE:")
    stats = pipeline.get_api_statistics()
    print(f"  • Total Requests: {stats['request_count']}")
    print(f"  • Input Tokens: {stats['total_input_tokens']:,}")
    print(f"  • Output Tokens: {stats['total_output_tokens']:,}")
    print(f"  • Estimated Cost: ${stats['estimated_cost_usd']:.4f}")
    print()
    
    print("="*70)
    print("✓ ESTIMATION COMPLETE!")
    print("="*70)
    print()
    print("Next steps:")
    print("  1. Review the PDF report for detailed cost breakdowns")
    print("  2. Use the UI JSON file to display results in your application")
    print("  3. Get actual quotes from contractors for accurate pricing")
    print()


if __name__ == "__main__":
    main()

