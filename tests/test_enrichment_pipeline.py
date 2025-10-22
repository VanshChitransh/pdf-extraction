#!/usr/bin/env python3
"""
Comprehensive test script for the data enrichment pipeline.
Tests all phases with sample data.
"""

import json
import logging
from pathlib import Path

from src.data_enrichment_pipeline import DataEnrichmentPipeline
from src.validation import IssueSchemaValidator
from src.cleaning import TextCleaner
from src.normalization import SeverityNormalizer, ActionNormalizer
from src.enrichment import ComponentTaxonomy, AttributeExtractor, MetadataEnricher
from src.classification import IssueClassifier, IssueGrouper, CostStrategyAssigner

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Sample test data
SAMPLE_ISSUES = [
    {
        "id": "TEST_001",
        "section": "II. PLUMBING SYSTEM",
        "subsection": "Water Heater",
        "status": "D",
        "priority": "high",
        "title": "Water heater showing signs of age and minor corrosion",
        "description": "The water heater in the utility room shows signs of age with minor surface rust on the tank. Unit is approximately 12 years old. Recommend replacement or further evaluation by licensed plumber.",
        "page_numbers": [15],
        "estimated_cost": None
    },
    {
        "id": "TEST_002",
        "section": "I. STRUCTURAL SYSTEMS",
        "subsection": "Foundation",
        "status": "D",
        "priority": "critical",
        "title": "Significant cracks observed in foundation",
        "description": "Multiple cracks approximately 2-3 inches wide observed in concrete foundation at northwest corner. Water staining present. Immediate evaluation by structural engineer recommended for safety.",
        "page_numbers": [8],
        "estimated_cost": None
    },
    {
        "id": "TEST_003",
        "section": "III. ELECTRICAL SYSTEM",
        "subsection": "Outlets",
        "status": "D",
        "priority": "medium",
        "title": "GFCI outlets missing in bathroom",
        "description": "Bathroom outlets near sink do not have GFCI protection. Install GFCI outlets per current electrical code requirements.",
        "page_numbers": [12],
        "estimated_cost": None
    },
    {
        "id": "TEST_004",
        "section": "III. ELECTRICAL SYSTEM",
        "subsection": "Outlets",
        "status": "D",
        "priority": "medium",
        "title": "GFCI outlet not functioning in kitchen",
        "description": "Kitchen GFCI outlet near sink failed to trip during testing. Replace GFCI outlet.",
        "page_numbers": [12],
        "estimated_cost": None
    },
    {
        "id": "TEST_005",
        "section": "IV. HVAC SYSTEM",
        "subsection": "Air Conditioning",
        "status": "D",
        "priority": "high",
        "title": "AC unit not cooling efficiently",
        "description": "Central air conditioning unit in backyard showing reduced cooling capacity. System is 18 years old and may need replacement. Further evaluation by HVAC technician recommended.",
        "page_numbers": [18],
        "estimated_cost": None
    },
    {
        "id": "TEST_006",
        "section": "V. ROOFING",
        "subsection": "Shingles",
        "status": "D",
        "priority": "low",
        "title": "Minor shingle damage on south side",
        "description": "A few damaged shingles observed on south-facing roof section. Cosmetic issue, monitor for now. Consider repair during next maintenance cycle.",
        "page_numbers": [20],
        "estimated_cost": None
    }
]


def test_validation():
    """Test schema validation."""
    logger.info("\n" + "="*70)
    logger.info("TEST: Schema Validation")
    logger.info("="*70)
    
    validator = IssueSchemaValidator()
    
    # Test with good data
    result = validator.validate(SAMPLE_ISSUES[0])
    assert result.is_valid, "Valid issue should pass validation"
    logger.info("✓ Valid issue passed validation")
    
    # Test with missing required field
    bad_issue = {"id": "BAD", "section": "Test"}  # Missing description and status
    result = validator.validate(bad_issue)
    assert not result.is_valid, "Invalid issue should fail validation"
    assert len(result.errors) > 0, "Should have validation errors"
    logger.info(f"✓ Invalid issue caught {len(result.errors)} errors")
    
    # Test batch validation
    cleaned, results = validator.validate_batch(SAMPLE_ISSUES)
    logger.info(f"✓ Batch validation: {len(cleaned)} issues processed")
    
    summary = validator.get_validation_summary(results)
    logger.info(f"  Success rate: {summary['success_rate']:.1f}%")
    logger.info(f"  Total errors: {summary['total_errors']}")
    logger.info(f"  Total warnings: {summary['total_warnings']}")


