# PDF Inspection Report Extraction Pipeline

A comprehensive Python pipeline for extracting structured data from PDF inspection reports, designed specifically for real estate inspection documents.

## Features

- **Metadata Extraction**: Automatically extracts report metadata including property address, inspection date, and report number
- **Structured Text Extraction**: Preserves hierarchical structure (sections, subsections) and formatting information
- **Table Extraction**: Intelligently extracts and classifies tables (cost estimates, elevation surveys, checklists)
- **Issue Classification**: Automatically categorizes inspection issues by status and priority
- **Data Structuring**: Links related data (tables, text) to specific issues
- **Caching**: Built-in caching system to avoid reprocessing unchanged files

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
- `ExtractedImage`: Image with context and OCR
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