"""
Structured text extraction with hierarchy preservation.
"""
import re
import pdfplumber
from typing import List, Dict, Tuple, Optional
from .models import TextBlock


def extract_structured_text(pdf_path: str) -> List[TextBlock]:
    """
    Extract text while preserving hierarchical structure.
    This is critical for maintaining context.
    """
    blocks = []
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            current_section = None
            current_subsection = None
            
            for page_num, page in enumerate(pdf.pages, 1):
                # Extract text with layout preservation
                text = page.extract_text(layout=True)
                
                # Also get detailed word-level data for formatting detection
                words = page.extract_words(extra_attrs=['fontname', 'size'])
                
                # Parse into structured blocks
                lines = text.split('\n')
                
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Detect section headers (Roman numerals)
                    section_match = re.match(r'^([IVX]+)\.\s+(.+)$', line)
                    if section_match:
                        current_section = line
                        current_subsection = None
                        continue
                    
                    # Detect subsections (A, B, C, etc.)
                    subsection_match = re.match(r'^([A-Z])\.\s+(.+)$', line)
                    if subsection_match:
                        current_subsection = line
                        continue
                    
                    # Detect status indicators (various checkbox patterns)
                    status = detect_status_indicators(line)
                    
                    # Detect formatting (bold = high priority, underline = medium)
                    formatting = detect_formatting(line, words, page_num)
                    
                    # Get bounding box for the text
                    bbox = get_text_bbox(line, page, words)
                    
                    blocks.append(TextBlock(
                        page_num=page_num,
                        section=current_section or "HEADER",
                        subsection=current_subsection or "",
                        status=status,
                        content=line,
                        bbox=bbox,
                        formatting=formatting
                    ))
    
    except Exception as e:
        print(f"Error extracting structured text from {pdf_path}: {e}")
        # Fallback to simple text extraction
        return extract_text_simple(pdf_path)
    
    return blocks


def detect_status_indicators(line: str) -> Optional[str]:
    """
    Detect status indicators in text lines.
    """
    # Common checkbox patterns in inspection reports
    checkbox_patterns = [
        r'\b([þ✓]|¨)\s*([þ✓]|¨)\s*([þ✓]|¨)\s*([þ✓]|¨)',  # Four checkboxes
        r'\b([þ✓]|¨)\s*([þ✓]|¨)\s*([þ✓]|¨)',  # Three checkboxes
        r'\b([þ✓]|¨)\s*([þ✓]|¨)',  # Two checkboxes
        r'\b([þ✓]|¨)',  # Single checkbox
        r'\b([DINP])\b',  # Direct status letters
    ]
    
    for pattern in checkbox_patterns:
        match = re.search(pattern, line)
        if match:
            groups = match.groups()
            if len(groups) == 4:  # Four checkboxes
                status_map = ['I', 'NI', 'NP', 'D']
                status = [status_map[i] for i, cb in enumerate(groups) if cb in ['þ', '✓']]
                return status[0] if status else None
            elif len(groups) == 3:  # Three checkboxes
                status_map = ['I', 'NI', 'D']
                status = [status_map[i] for i, cb in enumerate(groups) if cb in ['þ', '✓']]
                return status[0] if status else None
            elif len(groups) == 2:  # Two checkboxes
                status_map = ['I', 'D']
                status = [status_map[i] for i, cb in enumerate(groups) if cb in ['þ', '✓']]
                return status[0] if status else None
            elif len(groups) == 1:  # Single checkbox or direct status
                if groups[0] in ['þ', '✓']:
                    return 'I'  # Inspected
                elif groups[0] in ['D', 'I', 'N', 'P']:
                    return groups[0]
    
    return None


def detect_formatting(text: str, words: List[dict], page_num: int) -> Dict[str, bool]:
    """
    Detect if text is bold, italic, or underlined.
    This helps prioritize issues.
    """
    # Find words that match our text
    matching_words = [w for w in words if w['text'] in text]
    
    if not matching_words:
        return {'bold': False, 'italic': False, 'underlined': False}
    
    # Check font properties
    font_names = [w['fontname'].lower() for w in matching_words if w.get('fontname')]
    font_sizes = [w['size'] for w in matching_words if w.get('size')]
    
    # Determine if text is bold (usually indicated by font name or size)
    is_bold = any('bold' in fn for fn in font_names) or \
              any('black' in fn for fn in font_names) or \
              (font_sizes and max(font_sizes) > 12)  # Larger font might indicate emphasis
    
    is_italic = any('italic' in fn for fn in font_names) or \
                any('oblique' in fn for fn in font_names)
    
    # Underline detection would require more complex analysis
    is_underlined = False
    
    return {
        'bold': is_bold,
        'italic': is_italic,
        'underlined': is_underlined
    }


def get_text_bbox(text: str, page, words: List[dict]) -> Tuple[float, float, float, float]:
    """
    Get bounding box for text on the page.
    """
    # Find words that match our text
    matching_words = [w for w in words if w['text'] in text]
    
    if not matching_words:
        return (0.0, 0.0, 0.0, 0.0)
    
    # Calculate bounding box from word positions
    x0 = min(w['x0'] for w in matching_words)
    y0 = min(w['top'] for w in matching_words)
    x1 = max(w['x1'] for w in matching_words)
    y1 = max(w['bottom'] for w in matching_words)
    
    return (x0, y0, x1, y1)


def extract_text_simple(pdf_path: str) -> List[TextBlock]:
    """
    Fallback simple text extraction when structured extraction fails.
    """
    blocks = []
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                text = page.extract_text()
                if text:
                    lines = text.split('\n')
                    for line in lines:
                        line = line.strip()
                        if line:
                            blocks.append(TextBlock(
                                page_num=page_num,
                                section="UNKNOWN",
                                subsection="",
                                status=None,
                                content=line,
                                bbox=(0.0, 0.0, 0.0, 0.0),
                                formatting={'bold': False, 'italic': False, 'underlined': False}
                            ))
    except Exception as e:
        print(f"Error in simple text extraction: {e}")
    
    return blocks


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
