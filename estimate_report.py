#!/usr/bin/env python3
"""
CLI tool for generating cost estimates from inspection reports.
"""
import argparse
import logging
import sys
import os
from datetime import datetime
from src.estimation_pipeline import EstimationPipeline

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def progress_callback(current: int, total: int, message: str):
    """Display progress to user."""
    percent = (current / total) * 100 if total > 0 else 0
    bar_length = 40
    filled = int(bar_length * current / total) if total > 0 else 0
    bar = '=' * filled + '-' * (bar_length - filled)
    print(f'\r[{bar}] {percent:.0f}% - {message}', end='', flush=True)
    if current >= total:
        print()  # New line when complete


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Generate cost estimates for home inspection reports',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Estimate costs for a report (using API key from environment)
  python estimate_report.py extracted_data/6-report.json
  
  # Specify API key directly
  python estimate_report.py extracted_data/6-report.json --api-key YOUR_KEY
  
  # Custom output directory
  python estimate_report.py extracted_data/6-report.json --output-dir ./my_estimates
  
  # Generate only PDF (skip UI JSON)
  python estimate_report.py extracted_data/6-report.json --pdf-only
  
  # Verbose logging
  python estimate_report.py extracted_data/6-report.json --verbose
        """
    )
    
    parser.add_argument(
        'json_path',
        help='Path to extracted inspection report JSON file'
    )
    
    parser.add_argument(
        '--api-key',
        help='Google Gemini API key (or set GEMINI_API_KEY environment variable)',
        default=None
    )
    
    parser.add_argument(
        '--output-dir',
        help='Output directory for generated files (default: ./estimates)',
        default='./estimates'
    )
    
    parser.add_argument(
        '--location',
        help='Property location (default: Houston, TX)',
        default='Houston, TX'
    )
    
    parser.add_argument(
        '--pdf-only',
        action='store_true',
        help='Generate only PDF report (skip UI JSON)'
    )
    
    parser.add_argument(
        '--ui-only',
        action='store_true',
        help='Generate only UI JSON (skip PDF report)'
    )
    
    parser.add_argument(
        '--no-batch',
        action='store_true',
        help='Disable batch processing (process issues one at a time)'
    )
    
    parser.add_argument(
        '--max-workers',
        type=int,
        default=3,
        help='Maximum concurrent API calls (default: 3)'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Setup logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Check input file exists
    if not os.path.exists(args.json_path):
        logger.error(f"Input file not found: {args.json_path}")
        sys.exit(1)
    
    # Get API key
    api_key = args.api_key or os.getenv('GEMINI_API_KEY')
    if not api_key:
        logger.error("API key not provided. Use --api-key or set GEMINI_API_KEY environment variable")
        sys.exit(1)
    
    try:
        # Initialize pipeline
        print(f"\n{'='*60}")
        print("HOME REPAIR COST ESTIMATION")
        print(f"{'='*60}\n")
        
        print(f"Input: {args.json_path}")
        print(f"Location: {args.location}")
        print(f"Output Directory: {args.output_dir}")
        print()
        
        pipeline = EstimationPipeline(
            gemini_api_key=api_key,
            location=args.location,
            output_dir=args.output_dir,
            use_batch=not args.no_batch,
            max_workers=args.max_workers
        )
        
        # Run estimation
        print("Generating cost estimates...")
        result = pipeline.estimate_costs(args.json_path, progress_callback)
        
        print(f"\n{'='*60}")
        print("ESTIMATION RESULTS")
        print(f"{'='*60}\n")
        
        print(f"Property: {result.property_address}")
        print(f"Inspection Date: {result.inspection_date}")
        print()
        
        print(f"Total Issues: {result.total_issues}")
        print(f"Deficient Issues: {result.deficient_issues}")
        print(f"Estimates Generated: {len(result.estimates)}")
        print()
        
        print(f"ESTIMATED TOTAL COST:")
        print(f"  ${result.total_cost_min:,.0f} - ${result.total_cost_max:,.0f}")
        print()
        
        # Show top priorities
        if result.top_priorities:
            print("TOP PRIORITIES:")
            for i, estimate in enumerate(result.top_priorities[:5], 1):
                cost_range = f"${estimate.cost_breakdown.total_min:,.0f} - ${estimate.cost_breakdown.total_max:,.0f}"
                print(f"  {i}. [{estimate.urgency.upper()}] {estimate.repair_name[:60]}")
                print(f"     Cost: {cost_range}")
            print()
        
        # Generate outputs
        outputs = []
        
        if not args.ui_only:
            print("Generating PDF report...")
            pdf_path = pipeline.generate_pdf(result)
            outputs.append(('PDF Report', pdf_path))
            print(f"  ✓ {pdf_path}")
        
        if not args.pdf_only:
            print("Generating UI data...")
            ui_path = pipeline.generate_ui_data(result)
            outputs.append(('UI Data', ui_path))
            print(f"  ✓ {ui_path}")
        
        # Save raw result
        result_filename = f"estimate_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        result_path = os.path.join(args.output_dir, result_filename)
        result.to_json(result_path)
        outputs.append(('Raw Result', result_path))
        print(f"  ✓ {result_path}")
        
        # Show API usage
        print()
        stats = pipeline.get_api_statistics()
        print(f"API Usage:")
        print(f"  Requests: {stats['request_count']}")
        print(f"  Input Tokens: {stats['total_input_tokens']:,}")
        print(f"  Output Tokens: {stats['total_output_tokens']:,}")
        print(f"  Estimated Cost: ${stats['estimated_cost_usd']:.4f}")
        
        print(f"\n{'='*60}")
        print("✓ ESTIMATION COMPLETE")
        print(f"{'='*60}\n")
        
        print("Generated Files:")
        for name, path in outputs:
            print(f"  • {name}: {path}")
        
        print()
        
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error during estimation: {e}", exc_info=args.verbose)
        sys.exit(1)


if __name__ == "__main__":
    main()

