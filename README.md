# PDF Inspection Report Extraction & AI Cost Estimation Pipeline

A comprehensive Python pipeline for extracting structured data from PDF inspection reports and generating AI-powered repair cost estimates, designed specifically for Houston, Texas real estate properties.

## Features

### PDF Extraction
- **Metadata Extraction**: Automatically extracts report metadata including property address, inspection date, and report number
- **Structured Text Extraction**: Preserves hierarchical structure (sections, subsections) and formatting information
- **Table Extraction**: Intelligently extracts and classifies tables (cost estimates, elevation surveys, checklists)
- **Issue Classification**: Automatically categorizes inspection issues by status and priority
- **Data Structuring**: Links related data (tables, text) to specific issues
- **Caching**: Built-in caching system to avoid reprocessing unchanged files

### AI Cost Estimation (NEW!)
- **Houston-Specific Estimates**: AI-powered cost estimates using Google Gemini 2.5 Flash with Houston market rates
- **Detailed Breakdowns**: Labor and material costs with minimum/maximum ranges
- **Priority Analysis**: Automatic urgency classification and prioritization
- **Professional PDF Reports**: Generate beautiful, comprehensive PDF cost reports
- **UI-Ready Data**: Export JSON data formatted for web/mobile applications
- **Batch Processing**: Efficient parallel processing of multiple issues
- **Market Context**: Incorporates Houston climate, building codes, and seasonal considerations

> **Note**: Image extraction is currently disabled in the pipeline.

## Installation

### Prerequisites

- Python 3.8+

### Installation

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

## Usage

### Part 1: PDF Extraction

#### Command Line Interface

```bash
# Basic usage - Extract data from PDF
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

### Part 2: AI Cost Estimation

#### Setup API Key

First, obtain a Google Gemini API key from [Google AI Studio](https://makersuite.google.com/app/apikey).

Then set your API key (choose one method):

```bash
# Option 1: Environment variable
export GEMINI_API_KEY="your_api_key_here"

# Option 2: Create .env file in project root
echo "GEMINI_API_KEY=your_api_key_here" > .env

# Option 3: Pass directly to script (see below)
```

#### Command Line Interface

```bash
# Basic usage - Generate cost estimates from extracted JSON
python estimate_report.py extracted_data/6-report.json

# Specify API key directly
python estimate_report.py extracted_data/6-report.json --api-key YOUR_KEY

# Custom output directory
python estimate_report.py extracted_data/6-report.json --output-dir ./my_estimates

# Generate only PDF report
python estimate_report.py extracted_data/6-report.json --pdf-only

# Generate only UI JSON
python estimate_report.py extracted_data/6-report.json --ui-only

# Disable batch processing (process one at a time)
python estimate_report.py extracted_data/6-report.json --no-batch

# Verbose logging
python estimate_report.py extracted_data/6-report.json --verbose
```

#### Complete Workflow Example

```bash
# Step 1: Extract data from PDF
python main.py 6-report.pdf --output-dir extracted_data

# Step 2: Generate cost estimates
python estimate_report.py extracted_data/6-report.json

# Results will be in ./estimates/ directory:
#   - cost_estimate_TIMESTAMP.pdf      (Professional PDF report)
#   - estimate_ui_TIMESTAMP.json       (UI-ready JSON data)
#   - estimate_result_TIMESTAMP.json   (Raw estimation result)
```

### Programmatic Usage

#### PDF Extraction

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

#### AI Cost Estimation

```python
from src.estimation_pipeline import EstimationPipeline

# Initialize estimation pipeline
pipeline = EstimationPipeline(
    gemini_api_key="YOUR_API_KEY",
    location="Houston, TX",
    output_dir="./estimates"
)

# Generate cost estimates
result = pipeline.estimate_costs("extracted_data/6-report.json")

# Access results
print(f"Total cost: ${result.total_cost_min:,.0f} - ${result.total_cost_max:,.0f}")
print(f"Found {len(result.estimates)} repairs to estimate")

# Generate PDF and UI outputs
pdf_path = pipeline.generate_pdf(result)
ui_path = pipeline.generate_ui_data(result)

