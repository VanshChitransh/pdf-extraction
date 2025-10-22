# PDF Inspection Report Extraction Pipeline

A comprehensive Python pipeline for extracting structured data from PDF inspection reports, designed specifically for real estate inspection documents.

## 🎉 NEW: Phase 1 Enhancements (Cost Estimation Precision)

**Major improvements to cost estimation accuracy and reliability!**

### What's New
- ✅ **Multi-Dimensional Confidence Scoring**: 11-factor analysis (vs single number)
- ✅ **Houston Cost Database**: 40+ components with market-accurate pricing
- ✅ **Issue Relationship Analyzer**: Detects causal chains & bundling opportunities (15-25% savings)
- ✅ **7 Trade Specialist Prompts**: HVAC, Plumbing, Electrical, Roofing, Foundation, Structural, Pest
- ✅ **Hybrid Estimation**: Database grounding + AI intelligence

**Quick Start**:
```bash
# Run the demo
python3 demo_enhancements.py

# Or use enhanced estimator on your data
python3 enhanced_cost_estimator.py --input enriched_data/6-report_enriched.json
```

📖 **[Read Phase 1 Documentation](PHASE1_ENHANCEMENTS.md)** for detailed features and usage.

📊 **[See Implementation Summary](IMPLEMENTATION_SUMMARY.md)** for delivery metrics and testing results.

---

## Core Features

- **Metadata Extraction**: Automatically extracts report metadata including property address, inspection date, and report number
- **Structured Text Extraction**: Preserves hierarchical structure (sections, subsections) and formatting information
- **Table Extraction**: Intelligently extracts and classifies tables (cost estimates, elevation surveys, checklists)
- **Image Extraction**: Disabled (not needed for cost estimation)
- **Issue Classification**: Automatically categorizes inspection issues by status and priority
- **Data Structuring**: Links related data (tables, text) to specific issues
- **Caching**: Built-in caching system to avoid reprocessing unchanged files

## Installation

### Prerequisites

- Python 3.8+

### macOS Installation

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

### Linux Installation

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

## Usage

### Command Line Interface

```bash
# Basic usage
python main.py path/to/report.pdf

# With custom output directory
python main.py path/to/report.pdf --output-dir ./custom_output

# Force reprocessing (ignore cache)
python main.py path/to/report.pdf --force

# Disable caching
python main.py path/to/report.pdf --no-cache

# Verbose output
python main.py path/to/report.pdf --verbose
```

### Programmatic Usage

```python
from src.pipeline import PDFExtractionPipeline

# Initialize pipeline
pipeline = PDFExtractionPipeline(output_dir="./extracted_data")

# Process a PDF
report = pipeline.process_pdf("path/to/report.pdf")

# Access extracted data
print(f"Found {len(report.issues)} issues")
print(f"Found {len(report.tables)} tables")

# Access specific issues
for issue in report.issues:
    if issue.status == 'D':  # Deficient items
        print(f"Deficient: {issue.title}")
        print(f"Priority: {issue.priority}")
```

## Output Structure

The pipeline generates a structured JSON file containing:

### Metadata
- `filename`: Original PDF filename
- `total_pages`: Number of pages in the document
- `report_type`: 'inspection' or 'estimate'
- `report_number`: Report identifier
- `inspection_date`: Date of inspection
- `property_address`: Property address

### Issues
Each issue contains:
- `id`: Unique identifier
- `section`: Report section (e.g., "I. STRUCTURAL SYSTEMS")
- `subsection`: Subsection (e.g., "A. Foundations")
- `status`: Issue status (D=Deficient, I=Inspected, NI=Not Inspected, NP=Not Present)
- `priority`: Priority level (high, medium, low, info)
- `title`: Short description
- `description`: Full text content
- `page_numbers`: Pages where issue appears
- `estimated_cost`: Cost estimate if available

### Tables
- `page_num`: Page number
- `section`: Associated section
- `table_data`: Extracted table data
- `column_headers`: Table headers
- `table_type`: Classification (elevation_survey, cost_estimate, checklist, etc.)

## Architecture

### Core Components

1. **Metadata Extractor** (`src/metadata_extractor.py`)
   - Extracts basic PDF metadata using PyPDF2
   - Pattern matching for report-specific information

2. **Text Extractor** (`src/text_extractor.py`)
   - Structured text extraction with pdfplumber
   - Hierarchical section detection
   - Status indicator recognition
   - Formatting analysis

3. **Table Extractor** (`src/table_extractor.py`)
   - Table detection and extraction
   - Semantic classification
   - Data cleaning and validation

4. **Data Structurer** (`src/data_structurer.py`)
   - Issue classification and linking
   - Priority assignment
   - Data validation

5. **Pipeline Orchestrator** (`src/pipeline.py`)
   - Main processing pipeline
   - Caching system
   - Error handling and logging

### Data Models

All data structures are defined in `src/models.py` using Python dataclasses:

- `PDFMetadata`: Basic document information
- `TextBlock`: Structured text with formatting
- `ExtractedTable`: Table data with classification
- `InspectionIssue`: Complete issue information
- `StructuredReport`: Final structured output

## Configuration

### Caching

The pipeline includes a built-in caching system that stores processed results based on file hash. This prevents reprocessing of unchanged files.

