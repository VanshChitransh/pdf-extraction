"""
Phase 1.2: Text Cleaning
Fixes common OCR/extraction errors in text fields.
"""

import re
import unicodedata
from typing import Dict, List, Set
from difflib import SequenceMatcher
import logging

logger = logging.getLogger(__name__)


class TextCleaner:
    """Cleans and normalizes extracted text data."""
    
    # Common OCR corrections
    OCR_CORRECTIONS = {
        # Numbers confused with letters
        'roo1': 'roof',
        'wa11': 'wall',
        '0utlet': 'outlet',
        '1eak': 'leak',
        'f1oor': 'floor',
        'cei1ing': 'ceiling',
        'e1ectrical': 'electrical',
        'p1umbing': 'plumbing',
        'rep1ace': 'replace',
        'insta11': 'install',
        
        # Letters confused with numbers
        'O' : '0',  # Only in numeric contexts
        'l': '1',   # Only in numeric contexts
        
        # Common word errors
        'tbe': 'the',
        'tbis': 'this',
        'witb': 'with',
        'tbat': 'that',
        'wbere': 'where',
        'wben': 'when',
        'repai r': 'repair',
        'rep air': 'repair',
        'repa ir': 'repair',
        'inspec tion': 'inspection',
        'inspect ion': 'inspection',
        'recomm end': 'recommend',
        'recommen d': 'recommend',
        
        # Material/component specific
        'HV AC': 'HVAC',
        'A/C': 'AC',
        'wat er': 'water',
        'ele ctrical': 'electrical',
        'plumb ing': 'plumbing',
        'struc tural': 'structural',
    }
    
    # Common terms that should be title case
    TITLE_CASE_ITEMS = {
        'hvac', 'ac', 'gfci', 'afci', 'pex', 'pvc', 'abs', 'csst',
        'led', 'cfl', 'tpo', 'epdm', 'eifs'
    }
    
    def __init__(self):
        """Initialize the text cleaner."""
        self.seen_descriptions = []
    
    def clean_text(self, text: str, preserve_case: bool = False) -> str:
        """
        Clean text with various normalization steps.
        
        Args:
            text: Text to clean
            preserve_case: Whether to preserve original casing
            
        Returns:
            Cleaned text
        """
        if not text or not isinstance(text, str):
            return ""
        
        original_text = text
        
        # Normalize Unicode characters
        text = unicodedata.normalize('NFKD', text)
        
        # Remove control characters but preserve newlines
        text = ''.join(char for char in text if unicodedata.category(char)[0] != 'C' or char in '\n\r\t')
        
        # Normalize whitespace
        text = self._normalize_whitespace(text)
        
        # Apply OCR corrections
        text = self._apply_ocr_corrections(text)
        
        # Fix common punctuation issues
        text = self._fix_punctuation(text)
        
        # Remove excessive repetition
        text = self._remove_repetition(text)
        
        # Normalize casing if requested
        if not preserve_case:
            text = self._normalize_case(text)
        
        # Final cleanup
        text = text.strip()
        
        if text != original_text:
            logger.debug(f"Cleaned text: '{original_text[:50]}...' -> '{text[:50]}...'")
        
        return text
    
    def _normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace while preserving structure."""
        # Replace multiple spaces with single space
        text = re.sub(r' +', ' ', text)
        
        # Replace multiple newlines with double newline
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Remove spaces at line boundaries
        text = re.sub(r' *\n *', '\n', text)
        
        # Remove trailing spaces
        lines = text.split('\n')
        lines = [line.rstrip() for line in lines]
        text = '\n'.join(lines)
        
        return text
    
    def _apply_ocr_corrections(self, text: str) -> str:
        """Apply OCR error corrections."""
        # Word-level corrections
        words = text.split()
        corrected_words = []
        
        for word in words:
            word_lower = word.lower()
            
            # Check if word is in correction dictionary
            if word_lower in self.OCR_CORRECTIONS:
                corrected = self.OCR_CORRECTIONS[word_lower]
                # Preserve original casing pattern
                if word[0].isupper():
                    corrected = corrected.capitalize()
                corrected_words.append(corrected)
            else:
                corrected_words.append(word)
        
        text = ' '.join(corrected_words)
        
        # Pattern-based corrections
        # Fix split words (e.g., "rep air" -> "repair")
        text = re.sub(r'\b(\w+)\s+(\w{1,2})\b', lambda m: m.group(1) + m.group(2) if m.group(2) in ['ed', 'er', 'ly', 'al', 'or', 'ar', 'ir'] else m.group(0), text)
        
        return text
    
    def _fix_punctuation(self, text: str) -> str:
        """Fix common punctuation issues."""
        # Fix spacing around punctuation
        text = re.sub(r'\s+([.,;:!?])', r'\1', text)
        text = re.sub(r'([.,;:!?])([A-Za-z])', r'\1 \2', text)
        
        # Fix ellipsis
        text = re.sub(r'\.\.\.+', '...', text)
        
        # Fix quotes
        text = re.sub(r'"([^"]*)"', r'"\1"', text)
        
        # Remove multiple punctuation
        text = re.sub(r'([!?.]){2,}', r'\1', text)
        
        return text
    
    def _remove_repetition(self, text: str) -> str:
        """Remove excessive word or phrase repetition."""
        # Remove duplicate adjacent words
        text = re.sub(r'\b(\w+)\s+\1\b', r'\1', text, flags=re.IGNORECASE)
        
        # Remove duplicate adjacent phrases (up to 5 words)
        for n in range(5, 1, -1):
            pattern = r'\b(' + r'\s+'.join([r'\w+'] * n) + r')\s+\1\b'
            text = re.sub(pattern, r'\1', text, flags=re.IGNORECASE)
        
        return text
    
    def _normalize_case(self, text: str) -> str:
        """Normalize casing for consistency."""
        # Preserve acronyms and special terms
        words = text.split()
        normalized_words = []
        
        for word in words:
            word_lower = word.lower()
            
            # Check if it's a special term
            if word_lower in self.TITLE_CASE_ITEMS:
                normalized_words.append(word.upper())
            # If all caps and longer than 1 char, might be acronym
            elif word.isupper() and len(word) > 1:
                normalized_words.append(word)
            # Otherwise apply sentence case
            else:
                normalized_words.append(word)
        
        return ' '.join(normalized_words)
    
    def clean_item_name(self, item: str) -> str:
        """
        Clean and normalize item/component names.
        
        Args:
            item: Item name
            
        Returns:
            Cleaned item name in title case
        """
        if not item:
            return ""
        
        # Basic cleaning
        item = self.clean_text(item, preserve_case=True)
        
        # Title case for item names
        item = item.title()
        
        # But preserve acronyms
        for term in self.TITLE_CASE_ITEMS:
            item = re.sub(r'\b' + term + r'\b', term.upper(), item, flags=re.IGNORECASE)
        
        return item
    
    def clean_description(self, description: str) -> str:
        """
        Clean inspection description text.
        
        Args:
            description: Description text
            
        Returns:
            Cleaned description
        """
        if not description:
            return ""
        
        # Apply general cleaning
        description = self.clean_text(description)
        
        # Ensure proper sentence structure
        description = self._ensure_sentence_structure(description)
        
        return description
    
    def _ensure_sentence_structure(self, text: str) -> str:
        """Ensure text has proper sentence structure."""
        if not text:
            return ""
        
        # Capitalize first letter
        if text[0].islower():
            text = text[0].upper() + text[1:]
        
        # Ensure ends with period if not other punctuation
        if text[-1] not in '.!?':
            text += '.'
        
        # Capitalize after periods
        text = re.sub(r'([.!?])\s+([a-z])', lambda m: m.group(1) + ' ' + m.group(2).upper(), text)
        
        return text
    
    def is_duplicate(self, text: str, threshold: float = 0.85) -> bool:
        """
        Check if text is duplicate or very similar to previously seen text.
        
        Args:
            text: Text to check
            threshold: Similarity threshold (0-1)
            
        Returns:
            True if duplicate
        """
        if not text:
            return False
        
        # Normalize for comparison
        normalized = self.clean_text(text.lower())
        
        # Check against previously seen descriptions
        for seen in self.seen_descriptions:
            similarity = SequenceMatcher(None, normalized, seen).ratio()
            if similarity >= threshold:
                logger.debug(f"Found duplicate text (similarity: {similarity:.2f})")
                return True
        
        # Add to seen list
        self.seen_descriptions.append(normalized)
        return False
    
    def clean_issue(self, issue: Dict) -> Dict:
        """
        Clean all text fields in an issue.
        
        Args:
            issue: Issue dictionary
            
        Returns:
            Issue with cleaned text fields
        """
        cleaned = issue.copy()
        
        # Clean title
        if 'title' in cleaned and cleaned['title']:
            cleaned['title'] = self.clean_text(cleaned['title'])
        
        # Clean description
        if 'description' in cleaned and cleaned['description']:
            cleaned['description'] = self.clean_description(cleaned['description'])
        
        # Clean section names
        if 'section' in cleaned and cleaned['section']:
            cleaned['section'] = self.clean_text(cleaned['section'])
        
        if 'subsection' in cleaned and cleaned['subsection']:
            cleaned['subsection'] = self.clean_text(cleaned['subsection'])
        
        # Clean any item/component fields
        if 'item' in cleaned and cleaned['item']:
            cleaned['item'] = self.clean_item_name(cleaned['item'])
        
        return cleaned
    
    def reset_duplicate_tracking(self):
        """Reset the duplicate tracking for a new document."""
        self.seen_descriptions = []

