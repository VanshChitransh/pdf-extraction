"""
Phase 1 Enhancement: Pre-Estimation Data Quality Validation

Validates issue data BEFORE sending to AI estimation to:
- Reduce wasted API calls by 15-20%
- Improve estimation accuracy
- Prevent nonsensical results reaching users

Features:
- Unicode/encoding corruption detection
- Metadata/boilerplate content filtering
- Minimum viable content checks
- Status code validation
- Semantic meaningfulness scoring
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import re
import unicodedata
import logging

logger = logging.getLogger(__name__)


class ValidationAction(Enum):
    """Actions to take based on validation results."""
    ACCEPT = "accept"
    EXCLUDE = "exclude_from_estimation"
    FLAG_FOR_REVIEW = "flag_for_human_review"
    NORMALIZE_AND_RETRY = "normalize_or_exclude"


@dataclass
class DataQualityResult:
    """Result of data quality validation."""
    valid: bool
    reason: str
    action: ValidationAction
    quality_score: float  # 0.0-1.0
    issues_found: List[str]
    suggestions: List[str]


class DataQualityValidator:
    """
    Validates issue data quality before AI estimation.
    
    Checks:
    1. Unicode/encoding integrity
    2. Non-metadata content
    3. Minimum description length and quality
    4. Valid status codes
    5. Semantic meaningfulness
    
    Usage:
        validator = DataQualityValidator()
        result = validator.validate_issue(issue)
        
        if result.valid:
            # Proceed with estimation
        elif result.action == ValidationAction.EXCLUDE:
            # Skip this issue
        elif result.action == ValidationAction.FLAG_FOR_REVIEW:
            # Mark for manual review
    """
    
    # Metadata keywords that indicate boilerplate content
    METADATA_KEYWORDS = [
        'contractual time limitations',
        'qualified service professionals',
        'option periods',
        'prior to the expiration',
        'it is recommended that',
        'the inspector is not required',
        'responsibility of the client',
        'indicate an item as deficient',
        'adversely and materially affects',
        'as specified by the sops',
        'does not constitute',
        'this report',
        'inspection standards',
        'limitations of inspection',
    ]
    
    # Common header/section markers (STRENGTHENED for Phase 1)
    HEADER_PATTERNS = [
        r'^comments?:?\s*$',
        r'^note:?\s*$',
        r'^notes?:?\s*$',
        r'^important:?\s*$',
        r'^disclaimer:?\s*$',
        r'^observations?:?\s*$',
        r'^findings?:?\s*$',
        r'^summary:?\s*$',
        r'^recommendations?:?\s*$',
        r'^overview:?\s*$',
        r'^inspection notes?:?\s*$',
        r'^general:?\s*$',
        r'^[ivx]+\.\s*[A-Z\s]+$',  # Roman numerals + caps (section headers)
        r'^[A-Z\s]+:?\s*$',  # All caps (likely header)
        r'^\d+\.\s*[A-Z\s]+$',  # Numbered section headers
    ]
    
    # Valid status codes
    VALID_STATUSES = {'D', 'I', 'NI', 'NP', 'Deficient', 'Inspected', 'Not Inspected', 'Not Present'}
    
    # Minimum quality thresholds
    # RELAXED (Oct 2025): Reducing false positives from PDF extraction artifacts
    MIN_DESCRIPTION_LENGTH = 5         # Further reduced from 10 to allow shorter valid descriptions
    MIN_QUALITY_SCORE = 0.3            # Reduced from 0.5 to allow more issues through
    MIN_ASCII_RATIO = 0.2              # Was 0.3 - now allows 80% non-ASCII
    MAX_SPECIAL_CHAR_RATIO = 0.7       # Was 0.5 - now allows 70% special chars
    
    def __init__(self, strict_mode: bool = False):
        """
        Initialize validator.
        
        Args:
            strict_mode: If True, apply stricter quality thresholds
        """
        self.strict_mode = strict_mode
        if strict_mode:
            self.MIN_DESCRIPTION_LENGTH = 20
            self.MIN_QUALITY_SCORE = 0.6
        
        self.stats = {
            'total_validated': 0,
            'passed': 0,
            'failed': 0,
            'excluded': 0,
            'flagged_for_review': 0,
            'failure_reasons': {}
        }
    
    def validate_issue(self, issue: Dict[str, Any]) -> DataQualityResult:
        """
        Validate a single issue for data quality.
        
        Args:
            issue: Issue dictionary with at minimum 'description' and 'status'
            
        Returns:
            DataQualityResult with validation outcome
        """
        self.stats['total_validated'] += 1
        
        issues_found = []
        suggestions = []
        quality_score = 1.0
        
        # Extract key fields
        description = issue.get('description', '').strip()
        title = issue.get('title', '').strip()
        status = issue.get('status', '')
        section = issue.get('section', '')
        issue_id = issue.get('id', 'unknown')
        
        # Check 1: Empty or missing description
        if not description:
            self._update_stats('failed', 'empty_description')
            return DataQualityResult(
                valid=False,
                reason="Empty or missing description",
                action=ValidationAction.EXCLUDE,
                quality_score=0.0,
                issues_found=["No description provided"],
                suggestions=["Ensure extraction captured description text"]
            )
        
        # Check 2: Unicode/encoding corruption
        # Always normalize first to fix common issues
        try:
            from src.text_extractor import normalize_unicode_text
            description = normalize_unicode_text(description)
            title = normalize_unicode_text(title)
        except (ImportError, Exception) as e:
            # Fallback to basic normalization if import fails
            import unicodedata as _unicodedata
            try:
                description = _unicodedata.normalize('NFKD', description)
                title = _unicodedata.normalize('NFKD', title)
            except Exception:
                pass  # Keep original text if normalization fails
        
        # Then check for any remaining corruption AFTER normalization
        corruption_result = self._check_unicode_corruption(description, title)
        
        # After normalization, only exclude if STILL severely corrupted
        # This prevents false positives from PDF extraction artifacts
        if corruption_result['corrupted'] and corruption_result['severity'] == 'severe':
            # Check if corruption is REALLY severe (multiple indicators)
            severe_indicators = [
                '\ufffd' in description or '\ufffd' in title,  # Replacement char (true corruption)
                '\x00' in description or '\x00' in title,      # Null bytes (true corruption)
            ]
            
            if any(severe_indicators):
                # TRUE corruption that normalization couldn't fix
                issues_found.append(f"Text has severe encoding issues: {corruption_result['reason']}")
                quality_score -= 0.5
                # Still continue validation - only exclude if combined with other issues
            else:
                # Likely false positive - just apply small penalty
                issues_found.append(f"Text has unusual characters: {corruption_result['reason']}")
                quality_score -= 0.1
        else:
            # Just apply the penalty if any
            if corruption_result['penalty'] > 0:
                issues_found.append(f"Text had minor encoding issues (fixed): {corruption_result['reason']}")
            quality_score -= min(0.1, corruption_result['penalty'])  # Cap penalty at 0.1
        
        # Check 3: Metadata/boilerplate content
        if self._is_metadata_content(description, title, section, issue_id):
            self._update_stats('failed', 'metadata_content')
            return DataQualityResult(
                valid=False,
                reason="Metadata or boilerplate content, not actionable issue",
                action=ValidationAction.EXCLUDE,
                quality_score=0.1,
                issues_found=["Contains boilerplate/header text"],
                suggestions=["Filter during extraction phase", "Improve table parsing logic"]
            )
        
        # NEW: Check 3b: Explicit non-issue/affirmative statements (e.g., "No issues observed")
        if self._is_non_issue_statement(description):
            self._update_stats('failed', 'non_issue_statement')
            return DataQualityResult(
                valid=False,
                reason="Affirmative non-issue statement (no action needed)",
                action=ValidationAction.EXCLUDE,
                quality_score=0.9,
                issues_found=["Non-issue affirmation detected"],
                suggestions=["Do not send to estimation; skip"]
            )
        
        # Check 4: Minimum description length
        if len(description) < self.MIN_DESCRIPTION_LENGTH:
            issues_found.append(f"Description too short ({len(description)} chars)")
            quality_score -= 0.3
            if self.strict_mode:
                self._update_stats('failed', 'insufficient_description')
                return DataQualityResult(
                    valid=False,
                    reason=f"Description too short ({len(description)} chars, minimum {self.MIN_DESCRIPTION_LENGTH})",
                    action=ValidationAction.FLAG_FOR_REVIEW,
                    quality_score=quality_score,
                    issues_found=issues_found,
                    suggestions=["Manual review needed", "Check if extraction truncated content"]
                )
        
        # Check 5: Status validation
        if status not in self.VALID_STATUSES:
            issues_found.append(f"Invalid status code: '{status}'")
            suggestions.append("Normalize status or exclude")
            quality_score -= 0.2
            if self.strict_mode:
                self._update_stats('failed', 'invalid_status')
                return DataQualityResult(
                    valid=False,
                    reason=f"Invalid status code '{status}'",
                    action=ValidationAction.NORMALIZE_AND_RETRY,
                    quality_score=quality_score,
                    issues_found=issues_found,
                    suggestions=suggestions
                )
        
        # Check 6: Semantic meaningfulness
        meaning_score = self._assess_semantic_meaning(description)
        if meaning_score < 0.3:
            issues_found.append("Low semantic meaningfulness score")
            quality_score -= 0.3
        quality_score = max(0.0, quality_score - (1.0 - meaning_score) * 0.2)
        
        # Check 7: Header-like content (Phase 1 Enhancement: More definitive exclusion)
        if self._looks_like_header(title, description):
            issues_found.append("Appears to be section header, not issue")
            # Phase 1: Immediately exclude headers without waiting for quality threshold
            self._update_stats('failed', 'header_content')
            return DataQualityResult(
                valid=False,
                reason="Content appears to be section header, not actionable issue",
                action=ValidationAction.EXCLUDE,
                quality_score=0.2,  # Low score for headers
                issues_found=issues_found,
                suggestions=["Filter headers during extraction"]
            )
        
        # Final quality check
        if quality_score < self.MIN_QUALITY_SCORE:
            self._update_stats('failed', 'low_quality_score')
            return DataQualityResult(
                valid=False,
                reason=f"Quality score too low ({quality_score:.2f})",
                action=ValidationAction.FLAG_FOR_REVIEW,
                quality_score=quality_score,
                issues_found=issues_found,
                suggestions=suggestions or ["Manual review recommended"]
            )
        
        # Passed validation
        self._update_stats('passed', None)
        
        # But flag for review if score is borderline
        if quality_score < 0.7:
            suggestions.append("Consider manual review due to borderline quality")
        
        return DataQualityResult(
            valid=True,
            reason="Passed quality validation",
            action=ValidationAction.ACCEPT,
            quality_score=quality_score,
            issues_found=issues_found,
            suggestions=suggestions
        )
    
    def _check_unicode_corruption(self, description: str, title: str) -> Dict[str, Any]:
        """
        Detect Unicode/encoding corruption.
        
        Returns:
            Dict with 'corrupted' (bool), 'reason' (str), 'severity' (str), 'penalty' (float)
        """
        text = f"{title} {description}"
        
        # Check for specific corruption patterns
        corruption_indicators = {
            'þ': "Icelandic thorn character (likely corruption)",
            'Þ': "Icelandic thorn character (likely corruption)",
            '\u0308': "Combining diacritical mark without base character",
            '\ufffd': "Unicode replacement character (encoding error)",
            '\x00': "Null byte in text"
        }
        
        for char, reason in corruption_indicators.items():
            if char in text:
                return {'corrupted': True, 'reason': reason, 'severity': 'severe', 'penalty': 0.3}
        
        # Check ASCII ratio
        ascii_count = sum(1 for c in text if ord(c) < 128)
        ascii_ratio = ascii_count / len(text) if text else 1.0
        
        if ascii_ratio < self.MIN_ASCII_RATIO:
            return {
                'corrupted': True,
                'reason': f"Too many non-ASCII characters ({ascii_ratio:.1%} ASCII)",
                'severity': 'moderate',
                'penalty': 0.3
            }
        
        # Check for excessive special characters
        special_chars = sum(1 for c in text if unicodedata.category(c).startswith('P') or unicodedata.category(c).startswith('S'))
        special_ratio = special_chars / len(text) if text else 0.0
        
        if special_ratio > self.MAX_SPECIAL_CHAR_RATIO:
            # High special char ratio - penalize but don't fail
            return {
                'corrupted': False,
                'reason': 'High special character ratio',
                'severity': 'minor',
                'penalty': 0.2
            }
        
        # Check for garbled text patterns (repeated diacritics, etc.)
        if re.search(r'[\u0300-\u036f]{3,}', text):  # 3+ combining diacriticals in a row
            return {
                'corrupted': True,
                'reason': "Excessive combining diacritical marks",
                'severity': 'moderate',
                'penalty': 0.2
            }
        
        return {'corrupted': False, 'reason': '', 'severity': 'none', 'penalty': 0}
    
    def _is_metadata_content(self, description: str, title: str, section: str, issue_id: str) -> bool:
        """
        Detect if content is metadata/boilerplate rather than an actionable issue.
        
        Returns:
            True if this is metadata, False if it's a real issue
        """
        # Check section/ID
        if section.upper() == 'HEADER' or 'HEADER' in issue_id.upper():
            return True
        
        # Check for metadata keywords
        text_lower = f"{title} {description}".lower()
        for keyword in self.METADATA_KEYWORDS:
            if keyword in text_lower:
                return True
        
        # Check for disclaimer-like patterns
        if any(phrase in text_lower for phrase in [
            'the inspector',
            'this report',
            'is not required to',
            'does not include',
            'limitations',
            'disclaimer',
        ]):
            # But allow if it seems like actual issue description
            if not any(word in text_lower for word in [
                'repair', 'replace', 'damaged', 'missing', 'leak', 'crack',
                'worn', 'rusted', 'broken', 'defect', 'recommend', 'install'
            ]):
                return True
        
        return False
    
    def _is_non_issue_statement(self, description: str) -> bool:
        """Detect explicit non-issue affirmations, e.g., 'No issues observed', 'Functional', etc."""
        desc = description.lower().strip()
        non_issue_patterns = [
            r"\bno\s+(significant\s+)?(issues|deficiencies|damage|leaks?|moisture|hazards?)\s+(observed|detected|noted|found)\b",
            r"\bno\s+(active\s+)?(leaks?|moisture)\b",
            r"\bperforming\s+its\s+intended\s+function\b",
            r"\boperating\s+as\s+designed\b",
            r"\bfunctional\b",
            r"\bsatisfactory\b",
            r"\bwithin\s+normal\s+limits\b",
            r"\bno\s+significant\s+deficiencies\b",
            r"\bno\s+(apparent\s+)?(problems|concerns)\b",
        ]
        for pat in non_issue_patterns:
            if re.search(pat, desc):
                return True
        return False
    
    def _looks_like_header(self, title: str, description: str) -> bool:
        """Check if content looks like a section header (STRENGTHENED for Phase 1)."""
        # Check title patterns
        # Note: Some patterns are case-sensitive (all-caps checks), others are case-insensitive
        case_insensitive_patterns = [
            r'^comments?:?\s*$',
            r'^note:?\s*$',
            r'^notes?:?\s*$',
            r'^important:?\s*$',
            r'^disclaimer:?\s*$',
            r'^observations?:?\s*$',
            r'^findings?:?\s*$',
            r'^summary:?\s*$',
            r'^recommendations?:?\s*$',
            r'^overview:?\s*$',
            r'^inspection notes?:?\s*$',
            r'^general:?\s*$',
        ]
        
        case_sensitive_patterns = [
            r'^[ivx]+\.\s*[A-Z\s]+$',  # Roman numerals + caps (section headers)
            r'^[A-Z\s]+:?\s*$',  # All caps (likely header)
            r'^\d+\.\s*[A-Z\s]+$',  # Numbered section headers
        ]
        
        for pattern in case_insensitive_patterns:
            if re.match(pattern, title, re.IGNORECASE):
                return True
            if re.match(pattern, description, re.IGNORECASE):
                return True
        
        for pattern in case_sensitive_patterns:
            if re.match(pattern, title):  # Case-sensitive!
                return True
            if re.match(pattern, description):
                return True
        
        # All caps title with short description
        if title and title.isupper() and len(description) < 30:
            return True
        
        # Title and description are identical and short
        if title == description and len(title) < 50:
            return True
        
        # Title is just a single word (optionally followed by colon)
        # Catches: "Comments:", "Note:", "Important:", "Observations", etc.
        title_stripped = title.strip()
        words_in_title = title_stripped.replace(':', '').strip().split()
        
        # Single-word titles (with or without colon) that are likely headers
        if len(words_in_title) == 1:
            single_word = words_in_title[0].lower()
            header_words = ['comment', 'comments', 'note', 'notes', 'observation', 
                           'observations', 'finding', 'findings', 'important', 
                           'summary', 'overview', 'general', 'recommendation', 
                           'recommendations', 'disclaimer']
            if single_word in header_words:
                return True
        
        # Title is all caps with 2-3 words and looks like a section header
        # (e.g., "GENERAL FINDINGS", "IMPORTANT NOTES")
        if title_stripped.isupper() and 2 <= len(words_in_title) <= 3:
            # Check if description also explicitly indicates it's a section
            section_indicators = ['section for', 'brief note', 'for your information', 
                                 'please note', 'refer to']
            if any(indicator in description.lower() for indicator in section_indicators):
                return True
            # Or if description is very short and just repeats/explains the header
            if len(description) < 40:
                return True
        
        # Description starts with "Comments:" or similar followed by actual content
        # This catches cases like: "Comments: Dryer vent contains lint buildup..."
        if re.match(r'^(comments?|notes?|observations?|findings?|important):\s+', description, re.IGNORECASE):
            # Check if this is ONLY a header (short) or has substantial content after
            content_after = re.sub(r'^(comments?|notes?|observations?|findings?|important):\s+', '', description, flags=re.IGNORECASE)
            
            # If very short, likely just a header
            if len(content_after) < 15:
                return True
            
            # ENHANCEMENT: Check if content after header describes an actual issue
            # Keywords that indicate this is a REAL issue, not just a header
            issue_keywords = [
                'damaged', 'broken', 'cracked', 'leak', 'missing', 'worn',
                'high', 'low', 'incorrect', 'improper', 'not', 'should',
                'recommend', 'repair', 'replace', 'too', 'excessive',
                'insufficient', 'deficient', 'deteriorat', 'rust', 'corroded'
            ]
            
            content_lower = content_after.lower()
            has_issue_keyword = any(keyword in content_lower for keyword in issue_keywords)
            
            # If it has issue keywords AND is long enough, it's likely a real issue
            if has_issue_keyword and len(content_after) > 30:
                return False  # NOT a header, it's a real issue!
            elif len(content_after) < 30:
                return True  # Short and no issue keywords = header
        
        # Title contains only "general" + another word (e.g., "GENERAL FINDINGS", "General Notes")
        if re.match(r'^general\s+\w+\s*$', title.strip(), re.IGNORECASE):
            return True
        
        # Description is very short and ends with colon (section marker)
        if len(description) < 20 and description.strip().endswith(':'):
            return True
        
        # Description is just a copy of title with minor changes (indicates header)
        if title.lower().strip() in description.lower().strip() and len(description) < 60:
            # Check if there's actual actionable content beyond the title repetition
            has_action_words = any(word in description.lower() for word in [
                'repair', 'replace', 'fix', 'install', 'damaged', 'leak', 'crack'
            ])
            if not has_action_words:
                return True
        
        # Check for common non-actionable phrases that indicate metadata
        non_actionable_phrases = [
            'for your information',
            'please note',
            'inspector recommends',
            'refer to',
            'see section',
            'as noted',
            'section for',
            'brief note',
        ]
        desc_lower = description.lower()
        if any(phrase in desc_lower for phrase in non_actionable_phrases) and len(description) < 100:
            # Short descriptions with these phrases are likely headers/notes
            return True
        
        return False
    
    def _assess_semantic_meaning(self, text: str) -> float:
        """
        Assess semantic meaningfulness of text.
        
        Returns:
            Score from 0.0 (meaningless) to 1.0 (highly meaningful)
        """
        if not text:
            return 0.0
        
        score = 0.5  # Start neutral
        
        # Check for actionable keywords (good sign)
        actionable_keywords = [
            'repair', 'replace', 'install', 'fix', 'damaged', 'missing',
            'leak', 'crack', 'broken', 'worn', 'rusted', 'defect',
            'recommend', 'maintain', 'seal', 'clean', 'adjust', 'service'
        ]
        
        text_lower = text.lower()
        keyword_count = sum(1 for kw in actionable_keywords if kw in text_lower)
        score += min(0.3, keyword_count * 0.1)
        
        # Check for specific details (numbers, measurements, locations)
        has_numbers = bool(re.search(r'\d+', text))
        has_measurements = bool(re.search(r'\d+\s*(inch|ft|year|degree|percent|%|")', text, re.IGNORECASE))
        has_location = any(loc in text_lower for loc in [
            'roof', 'wall', 'floor', 'ceiling', 'attic', 'basement',
            'kitchen', 'bathroom', 'bedroom', 'garage', 'exterior', 'interior'
        ])
        
        if has_numbers:
            score += 0.1
        if has_measurements:
            score += 0.1
        if has_location:
            score += 0.1
        
        # Check word count (too short or too long is suspicious)
        word_count = len(text.split())
        if 5 <= word_count <= 100:
            score += 0.1
        elif word_count < 3:
            score -= 0.3
        
        return min(1.0, max(0.0, score))
    
    def _update_stats(self, result: str, reason: Optional[str]):
        """Update validation statistics."""
        if result in ['passed', 'failed']:
            self.stats[result] += 1
        
        if reason:
            self.stats['failure_reasons'][reason] = self.stats['failure_reasons'].get(reason, 0) + 1
    
    def validate_batch(self, issues: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate a batch of issues.
        
        Args:
            issues: List of issue dictionaries
            
        Returns:
            Dict with:
            - 'valid_issues': List of issues that passed
            - 'excluded_issues': List of issues to exclude
            - 'flagged_issues': List of issues needing review
            - 'results': Full validation results for each issue
            - 'summary': Statistics summary
        """
        valid_issues = []
        excluded_issues = []
        flagged_issues = []
        results = []
        
        for issue in issues:
            result = self.validate_issue(issue)
            results.append({
                'issue_id': issue.get('id', 'unknown'),
                'result': result
            })
            
            if result.action == ValidationAction.ACCEPT:
                # Add quality metadata
                issue['data_quality_score'] = result.quality_score
                issue['data_quality_issues'] = result.issues_found
                valid_issues.append(issue)
            elif result.action == ValidationAction.EXCLUDE:
                self.stats['excluded'] += 1
                excluded_issues.append({
                    'issue': issue,
                    'reason': result.reason
                })
            elif result.action == ValidationAction.FLAG_FOR_REVIEW:
                self.stats['flagged_for_review'] += 1
                # Still include but mark for review
                issue['data_quality_score'] = result.quality_score
                issue['data_quality_issues'] = result.issues_found
                issue['needs_manual_review'] = True
                issue['review_reason'] = result.reason
                flagged_issues.append(issue)
                valid_issues.append(issue)  # Include in valid but marked
        
        summary = self.get_stats_summary()
        
        return {
            'valid_issues': valid_issues,
            'excluded_issues': excluded_issues,
            'flagged_issues': flagged_issues,
            'results': results,
            'summary': summary
        }
    
    def get_stats_summary(self) -> Dict[str, Any]:
        """Get validation statistics summary."""
        total = self.stats['total_validated']
        
        return {
            'total_validated': total,
            'passed': self.stats['passed'],
            'failed': self.stats['failed'],
            'excluded': self.stats['excluded'],
            'flagged_for_review': self.stats['flagged_for_review'],
            'pass_rate': (self.stats['passed'] / total * 100) if total > 0 else 0,
            'exclusion_rate': (self.stats['excluded'] / total * 100) if total > 0 else 0,
            'failure_reasons': self.stats['failure_reasons']
        }
    
    def reset_stats(self):
        """Reset validation statistics."""
        self.stats = {
            'total_validated': 0,
            'passed': 0,
            'failed': 0,
            'excluded': 0,
            'flagged_for_review': 0,
            'failure_reasons': {}
        }