```python
# Disable caching
pipeline = PDFExtractionPipeline(enable_caching=False)

# Clear cache
pipeline.clear_cache()
```

### Logging

The pipeline uses Python's logging module for detailed output:

```python
import logging
logging.basicConfig(level=logging.INFO)
```

## AI Cost Estimation (New!)

Transform enriched inspection data into accurate cost estimates using AI-powered analysis.

### Quick Start

```bash
# Set API key
export GEMINI_API_KEY="your-key-here"

# Run cost estimation
python cost_estimation_pipeline.py --input enriched_data/6-report_enriched.json
```

### Features

- 🎯 **Houston Market Context**: Pricing optimized for Houston, TX market
- 🤖 **AI-Powered Analysis**: Uses Gemini 2.5 Flash or GPT-4
- ✅ **Automatic Validation**: Catches errors and hallucinations
- 📊 **Version Tracking**: A/B test prompt improvements
- 💰 **Cost Optimized**: Batch processing reduces API costs by 90%
- 🔍 **Quality Control**: Flags low-confidence estimates for review

### Pipeline Components

1. **Prompt Builder** - Assembles Houston-specific prompts with property context
2. **Context Manager** - Optimizes token usage and batching
3. **Output Validator** - Validates responses and detects hallucinations
4. **Version Control** - Tracks performance and enables comparison

### Usage

**Individual Processing (highest quality):**
```bash
python cost_estimation_pipeline.py \
    --input enriched_data/6-report_enriched.json \
    --batch-size 1
```

**Batch Processing (lowest cost):**
```bash
python cost_estimation_pipeline.py \
    --input enriched_data/6-report_enriched.json \
    --batch-size 10
```

**Python API:**
```python
from cost_estimation_pipeline import CostEstimationPipeline

pipeline = CostEstimationPipeline(
    model="gemini-2.5-flash",
    temperature=0.3,
    batch_size=10
)

result = pipeline.process_report(
    enriched_data_path="enriched_data/6-report_enriched.json"
)

print(f"Total cost range: ${result['summary']['total_estimated_low']} - ${result['summary']['total_estimated_high']}")
```

### Cost Estimates

| Scenario | API Calls | Estimated Cost |
|----------|-----------|----------------|
| 47 issues (individual) | 47 | $0.15-0.25 |
| 47 issues (batch=10) | 5 | $0.02-0.05 |

**Model Pricing (per 1M tokens):**
- Gemini 2.5 Flash: $0.075 input, $0.30 output ⚡️ **Recommended**
- Gemini Pro: $0.50 input, $1.50 output
- GPT-4 Turbo: $10.00 input, $30.00 output

### Output Format

```json
{
  "summary": {
    "total_issues": 47,
    "estimated_issues": 45,
    "total_estimated_low": 12500,
    "total_estimated_high": 35800
  },
  "cost_estimates": [
    {
      "item": "Air Conditioning Condenser Unit",
      "issue_description": "Refrigerant leak with low pressure",
      "severity": "High",
      "estimated_low": 800,
      "estimated_high": 2500,
      "confidence_score": 65,
      "reasoning": "Leak detection ($300-600), recharge ($300-600)...",
      "assumptions": ["Leak is accessible", "Compressor functional"],
      "risk_factors": ["Unit age may warrant replacement"],
      "validation": {
        "valid": true,
        "needs_review": true,
        "quality_score": 85
      }
    }
  ]
}
```

### Documentation

See [PROMPT_ENGINEERING_README.md](PROMPT_ENGINEERING_README.md) for complete documentation on:
- Prompt design and templates
- Houston market context
- Validation rules and quality control
- Version tracking and A/B testing
- Best practices and troubleshooting

## Error Handling

The pipeline includes comprehensive error handling:

- Graceful fallbacks for failed extractions
- Detailed error logging
- Validation of extracted data
- Recovery from partial failures

## Performance

- **Caching**: Avoids reprocessing unchanged files
- **Parallel Processing**: Can be extended for batch processing
- **Memory Efficient**: Processes large PDFs without loading entire document into memory
- **Incremental**: Can be extended to process page-by-page for very large documents

## Limitations

1. **Image Extraction**: Disabled - not needed for cost estimation (saves 95% storage and 10-30x processing time)
2. **Pattern Matching**: Relies on consistent document formatting
3. **Language Support**: Currently optimized for English inspection reports

## Extending the Pipeline

### Adding New Table Types

```python
def classify_table(headers, data):
    # Add new classification logic
    if 'your_keyword' in combined_text:
        return 'your_table_type'
```

### Custom Status Detection

```python
def detect_status_indicators(line):
    # Add new status patterns
    if re.search(r'your_pattern', line):
        return 'YOUR_STATUS'
```

### Additional Metadata Fields

```python
@dataclass
class PDFMetadata:
    # Add new fields
    custom_field: Optional[str] = None
```

## Troubleshooting

### Common Issues

1. **Memory errors**: Process smaller batches or individual pages
2. **Pattern matching failures**: Ensure PDFs follow standard inspection report format

### Debug Mode

```bash
python main.py report.pdf --verbose
```

## License

This project is provided as-is for educational and development purposes.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Support

For issues and questions, please check the troubleshooting section or create an issue in the repository.