#!/usr/bin/env python3
"""
Main entry point for PDF extraction pipeline.
"""

import os
import sys
import argparse
from src.pipeline import PDFExtractionPipeline


def main():
    parser = argparse.ArgumentParser(description='Extract structured data from PDF inspection reports')
    parser.add_argument('pdf_path', help='Path to PDF file to process')
    parser.add_argument('--output-dir', '-o', default='./extracted_data', 
                       help='Output directory for extracted data')
    parser.add_argument('--no-cache', action='store_true', 
                       help='Disable caching')
    parser.add_argument('--force', action='store_true',
                       help='Force reprocessing even if cached')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Check if PDF exists
    if not os.path.exists(args.pdf_path):
        print(f"Error: PDF file not found: {args.pdf_path}")
        sys.exit(1)
    
    # Initialize pipeline
    pipeline = PDFExtractionPipeline(
        output_dir=args.output_dir,
        enable_caching=not args.no_cache
    )
    
    try:
        # Process PDF
        print(f"Processing: {args.pdf_path}")
        report = pipeline.process_pdf(args.pdf_path, force_reprocess=args.force)
        
        # Print summary
        print("\n" + "="*50)
        print("EXTRACTION SUMMARY")
        print("="*50)
        print(f"File: {report.metadata.filename}")
        print(f"Pages: {report.metadata.total_pages}")
        print(f"Report Type: {report.metadata.report_type}")
        print(f"Property Address: {report.metadata.property_address}")
        print(f"Issues Found: {len(report.issues)}")
        print(f"Tables Extracted: {len(report.tables)}")
        
        # Issues by status
        status_counts = {}
        for issue in report.issues:
            status_counts[issue.status] = status_counts.get(issue.status, 0) + 1
        
        print(f"\nIssues by Status:")
        for status, count in status_counts.items():
            print(f"  {status}: {count}")
        
        # Issues by priority
        priority_counts = {}
        for issue in report.issues:
            priority_counts[issue.priority] = priority_counts.get(issue.priority, 0) + 1
        
        print(f"\nIssues by Priority:")
        for priority, count in priority_counts.items():
            print(f"  {priority}: {count}")
        
        print(f"\nOutput saved to: {args.output_dir}")
        
    except Exception as e:
        print(f"Error processing PDF: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