# Or run full pipeline at once
output = pipeline.process_full_pipeline("extracted_data/6-report.json")
print(f"PDF: {output['pdf_path']}")
print(f"UI Data: {output['ui_path']}")
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

**PDF Extraction Models:**
- `PDFMetadata`: Basic document information
- `TextBlock`: Structured text with formatting
- `ExtractedTable`: Table data with classification
- `ExtractedImage`: Image with context and OCR
- `InspectionIssue`: Complete issue information
- `StructuredReport`: Final structured output

**Cost Estimation Models:**
- `CostBreakdown`: Labor and material cost breakdown
- `RepairEstimate`: Complete estimate for single issue
- `EstimationResult`: Aggregated results for entire report

### AI Cost Estimation Architecture

The cost estimation system consists of multiple integrated components:

1. **AI Estimator** (`src/ai_estimator.py`)
   - Google Gemini 2.5 Flash API integration
   - Retry logic and rate limiting
   - Token counting and cost tracking
   - JSON-structured output

2. **Data Preparer** (`src/data_preparer.py`)
   - Filters deficient issues from reports
   - Transforms data for AI consumption
   - Groups issues by section/priority

3. **Chunk Manager** (`src/chunk_manager.py`)
   - Batches issues for efficient API calls
   - Maintains context across related issues
   - Token budget management

4. **Cost Estimator** (`src/cost_estimator.py`)
   - Main orchestration engine
   - Parallel API call processing
   - Cost aggregation and statistics

5. **Prompt Engineering** (`src/prompts.py`)
   - Houston-specific market context
   - 2025 labor and material rates
   - Climate and building code considerations

6. **PDF Generator** (`src/pdf_generator.py`)
   - Professional report layout
   - Color-coded priorities
   - Section breakdowns and summaries

7. **UI Data Formatter** (`src/ui_data_formatter.py`)
   - Frontend-optimized JSON output
   - Chart-ready data structures
   - Responsive design considerations

8. **Estimation Pipeline** (`src/estimation_pipeline.py`)
   - End-to-end workflow orchestration
   - Progress tracking
   - Multi-format output generation

### Cost Estimation Output Formats

#### PDF Report
Professional PDF report includes:
- **Cover Page**: Property info, total cost estimate
- **Executive Summary**: Top priorities, cost by section
- **Detailed Estimates**: Full breakdown per issue
- **Houston Considerations**: Local market factors
- **Disclaimer**: Estimation limitations

#### UI JSON Data
Frontend-optimized JSON with:
- **Summary Statistics**: Total costs, issue counts, priority breakdown
- **Section Details**: Costs and issues grouped by section
- **Top Priorities**: Highest urgency items
- **Chart Data**: Ready for visualization (pie, bar charts)
- **Formatted Values**: Pre-formatted currency strings

#### Sample Cost Estimate Structure
```json
{
  "repair_name": "Attic Insulation Replacement",
  "cost": {
    "labor": {"min": 800, "max": 1200},
    "materials": {"min": 400, "max": 600},
    "total": {"min": 1200, "max": 1800}
  },
  "timeline": {"min_days": 1, "max_days": 2},
  "urgency": "medium",
  "contractor_type": "Insulation Specialist",
  "houston_notes": "R-38 recommended for Houston heat",
  "confidence_score": 0.85
}
```

### Houston Market Context

The AI estimation system is specifically trained for Houston, TX market with:

**Labor Rates (2025):**
- HVAC: $85-$150/hr
- Plumbing: $80-$130/hr  
- Electrical: $75-$125/hr
- General Contractor: $60-$100/hr
- Roofing: $70-$120/hr

**Climate Considerations:**
- High humidity (60-80% average)
- Hot summers requiring robust AC
- Hurricane season impacts (June-November)
- Foundation issues from clay soil
- Frequent flooding concerns

**Local Factors:**
- Houston building codes
- Permit requirements and costs
- Seasonal pricing variations
- Common Houston home issues

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

1. **Image Extraction**: Image extraction is currently disabled
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
2. **Pattern matching issues**: Ensure PDFs have consistent formatting

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