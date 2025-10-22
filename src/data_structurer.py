"""
Data structuring and issue linking.
"""
from typing import List, Dict, Optional
from .models import (
    PDFMetadata, TextBlock, ExtractedTable,
    InspectionIssue, StructuredReport
)


def structure_extraction_results(
    metadata: PDFMetadata,
    text_blocks: List[TextBlock],
    tables: List[ExtractedTable]
) -> StructuredReport:
    """
    Combine all extracted data into a structured format.
    """
    issues = extract_inspection_issues(text_blocks)
    
    # Extract cost estimates from tables
    extract_cost_estimates(issues, tables)
    
    # Group text by sections
    raw_sections = group_text_by_section(text_blocks)
    
    return StructuredReport(
        metadata=metadata,
        issues=issues,
        tables=tables,
        raw_sections=raw_sections
    )


def extract_inspection_issues(text_blocks: List[TextBlock]) -> List[InspectionIssue]:
    """
    Extract structured inspection issues from text blocks.
    """
    issues = []
    current_issue = None
    issue_counter = 0
    
    for block in text_blocks:
        # Start new issue if we hit status change or specific keywords
        if should_start_new_issue(block, current_issue):
            if current_issue:
                issues.append(current_issue)
                issue_counter += 1
            
            # Determine priority from formatting and content
            priority = determine_priority(block)
            
            current_issue = InspectionIssue(
                id=f"{block.section}_{issue_counter}",
                section=block.section,
                subsection=block.subsection,
                status=block.status or 'I',
                priority=priority,
                title=extract_title(block.content),
                description=block.content,
                page_numbers=[block.page_num],
                estimated_cost=None
            )
        
        elif current_issue:
            # Append to current issue
            current_issue.description += "\n" + block.content
            if block.page_num not in current_issue.page_numbers:
                current_issue.page_numbers.append(block.page_num)
    
    # Add last issue
    if current_issue:
        issues.append(current_issue)
    
    return issues


def should_start_new_issue(block: TextBlock, current_issue: Optional[InspectionIssue]) -> bool:
    """
    Determine if a new issue should be started based on the text block.
    """
    # Start new issue if status is 'D' (Deficient)
    if block.status == 'D':
        return True
    
    # Start new issue if we hit specific keywords
    content_lower = block.content.lower()
    issue_keywords = [
        'comments:', 'note:', 'observation:', 'finding:', 'issue:',
        'deficiency:', 'problem:', 'concern:', 'recommendation:'
    ]
    
    if any(keyword in content_lower for keyword in issue_keywords):
        return True
    
    # Start new issue if we're in a new subsection and current issue is long
    if (current_issue and 
        block.subsection != current_issue.subsection and 
        len(current_issue.description) > 200):
        return True
    
    # Start new issue if we're in a new section
    if (current_issue and 
        block.section != current_issue.section):
        return True
    
    return False


def determine_priority(block: TextBlock) -> str:
    """
    Determine issue priority based on formatting and content.
    """
    # High priority indicators
    if block.formatting.get('bold', False):
        return 'high'
    
    # Check content for priority keywords
    content_lower = block.content.lower()
    
    high_priority_keywords = [
        'safety', 'hazard', 'danger', 'urgent', 'critical', 'severe',
        'structural', 'foundation', 'electrical', 'gas', 'fire'
    ]
    
    if any(keyword in content_lower for keyword in high_priority_keywords):
        return 'high'
    
    # Medium priority indicators
    if block.formatting.get('underlined', False):
        return 'medium'
    
    medium_priority_keywords = [
        'repair', 'replace', 'maintenance', 'damage', 'worn', 'crack'
    ]
    
    if any(keyword in content_lower for keyword in medium_priority_keywords):
        return 'medium'
    
    # Low priority for informational items
    if block.status in ['I', 'NI', 'NP']:
        return 'low'
    
    return 'info'


