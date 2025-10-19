#!/usr/bin/env python3
"""
Validation script to test the implementation structure.
Tests imports and basic functionality without making API calls.
"""
import sys
import os

print("="*70)
print("IMPLEMENTATION VALIDATION")
print("="*70)
print()

# Test 1: Check all modules can be imported
print("1. Testing module imports...")
try:
    from src import models
    from src import prompts
    from src import data_preparer
    from src import chunk_manager
    print("   ✓ Core modules imported successfully")
except ImportError as e:
    print(f"   ✗ Failed to import core modules: {e}")
    sys.exit(1)

# Test 2: Check model definitions
print("\n2. Testing model definitions...")
try:
    from src.models import (
        PDFMetadata, InspectionIssue, StructuredReport,
        CostBreakdown, RepairEstimate, EstimationResult
    )
    print("   ✓ All models defined correctly")
except ImportError as e:
    print(f"   ✗ Failed to import models: {e}")
    sys.exit(1)

# Test 3: Check prompts
print("\n3. Testing prompt templates...")
try:
    from src.prompts import (
        SYSTEM_PROMPT, HOUSTON_MARKET_CONTEXT,
        create_estimation_prompt, create_batch_estimation_prompt
    )
    assert len(SYSTEM_PROMPT) > 0, "System prompt is empty"
    assert "Houston" in HOUSTON_MARKET_CONTEXT, "Houston context missing"
    print("   ✓ Prompt templates configured")
except (ImportError, AssertionError) as e:
    print(f"   ✗ Failed prompt test: {e}")
    sys.exit(1)

# Test 4: Test data preparer
print("\n4. Testing data preparation...")
try:
    from src.data_preparer import DataPreparer
    preparer = DataPreparer(location="Houston, TX")
    
    # Check if sample JSON exists
    sample_json = "extracted_data/6-report.json"
    if os.path.exists(sample_json):
        report = preparer.load_report(sample_json)
        deficient = preparer.filter_deficient_issues(report)
        print(f"   ✓ Data preparer working ({len(deficient)} deficient issues found)")
    else:
        print(f"   ⚠ Sample JSON not found, skipping load test")
        print("   ✓ Data preparer initialized")
except Exception as e:
    print(f"   ✗ Failed data preparer test: {e}")
    sys.exit(1)

# Test 5: Test chunk manager
print("\n5. Testing chunk manager...")
try:
    from src.chunk_manager import ChunkManager
    manager = ChunkManager(max_issues_per_chunk=5)
    
    if os.path.exists("extracted_data/6-report.json"):
        report = preparer.load_report("extracted_data/6-report.json")
        deficient = preparer.filter_deficient_issues(report)
        
        chunks = manager.chunk_issues(deficient, strategy="section")
        stats = manager.get_chunking_stats(chunks)
        print(f"   ✓ Chunk manager working ({stats['total_chunks']} chunks created)")
    else:
        print("   ✓ Chunk manager initialized")
except Exception as e:
    print(f"   ✗ Failed chunk manager test: {e}")
    sys.exit(1)

# Test 6: Check file structure
print("\n6. Checking file structure...")
required_files = [
    "src/ai_estimator.py",
    "src/prompts.py",
    "src/data_preparer.py",
    "src/chunk_manager.py",
    "src/cost_estimator.py",
    "src/pdf_generator.py",
    "src/ui_data_formatter.py",
    "src/estimation_pipeline.py",
    "estimate_report.py",
    "estimate_example.py"
]

missing = []
for file in required_files:
    if not os.path.exists(file):
        missing.append(file)

if missing:
    print(f"   ✗ Missing files: {', '.join(missing)}")
    sys.exit(1)
else:
    print(f"   ✓ All required files present ({len(required_files)} files)")

# Test 7: Check model serialization
print("\n7. Testing model serialization...")
try:
    cost_breakdown = CostBreakdown(
        labor_min=500.0,
        labor_max=800.0,
        materials_min=200.0,
        materials_max=400.0,
        total_min=700.0,
        total_max=1200.0
    )
    
    estimate = RepairEstimate(
        issue_id="TEST_1",
        repair_name="Test Repair",
        cost_breakdown=cost_breakdown,
        timeline_days_min=1,
        timeline_days_max=3,
        urgency="medium",
        contractor_type="Licensed Contractor",
        houston_notes="Test note",
        explanation="Test explanation",
        confidence_score=0.85
    )
    
    # Test serialization
    estimate_dict = estimate.to_dict()
    assert 'issue_id' in estimate_dict, "Serialization failed"
    print("   ✓ Model serialization working")
except Exception as e:
    print(f"   ✗ Failed serialization test: {e}")
    sys.exit(1)

# Test 8: Validate prompt generation
print("\n8. Testing prompt generation...")
try:
    test_issue = {
        "id": "TEST_1",
        "property_location": "Houston, TX 77084",
        "inspection_date": "August 16, 2025",
        "section": "I. STRUCTURAL SYSTEMS",
        "subsection": "D. Roof Structures",
        "status": "D",
        "priority": "high",
        "description": "Roof damage observed"
    }
    
    prompt = create_estimation_prompt(test_issue)
    assert "Houston" in prompt, "Location not in prompt"
    assert "Roof damage" in prompt, "Issue description not in prompt"
    print("   ✓ Prompt generation working")
except Exception as e:
    print(f"   ✗ Failed prompt generation test: {e}")
    sys.exit(1)

print()
print("="*70)
print("✓ ALL VALIDATION TESTS PASSED")
print("="*70)
print()
print("Implementation is ready!")
print()
print("Next steps:")
print("  1. Install dependencies: pip install -r requirements.txt")
print("  2. Set your API key: export GEMINI_API_KEY='your_key'")
print("  3. Run estimation: python estimate_report.py extracted_data/6-report.json")
print("  4. Or run example: python estimate_example.py")
print()

