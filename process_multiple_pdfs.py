#!/usr/bin/env python3
"""
Process multiple PDF files using the extraction pipeline.
"""

import os
import glob
from src.pipeline import PDFExtractionPipeline


def process_multiple_pdfs(pdf_directory=".", output_dir="./batch_output"):
    """
    Process all PDF files in a directory.
    """
    # Initialize pipeline
    pipeline = PDFExtractionPipeline(output_dir=output_dir)
    
    # Find all PDF files
    pdf_files = glob.glob(os.path.join(pdf_directory, "*.pdf"))
    
    if not pdf_files:
        print("No PDF files found in the current directory.")
        return
    
    print(f"Found {len(pdf_files)} PDF files to process:")
    for pdf_file in pdf_files:
        print(f"  - {os.path.basename(pdf_file)}")
    
    print("\n" + "="*60)
    
    # Process each PDF
    results = []
    for i, pdf_path in enumerate(pdf_files, 1):
        print(f"\n[{i}/{len(pdf_files)}] Processing: {os.path.basename(pdf_path)}")
        
        try:
            report = pipeline.process_pdf(pdf_path)
            
            # Store results
            result = {
                'filename': report.metadata.filename,
                'pages': report.metadata.total_pages,
                'issues': len(report.issues),
                'deficient': len([i for i in report.issues if i.status == 'D']),
                'tables': len(report.tables),
                'address': report.metadata.property_address
            }
            results.append(result)
            
            print(f"  ✓ Success: {result['issues']} issues, {result['deficient']} deficient")
            
        except Exception as e:
            print(f"  ✗ Error: {e}")
            results.append({
                'filename': os.path.basename(pdf_path),
                'error': str(e)
            })
    
    # Print summary
    print(f"\n{'='*60}")
    print("BATCH PROCESSING SUMMARY")
    print(f"{'='*60}")
    
    successful = [r for r in results if 'error' not in r]
    failed = [r for r in results if 'error' in r]
    
    print(f"Successfully processed: {len(successful)}")
    print(f"Failed: {len(failed)}")
    
    if successful:
        print(f"\nSuccessful extractions:")
        for result in successful:
            print(f"  {result['filename']}: {result['issues']} issues, {result['deficient']} deficient")
            if result['address']:
                print(f"    Address: {result['address']}")
    
    if failed:
        print(f"\nFailed extractions:")
        for result in failed:
            print(f"  {result['filename']}: {result['error']}")
    
    return results


def process_specific_files(pdf_files, output_dir="./specific_output"):
    """
    Process specific PDF files.
    """
    pipeline = PDFExtractionPipeline(output_dir=output_dir)
    
    for pdf_file in pdf_files:
        if not os.path.exists(pdf_file):
            print(f"File not found: {pdf_file}")
            continue
        
        print(f"Processing: {pdf_file}")
        try:
            report = pipeline.process_pdf(pdf_file)
            print(f"  ✓ Success: {len(report.issues)} issues extracted")
        except Exception as e:
            print(f"  ✗ Error: {e}")


if __name__ == "__main__":
    # Example 1: Process all PDFs in current directory
    print("Processing all PDF files in current directory...")
    results = process_multiple_pdfs()
    
    # Example 2: Process specific files
    # specific_files = ["7-report.pdf", "8-report.pdf"]
    # process_specific_files(specific_files)