def extract_title(content: str) -> str:
    """
    Extract a concise title from issue content.
    """
    # Take first sentence or first 100 characters
    sentences = content.split('.')
    if sentences and len(sentences[0]) < 100:
        return sentences[0].strip()
    
    # Fallback to first 100 characters
    return content[:100].strip() + ('...' if len(content) > 100 else '')


def extract_cost_estimates(issues: List[InspectionIssue], tables: List[ExtractedTable]) -> None:
    """
    Extract cost estimates from tables and link to issues.
    """
    for table in tables:
        if table.table_type != 'cost_estimate':
            continue
        
        # Look for cost data in table
        cost_data = extract_cost_data_from_table(table)
        if not cost_data:
            continue
        
        # Try to link to relevant issues
        for issue in issues:
            if (issue.section == table.section and 
                any(pn == table.page_num for pn in issue.page_numbers)):
                issue.estimated_cost = cost_data
                break


def extract_cost_data_from_table(table: ExtractedTable) -> Optional[Dict[str, float]]:
    """
    Extract cost range from a cost estimate table.
    """
    cost_data = None
    
    for row in table.table_data:
        for cell in row:
            if not cell:
                continue
            
            # Look for price patterns
            import re
            price_patterns = [
                r'\$(\d+(?:,\d{3})*(?:\.\d{2})?)',  # $1,234.56
                r'(\d+(?:,\d{3})*(?:\.\d{2})?)\s*\$',  # 1234.56$
                r'(\d+(?:,\d{3})*(?:\.\d{2})?)\s*dollars?',  # 1234.56 dollars
            ]
            
            for pattern in price_patterns:
                matches = re.findall(pattern, cell)
                if matches:
                    try:
                        # Convert to float
                        prices = []
                        for match in matches:
                            price_str = match.replace(',', '')
                            price = float(price_str)
                            prices.append(price)
                        
                        if prices:
                            cost_data = {
                                'min': min(prices),
                                'max': max(prices),
                                'average': sum(prices) / len(prices)
                            }
                            break
                    except ValueError:
                        continue
        
        if cost_data:
            break
    
    return cost_data


def group_text_by_section(blocks: List[TextBlock]) -> Dict[str, str]:
    """
    Create a simple section → text mapping for fallback.
    """
    sections = {}
    for block in blocks:
        section_key = f"{block.section} > {block.subsection}" if block.subsection else block.section
        if section_key not in sections:
            sections[section_key] = ""
        sections[section_key] += block.content + "\n"
    return sections


def validate_extraction(report: StructuredReport) -> bool:
    """
    Ensure extraction quality.
    """
    # Basic validation checks
    if not report.issues:
        print("Warning: No issues extracted")
        return False
    
    if not report.metadata.property_address:
        print("Warning: No property address found")
    
    # Image extraction is disabled
    # if not report.images:
    #     print("Warning: No images extracted")
    
    # Check for reasonable number of issues
    if len(report.issues) < 5:
        print("Warning: Very few issues extracted, might indicate extraction problems")
    
    return True


def get_extraction_summary(report: StructuredReport) -> Dict[str, any]:
    """
    Generate a summary of the extraction results.
    """
    return {
        'total_issues': len(report.issues),
        'issues_by_status': {
            'deficient': len([i for i in report.issues if i.status == 'D']),
            'inspected': len([i for i in report.issues if i.status == 'I']),
            'not_inspected': len([i for i in report.issues if i.status == 'NI']),
            'not_present': len([i for i in report.issues if i.status == 'NP'])
        },
        'issues_by_priority': {
            'high': len([i for i in report.issues if i.priority == 'high']),
            'medium': len([i for i in report.issues if i.priority == 'medium']),
            'low': len([i for i in report.issues if i.priority == 'low']),
            'info': len([i for i in report.issues if i.priority == 'info'])
        },
        'total_tables': len(report.tables),
        'pages_processed': report.metadata.total_pages,
        'sections_found': len(report.raw_sections)
    }
