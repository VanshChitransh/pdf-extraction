"""
Phase 4: Data Enrichment Pipeline
Main pipeline that orchestrates all validation, cleaning, normalization, enrichment, and classification.
"""

import json
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path

# Import all components
from .validation import IssueSchemaValidator, ValidationResult
from .validation.data_quality_validator import DataQualityValidator
from .cleaning import TextCleaner
from .normalization import SeverityNormalizer, ActionNormalizer
from .enrichment import ComponentTaxonomy, AttributeExtractor, MetadataEnricher
from .classification import IssueClassifier, IssueGrouper, CostStrategyAssigner

logger = logging.getLogger(__name__)


class DataEnrichmentPipeline:
    """
    Complete data enrichment pipeline for inspection issues.
    
    Processes raw extraction data through:
    1. Validation & Cleaning
    2. Normalization
    3. Enrichment
    4. Classification & Grouping
    """
    
    def __init__(self, property_data: Optional[Dict] = None):
        """
        Initialize the enrichment pipeline.
        
        Args:
            property_data: Optional property information for context
        """
        # Initialize all components
        self.validator = IssueSchemaValidator()
        self.data_quality_validator = DataQualityValidator(strict_mode=False)
        self.text_cleaner = TextCleaner()
        self.severity_normalizer = SeverityNormalizer()
        self.action_normalizer = ActionNormalizer()
        self.component_taxonomy = ComponentTaxonomy()
        self.attribute_extractor = AttributeExtractor()
        self.metadata_enricher = MetadataEnricher(property_data)
        self.issue_classifier = IssueClassifier()
        self.issue_grouper = IssueGrouper()
        self.cost_strategy_assigner = CostStrategyAssigner()
        
        self.processing_stats = {}
    
    def process_issues(self, issues: List[Dict]) -> Dict[str, Any]:
        """
        Process a list of issues through the complete pipeline.
        
        Args:
            issues: List of raw issue dictionaries
            
        Returns:
            Dictionary containing processed issues and statistics
        """
        logger.info(f"Starting enrichment pipeline for {len(issues)} issues")
        
        # Reset processing stats
        self.processing_stats = {
            'total_input': len(issues),
            'phases': {}
        }
        
        # Phase 1: Validation & Cleaning
        logger.info("Phase 1: Validation & Cleaning")
        issues = self._phase1_validation_cleaning(issues)
        
        # Phase 2: Normalization
        logger.info("Phase 2: Normalization")
        issues = self._phase2_normalization(issues)
        
        # Phase 3: Enrichment
        logger.info("Phase 3: Enrichment")
        issues = self._phase3_enrichment(issues)
        
        # Phase 4: Classification
        logger.info("Phase 4: Classification")
        issues = self._phase4_classification(issues)
        
        # Phase 5: Grouping
        logger.info("Phase 5: Grouping")
        issues = self._phase5_grouping(issues)
        
        # Phase 6: Cost Strategy Assignment
        logger.info("Phase 6: Cost Strategy Assignment")
        issues = self._phase6_cost_strategy(issues)
        
        # Generate final summary
        summary = self._generate_summary(issues)
        
        logger.info(f"Pipeline complete. Processed {len(issues)} issues successfully")
        
        return {
            'issues': issues,
            'summary': summary,
            'processing_stats': self.processing_stats,
            'groups': self.issue_grouper.get_groups()
        }
    
    def _phase1_validation_cleaning(self, issues: List[Dict]) -> List[Dict]:
        """Phase 1: Schema validation, text cleaning, and data quality filtering."""
        phase_stats = {
            'validation_errors': 0,
            'validation_warnings': 0,
            'text_cleaned': 0,
            'quality_passed': 0,
            'quality_excluded': 0,
            'quality_flagged_for_review': 0,
        }
        
        # 1.1 Schema Validation
        logger.debug("Running schema validation...")
        validated_issues, validation_results = self.validator.validate_batch(issues)
        
        validation_summary = self.validator.get_validation_summary(validation_results)
        phase_stats['validation_errors'] = validation_summary['total_errors']
        phase_stats['validation_warnings'] = validation_summary['total_warnings']
        phase_stats['success_rate'] = validation_summary['success_rate']
        
        # 1.2 Text Cleaning
        logger.debug("Running text cleaning...")
        self.text_cleaner.reset_duplicate_tracking()
        cleaned_issues = []
        
        for issue in validated_issues:
            cleaned = self.text_cleaner.clean_issue(issue)
            
            # Check for duplicates
            if self.text_cleaner.is_duplicate(cleaned.get('description', '')):
                cleaned['is_duplicate'] = True
            
            cleaned_issues.append(cleaned)
            phase_stats['text_cleaned'] += 1
        
        # 1.3 Data Quality Validation (filter out headers/boilerplate, low-quality items)
        logger.debug("Running data quality validation...")
        dq_summary = self.data_quality_validator.validate_batch(cleaned_issues)
        issues_after_quality = dq_summary['valid_issues']
        phase_stats['quality_passed'] = len(dq_summary['valid_issues'])
        phase_stats['quality_excluded'] = len(dq_summary['excluded_issues'])
        phase_stats['quality_flagged_for_review'] = len(dq_summary['flagged_issues'])
        phase_stats['quality_stats'] = dq_summary['summary']
        
        self.processing_stats['phases']['validation_cleaning'] = phase_stats
        return issues_after_quality
    
    def _phase2_normalization(self, issues: List[Dict]) -> List[Dict]:
        """Phase 2: Severity and action normalization."""
        phase_stats = {
            'severity_normalized': 0,
            'action_normalized': 0
        }
        
        # 1.3 Severity Normalization
        logger.debug("Normalizing severity...")
        issues = self.severity_normalizer.normalize_batch(issues)
        phase_stats['severity_normalized'] = len(issues)
        
        # 1.4 Action Normalization
        logger.debug("Normalizing actions...")
        issues = self.action_normalizer.normalize_batch(issues)
        phase_stats['action_normalized'] = len(issues)
        
        self.processing_stats['phases']['normalization'] = phase_stats
        return issues
    
    def _phase3_enrichment(self, issues: List[Dict]) -> List[Dict]:
        """Phase 3: Data enrichment."""
        phase_stats = {
            'components_standardized': 0,
            'attributes_extracted': 0,
            'metadata_enriched': 0
        }
        
        # 2.1 Component Standardization
        logger.debug("Standardizing components...")
        enriched_issues = []
        for issue in issues:
            enriched = self.component_taxonomy.enrich_issue(issue)
            enriched_issues.append(enriched)
            phase_stats['components_standardized'] += 1
        
        # 2.2 Attribute Extraction
        logger.debug("Extracting attributes...")
        enriched_issues = self.attribute_extractor.extract_batch(enriched_issues)
        phase_stats['attributes_extracted'] = len(enriched_issues)
        
        # 2.3 Metadata Enrichment
        logger.debug("Enriching metadata...")
        enriched_issues = self.metadata_enricher.enrich_batch(enriched_issues)
        phase_stats['metadata_enriched'] = len(enriched_issues)
        
        self.processing_stats['phases']['enrichment'] = phase_stats
        return enriched_issues
    
    def _phase4_classification(self, issues: List[Dict]) -> List[Dict]:
        """Phase 4: Multi-level classification."""
        phase_stats = {
            'issues_classified': 0
        }
        
        # 3.1 Multi-level Classification
        logger.debug("Classifying issues...")
        classified_issues = self.issue_classifier.classify_batch(issues)
        phase_stats['issues_classified'] = len(classified_issues)
        
        # Get classification summary
        classification_summary = self.issue_classifier.get_classification_summary(classified_issues)
        phase_stats['classification_summary'] = classification_summary
        
        self.processing_stats['phases']['classification'] = phase_stats
        return classified_issues
    
    def _phase5_grouping(self, issues: List[Dict]) -> List[Dict]:
        """Phase 5: Issue grouping."""
        phase_stats = {
            'issues_grouped': 0
        }
        
        # 3.2 Group Related Issues
        logger.debug("Grouping related issues...")
        grouped_issues = self.issue_grouper.group_issues(issues)
        
        group_summary = self.issue_grouper.get_group_summary()
        phase_stats['group_summary'] = group_summary
        phase_stats['issues_grouped'] = group_summary['total_issues_grouped']
        
        self.processing_stats['phases']['grouping'] = phase_stats
        return grouped_issues
    
    def _phase6_cost_strategy(self, issues: List[Dict]) -> List[Dict]:
        """Phase 6: Cost strategy assignment."""
        phase_stats = {
            'strategies_assigned': 0
        }
        
        # 3.3 Assign Cost Strategy
        logger.debug("Assigning cost strategies...")
        issues_with_strategy = self.cost_strategy_assigner.assign_batch(issues)
        phase_stats['strategies_assigned'] = len(issues_with_strategy)
        
        strategy_summary = self.cost_strategy_assigner.get_strategy_summary(issues_with_strategy)
        phase_stats['strategy_summary'] = strategy_summary
        
        self.processing_stats['phases']['cost_strategy'] = phase_stats
        return issues_with_strategy
    
    def _generate_summary(self, issues: List[Dict]) -> Dict[str, Any]:
        """Generate comprehensive summary of processed data."""
        summary = {
            'total_issues': len(issues),
            'by_severity': {},
            'by_action': {},
            'by_category': {},
            'by_trade': {},
            'by_complexity': {},
            'by_strategy': {},
            'safety_issues': 0,
            'grouped_issues': 0,
            'avg_urgency': 0,
            'avg_complexity': 0
        }
        
        urgency_scores = []
        complexity_scores = []
        
        for issue in issues:
            # Count by severity
            severity = issue.get('standard_severity', 'unknown')
            summary['by_severity'][severity] = summary['by_severity'].get(severity, 0) + 1
            
            # Count by action
            action = issue.get('standard_action', 'unknown')
            summary['by_action'][action] = summary['by_action'].get(action, 0) + 1
            
            # Count by category
            category = issue.get('standard_category', 'Unknown')
            summary['by_category'][category] = summary['by_category'].get(category, 0) + 1
            
            # Count by trade
            trade = issue.get('classification', {}).get('trade', 'unknown')
            summary['by_trade'][trade] = summary['by_trade'].get(trade, 0) + 1
            
            # Count by complexity
            complexity = issue.get('classification', {}).get('complexity', 'unknown')
            summary['by_complexity'][complexity] = summary['by_complexity'].get(complexity, 0) + 1
            
            # Count by strategy
            strategy = issue.get('cost_strategy', 'unknown')
            summary['by_strategy'][strategy] = summary['by_strategy'].get(strategy, 0) + 1
            
            # Count safety issues
            if issue.get('safety_flag'):
                summary['safety_issues'] += 1
            
            # Count grouped issues
            if issue.get('is_grouped'):
                summary['grouped_issues'] += 1
            
            # Collect scores
            if 'urgency_score' in issue:
                urgency_scores.append(issue['urgency_score'])
            if 'complexity_factor' in issue:
                complexity_scores.append(issue['complexity_factor'])
        
        # Calculate averages
        if urgency_scores:
            summary['avg_urgency'] = round(sum(urgency_scores) / len(urgency_scores), 2)
        if complexity_scores:
            summary['avg_complexity'] = round(sum(complexity_scores) / len(complexity_scores), 2)
        
        return summary
    
    def process_from_json(self, json_path: str) -> Dict[str, Any]:
        """
        Load issues from JSON file and process them.
        
        Args:
            json_path: Path to JSON file with issues
            
        Returns:
            Processed results
        """
        logger.info(f"Loading issues from {json_path}")
        
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Extract issues from data structure
        if isinstance(data, dict):
            issues = data.get('issues', [])
            
            # Extract property data if available
            if 'metadata' in data:
                property_data = {
                    'address': data['metadata'].get('property_address'),
                    'total_pages': data['metadata'].get('total_pages'),
                    'inspection_date': data['metadata'].get('inspection_date')
                }
                self.metadata_enricher.set_property_data(property_data)
        else:
            issues = data
        
        # Process issues
        return self.process_issues(issues)
    
    def save_results(self, results: Dict[str, Any], output_path: str):
        """
        Save processed results to JSON file.
        
        Args:
            results: Processing results
            output_path: Output file path
        """
        logger.info(f"Saving enriched data to {output_path}")
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"Results saved successfully")
    
    def get_processing_stats(self) -> Dict:
        """Get processing statistics."""
        return self.processing_stats

