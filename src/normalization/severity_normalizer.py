"""
Phase 1.3: Severity Normalization
Maps various severity terms to a standard scale with confidence scoring.
"""

from typing import Dict, Tuple, List
from difflib import SequenceMatcher
import re
import logging

logger = logging.getLogger(__name__)


class SeverityNormalizer:
    """Normalizes severity descriptions to standard categories."""
    
    # Standard severity mapping with keywords
    SEVERITY_MAPPING = {
        'critical': [
            'critical', 'immediate', 'urgent', 'emergency', 'safety hazard',
            'dangerous', 'severe', 'life safety', 'imminent danger', 'hazardous',
            'unsafe', 'immediate attention', 'serious safety', 'extreme'
        ],
        'high': [
            'high priority', 'high', 'major', 'significant', 'important',
            'needs immediate repair', 'structural concern', 'substantial',
            'considerable', 'notable', 'prompt attention', 'serious'
        ],
        'medium': [
            'moderate', 'medium', 'attention needed', 'monitor', 'should repair',
            'recommended', 'advisable', 'typical', 'common', 'routine repair',
            'normal wear', 'standard maintenance'
        ],
        'low': [
            'minor', 'low', 'cosmetic', 'informational', 'low priority',
            'aesthetic', 'appearance', 'optional', 'convenience', 'nice to have',
            'improvement', 'minor concern', 'slight'
        ]
    }
    
    # Status code to severity mapping (TREC inspection report specific)
    STATUS_TO_SEVERITY = {
        'D': 'high',      # Deficient
        'I': 'low',       # Inspected (normal)
        'NI': 'medium',   # Not Inspected
        'NP': 'low',      # Not Present
        'Deficient': 'high',
        'Inspected': 'low',
        'Not Inspected': 'medium',
        'Not Present': 'low'
    }
    
    # Context-based severity boosters
    SEVERITY_BOOSTERS = {
        'critical': ['leak', 'water damage', 'electrical', 'fire', 'gas', 'structural', 'foundation', 'safety'],
        'high': ['roof', 'hvac', 'plumbing', 'major system', 'significant damage'],
    }
    
    def normalize(self, severity_text: str, status: str = None, description: str = None) -> Tuple[str, float]:
        """
        Normalize severity text to standard category.
        
        Args:
            severity_text: Raw severity text
            status: Issue status code (D, I, NI, NP)
            description: Issue description for context
            
        Returns:
            Tuple of (normalized_severity, confidence_score)
        """
        if not severity_text and not status:
            return 'unknown', 0.0
        
        # If we have status code, use it as primary indicator
        if status and status in self.STATUS_TO_SEVERITY:
            base_severity = self.STATUS_TO_SEVERITY[status]
            confidence = 0.7  # Base confidence from status code
            
            # Boost confidence if severity_text agrees
            if severity_text:
                text_severity, text_confidence = self._match_severity_text(severity_text)
                if text_severity == base_severity:
                    confidence = min(0.95, confidence + text_confidence * 0.3)
                elif text_severity and text_confidence > 0.8:
                    # Text is very confident in different severity
                    base_severity = text_severity
                    confidence = text_confidence
            
            # Apply context-based adjustments
            if description:
                base_severity, confidence = self._apply_context_boost(base_severity, confidence, description)
            
            return base_severity, confidence
        
        # No status, rely on text matching
        if severity_text:
            severity, confidence = self._match_severity_text(severity_text)
            
            if description:
                severity, confidence = self._apply_context_boost(severity, confidence, description)
            
            return severity, confidence
        
        return 'unknown', 0.0
    
    def _match_severity_text(self, text: str) -> Tuple[str, float]:
        """
        Match severity text to standard category using fuzzy matching.
        
        Args:
            text: Severity text
            
        Returns:
            Tuple of (severity, confidence)
        """
        if not text:
            return 'unknown', 0.0
        
        text_lower = text.lower().strip()
        
        # Direct exact matches (highest confidence)
        for severity, keywords in self.SEVERITY_MAPPING.items():
            if text_lower in keywords:
                return severity, 0.95
        
        # Fuzzy matching
        best_match = ('unknown', 0.0)
        
        for severity, keywords in self.SEVERITY_MAPPING.items():
            for keyword in keywords:
                # Check if keyword is in text
                if keyword in text_lower:
                    confidence = len(keyword) / len(text_lower)
                    confidence = min(0.9, confidence)
                    if confidence > best_match[1]:
                        best_match = (severity, confidence)
                
                # Fuzzy string matching
                similarity = SequenceMatcher(None, text_lower, keyword).ratio()
                if similarity > 0.7 and similarity > best_match[1]:
                    best_match = (severity, similarity * 0.85)  # Slightly lower confidence for fuzzy
        
        return best_match
    
    def _apply_context_boost(self, severity: str, confidence: float, description: str) -> Tuple[str, float]:
        """
        Adjust severity based on description context.
        
        Args:
            severity: Current severity
            confidence: Current confidence
            description: Issue description
            
        Returns:
            Adjusted (severity, confidence)
        """
        if not description:
            return severity, confidence
        
        description_lower = description.lower()
        
        # Check for critical keywords
        for keyword in self.SEVERITY_BOOSTERS['critical']:
            if keyword in description_lower:
                # Boost to critical if found
                if severity in ['low', 'medium']:
                    logger.debug(f"Boosting severity from {severity} to high due to keyword: {keyword}")
                    return 'high', min(0.9, confidence + 0.1)
                elif severity == 'high' and 'safety' in description_lower:
                    logger.debug(f"Boosting severity from high to critical due to safety concern")
                    return 'critical', min(0.95, confidence + 0.1)
        
        # Check for high priority keywords
        for keyword in self.SEVERITY_BOOSTERS['high']:
            if keyword in description_lower:
                if severity == 'low':
                    logger.debug(f"Boosting severity from low to medium due to keyword: {keyword}")
                    return 'medium', min(0.85, confidence + 0.1)
        
        return severity, confidence
    
    def normalize_batch(self, issues: List[Dict]) -> List[Dict]:
        """
        Normalize severity for a batch of issues.
        
        Args:
            issues: List of issue dictionaries
            
        Returns:
            Issues with normalized severity
        """
        for issue in issues:
            severity_text = issue.get('severity', '') or issue.get('priority', '')
            status = issue.get('status', '')
            description = issue.get('description', '')
            
            normalized_severity, confidence = self.normalize(severity_text, status, description)
            
            issue['standard_severity'] = normalized_severity
            issue['severity_confidence'] = confidence
            
            logger.debug(f"Normalized severity: '{severity_text}' -> '{normalized_severity}' (confidence: {confidence:.2f})")
        
        return issues
    
    def get_severity_score(self, severity: str) -> int:
        """
        Get numeric score for severity (for sorting/prioritization).
        
        Args:
            severity: Standard severity level
            
        Returns:
            Numeric score (higher = more severe)
        """
        scores = {
            'critical': 4,
            'high': 3,
            'medium': 2,
            'low': 1,
            'unknown': 0
        }
        return scores.get(severity, 0)

