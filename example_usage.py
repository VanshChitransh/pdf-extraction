#!/usr/bin/env python3
"""
Example usage of the PDF extraction pipeline.
"""

import json
from src.pipeline import PDFExtractionPipeline
from src.models import StructuredReport


def main():
    """
    Demonstrate the PDF extraction pipeline usage.
    """
    # Initialize the pipeline
    pipeline = PDFExtractionPipeline(output_dir="./extracted_data")
    
    # Process a PDF file
    pdf_path = "6-report.pdf"
    
    try:
        print(f"Processing: {pdf_path}")
        report = pipeline.process_pdf(pdf_path)
        
        # Display basic information
        print(f"\n{'='*50}")
        print("EXTRACTION RESULTS")
        print(f"{'='*50}")
        print(f"File: {report.metadata.filename}")
        print(f"Pages: {report.metadata.total_pages}")
        print(f"Report Type: {report.metadata.report_type}")
        print(f"Property Address: {report.metadata.property_address}")
        print(f"Report Number: {report.metadata.report_number}")
        print(f"Inspection Date: {report.metadata.inspection_date}")
        
        # Display issues summary
        print(f"\nISSUES SUMMARY:")
        print(f"Total Issues: {len(report.issues)}")
        
        # Count by status
        status_counts = {}
        for issue in report.issues:
            status_counts[issue.status] = status_counts.get(issue.status, 0) + 1
        
        print(f"\nIssues by Status:")
        for status, count in status_counts.items():
            print(f"  {status}: {count}")
        
        # Count by priority
        priority_counts = {}
        for issue in report.issues:
            priority_counts[issue.priority] = priority_counts.get(issue.priority, 0) + 1
        
        print(f"\nIssues by Priority:")
        for priority, count in priority_counts.items():
            print(f"  {priority}: {count}")
        
        # Display deficient issues
        deficient_issues = [issue for issue in report.issues if issue.status == 'D']
        if deficient_issues:
            print(f"\nDEFICIENT ISSUES ({len(deficient_issues)}):")
            for i, issue in enumerate(deficient_issues[:5], 1):  # Show first 5
                print(f"{i}. {issue.title}")
                print(f"   Section: {issue.section}")
                print(f"   Priority: {issue.priority}")
                print(f"   Pages: {issue.page_numbers}")
                print()
        
        # Display high priority issues
        high_priority_issues = [issue for issue in report.issues if issue.priority == 'high']
        if high_priority_issues:
            print(f"\nHIGH PRIORITY ISSUES ({len(high_priority_issues)}):")
            for i, issue in enumerate(high_priority_issues[:3], 1):  # Show first 3
                print(f"{i}. {issue.title}")
                print(f"   Status: {issue.status}")
                print(f"   Section: {issue.section}")
                print()
        
        # Display tables summary
        print(f"\nTABLES SUMMARY:")
        print(f"Total Tables: {len(report.tables)}")
        
        table_types = {}
        for table in report.tables:
            table_types[table.table_type] = table_types.get(table.table_type, 0) + 1
        
        print(f"Table Types:")
        for table_type, count in table_types.items():
            print(f"  {table_type}: {count}")
        
        # Show sample table data
        if report.tables:
            print(f"\nSAMPLE TABLE DATA:")
            sample_table = report.tables[0]
            print(f"Type: {sample_table.table_type}")
            print(f"Page: {sample_table.page_num}")
            print(f"Headers: {sample_table.column_headers}")
            if sample_table.table_data:
                print(f"Sample Row: {sample_table.table_data[0]}")
        
        # Save detailed report
        output_file = f"./extracted_data/{report.metadata.filename.replace('.pdf', '')}_detailed.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report.to_dict(), f, indent=2, default=str)
        
        print(f"\nDetailed report saved to: {output_file}")
        
        # Display processing statistics
        stats = pipeline.get_processing_stats()
        print(f"\nPROCESSING STATISTICS:")
        print(f"Processed Files: {stats.get('processed_files', 0)}")
        print(f"Cached Files: {stats.get('cached_files', 0)}")
        
    except Exception as e:
        print(f"Error processing PDF: {e}")
        import traceback
        traceback.print_exc()


def analyze_issues(report: StructuredReport):
    """
    Perform detailed analysis of extracted issues.
    """
    print(f"\n{'='*50}")
    print("DETAILED ISSUE ANALYSIS")
    print(f"{'='*50}")
    
    # Group issues by section
    section_issues = {}
    for issue in report.issues:
        section = issue.section
        if section not in section_issues:
            section_issues[section] = []
        section_issues[section].append(issue)
    
    for section, issues in section_issues.items():
        if section == "HEADER":
            continue  # Skip header issues
        
        print(f"\n{section}:")
        deficient_count = len([i for i in issues if i.status == 'D'])
        print(f"  Total Issues: {len(issues)}")
        print(f"  Deficient: {deficient_count}")
        
        if deficient_count > 0:
            print(f"  Deficient Items:")
            for issue in issues:
                if issue.status == 'D':
                    print(f"    - {issue.title[:80]}...")
                    if issue.estimated_cost:
                        cost = issue.estimated_cost
                        print(f"      Estimated Cost: ${cost.get('min', 0):.2f} - ${cost.get('max', 0):.2f}")


if __name__ == "__main__":
    main()
