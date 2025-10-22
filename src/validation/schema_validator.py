"""
Phase 1.1: Schema Validation
Ensures every JSON object has required fields and sets defaults for optional fields.
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class ValidationError:
    """Represents a validation error with context."""
    field: str
    error_type: str
    message: str
    severity: str  # 'critical', 'warning', 'info'
    

@dataclass
class ValidationResult:
    """Result of validation with cleaned data and errors."""
    is_valid: bool
    cleaned_data: Dict[str, Any]
    errors: List[ValidationError]
    warnings: List[ValidationError]
    

class IssueSchemaValidator:
    """Validates and cleans inspection issue data."""
    
    # Define required and optional fields
    REQUIRED_FIELDS = {
        'id': str,
        'section': str,
        'description': str,
        'status': str,
    }
    
    OPTIONAL_FIELDS = {
        'subsection': (str, ''),
        'priority': (str, 'unknown'),
        'title': (str, ''),
        'page_numbers': (list, []),
        'estimated_cost': (dict, None),
        # New enriched fields
        'severity': (str, 'unknown'),
        'suggested_action': (str, ''),
        'standard_category': (str, ''),
        'standard_severity': (str, ''),
        'standard_action': (str, ''),
        'extracted_attributes': (dict, {}),
        'enrichment_metadata': (dict, {}),
        'classification': (dict, {}),
        'cost_strategy': (str, ''),
        'grouped_with': (list, []),
        'validation_status': (str, 'pending'),
    }
    
    VALID_STATUSES = {'D', 'I', 'NI', 'NP', 'Deficient', 'Inspected', 'Not Inspected', 'Not Present'}
    VALID_PRIORITIES = {'critical', 'high', 'medium', 'low', 'info', 'unknown'}
    
    def validate(self, issue_data: Dict[str, Any]) -> ValidationResult:
        """
        Validate a single issue record.
        
        Args:
            issue_data: Dictionary containing issue data
            
        Returns:
            ValidationResult with cleaned data and any errors/warnings
        """
        errors = []
        warnings = []
        cleaned = issue_data.copy()
        
        # Check required fields
        for field, expected_type in self.REQUIRED_FIELDS.items():
            if field not in issue_data:
                errors.append(ValidationError(
                    field=field,
                    error_type='missing_required',
                    message=f"Required field '{field}' is missing",
                    severity='critical'
                ))
            elif issue_data[field] is None or (isinstance(issue_data[field], str) and not issue_data[field].strip()):
                errors.append(ValidationError(
                    field=field,
                    error_type='empty_required',
                    message=f"Required field '{field}' is empty",
                    severity='critical'
                ))
            elif not isinstance(issue_data[field], expected_type):
                warnings.append(ValidationError(
                    field=field,
                    error_type='type_mismatch',
                    message=f"Field '{field}' expected {expected_type.__name__}, got {type(issue_data[field]).__name__}",
                    severity='warning'
                ))
                # Try to convert
                try:
                    cleaned[field] = expected_type(issue_data[field])
                except:
                    errors.append(ValidationError(
                        field=field,
                        error_type='conversion_failed',
                        message=f"Could not convert '{field}' to {expected_type.__name__}",
                        severity='critical'
                    ))
        
        # Set defaults for optional fields
        for field, (expected_type, default_value) in self.OPTIONAL_FIELDS.items():
            if field not in cleaned or cleaned[field] is None:
                cleaned[field] = default_value
            elif not isinstance(cleaned[field], expected_type):
                warnings.append(ValidationError(
                    field=field,
                    error_type='type_mismatch',
                    message=f"Optional field '{field}' expected {expected_type.__name__}, got {type(cleaned[field]).__name__}",
                    severity='info'
                ))
                # Try to convert or use default
                try:
                    cleaned[field] = expected_type(cleaned[field]) if cleaned[field] else default_value
                except:
                    cleaned[field] = default_value
        
        # Validate status values
        if 'status' in cleaned and cleaned['status'] not in self.VALID_STATUSES:
            warnings.append(ValidationError(
                field='status',
                error_type='invalid_value',
                message=f"Status '{cleaned['status']}' not in valid statuses: {self.VALID_STATUSES}",
                severity='warning'
            ))
        
        # Validate priority values
        if 'priority' in cleaned and cleaned['priority'] not in self.VALID_PRIORITIES:
            warnings.append(ValidationError(
                field='priority',
                error_type='invalid_value',
                message=f"Priority '{cleaned['priority']}' not in valid priorities: {self.VALID_PRIORITIES}",
                severity='info'
            ))
        
        # Validate description length
        if 'description' in cleaned and len(cleaned['description']) < 10:
            warnings.append(ValidationError(
                field='description',
                error_type='too_short',
                message=f"Description is very short ({len(cleaned['description'])} chars), may be incomplete",
                severity='warning'
            ))
        
        # Check for duplicate or similar titles and descriptions
        if 'title' in cleaned and 'description' in cleaned:
            if cleaned['title'] == cleaned['description']:
                warnings.append(ValidationError(
                    field='title',
                    error_type='duplicate_content',
                    message="Title and description are identical",
                    severity='info'
                ))
        
        is_valid = len(errors) == 0
        
        return ValidationResult(
            is_valid=is_valid,
            cleaned_data=cleaned,
            errors=errors,
            warnings=warnings
        )
    
    def validate_batch(self, issues: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[ValidationResult]]:
        """
        Validate a batch of issues.
        
        Args:
            issues: List of issue dictionaries
            
        Returns:
            Tuple of (cleaned_issues, validation_results)
        """
        cleaned_issues = []
        results = []
        
        for i, issue in enumerate(issues):
            result = self.validate(issue)
            results.append(result)
            
            if result.is_valid:
                cleaned_issues.append(result.cleaned_data)
                logger.debug(f"Issue {i} validated successfully")
            else:
                logger.warning(f"Issue {i} validation failed: {len(result.errors)} errors")
                for error in result.errors:
                    logger.warning(f"  - {error.field}: {error.message}")
                # Still add cleaned data but mark as failed
                result.cleaned_data['validation_status'] = 'failed'
                cleaned_issues.append(result.cleaned_data)
        
        return cleaned_issues, results
    
    def get_validation_summary(self, results: List[ValidationResult]) -> Dict[str, Any]:
        """
        Generate a summary of validation results.
        
        Args:
            results: List of validation results
            
        Returns:
            Summary dictionary
        """
        total = len(results)
        valid = sum(1 for r in results if r.is_valid)
        invalid = total - valid
        
        total_errors = sum(len(r.errors) for r in results)
        total_warnings = sum(len(r.warnings) for r in results)
        
        error_types = {}
        for result in results:
            for error in result.errors + result.warnings:
                error_types[error.error_type] = error_types.get(error.error_type, 0) + 1
        
        return {
            'total_issues': total,
            'valid_issues': valid,
            'invalid_issues': invalid,
            'success_rate': (valid / total * 100) if total > 0 else 0,
            'total_errors': total_errors,
            'total_warnings': total_warnings,
            'error_types': error_types
        }

