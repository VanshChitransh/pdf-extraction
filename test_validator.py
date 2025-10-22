"""
Standalone test for the updated DataQualityValidator.
"""

# Import only what we need
import sys
import os
import re
from enum import Enum, auto
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple

# Copy the necessary classes from data_quality_validator.py
class ValidationAction(Enum):
    ACCEPT = auto()
    EXCLUDE = auto()
    FLAG_FOR_REVIEW = auto()
    NORMALIZE_AND_RETRY = auto()

@dataclass
class DataQualityResult:
    valid: bool
    reason: str
    action: ValidationAction
    quality_score: float
    issues_found: List[str]
    suggestions: List[str] = None

# Implement the updated validator with our changes
class DataQualityValidator:
    def __init__(self, strictness_level="normal"):
        # Relaxed parameters as per our changes
        self.MIN_DESCRIPTION_LENGTH = 5  # Reduced from 10
        self.MIN_QUALITY_SCORE = 0.3     # Reduced from 0.5
        self.MIN_ASCII_RATIO = 0.2       # Reduced from 0.8
        self.MAX_SPECIAL_CHAR_RATIO = 0.7  # Increased from 0.3
        
        # Other parameters (unchanged)
        self.strictness_level = strictness_level
        self.metadata_keywords = [
            "page", "of", "report", "inspection", "texas", "real estate", 
            "commission", "property", "prepared", "trec", "promulgated"
        ]
        self.header_patterns = [
            r"^[IVX]+\.\s+",  # Roman numerals
            r"^\d+\.\s+",     # Decimal numbering
            r"^[A-Z]\.\s+",   # Letter numbering
            r"^•\s+",         # Bullet points
            r"^Section\s+\d+", # Section headers
        ]
        self.valid_statuses = ["D", "NP", "NI", "I", "IR", "S", "P"]
        
    def normalize_unicode_text(self, text):
        """
        Aggressively normalize Unicode text to handle PDF extraction artifacts.
        """
        if not text:
            return text
            
        # Replace common problematic characters
        replacements = {
            'þ': 'th',
            'ð': 'd',
            'ø': 'o',
            '·': '•',
            '—': '-',
            '–': '-',
            ''': "'",
            ''': "'",
            '"': '"',
            '"': '"',
            '…': '...',
            '\ufeff': '',  # BOM
            '\u200b': '',  # Zero width space
            '\u200c': '',  # Zero width non-joiner
            '\u200d': '',  # Zero width joiner
            '\u2028': ' ', # Line separator
            '\u2029': ' ', # Paragraph separator
        }
        
        for char, replacement in replacements.items():
            text = text.replace(char, replacement)
        
        # Normalize combining diacritical marks
        text = re.sub(r'[\u0300-\u036f]+', '', text)
        
        # Replace multiple spaces with a single space
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
        
    def validate_issue(self, issue):
        """Validate an issue for quality before estimation."""
        issues_found = []
        suggestions = []
        quality_score = 1.0  # Start with perfect score
        
        # Extract issue data
        description = issue.get("description", "")
        title = issue.get("title", "")
        status = issue.get("status", "")
        
        # Always normalize text first
        normalized_description = self.normalize_unicode_text(description)
        normalized_title = self.normalize_unicode_text(title)
        
        # Check for empty description
        if not normalized_description:
            return DataQualityResult(
                valid=False,
                reason="Empty description",
                action=ValidationAction.EXCLUDE,
                quality_score=0.0,
                issues_found=["Empty description"]
            )
        
        # Check for remaining unicode corruption after normalization
        corruption_status, corruption_reason, corruption_penalty = self._check_unicode_corruption(normalized_description)
        if corruption_status == "severe":
            return DataQualityResult(
                valid=False,
                reason=f"Severe Unicode corruption: {corruption_reason}",
                action=ValidationAction.EXCLUDE,
                quality_score=0.0,
                issues_found=[f"Unicode corruption: {corruption_reason}"]
            )
        elif corruption_status == "moderate":
            quality_score -= corruption_penalty
            issues_found.append(f"Moderate Unicode artifacts: {corruption_reason}")
            suggestions.append("Consider manual review of text")
        
        # Check for metadata/boilerplate content
        if self._is_metadata_content(normalized_description, normalized_title):
            return DataQualityResult(
                valid=False,
                reason="Contains only metadata or boilerplate content",
                action=ValidationAction.EXCLUDE,
                quality_score=0.1,
                issues_found=["Metadata or boilerplate content"]
            )
        
        # Check for minimum description length
        if len(normalized_description) < self.MIN_DESCRIPTION_LENGTH:
            return DataQualityResult(
                valid=False,
                reason=f"Description too short (min {self.MIN_DESCRIPTION_LENGTH} chars)",
                action=ValidationAction.EXCLUDE,
                quality_score=0.2,
                issues_found=["Description too short"]
            )
        
        # Check for valid status code
        if status and status not in self.valid_statuses:
            quality_score -= 0.2
            issues_found.append(f"Invalid status code: {status}")
            suggestions.append(f"Valid status codes: {', '.join(self.valid_statuses)}")
        
        # Final quality check
        if quality_score < self.MIN_QUALITY_SCORE:
            return DataQualityResult(
                valid=False,
                reason=f"Quality score too low: {quality_score:.2f}",
                action=ValidationAction.EXCLUDE,
                quality_score=quality_score,
                issues_found=issues_found,
                suggestions=suggestions
            )
        
        return DataQualityResult(
            valid=True,
            reason="Passed all quality checks",
            action=ValidationAction.ACCEPT,
            quality_score=quality_score,
            issues_found=issues_found,
            suggestions=suggestions
        )
    
    def _check_unicode_corruption(self, text):
        """
        Check for Unicode corruption in text.
        Returns (status, reason, penalty) where status is "none", "moderate", or "severe"
        """
        if not text:
            return "none", "", 0.0
            
        # Check for severe corruption indicators that would still cause failure
        if '\ufffd' in text or '\x00' in text:
            return "severe", "Contains replacement character or null byte", 1.0
            
        # Count ASCII vs non-ASCII characters
        ascii_count = sum(1 for c in text if ord(c) < 128)
        total_chars = len(text)
        
        if total_chars == 0:
            return "none", "", 0.0
            
        ascii_ratio = ascii_count / total_chars
        
        # Count special characters
        special_chars = sum(1 for c in text if not c.isalnum() and not c.isspace())
        special_char_ratio = special_chars / total_chars if total_chars > 0 else 0
        
        # Check for combining diacritical marks
        combining_marks = len(re.findall(r'[\u0300-\u036f]', text))
        
        # Apply penalties instead of outright failing
        if ascii_ratio < self.MIN_ASCII_RATIO:
            penalty = 0.3 * (1 - (ascii_ratio / self.MIN_ASCII_RATIO))
            return "moderate", f"Low ASCII ratio ({ascii_ratio:.2f})", penalty
            
        if special_char_ratio > self.MAX_SPECIAL_CHAR_RATIO:
            penalty = 0.3 * (special_char_ratio / self.MAX_SPECIAL_CHAR_RATIO)
            return "moderate", f"High special character ratio ({special_char_ratio:.2f})", penalty
            
        if combining_marks > 5:
            penalty = 0.2 * (combining_marks / 10)
            return "moderate", f"Multiple combining diacritical marks ({combining_marks})", penalty
            
        return "none", "", 0.0
    
    def _is_metadata_content(self, description, title):
        """Check if text is metadata or boilerplate content."""
        # Check for section/ID indicators
        if re.search(r'^(section|page|id|ref)[\s\:\.]+\d+', description.lower()):
            return True
            
        # Check for metadata keywords
        metadata_count = sum(1 for keyword in self.metadata_keywords if keyword.lower() in description.lower())
        if metadata_count >= 3 and len(description) < 100:
            return True
            
        # Check for disclaimer-like patterns
        if re.search(r'(this report|this document|disclaimer|copyright|all rights reserved)', description.lower()):
            if len(description) < 150:  # Short disclaimers
                return True
                
        # Make sure we don't exclude actual issue descriptions
        issue_indicators = ['defect', 'damage', 'broken', 'leak', 'crack', 'worn', 'missing', 'observed']
        if any(indicator in description.lower() for indicator in issue_indicators):
            return False
            
        return False

