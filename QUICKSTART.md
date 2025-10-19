# Quick Start Guide: AI Cost Estimation

Get up and running with AI-powered cost estimation in minutes!

## Prerequisites

1. **Python 3.8+** installed
2. **Google Gemini API Key** - Get yours at [Google AI Studio](https://makersuite.google.com/app/apikey)
3. **Inspection Report PDF** - A Texas home inspection report

## Installation

```bash
# 1. Navigate to project directory
cd pdf-extraction

# 2. Activate virtual environment
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
```

## Step-by-Step Workflow

### Step 1: Extract Data from PDF

First, extract structured data from your inspection report PDF:

```bash
python main.py 6-report.pdf --output-dir extracted_data
```

**Output**: `extracted_data/6-report.json` with structured inspection data

### Step 2: Generate Cost Estimates

Now generate AI-powered cost estimates:

```bash
# Using your API key
python estimate_report.py extracted_data/6-report.json \
    --api-key AIzaSyD5fPlOw8e7fU6zKFf-lo2w65XhzSwzOSA
```

**Output** (in `./estimates/` directory):
- `cost_estimate_TIMESTAMP.pdf` - Professional PDF report
- `estimate_ui_TIMESTAMP.json` - UI-ready JSON data
- `estimate_result_TIMESTAMP.json` - Raw results

### Step 3: Review Results

Open the generated PDF report to see:
- Total cost estimates (min-max ranges)
- Top priority repairs
- Cost breakdown by section
- Houston-specific considerations
- Contractor recommendations

## Quick Example

Run the included example script:

```bash
python estimate_example.py
```

This will:
1. Load the sample inspection report
2. Generate cost estimates using AI
3. Create PDF and JSON outputs
4. Display summary in terminal

## API Key Setup

### Option 1: Environment Variable (Recommended)

```bash
export GEMINI_API_KEY="AIzaSyD5fPlOw8e7fU6zKFf-lo2w65XhzSwzOSA"
python estimate_report.py extracted_data/6-report.json
```

### Option 2: .env File

Create `.env` file in project root:

```
GEMINI_API_KEY=AIzaSyD5fPlOw8e7fU6zKFf-lo2w65XhzSwzOSA
```

Then run:

```bash
python estimate_report.py extracted_data/6-report.json
```

### Option 3: Command Line

```bash
python estimate_report.py extracted_data/6-report.json \
    --api-key AIzaSyD5fPlOw8e7fU6zKFf-lo2w65XhzSwzOSA
```

## Programmatic Usage

```python
from src.estimation_pipeline import EstimationPipeline

# Initialize pipeline
pipeline = EstimationPipeline(
    gemini_api_key="YOUR_API_KEY",
    location="Houston, TX",
    output_dir="./estimates"
)

# Generate estimates
result = pipeline.estimate_costs("extracted_data/6-report.json")

# Access results
print(f"Total cost: ${result.total_cost_min:,.0f} - ${result.total_cost_max:,.0f}")

# Generate outputs
pdf_path = pipeline.generate_pdf(result)
ui_path = pipeline.generate_ui_data(result)
```

## Understanding the Output

### PDF Report Sections

1. **Cover Page**
   - Property address and inspection date
   - Total estimated cost range
   - Summary statistics

2. **Executive Summary**
   - Top 5 priority repairs
   - Cost breakdown by major section

3. **Detailed Estimates**
   - Each repair listed with:
     - Cost breakdown (labor + materials)
     - Timeline estimate
     - Urgency level
     - Contractor type needed
     - Houston-specific notes

4. **Houston Considerations**
   - Local market factors
   - Climate considerations
   - Seasonal timing recommendations

5. **Disclaimer**
   - Important limitations and notes

### UI JSON Structure

```json
{
  "metadata": {
    "property_address": "...",
    "inspection_date": "...",
    "location": "Houston, TX"
  },
  "summary": {
    "total_issues": 45,
    "deficient_issues": 23,
    "estimated_total": {
      "min": 15000,
      "max": 25000,
      "formatted_range": "$15,000 - $25,000"
    },
    "priority_breakdown": {
      "high": 5,
      "medium": 10,
      "low": 8
    }
  },
  "sections": [...],
  "top_priorities": [...],
  "charts": {...}
}
```

## Cost Estimation Features

### Houston-Specific Pricing
- Labor rates based on Houston market (2025)
- Local material costs
- Permit requirements for Houston/Harris County
- Climate factors (humidity, hurricanes, heat)
- Common Houston home issues

### What Gets Estimated
- ✅ All "Deficient" (D) status items
- ✅ Labor and material costs separately
- ✅ Realistic min-max ranges
- ✅ Timeline estimates
- ✅ Urgency classification
- ❌ Not estimated: Informational items, already compliant items

### Cost Ranges
Estimates provide min-max ranges because:
- Contractor rates vary
- Material choices affect price
- Extent of damage may require inspection
- Market conditions fluctuate
- Coordination complexity varies

**Always get multiple contractor quotes for actual pricing!**

## API Usage & Costs

### Gemini 2.5 Flash Pricing
- Input: $0.075 per 1M tokens
- Output: $0.30 per 1M tokens

### Typical Report Costs
- 35-page inspection report
- ~23 deficient issues
- Estimated tokens: 15K input, 8K output
- **Cost per report: ~$0.001-$0.003** (very affordable!)

### View Usage Statistics
After running estimation:

```python
stats = pipeline.get_api_statistics()
print(f"Requests: {stats['request_count']}")
print(f"Cost: ${stats['estimated_cost_usd']:.4f}")
```

## Troubleshooting

### "No module named 'google.generativeai'"
```bash
pip install google-generativeai
```

### "API key not found"
Make sure you've set the API key using one of the three methods above.

### "SSL Certificate Error"
If installing packages fails due to SSL:
```bash
pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org google-generativeai
```

### "No deficient issues found"
The report may not have any items marked as "Deficient" (D). Check the extracted JSON file.

### API Rate Limits
Free tier: 15 requests per minute. The pipeline automatically handles rate limiting with delays between requests.

## Next Steps

1. **Extract Your Report**: Run extraction on your own inspection PDFs
2. **Review Estimates**: Check the generated PDF reports
3. **Get Contractor Quotes**: Use estimates as a guide, but always get professional quotes
4. **Customize**: Modify `src/prompts.py` to adjust pricing or add more context
5. **Integrate**: Use the UI JSON in your web/mobile application

## Support

For issues or questions:
1. Check the main [README.md](README.md) for detailed documentation
2. Review the [implementation plan](ai-cost-estimation.plan.md)
3. Run validation: `python validate_implementation.py`

## Important Notes

⚠️ **These are estimates, not quotes**
- Actual costs may vary significantly
- Always consult licensed contractors
- Get multiple professional quotes
- Consider this a planning tool

✅ **Houston-Specific**
- Estimates are tailored for Houston, TX market
- Includes local labor rates and considerations
- For other locations, adjust prompts in `src/prompts.py`

🔒 **API Key Security**
- Never commit API keys to version control
- Use environment variables or .env files
- Keep your .env file in .gitignore

