"""
Phase 1.4: Suggested Action Normalization
Classifies and normalizes suggested actions to standard taxonomy.
"""

from typing import Dict, List, Tuple
import re
import logging

logger = logging.getLogger(__name__)


class ActionNormalizer:
    """Normalizes suggested actions to standard categories."""
    
    # Standard action taxonomy with keywords
    ACTION_TAXONOMY = {
        'immediate_repair': {
            'keywords': [
                'repair immediately', 'fix asap', 'urgent repair', 'immediate attention',
                'repair now', 'address immediately', 'correct asap', 'fix urgently',
                'emergency repair', 'repair promptly'
            ],
            'patterns': [
                r'repair.*immediately',
                r'immediate.*repair',
                r'fix.*asap',
                r'urgent.*repair',
                r'emergency.*repair'
            ]
        },
        'replacement': {
            'keywords': [
                'replace', 'replacement needed', 'install new', 'full replacement',
                'remove and replace', 'new installation', 'replace unit', 'replace system',
                'upgrade to new', 'install replacement'
            ],
            'patterns': [
                r'replace\b',
                r'replacement',
                r'install\s+new',
                r'remove\s+and\s+replace'
            ]
        },
        'further_inspection': {
            'keywords': [
                'further evaluation', 'specialist evaluation', 'professional assessment',
                'detailed inspection', 'evaluate by', 'inspection by', 'consult with',
                'expert opinion', 'licensed contractor', 'qualified professional',
                'further investigation', 'additional inspection', 'specialist required'
            ],
            'patterns': [
                r'evaluat.*by',
                r'inspect.*by',
                r'consult\s+with',
                r'licensed\s+(contractor|professional)',
                r'qualified\s+(contractor|professional)',
                r'specialist',
                r'expert.*opinion'
            ]
        },
        'monitoring': {
            'keywords': [
                'monitor', 'observe', 'watch', 'track over time', 'periodic inspection',
                'check regularly', 'keep an eye on', 'review periodically', 'monitor condition',
                'ongoing observation', 'routine check'
            ],
            'patterns': [
                r'monitor\b',
                r'observe\b',
                r'watch\b',
                r'track.*time',
                r'periodic'
            ]
        },
        'maintenance': {
            'keywords': [
                'maintain', 'service', 'clean', 'routine maintenance', 'regular maintenance',
                'upkeep', 'servicing', 'scheduled maintenance', 'preventive maintenance',
                'maintain regularly', 'keep maintained', 'routine service'
            ],
            'patterns': [
                r'maintain\b',
                r'maintenance\b',
                r'service\b',
                r'clean\b',
                r'upkeep\b'
            ]
        },
        'no_action': {
            'keywords': [
                'no action required', 'acceptable condition', 'within normal limits',
                'no repair needed', 'informational only', 'for your information',
                'note only', 'no deficiency'
            ],
            'patterns': [
                r'no\s+action',
                r'no\s+repair',
                r'acceptable',
                r'informational\s+only'
            ]
        }
    }
    
    # Action priority scores
    ACTION_PRIORITY = {
        'immediate_repair': 5,
        'replacement': 4,
        'further_inspection': 3,
        'maintenance': 2,
        'monitoring': 1,
        'no_action': 0,
        'unknown': 0
    }
    
    def normalize(self, action_text: str, description: str = None, severity: str = None) -> Tuple[str, float]:
        """
        Normalize action text to standard category.
        
        Args:
            action_text: Raw action text
            description: Full description for context
            severity: Severity level for context
            
        Returns:
            Tuple of (normalized_action, confidence_score)
        """
        if not action_text and not description:
            return 'unknown', 0.0
        
        # Combine action text and description for analysis
        text_to_analyze = ' '.join(filter(None, [action_text, description])).lower()
        
        # Try keyword matching first (highest confidence)
        action, confidence = self._match_keywords(text_to_analyze)
        
        # If low confidence, try pattern matching
        if confidence < 0.7:
            pattern_action, pattern_conf = self._match_patterns(text_to_analyze)
            if pattern_conf > confidence:
                action = pattern_action
                confidence = pattern_conf
        
        # Apply severity-based adjustments
        if severity:
            action, confidence = self._apply_severity_context(action, confidence, severity)
        
        return action, confidence
    
    def _match_keywords(self, text: str) -> Tuple[str, float]:
        """
        Match action using keyword search.
        
        Args:
            text: Text to analyze
            
        Returns:
            Tuple of (action, confidence)
        """
        best_match = ('unknown', 0.0)
        
        for action, config in self.ACTION_TAXONOMY.items():
            for keyword in config['keywords']:
                if keyword in text:
                    # Calculate confidence based on keyword length and specificity
                    confidence = min(0.95, 0.6 + len(keyword.split()) * 0.1)
                    if confidence > best_match[1]:
                        best_match = (action, confidence)
        
        return best_match
    
    def _match_patterns(self, text: str) -> Tuple[str, float]:
        """
        Match action using regex patterns.
        
        Args:
            text: Text to analyze
            
        Returns:
            Tuple of (action, confidence)
        """
        best_match = ('unknown', 0.0)
        
        for action, config in self.ACTION_TAXONOMY.items():
            for pattern in config['patterns']:
                if re.search(pattern, text, re.IGNORECASE):
                    confidence = 0.85  # Pattern matches are slightly less confident than exact keywords
                    if confidence > best_match[1]:
                        best_match = (action, confidence)
        
        return best_match
    
    def _apply_severity_context(self, action: str, confidence: float, severity: str) -> Tuple[str, float]:
        """
        Adjust action based on severity context.
        
        Args:
            action: Current action
            confidence: Current confidence
            severity: Severity level
            
        Returns:
            Adjusted (action, confidence)
        """
        # Critical/high severity items likely need immediate repair or replacement
        if severity in ['critical', 'high']:
            if action in ['monitoring', 'maintenance', 'no_action']:
                logger.debug(f"Upgrading action from {action} to immediate_repair due to {severity} severity")
                return 'immediate_repair', min(0.85, confidence + 0.1)
        
        # Low severity items are less likely to need immediate action
        elif severity == 'low':
            if action == 'immediate_repair':
                logger.debug(f"Downgrading action from immediate_repair to maintenance due to low severity")
                return 'maintenance', min(0.8, confidence + 0.1)
        
        return action, confidence
    
    def normalize_batch(self, issues: List[Dict]) -> List[Dict]:
        """
        Normalize actions for a batch of issues.
        
        Args:
            issues: List of issue dictionaries
            
        Returns:
            Issues with normalized actions
        """
        for issue in issues:
            action_text = issue.get('suggested_action', '')
            description = issue.get('description', '')
            severity = issue.get('standard_severity', '') or issue.get('severity', '')
            
            normalized_action, confidence = self.normalize(action_text, description, severity)
            
            issue['standard_action'] = normalized_action
            issue['action_confidence'] = confidence
            issue['action_priority'] = self.get_action_priority(normalized_action)
            
            logger.debug(f"Normalized action: '{action_text[:50] if action_text else description[:50]}...' -> '{normalized_action}' (confidence: {confidence:.2f})")
        
        return issues
    
    def get_action_priority(self, action: str) -> int:
        """
        Get numeric priority for action (for sorting).
        
        Args:
            action: Standard action type
            
        Returns:
            Numeric priority (higher = more urgent)
        """
        return self.ACTION_PRIORITY.get(action, 0)
    
    def get_action_description(self, action: str) -> str:
        """
        Get human-readable description of action type.
        
        Args:
            action: Standard action type
            
        Returns:
            Description text
        """
        descriptions = {
            'immediate_repair': 'Requires immediate repair or correction',
            'replacement': 'Full component replacement recommended',
            'further_inspection': 'Needs specialist evaluation or detailed inspection',
            'monitoring': 'Monitor condition over time',
            'maintenance': 'Routine maintenance or upkeep required',
            'no_action': 'No action required',
            'unknown': 'Action recommendation unclear'
        }
        return descriptions.get(action, 'Unknown action type')

