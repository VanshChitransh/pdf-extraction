"""
Metadata extraction from PDF files.
"""
import re
import PyPDF2
from typing import Optional
from .models import PDFMetadata


def extract_metadata(pdf_path: str) -> PDFMetadata:
    """
    Extract basic metadata from the PDF.
    This helps us understand document structure before deep processing.
    """
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            first_page = pdf_reader.pages[0]
            first_page_text = first_page.extract_text()
            
            # Pattern matching for key metadata
            report_number = re.search(r'Report Number:\s*(\S+)', first_page_text)
            inspection_date = re.search(r'Inspection Date:\s*(.+?)(?:\n|$)', first_page_text)
            address = re.search(r'(\d+\s+[\w\s]+,\s*\w+,\s*TX\s*\d{5})', first_page_text)
            
            # Try alternative date patterns
            if not inspection_date:
                inspection_date = re.search(r'Date:\s*(.+?)(?:\n|$)', first_page_text)
            
            # Try alternative address patterns
            if not address:
                address = re.search(r'(\d+\s+[\w\s]+,\s*\w+,\s*[A-Z]{2}\s*\d{5})', first_page_text)
            
            # Determine report type
            report_type = 'estimate' if 'Repair Pricer' in first_page_text else 'inspection'
            
            # Extract filename from path
            filename = pdf_path.split('/')[-1]
            
            metadata = PDFMetadata(
                filename=filename,
                total_pages=len(pdf_reader.pages),
                report_type=report_type,
                report_number=report_number.group(1) if report_number else None,
                inspection_date=inspection_date.group(1).strip() if inspection_date else None,
                property_address=address.group(1) if address else None
            )
            
            return metadata
        
    except Exception as e:
        print(f"Error extracting metadata from {pdf_path}: {e}")
        # Return minimal metadata on error
        return PDFMetadata(
            filename=pdf_path.split('/')[-1],
            total_pages=0,
            report_type='unknown',
            report_number=None,
            inspection_date=None,
            property_address=None
        )


def extract_additional_metadata(pdf_path: str) -> dict:
    """
    Extract additional metadata that might be useful.
    """
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            metadata = pdf_reader.metadata
            
            additional_info = {
                'title': metadata.get('/Title', '') if metadata else '',
                'author': metadata.get('/Author', '') if metadata else '',
                'subject': metadata.get('/Subject', '') if metadata else '',
                'creator': metadata.get('/Creator', '') if metadata else '',
                'producer': metadata.get('/Producer', '') if metadata else '',
                'creation_date': metadata.get('/CreationDate', '') if metadata else '',
                'modification_date': metadata.get('/ModDate', '') if metadata else '',
                'file_size': len(pdf_reader.pages)
            }
            
            return additional_info
        
    except Exception as e:
        print(f"Error extracting additional metadata: {e}")
        return {}
