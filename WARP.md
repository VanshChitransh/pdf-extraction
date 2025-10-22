# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

**Purpose**: Extract structured data from PDF home inspection reports, then enrich, classify, group, and prepare data for cost estimation workflows with AI-powered analysis.

**Tech Stack**: 
- Python 3.8+
- PDF Processing: PyPDF2, pdfplumber
- AI Integration: google-generativeai (Gemini), openai (GPT-4)
- Testing: pytest
- No linting/build tools configured

**Sample PDFs**: 6-report.pdf, 7-report.pdf, 8-report.pdf (in repo root)

## Common Commands

### Setup (macOS/Linux)
```bash path=null start=null
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Extraction & Enrichment
```bash path=null start=null
# Basic PDF extraction
python main.py 6-report.pdf

# Run extraction example
python examples/example_usage.py

# Data enrichment pipeline demo
python examples/demo_enhancements.py

# Enrich extracted JSON
python enrich_data.py --input extracted_data/6-report.json
```

### Cost Estimation
```bash path=null start=null
# Set API key (required for AI estimation)
export GEMINI_API_KEY="your-key-here"

# Run cost estimation pipelines
python cost_estimation_pipeline.py --input enriched_data/6-report_enriched.json
python enhanced_cost_estimator.py --input enriched_data/6-report_enriched.json
python rule_based_cost_estimator.py --input enriched_data/6-report_enriched.json
python precise_cost_estimator.py --input enriched_data/6-report_enriched.json

# Example with cost estimation
python examples/example_cost_estimation.py
```

### Testing
```bash path=null start=null
# Run all tests
pytest -q

# Run specific test suites
pytest -q tests/test_enrichment_pipeline.py
pytest -q tests/test_phase1_improvements.py
pytest -q tests/test_phase2_improvements.py
pytest -q tests/test_phase3_learning_loop.py
pytest -q tests/test_validation_improvements.py

# Run tests directly as scripts
python tests/test_enrichment_pipeline.py
python tests/test_phase1_improvements.py

# Root-level test scripts
python test_api_connection.py
python test_component_classification.py
python test_taxonomy_standalone.py
python test_validator.py
```

### Utilities
```bash path=null start=null
# Analysis and comparison tools
python utils/analyze_variance.py
python utils/compare_estimates.py
python utils/verify_estimates.py

