"""
Table extraction with semantic classification.
"""
import pdfplumber
from typing import List, Dict, Optional
from .models import ExtractedTable


def extract_tables(pdf_path: str) -> List[ExtractedTable]:
    """
    Extract tables with semantic understanding.
    Tables contain critical structured data.
    """
    tables = []
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                # pdfplumber has excellent table detection
                page_tables = page.extract_tables()
                
                for table in page_tables:
                    if not table or len(table) < 2:
                        continue
                    
                    # Clean table data
                    cleaned_table = clean_table_data(table)
                    if not cleaned_table or len(cleaned_table) < 2:
                        continue
                    
                    # First row is usually headers
                    headers = [str(cell).strip() if cell else '' for cell in cleaned_table[0]]
                    data = [[str(cell).strip() if cell else '' for cell in row] for row in cleaned_table[1:]]
                    
                    # Skip if no meaningful data
                    if not any(headers) and not any(any(row) for row in data):
                        continue
                    
                    # Classify table type
                    table_type = classify_table(headers, data)
                    
                    # Determine section context
                    section = get_current_section(page, page_num)
                    
                    tables.append(ExtractedTable(
                        page_num=page_num,
                        section=section,
                        table_data=data,
                        column_headers=headers,
                        table_type=table_type
                    ))
    
    except Exception as e:
        print(f"Error extracting tables from {pdf_path}: {e}")
    
    return tables


def clean_table_data(table: List[List]) -> List[List]:
    """
    Clean and normalize table data.
    """
    cleaned = []
    for row in table:
        if not row:
            continue
        
        # Clean each cell
        cleaned_row = []
        for cell in row:
            if cell is None:
                cleaned_row.append('')
            else:
                # Convert to string and strip whitespace
                cleaned_cell = str(cell).strip()
                # Remove extra whitespace
                cleaned_cell = ' '.join(cleaned_cell.split())
                cleaned_row.append(cleaned_cell)
        
        # Only add row if it has some content
        if any(cleaned_row):
            cleaned.append(cleaned_row)
    
    return cleaned


def classify_table(headers: List[str], data: List[List[str]]) -> str:
    """
    Determine what type of table this is based on headers and content.
    """
    header_text = ' '.join(headers).lower()
    data_text = ' '.join([' '.join(row) for row in data]).lower()
    combined_text = header_text + ' ' + data_text
    
    # Elevation survey tables
    if any(keyword in combined_text for keyword in ['elevation', 'height', 'level', 'grade', 'slope']):
        return 'elevation_survey'
    
    # Cost estimate tables
    elif any(keyword in combined_text for keyword in ['price', 'cost', 'range', '$', 'estimate', 'repair']):
        return 'cost_estimate'
    
    # Inspection checklist tables
    elif any(keyword in combined_text for keyword in ['i', 'ni', 'np', 'd', 'inspected', 'deficient']):
        return 'inspection_checklist'
    
    # Measurement tables
    elif any(keyword in combined_text for keyword in ['measurement', 'dimension', 'length', 'width', 'depth']):
        return 'measurement'
    
    # Summary tables
    elif any(keyword in combined_text for keyword in ['summary', 'total', 'count', 'number']):
        return 'summary'
    
    else:
        return 'generic'


def get_current_section(page, page_num: int) -> str:
    """
    Determine which section the table belongs to based on page content.
    """
    try:
        # Get text from the page
        text = page.extract_text()
        if not text:
            return f"PAGE_{page_num}"
        
        # Look for section headers (Roman numerals)
        import re
        lines = text.split('\n')
        
        current_section = None
        for line in lines:
            line = line.strip()
            # Match Roman numeral sections
            section_match = re.match(r'^([IVX]+)\.\s+(.+)$', line)
            if section_match:
                current_section = line
                break
        
        return current_section or f"PAGE_{page_num}"
    
    except Exception:
        return f"PAGE_{page_num}"


def extract_table_metadata(table: ExtractedTable) -> Dict[str, any]:
    """
    Extract additional metadata from a table.
    """
    metadata = {
        'row_count': len(table.table_data),
        'column_count': len(table.column_headers),
        'has_numeric_data': False,
        'has_currency_data': False,
        'has_date_data': False
    }
    
    # Check for numeric data
    for row in table.table_data:
        for cell in row:
            if cell and any(char.isdigit() for char in cell):
                metadata['has_numeric_data'] = True
                break
        if metadata['has_numeric_data']:
            break
    
    # Check for currency data
    combined_text = ' '.join(table.column_headers + [' '.join(row) for row in table.table_data])
    if '$' in combined_text or 'price' in combined_text.lower():
        metadata['has_currency_data'] = True
    
    # Check for date data
    import re
    date_pattern = r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b'
    if re.search(date_pattern, combined_text):
        metadata['has_date_data'] = True
    
    return metadata


def validate_table(table: ExtractedTable) -> bool:
    """
    Validate that a table has meaningful data.
    """
    # Must have headers or data
    if not table.column_headers and not table.table_data:
        return False
    
    # Must have at least some non-empty content
    all_content = table.column_headers + [' '.join(row) for row in table.table_data]
    if not any(content.strip() for content in all_content):
        return False
    
    # Must have reasonable dimensions
    if len(table.table_data) > 1000:  # Too many rows
        return False
    
    if len(table.column_headers) > 50:  # Too many columns
        return False
    
    return True
