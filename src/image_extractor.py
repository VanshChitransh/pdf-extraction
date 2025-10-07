"""
Image extraction with context and OCR.
"""
import os
from PIL import Image
import pytesseract
from typing import List, Optional, Tuple
from .models import ExtractedImage


def extract_images_with_context(pdf_path: str, output_dir: str) -> List[ExtractedImage]:
    """
    Extract images and link them to their context.
    This is crucial for understanding WHAT the image shows.
    Note: This is a simplified version without PyMuPDF - images will be extracted as page images.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    images = []
    
    try:
        # For now, we'll convert each page to an image since we don't have PyMuPDF
        # This is a simplified approach - in production you'd want proper image extraction
        from pdf2image import convert_from_path
        
        # Convert PDF pages to images
        pages = convert_from_path(pdf_path)
        
        for page_num, page_image in enumerate(pages):
            # Save page as image
            image_filename = f"page{page_num+1}_full.png"
            image_path = os.path.join(output_dir, image_filename)
            page_image.save(image_path, 'PNG')
            
            # Get image bytes
            with open(image_path, 'rb') as f:
                image_bytes = f.read()
            
            # OCR the page image
            ocr_text = perform_ocr(image_path)
            
            # Try to find caption from OCR text
            caption = extract_caption(ocr_text)
            
            # Determine section from OCR text
            section = determine_section_from_text(ocr_text, ocr_text)
            
            images.append(ExtractedImage(
                page_num=page_num + 1,
                image_index=1,  # Only one image per page in this simplified version
                image_data=image_bytes,
                image_path=image_path,
                caption=caption,
                related_section=section,
                related_text=ocr_text or "",
                bbox=None,  # No bounding box info without PyMuPDF
                ocr_text=ocr_text
            ))
    
    except Exception as e:
        print(f"Error extracting images from {pdf_path}: {e}")
        # Fallback: create empty list
        return []
    
    return images


def extract_text_near_bbox(page, bbox: Optional[Tuple[float, float, float, float]], distance: int = 100) -> str:
    """
    Extract text within 'distance' points of the image.
    """
    if not bbox:
        return ""
    
    try:
        # Expand bbox by distance
        x0, y0, x1, y1 = bbox
        search_bbox = (
            max(0, x0 - distance),
            max(0, y0 - distance),
            x1 + distance,
            y1 + distance
        )
        
        # Extract text within expanded bbox
        text = page.get_textbox(search_bbox)
        return text.strip()
    
    except Exception:
        return ""


def perform_ocr(image_path: str) -> Optional[str]:
    """
    OCR the image to extract any embedded text.
    """
    try:
        img = Image.open(image_path)
        text = pytesseract.image_to_string(img)
        return text.strip() if text.strip() else None
    except Exception as e:
        print(f"OCR failed for {image_path}: {e}")
        return None


def extract_caption(text: str) -> Optional[str]:
    """
    Look for common caption patterns.
    """
    if not text:
        return None
    
    # Look for short sentences after colons or in first line
    lines = text.split('\n')
    for line in lines[:3]:  # Check first 3 lines
        line = line.strip()
        if len(line) < 100 and ':' not in line and line:
            return line
    
    # Look for text that might be a caption (short, descriptive)
    for line in lines:
        line = line.strip()
        if 10 < len(line) < 80 and not any(char.isdigit() for char in line[:5]):
            return line
    
    return None


def determine_section_from_text(page_text: str, related_text: str) -> str:
    """
    Determine which section an image belongs to based on surrounding text.
    """
    if not page_text:
        return "UNKNOWN"
    
    # Look for section headers in page text
    import re
    lines = page_text.split('\n')
    
    current_section = None
    for line in lines:
        line = line.strip()
        # Match Roman numeral sections
        section_match = re.match(r'^([IVX]+)\.\s+(.+)$', line)
        if section_match:
            current_section = line
            break
    
    # If we found a section, return it
    if current_section:
        return current_section
    
    # Otherwise, try to infer from related text
    if related_text:
        # Look for keywords that might indicate section
        related_lower = related_text.lower()
        if any(keyword in related_lower for keyword in ['foundation', 'structural', 'beam']):
            return "STRUCTURAL SYSTEMS"
        elif any(keyword in related_lower for keyword in ['electrical', 'wiring', 'outlet']):
            return "ELECTRICAL SYSTEMS"
        elif any(keyword in related_lower for keyword in ['plumbing', 'pipe', 'drain']):
            return "PLUMBING SYSTEMS"
        elif any(keyword in related_lower for keyword in ['hvac', 'heating', 'cooling']):
            return "HEATING, VENTILATION AND AIR CONDITIONING SYSTEMS"
    
    return "UNKNOWN"


def validate_image(image_path: str) -> bool:
    """
    Validate that an extracted image is valid and readable.
    """
    try:
        with Image.open(image_path) as img:
            # Check if image has reasonable dimensions
            width, height = img.size
            if width < 50 or height < 50:
                return False
            
            # Check if image is not too large (memory concerns)
            if width > 5000 or height > 5000:
                return False
            
            # Try to load the image data
            img.load()
            return True
    
    except Exception:
        return False


def get_image_metadata(image_path: str) -> dict:
    """
    Extract metadata from an image file.
    """
    try:
        with Image.open(image_path) as img:
            return {
                'format': img.format,
                'mode': img.mode,
                'size': img.size,
                'width': img.width,
                'height': img.height,
                'has_transparency': 'transparency' in img.info
            }
    except Exception:
        return {}


def optimize_image_for_ocr(image_path: str, output_path: str) -> bool:
    """
    Optimize image for better OCR results.
    """
    try:
        with Image.open(image_path) as img:
            # Convert to grayscale for better OCR
            if img.mode != 'L':
                img = img.convert('L')
            
            # Increase contrast
            from PIL import ImageEnhance
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(2.0)
            
            # Save optimized image
            img.save(output_path)
            return True
    
    except Exception as e:
        print(f"Error optimizing image {image_path}: {e}")
        return False