# Batch estimation helper
utils/run_estimation.sh
```

### Linting/Build
- **Note**: No linter, formatter, or build configuration is present in this repo.

## Architecture Overview

### Core Extraction Pipeline (src/)

**Main orchestrator**: `src/pipeline.py` (PDFExtractionPipeline)
- Coordinates all extraction stages with caching
- Outputs: JSON in `extracted_data/`

**Processing flow**:
1. **Metadata extraction** (`metadata_extractor.py`) - PyPDF2-based extraction of report metadata
2. **Text extraction** (`text_extractor.py`) - pdfplumber-based structured text with section/subsection detection
3. **Table extraction** (`table_extractor.py`) - Detects and classifies tables (elevation_survey, cost_estimate, checklist)
4. **Data structuring** (`data_structurer.py`) - Assembles InspectionIssue objects with linked data

**Data models** (`models.py`):
- PDFMetadata, TextBlock, ExtractedTable, InspectionIssue, StructuredReport
- JSON serialization/deserialization built-in

### Data Enrichment Pipeline (src/data_enrichment_pipeline.py)

Multi-phase processing: validation → cleaning → normalization → enrichment → classification → grouping → cost strategy

**Validation** (`src/validation/`):
- `schema_validator.py` - Data quality and schema enforcement
- `data_quality_validator.py` - Quality checks and rule validation
- `estimation_validator.py` - Cost estimation result validation

**Cleaning** (`src/cleaning/`):
- `text_cleaner.py` - OCR error correction, duplicate detection

**Normalization** (`src/normalization/`):
- `severity_normalizer.py` - Standardize severity levels
- `action_normalizer.py` - Standardize recommended actions

**Enrichment** (`src/enrichment/`):
- `component_taxonomy.py` - Hierarchical component classification system
- `attribute_extractor.py` - Extract locations, measurements, materials
- `metadata_enricher.py` - Add urgency, complexity, safety flags

**Classification** (`src/classification/`):
- `issue_classifier.py` - Assign trade, work type, complexity
- `issue_grouper.py` - Group related issues for bundling
- `cost_strategy_assigner.py` - Tag cost strategy per issue

### Estimation System (src/estimation/)

**Cost databases and multipliers**:
- `cost_database.py` - Houston market component costs (40+ components)
- `houston_cost_multipliers.py` - Labor/permit adjustments by category

**Estimation strategies**:
- `cost_strategy_selector.py` - Choose lookup/formula/hybrid/LLM approach
- `hybrid_cost_estimator.py` - Combines multiple strategies
- `confidence_scorer.py` - 11-factor confidence analysis
- `relationship_analyzer.py` - Detects bundling opportunities and causal chains (15-25% savings)

### AI Prompting System (src/prompting/)

**Prompt engineering**:
- `prompt_builder.py` - Assembles prompts with context
- `context_manager.py` - Token optimization and batching
- `output_validator.py` - Response validation and hallucination detection
- `specialist_prompts.py` - 7 trade-specific prompts (HVAC, Plumbing, Electrical, Roofing, Foundation, Structural, Pest)
- `version_control.py` - Prompt versioning and A/B testing
- `prompt_templates.py` - Base prompt templates
- `enhanced_prompt_templates.py` - Advanced prompt templates

### Learning & Calibration (src/learning/)

**Continuous improvement**:
- `calibration_database.py` - Stores estimate vs actual costs
- `feedback_loop.py` - Applies calibration factors by category
- `variance_analyzer.py` - Metrics and problem-area detection

## Directory Structure

```
/Users/vansh/Coding/Project/pdf-extraction/
├── src/                                  # Core source code
│   ├── pipeline.py                       # Main extraction orchestrator
│   ├── metadata_extractor.py            # PDF metadata extraction
│   ├── text_extractor.py                # Structured text extraction
│   ├── table_extractor.py               # Table detection & classification
│   ├── data_structurer.py               # Issue assembly & linking
│   ├── models.py                        # Data models (dataclasses)
│   ├── data_enrichment_pipeline.py      # Multi-phase enrichment
│   ├── classification/                  # Issue classification
│   │   ├── issue_classifier.py
│   │   ├── issue_grouper.py
│   │   └── cost_strategy_assigner.py
│   ├── cleaning/                        # Data cleaning
│   │   └── text_cleaner.py
│   ├── enrichment/                      # Data enrichment
│   │   ├── component_taxonomy.py
│   │   ├── attribute_extractor.py
│   │   └── metadata_enricher.py
│   ├── estimation/                      # Cost estimation
│   │   ├── confidence_scorer.py
│   │   ├── cost_database.py
│   │   ├── cost_strategy_selector.py
│   │   ├── houston_cost_multipliers.py
│   │   ├── hybrid_cost_estimator.py
│   │   └── relationship_analyzer.py
│   ├── learning/                        # Learning loop
│   │   ├── calibration_database.py
│   │   ├── feedback_loop.py
│   │   └── variance_analyzer.py
│   ├── normalization/                   # Data normalization
│   │   ├── severity_normalizer.py
│   │   └── action_normalizer.py
│   ├── prompting/                       # AI prompting system
│   │   ├── prompt_builder.py
│   │   ├── context_manager.py
│   │   ├── output_validator.py
│   │   ├── specialist_prompts.py
│   │   ├── version_control.py
│   │   ├── prompt_templates.py
│   │   └── enhanced_prompt_templates.py
│   └── validation/                      # Validation system
│       ├── schema_validator.py
│       ├── data_quality_validator.py
│       └── estimation_validator.py
├── examples/                            # Example scripts
│   ├── example_usage.py                 # Basic extraction example
│   ├── demo_enhancements.py             # Phase 1 enhancements demo
│   └── example_cost_estimation.py       # Cost estimation example
├── tests/                               # Test suite
│   ├── test_enrichment_pipeline.py      # Enrichment tests
│   ├── test_phase1_improvements.py      # Phase 1 tests
│   ├── test_phase2_improvements.py      # Phase 2 estimation tests
│   ├── test_phase3_learning_loop.py     # Learning loop tests
│   ├── test_validation_improvements.py  # Validation tests
│   └── test_fixes.sh                    # Test helper script
├── utils/                               # Utility scripts
│   ├── analyze_variance.py              # Variance analysis
│   ├── compare_estimates.py             # Estimate comparison
│   ├── verify_estimates.py              # Estimate verification
│   └── run_estimation.sh                # Batch estimation helper
├── main.py                              # CLI entry point for extraction
├── enrich_data.py                       # CLI for enrichment
├── cost_estimation_pipeline.py          # Main cost estimation CLI
├── enhanced_cost_estimator.py           # Enhanced AI estimator
├── rule_based_cost_estimator.py         # Rule-based estimator
├── precise_cost_estimator.py            # Precise estimator
├── test_api_connection.py               # API connectivity test
├── test_component_classification.py     # Component classifier test
├── test_taxonomy_standalone.py          # Taxonomy test
├── test_validator.py                    # Validator test
├── extracted_data/                      # Extraction output
├── enriched_data/                       # Enrichment output
├── cost_estimates/                      # Estimation output
├── prompt_logs/                         # Prompt execution logs
├── 6-report.pdf                         # Sample report 1
├── 7-report.pdf                         # Sample report 2
├── 8-report.pdf                         # Sample report 3
├── requirements.txt                     # Python dependencies
├── README.md                            # Main documentation
├── WARP.md                              # This file
├── COST_ESTIMATION_PROBLEMS_ANALYSIS.md # Cost estimation analysis
└── CLEANUP_SUMMARY.md                   # Cleanup documentation
```

## Data Flow (End-to-End)

1. **PDF Input** (6-report.pdf, 7-report.pdf, 8-report.pdf)
   ↓
2. **Extraction Pipeline** (`src/pipeline.py`)
   - Metadata → Text → Tables → Structuring
   - Output: `extracted_data/*.json`
   ↓
3. **Enrichment Pipeline** (`src/data_enrichment_pipeline.py`)
   - Validation → Cleaning → Normalization → Enrichment → Classification → Grouping
   - Output: `enriched_data/*_enriched.json`
   ↓
4. **Cost Estimation** (multiple estimators available)
   - Strategy selection, confidence scoring, relationship analysis
   - AI prompting with specialist prompts
   - Output: `cost_estimates/*.json`
   ↓
5. **Learning Loop** (optional, `src/learning/`)
   - Calibration based on actual costs
   - Variance analysis and feedback

## Key Features

### Phase 1 Enhancements
- ✅ 11-factor confidence scoring (vs single number)
- ✅ Houston cost database (40+ components)
- ✅ Issue relationship analyzer (15-25% savings via bundling)
- ✅ 7 trade specialist prompts (HVAC, Plumbing, Electrical, etc.)
- ✅ Hybrid estimation (database grounding + AI intelligence)

### Estimation Strategies
- **Lookup**: Direct database lookup for common components
- **Formula**: Rule-based calculation for standard work
- **Hybrid**: Combines lookup + formula + AI insights
- **LLM**: Full AI-driven estimation with specialist prompts

### AI Integration
- **Models supported**: Gemini 2.5 Flash (recommended), Gemini Pro, GPT-4 Turbo
- **Cost optimization**: Batch processing reduces costs by 90%
- **Quality control**: Output validation, hallucination detection
- **Versioning**: A/B testing and prompt improvement tracking

## Important Notes

### Environment Variables
- `GEMINI_API_KEY` - Required for Gemini API access (AI estimation)
- `OPENAI_API_KEY` - Required for OpenAI API access (alternative)

## Current Status (2025-10-22)

### Authoritative outputs
- Enriched source: `enriched_data/6-report_enriched.json`
- Full-run estimates: `cost_estimates/6-report_with_validation.json`
- Latest test sample: `cost_estimates/test_fixes_results.json`
- API usage counter: `daily_api_usage.json` (today's count present ⇒ API reachable)

### Findings
- 53 issues extracted; many are headers/notes. Current run excluded ~38 for low quality.
- Full-run file shows 0 AI estimates and 0 database matches; test sample shows 3 estimates with costs.
- Validation flags: confidence scale mismatch (0–100 emitted vs 0–1 expected), and wide cost ranges (>3×) causing failures.
- Some taxonomy misclassifications (e.g., Roofing items tagged as HVAC/Grounds) reduce database match rate and strategy selection.

### What to do next
1. Use `gemini-2.5-flash` and batch (5–10) to stay within free-tier rate limits.
2. Normalize confidence to 0–1 before validation (or adjust validator to accept 0–100 and convert).
3. Relax range-ratio thresholds by category (e.g., allow 5× for vague/diagnostic items) or auto-reduce confidence when >3× instead of failing.
4. Prefer estimating only actionable `status == 'D'` and collapse obvious headers/notes.
5. Re-run enrichment (to apply taxonomy fixes) and then estimation.

### Rerun commands
```bash
# 1) Ensure deps and API key
source venv/bin/activate
export GEMINI_API_KEY="<your-key>"

# 2) (Optional) Re-enrich to apply latest validators/taxonomy
python enrich_data.py --input extracted_data/6-report.json --output enriched_data/6-report_enriched.json

# 3) Generate estimates (Gemini, batched)
python cost_estimation_pipeline.py \
  --input enriched_data/6-report_enriched.json \
  --output cost_estimates/6-report_with_validation.json \
  --model gemini-2.5-flash \
  --batch-size 10 \
  --temperature 0.3

# 4) Verify API connectivity if needed
python test_api_connection.py
```

### Troubleshooting
- If confidence errors like "out of valid range [0, 1]": ensure the estimator returns 0–1 or the validator rescales 0–100 ➜ 0–1.
- If many items excluded as headers: confirm `DataQualityValidator` patterns and keep only `D` (deficient) items for estimation.
- If database matches are 0: improve taxonomy mapping and synonyms so items align with `cost_database.py` keys.

### File Locations
- Input PDFs: Repo root (6-report.pdf, 7-report.pdf, 8-report.pdf)
- Extracted data: `extracted_data/`
- Enriched data: `enriched_data/`
- Cost estimates: `cost_estimates/`
- Prompt logs: `prompt_logs/v1.0/`
- Cache: `extracted_data/cache/`

### Known Caveats
- Image extraction is **disabled** for performance (saves 95% storage, 10-30x processing time)
- Some root-level estimator scripts reference features still in development
- Tests expect sample PDFs and enriched JSON files to be present
- No linting, formatting, or build tools configured

### API Costs (Gemini 2.5 Flash)
- 47 issues (individual): ~$0.15-0.25 (47 API calls)
- 47 issues (batch=10): ~$0.02-0.05 (5 API calls)
- Pricing per 1M tokens: $0.075 input, $0.30 output

## Testing Strategy

- **Unit tests**: In `tests/` directory, runnable via pytest or directly
- **Integration tests**: Root-level test scripts for specific components
- **No CI/CD**: Tests run manually
- **Coverage**: Phase 1, 2, 3 improvements, enrichment, validation, learning loop

## Common Development Patterns

### Running the full pipeline programmatically:
```python path=null start=null
from src.pipeline import PDFExtractionPipeline
from src.data_enrichment_pipeline import DataEnrichmentPipeline

# Extract
pipeline = PDFExtractionPipeline(output_dir="./extracted_data")
report = pipeline.process_pdf("6-report.pdf")

# Enrich
enricher = DataEnrichmentPipeline()
results = enricher.process_from_json('extracted_data/6-report.json')
enricher.save_results(results, 'enriched_data/6-report_enriched.json')
```

### Accessing structured data:
```python path=null start=null
# Read enriched data
import json
with open('enriched_data/6-report_enriched.json') as f:
    data = json.load(f)
    
for issue in data['issues']:
    print(f"{issue['component_category']}: {issue['title']}")
    print(f"Trade: {issue.get('primary_trade', 'Unknown')}")
    print(f"Cost strategy: {issue.get('cost_strategy', 'Unknown')}")
```
