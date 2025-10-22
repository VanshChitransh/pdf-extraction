#!/usr/bin/env python3
"""
Main script for running data enrichment pipeline on extracted PDF data.

Usage:
    python enrich_data.py <json_file> [--output <output_file>] [--verbose]
    
Example:
    python enrich_data.py extracted_data/8-report.json --output extracted_data/8-report_enriched.json
"""

import argparse
import json
import logging
import sys
from pathlib import Path

from src.data_enrichment_pipeline import DataEnrichmentPipeline


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )


def print_summary(results: dict):
    """Print a formatted summary of the processing results."""
    summary = results['summary']
    stats = results['processing_stats']
    
    print("\n" + "="*70)
    print("DATA ENRICHMENT SUMMARY")
    print("="*70)
    
    # Overview
    print(f"\nTotal Issues Processed: {summary['total_issues']}")
    print(f"Safety-Related Issues: {summary['safety_issues']}")
    print(f"Grouped Issues: {summary['grouped_issues']}")
    print(f"Average Urgency Score: {summary['avg_urgency']:.2f}/10")
    print(f"Average Complexity: {summary['avg_complexity']:.2f}/10")
    
    # By Severity
    print("\n--- By Severity ---")
    for severity, count in sorted(summary['by_severity'].items(), 
                                  key=lambda x: x[1], reverse=True):
        pct = (count / summary['total_issues']) * 100
        print(f"  {severity:15s}: {count:3d} ({pct:5.1f}%)")
    
    # By Category
    print("\n--- By Component Category ---")
    for category, count in sorted(summary['by_category'].items(), 
                                  key=lambda x: x[1], reverse=True)[:10]:
        pct = (count / summary['total_issues']) * 100
        print(f"  {category:20s}: {count:3d} ({pct:5.1f}%)")
    
    # By Trade
    print("\n--- By Trade ---")
    for trade, count in sorted(summary['by_trade'].items(), 
                               key=lambda x: x[1], reverse=True):
        pct = (count / summary['total_issues']) * 100
        print(f"  {trade:15s}: {count:3d} ({pct:5.1f}%)")
    
    # By Complexity
    print("\n--- By Complexity ---")
    for complexity, count in sorted(summary['by_complexity'].items()):
        pct = (count / summary['total_issues']) * 100
        print(f"  {complexity:15s}: {count:3d} ({pct:5.1f}%)")
    
    # By Cost Strategy
    print("\n--- By Cost Estimation Strategy ---")
    for strategy, count in sorted(summary['by_strategy'].items(), 
                                  key=lambda x: x[1], reverse=True):
        pct = (count / summary['total_issues']) * 100
        print(f"  {strategy:20s}: {count:3d} ({pct:5.1f}%)")
    
    # Groups
    if 'groups' in results and results['groups']:
        group_summary = stats['phases']['grouping']['group_summary']
        print(f"\n--- Issue Grouping ---")
        print(f"Total Groups Created: {group_summary['total_groups']}")
        print(f"Total Issues in Groups: {group_summary['total_issues_grouped']}")
        print(f"Average Group Size: {group_summary['avg_group_size']}")
        
        print("\nGroups by Type:")
        for group_type, count in group_summary['by_type'].items():
            print(f"  {group_type:20s}: {count}")
    
    # Processing Stats
    print("\n--- Processing Statistics ---")
    for phase, phase_stats in stats['phases'].items():
        print(f"\n{phase.replace('_', ' ').title()}:")
        for key, value in phase_stats.items():
            if not isinstance(value, dict):
                print(f"  {key}: {value}")
    
    print("\n" + "="*70)


def print_top_priority_issues(results: dict, n: int = 10):
    """Print top N priority issues."""
    issues = results['issues']
    
    # Sort by urgency score
    sorted_issues = sorted(issues, 
                          key=lambda x: x.get('urgency_score', 0), 
                          reverse=True)
    
    print(f"\n{'='*70}")
    print(f"TOP {n} PRIORITY ISSUES")
    print('='*70)
    
    for i, issue in enumerate(sorted_issues[:n], 1):
        print(f"\n{i}. {issue.get('title', 'No title')[:60]}")
        print(f"   Category: {issue.get('standard_category', 'Unknown')}")
        print(f"   Trade: {issue.get('classification', {}).get('trade', 'unknown')}")
        print(f"   Severity: {issue.get('standard_severity', 'unknown')}")
        print(f"   Action: {issue.get('standard_action', 'unknown')}")
        print(f"   Urgency Score: {issue.get('urgency_score', 0):.1f}/10")
        print(f"   Complexity: {issue.get('complexity_factor', 0):.1f}/10")
        print(f"   Cost Strategy: {issue.get('cost_strategy', 'unknown')}")
        if issue.get('safety_flag'):
            print(f"   ⚠️  SAFETY ISSUE")
        if issue.get('is_grouped'):
            print(f"   🔗 Grouped with {len(issue.get('grouped_with', []))} other issue(s)")


def main():
    parser = argparse.ArgumentParser(
        description='Enrich PDF extraction data with validation, normalization, and classification'
    )
    parser.add_argument('json_file', help='Input JSON file with extracted issues')
    parser.add_argument('--output', '-o', help='Output file for enriched data')
    parser.add_argument('--verbose', '-v', action='store_true', 
                       help='Enable verbose logging')
    parser.add_argument('--show-top', '-t', type=int, default=10,
                       help='Number of top priority issues to display (default: 10)')
    parser.add_argument('--property-info', help='JSON file with property information')
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    # Check input file exists
    if not Path(args.json_file).exists():
        logger.error(f"Input file not found: {args.json_file}")
        sys.exit(1)
    
    try:
        # Load property info if provided
        property_data = None
        if args.property_info:
            with open(args.property_info, 'r') as f:
                property_data = json.load(f)
        
        # Initialize pipeline
        logger.info("Initializing data enrichment pipeline...")
        pipeline = DataEnrichmentPipeline(property_data=property_data)
        
        # Process data
        logger.info(f"Processing {args.json_file}...")
        results = pipeline.process_from_json(args.json_file)
        
        # Determine output path
        if args.output:
            output_path = args.output
        else:
            input_path = Path(args.json_file)
            output_path = input_path.parent / f"{input_path.stem}_enriched.json"
        
        # Save results
        pipeline.save_results(results, str(output_path))
        
        # Print summary
        print_summary(results)
        
        # Print top priority issues
        if args.show_top > 0:
            print_top_priority_issues(results, args.show_top)
        
        print(f"\n✅ Enriched data saved to: {output_path}")
        
    except Exception as e:
        logger.error(f"Error processing data: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