def test_validator():
    """Test the updated validator with sample data."""
    print("Testing updated DataQualityValidator...")
    
    # Create validator
    validator = DataQualityValidator()
    
    # Sample issues with problematic text that would have been filtered before
    test_issues = [
        {
            "id": "test1",
            "title": "ROOF SURFACE: Older roof",
            "description": "Observed curled ends, and/or excessive granular loss of shingles. Soft spot observed at roof decking...",
            "status": "D"
        },
        {
            "id": "test2",
            "title": "· indicate an item as Deficient (D)",
            "description": "Observed multiple plug-in fragrance devices...",
            "status": "D"
        },
        {
            "id": "test3",
            "title": "HVAC system",
            "description": "HVAC system 12 years old, refrigerant level low...",
            "status": "D"
        },
        {
            "id": "test4",
            "title": "þ Plumbing issue",
            "description": "þ Observed leak under sink with water damage to cabinet.",
            "status": "D"
        },
        {
            "id": "test5",
            "title": "Comments:",
            "description": "Page 10 of 34 REI 7-6 (8/9/21) Promulgated by the Texas Real Estate Commission",
            "status": "I"
        }
    ]
    
    # Test each issue
    results = []
    for i, issue in enumerate(test_issues):
        print(f"\nTesting issue {i+1}: {issue['title']}")
        result = validator.validate_issue(issue)
        
        print(f"  Valid: {result.valid}")
        print(f"  Reason: {result.reason}")
        print(f"  Action: {result.action}")
        print(f"  Quality score: {result.quality_score:.2f}")
        print(f"  Issues found: {result.issues_found}")
        
        results.append({
            "issue_id": issue["id"],
            "valid": result.valid,
            "action": str(result.action),
            "quality_score": result.quality_score
        })
    
    # Print summary
    valid_count = sum(1 for r in results if r["valid"])
    print(f"\nSUMMARY: {valid_count}/{len(results)} issues passed validation ({valid_count/len(results)*100:.1f}%)")
    
    return results

if __name__ == "__main__":
    test_validator()