def test_text_cleaning():
    """Test text cleaning."""
    logger.info("\n" + "="*70)
    logger.info("TEST: Text Cleaning")
    logger.info("="*70)
    
    cleaner = TextCleaner()
    
    # Test OCR corrections
    dirty_text = "The roo1 needs rep air. Wa11 has water damage."
    clean_text = cleaner.clean_text(dirty_text)
    logger.info(f"✓ OCR correction: '{dirty_text}' -> '{clean_text}'")
    
    # Test whitespace normalization
    dirty_text = "Multiple    spaces   and\n\n\n\nnewlines"
    clean_text = cleaner.clean_text(dirty_text)
    logger.info(f"✓ Whitespace normalized")
    
    # Test issue cleaning
    issue = SAMPLE_ISSUES[0].copy()
    cleaned = cleaner.clean_issue(issue)
    logger.info(f"✓ Issue cleaned: {len(cleaned['description'])} chars")


def test_normalization():
    """Test severity and action normalization."""
    logger.info("\n" + "="*70)
    logger.info("TEST: Normalization")
    logger.info("="*70)
    
    # Test severity normalization
    severity_norm = SeverityNormalizer()
    
    test_cases = [
        ("critical", "D", "This is a safety hazard"),
        ("high priority", "D", "Major issue"),
        ("minor", "I", "Small cosmetic issue")
    ]
    
    for severity_text, status, description in test_cases:
        normalized, confidence = severity_norm.normalize(severity_text, status, description)
        logger.info(f"✓ Severity: '{severity_text}' -> '{normalized}' (confidence: {confidence:.2f})")
    
    # Test action normalization
    action_norm = ActionNormalizer()
    
    test_cases = [
        ("Replace immediately", "Further evaluation needed"),
        ("Monitor condition", "Keep an eye on this")
    ]
    
    for action, description in test_cases:
        normalized, confidence = action_norm.normalize(action, description)
        logger.info(f"✓ Action: '{action}' -> '{normalized}' (confidence: {confidence:.2f})")


def test_enrichment():
    """Test enrichment modules."""
    logger.info("\n" + "="*70)
    logger.info("TEST: Enrichment")
    logger.info("="*70)
    
    # Test component taxonomy
    taxonomy = ComponentTaxonomy()
    
    test_items = ["water heater", "AC unit", "foundation", "electrical panel", "roof shingles"]
    
    for item in test_items:
        category, subcat, conf = taxonomy.standardize(item)
        logger.info(f"✓ Taxonomy: '{item}' -> {category}/{subcat} (confidence: {conf:.2f})")
    
    # Test attribute extraction
    extractor = AttributeExtractor()
    
    test_desc = "Water damage approximately 2x3 feet in master bedroom ceiling near bathroom. Wood framing shows signs of rot."
    attributes = extractor.extract_attributes(test_desc)
    logger.info(f"✓ Extracted attributes: {list(attributes.keys())}")
    if attributes.get('locations'):
        logger.info(f"  Locations: {attributes['locations']}")
    if attributes.get('measurements'):
        logger.info(f"  Measurements: {attributes['measurements']}")
    if attributes.get('materials'):
        logger.info(f"  Materials: {attributes['materials']}")
    
    # Test metadata enrichment
    enricher = MetadataEnricher()
    
    issue = SAMPLE_ISSUES[1].copy()  # Foundation issue
    enriched = enricher.enrich_issue(issue)
    logger.info(f"✓ Metadata enriched:")
    logger.info(f"  Urgency score: {enriched['urgency_score']:.1f}/10")
    logger.info(f"  Complexity factor: {enriched['complexity_factor']:.1f}/10")
    logger.info(f"  Specialized labor: {enriched['requires_specialized_labor']}")


def test_classification():
    """Test issue classification."""
    logger.info("\n" + "="*70)
    logger.info("TEST: Classification")
    logger.info("="*70)
    
    classifier = IssueClassifier()
    
    # Classify sample issues
    for issue in SAMPLE_ISSUES[:3]:
        classified = classifier.classify_issue(issue)
        classification = classified['classification']
        logger.info(f"✓ Classified '{issue['title'][:40]}'...")
        logger.info(f"  Trade: {classification['trade']}")
        logger.info(f"  Work type: {classification['work_type']}")
        logger.info(f"  Complexity: {classification['complexity']}")


