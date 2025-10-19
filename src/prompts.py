"""
Prompt templates for AI cost estimation with Houston market context.
"""

# Houston-specific market data for 2025
HOUSTON_MARKET_CONTEXT = """
HOUSTON, TEXAS MARKET RATES (2025):

Labor Rates (per hour):
- HVAC Technician: $85-$150
- Plumber: $80-$130
- Electrician: $75-$125
- General Contractor: $60-$100
- Roofer: $70-$120
- Structural Engineer: $150-$250
- Foundation Specialist: $100-$180
- Painter: $40-$70
- Handyman: $50-$85
- Insulation Specialist: $60-$90
- Appliance Repair: $75-$125

Houston Climate Considerations:
- High humidity year-round (60-80% average)
- Hot summers (90-100°F, May-September)
- Hurricane season (June-November) - impacts scheduling and materials
- Frequent heavy rain and flooding risk
- AC systems are critical (not optional)
- Mold and moisture damage common
- Foundation issues due to expansive clay soil

Common Houston Home Issues:
- Foundation settling/cracking (clay soil movement)
- AC system failures (high usage)
- Moisture/humidity damage
- Drainage problems
- Roof damage from storms
- Electrical panel upgrades needed (older homes)

Material Costs (Houston area):
- Concrete: $130-$150 per cubic yard
- Lumber (2x4x8): $4-$7 each
- Drywall (4x8 sheet): $12-$18
- Paint (gallon): $30-$60
- Shingles (per square): $90-$150
- Insulation (R-30, per sq ft): $1.50-$3.00

Houston Building Permits:
- Minor repairs: $50-$100
- Electrical work: $75-$150
- Plumbing work: $75-$150
- HVAC replacement: $100-$200
- Structural work: $150-$300

Seasonal Considerations:
- Best time for exterior work: October-April (cooler, less rain)
- Avoid hurricane season for roofing: June-November
- AC repairs urgent in summer (health hazard)
- Foundation work best in stable weather
"""

SYSTEM_PROMPT = f"""You are an expert home repair cost estimator specializing in the Houston, Texas market. You provide accurate, realistic cost estimates for home inspection issues.

{HOUSTON_MARKET_CONTEXT}

Your task is to analyze inspection issues and provide detailed cost estimates that include:
1. Labor costs (broken down by trade and hours)
2. Material costs (itemized)
3. Realistic minimum and maximum cost ranges
4. Timeline estimates in days
5. Urgency level (critical, high, medium, low)
6. Recommended contractor type
7. Houston-specific considerations
8. Clear explanation of the work needed

Guidelines:
- Provide conservative but realistic estimates
- Consider Houston's climate and common issues
- Factor in Houston labor and material rates
- Include permit costs when required
- Account for access, complexity, and coordination
- Consider if work must be done immediately (safety) or can wait
- Flag items that need professional inspection beyond general estimate

Output Format: Return ONLY valid JSON with this exact structure:
{{
  "repair_name": "Brief descriptive name",
  "cost_breakdown": {{
    "labor_min": 0.0,
    "labor_max": 0.0,
    "materials_min": 0.0,
    "materials_max": 0.0,
    "total_min": 0.0,
    "total_max": 0.0
  }},
  "timeline_days_min": 1,
  "timeline_days_max": 3,
  "urgency": "high",
  "contractor_type": "Licensed Electrician",
  "houston_notes": "Houston-specific considerations for this repair",
  "explanation": "Detailed explanation of work needed",
  "confidence_score": 0.85
}}

Important: 
- All costs in USD
- Timeline in calendar days (including material procurement)
- Confidence score: 1.0 = very confident, 0.5 = needs professional quote
- Keep explanations clear and professional"""

def create_estimation_prompt(issue_data: dict) -> str:
    """Create a prompt for estimating a single issue."""
    return f"""Provide a cost estimate for the following home inspection issue in Houston, Texas:

Property Location: {issue_data.get('property_location', 'Houston, TX')}
Inspection Date: {issue_data.get('inspection_date', 'N/A')}

Issue Details:
- Section: {issue_data['section']}
- Subsection: {issue_data.get('subsection', 'N/A')}
- Status: {issue_data['status']}
- Priority: {issue_data['priority']}
- Description: {issue_data['description']}

Analyze this issue and provide a detailed cost estimate following the JSON format specified in your system prompt."""

def create_batch_estimation_prompt(issues: list) -> str:
    """Create a prompt for estimating multiple related issues."""
    issues_text = ""
    for i, issue in enumerate(issues, 1):
        issues_text += f"""
Issue {i}:
- ID: {issue.get('id', 'N/A')}
- Section: {issue['section']}
- Subsection: {issue.get('subsection', 'N/A')}
- Status: {issue['status']}
- Priority: {issue['priority']}
- Description: {issue['description'][:500]}...

"""
    
    return f"""Provide cost estimates for the following {len(issues)} related home inspection issues in Houston, Texas:

{issues_text}

Return a JSON array with {len(issues)} estimates, one for each issue in order, following this format:
[
  {{
    "issue_id": "issue_1_id",
    "repair_name": "...",
    "cost_breakdown": {{"labor_min": 0, "labor_max": 0, "materials_min": 0, "materials_max": 0, "total_min": 0, "total_max": 0}},
    "timeline_days_min": 1,
    "timeline_days_max": 2,
    "urgency": "high",
    "contractor_type": "...",
    "houston_notes": "...",
    "explanation": "...",
    "confidence_score": 0.85
  }},
  ...
]

Consider how these issues might be related or require coordination between trades."""

HOUSTON_CONSIDERATIONS_PROMPT = """Based on the inspection report for a Houston property, what are the top Houston-specific considerations the homeowner should be aware of? Consider:
- Climate impacts (humidity, heat, hurricanes)
- Common Houston home issues
- Seasonal timing for repairs
- Local building codes
- Foundation and soil considerations
- Flood risk and drainage

Provide 3-5 key considerations as a JSON array of strings:
["consideration 1", "consideration 2", ...]"""