def test_grouping():
    """Test issue grouping."""
    logger.info("\n" + "="*70)
    logger.info("TEST: Issue Grouping")
    logger.info("="*70)
    
    # First enrich issues with location and classification
    classifier = IssueClassifier()
    extractor = AttributeExtractor()
    
    enriched = []
    for issue in SAMPLE_ISSUES:
        issue = extractor.enrich_issue(issue)
        issue = classifier.classify_issue(issue)
        enriched.append(issue)
    
    # Group issues
    grouper = IssueGrouper()
    grouped = grouper.group_issues(enriched)
    
    groups = grouper.get_groups()
    summary = grouper.get_group_summary()
    
    logger.info(f"✓ Created {summary['total_groups']} groups")
    logger.info(f"  Total issues grouped: {summary['total_issues_grouped']}")
    logger.info(f"  Average group size: {summary['avg_group_size']}")
    
    for group in groups[:3]:  # Show first 3 groups
        logger.info(f"  {group['group_id']}: {group['issue_count']} issues ({group['group_type']})")


def test_cost_strategy():
    """Test cost strategy assignment."""
    logger.info("\n" + "="*70)
    logger.info("TEST: Cost Strategy Assignment")
    logger.info("="*70)
    
    # Prepare issues
    classifier = IssueClassifier()
    enricher = MetadataEnricher()
    
    enriched = []
    for issue in SAMPLE_ISSUES:
        issue = classifier.classify_issue(issue)
        issue = enricher.enrich_issue(issue)
        enriched.append(issue)
    
    # Assign strategies
    assigner = CostStrategyAssigner()
    with_strategy = assigner.assign_batch(enriched)
    
    for issue in with_strategy:
        logger.info(f"✓ {issue['title'][:40]}...")
        logger.info(f"  Strategy: {issue['cost_strategy']}")
        logger.info(f"  Confidence: {issue['strategy_confidence']:.2f}")


def test_full_pipeline():
    """Test complete pipeline."""
    logger.info("\n" + "="*70)
    logger.info("TEST: Full Pipeline")
    logger.info("="*70)
    
    pipeline = DataEnrichmentPipeline()
    
    # Process sample issues
    results = pipeline.process_issues(SAMPLE_ISSUES.copy())
    
    logger.info("✓ Pipeline completed successfully")
    logger.info(f"\nSummary:")
    logger.info(f"  Total issues: {results['summary']['total_issues']}")
    logger.info(f"  Safety issues: {results['summary']['safety_issues']}")
    logger.info(f"  Grouped issues: {results['summary']['grouped_issues']}")
    logger.info(f"  Average urgency: {results['summary']['avg_urgency']:.1f}/10")
    
    logger.info(f"\nBy Severity:")
    for severity, count in results['summary']['by_severity'].items():
        logger.info(f"  {severity}: {count}")
    
    logger.info(f"\nBy Trade:")
    for trade, count in results['summary']['by_trade'].items():
        logger.info(f"  {trade}: {count}")
    
    logger.info(f"\nBy Cost Strategy:")
    for strategy, count in results['summary']['by_strategy'].items():
        logger.info(f"  {strategy}: {count}")
    
    # Save test output
    output_path = Path("test_output_enriched.json")
    pipeline.save_results(results, str(output_path))
    logger.info(f"\n✓ Test output saved to: {output_path}")
    
    return results


def run_all_tests():
    """Run all tests."""
    logger.info("\n" + "="*70)
    logger.info("RUNNING ALL ENRICHMENT PIPELINE TESTS")
    logger.info("="*70)
    
    try:
        test_validation()
        test_text_cleaning()
        test_normalization()
        test_enrichment()
        test_classification()
        test_grouping()
        test_cost_strategy()
        results = test_full_pipeline()
        
        logger.info("\n" + "="*70)
        logger.info("✅ ALL TESTS PASSED!")
        logger.info("="*70)
        
        return True
        
    except Exception as e:
        logger.error(f"\n❌ TEST FAILED: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)

