"""
Estimation Prompt Builder

Assembles dynamic prompts for AI cost estimation by combining:
- System context (unchanging baseline)
- Property metadata (report-specific)
- Issue details (per-issue or batched)
- Seasonal context
- Related issues
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from .prompt_templates import (
    SYSTEM_CONTEXT,
    OUTPUT_CONSTRAINTS,
    FEW_SHOT_EXAMPLES,
    SEASONAL_CONTEXT,
    RELATED_ISSUES_PROMPTS,
    get_property_age_context
)

# Phase 1 Enhancement: Import enhanced templates
try:
    from .enhanced_prompt_templates import (
        get_enhanced_estimation_prompt,
        ENHANCED_SYSTEM_CONTEXT,
        ENHANCED_FEW_SHOT_EXAMPLES,
        ESTIMATION_RULES,
        VALIDATION_CHECKLIST
    )
    ENHANCED_PROMPTS_AVAILABLE = True
except ImportError:
    ENHANCED_PROMPTS_AVAILABLE = False


class EstimationPromptBuilder:
    """
    Builds prompts for AI cost estimation with Houston market context.
    
    Usage:
        builder = EstimationPromptBuilder(
            version="v1.0",
            include_examples=True,
            temperature=0.3
        )
        
        messages = builder.build_single_issue_prompt(
            issue=issue_data,
            property_data=property_metadata,
            related_issues=similar_issues
        )
    """
    
    def __init__(
        self,
        version: str = "v1.0",
        include_examples: bool = True,
        temperature: float = 0.3,
        custom_system_context: Optional[str] = None,
        use_enhanced_prompts: bool = True  # Phase 1: Use enhanced prompts by default
    ):
        """
        Initialize prompt builder.
        
        Args:
            version: Prompt version for tracking
            include_examples: Include few-shot examples in prompts
            temperature: AI temperature setting (0.2-0.3 for consistent estimates)
            custom_system_context: Override default system context
            use_enhanced_prompts: Use Phase 1 enhanced prompts with validation checklists
        """
        self.version = version
        self.include_examples = include_examples
        self.temperature = temperature
        self.use_enhanced_prompts = use_enhanced_prompts and ENHANCED_PROMPTS_AVAILABLE
        
        if self.use_enhanced_prompts:
            self.system_context = custom_system_context or ENHANCED_SYSTEM_CONTEXT
        else:
            self.system_context = custom_system_context or SYSTEM_CONTEXT
        
        self.prompt_count = 0
    
    def build_single_issue_prompt(
        self,
        issue: Dict[str, Any],
        property_data: Dict[str, Any],
        related_issues: Optional[List[Dict[str, Any]]] = None,
        current_date: Optional[datetime] = None
    ) -> List[Dict[str, str]]:
        """
        Build prompt for estimating a single issue.
        
        Args:
            issue: Issue data from enriched JSON
            property_data: Property metadata (age, size, location, etc.)
            related_issues: Other issues that may affect this estimate
            current_date: Date for seasonal context (defaults to today)
        
        Returns:
            List of message dicts for API call: [{"role": "system", "content": "..."}, ...]
        """
        self.prompt_count += 1
        
        if current_date is None:
            current_date = datetime.now()
        
        # Phase 1 Enhancement: Use enhanced prompts if enabled
        if self.use_enhanced_prompts:
            full_prompt = get_enhanced_estimation_prompt(
                issue=issue,
                property_context=property_data,
                include_examples=self.include_examples
            )
            messages = [
                {"role": "user", "content": full_prompt}
            ]
        else:
            # Original prompt building logic
            property_context = self._build_property_context(property_data, current_date)
            issue_prompt = self._build_issue_prompt(issue, property_data, related_issues)
            
            # Assemble full prompt
            user_message = f"{property_context}\n\n{issue_prompt}\n\n{OUTPUT_CONSTRAINTS}"
            
            if self.include_examples:
                user_message = f"{FEW_SHOT_EXAMPLES}\n\n{user_message}"
            
            messages = [
                {"role": "system", "content": self.system_context},
                {"role": "user", "content": user_message}
            ]
        
        return messages
    
    def build_batch_prompt(
        self,
        issues: List[Dict[str, Any]],
        property_data: Dict[str, Any],
        current_date: Optional[datetime] = None,
        max_issues: int = 10
    ) -> List[Dict[str, str]]:
        """
        Build prompt for estimating multiple related issues in one call.
        
        Batching reduces API costs but may reduce detail. Best for similar issues
        (e.g., all electrical, all plumbing) to maintain context.
        
        Args:
            issues: List of issue data from enriched JSON
            property_data: Property metadata
            current_date: Date for seasonal context
            max_issues: Maximum issues per batch (default 10)
        
        Returns:
            List of message dicts for API call
        """
        self.prompt_count += 1
        
        if current_date is None:
            current_date = datetime.now()
        
        # Limit batch size
        issues = issues[:max_issues]
        
        # Build context
        property_context = self._build_property_context(property_data, current_date)
        
        # Build batch issue prompt
        batch_prompt = self._build_batch_issue_prompt(issues, property_data)
        
        user_message = f"{property_context}\n\n{batch_prompt}\n\n{OUTPUT_CONSTRAINTS}"
        
        if self.include_examples:
            user_message = f"{FEW_SHOT_EXAMPLES}\n\n{user_message}"
        
        messages = [
            {"role": "system", "content": self.system_context},
            {"role": "user", "content": user_message}
        ]
        
        return messages
    
    def _build_property_context(
        self,
        property_data: Dict[str, Any],
        current_date: datetime
    ) -> str:
        """Build property-specific context."""
        
        year_built = property_data.get('year_built', property_data.get('built', 2000))
        property_type = property_data.get('type', 'Single-family home')
        square_footage = property_data.get('square_footage', property_data.get('size', 'Unknown'))
        location = property_data.get('location', 'Houston, TX')
        inspection_date = property_data.get('inspection_date', current_date.strftime('%B %Y'))
        
        # Get property age context
        age_context = get_property_age_context(year_built, current_date.year)
        
        # Get seasonal context
        month_name = current_date.strftime('%B')
        seasonal_info = SEASONAL_CONTEXT.get(month_name, "")
        
        # Build report summary if available
        report_summary = ""
        if 'issue_counts' in property_data:
            counts = property_data['issue_counts']
            report_summary = f"""
Report Summary:
- Total issues found: {counts.get('total', 'Unknown')}
- Critical issues: {counts.get('critical', 0)}
- High severity: {counts.get('high', 0)}
- Medium severity: {counts.get('medium', 0)}
- Low severity: {counts.get('low', 0)}
"""
        
        context = f"""Property Details:
- Built: {year_built} ({current_date.year - year_built} years old)
- Type: {property_type}
- Size: {square_footage} sq ft
- Location: {location}
- Inspection Date: {inspection_date}

Property Age Context:
{age_context}

Current Market Conditions:
- Date: {current_date.strftime('%B %Y')}
- Season: {seasonal_info}
{report_summary}"""
        
        return context.strip()
    
    def _build_issue_prompt(
        self,
        issue: Dict[str, Any],
        property_data: Dict[str, Any],
        related_issues: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """Build prompt for a single issue."""
        
        category = issue.get('category', 'General')
        item = issue.get('item', issue.get('component', 'Unknown'))
        description = issue.get('issue', issue.get('description', issue.get('issue_description', '')))
        severity = issue.get('severity', 'Unknown')
        location = issue.get('location', 'Not specified')
        action = issue.get('action', issue.get('suggested_action', 'Evaluate'))
        
        # Get related issues context
        related_context = self._build_related_issues_context(category, related_issues)
        
        # Get category-specific guidance
        category_guidance = self._get_category_guidance(category.lower())
        
        prompt = f"""Analyze the following issue and provide a detailed cost estimate:

Category: {category}
Item: {item}
Issue: {description}
Severity: {severity}
Location: {location}
Suggested Action: {action}

Context:
- This is a {property_data.get('year_built', 2000)}-built home in Houston, TX
{related_context}
{category_guidance}

Estimate the cost to {action.lower()} this issue, including:
- Labor (consider trade type, hourly rates, and hours required)
- Materials and supplies (Houston market prices)
- Permits or inspections if required (Houston permit costs)
- Contingency for related/hidden issues
- Any specialized equipment or techniques needed

Consider:
- Houston climate factors (humidity, heat, clay soil, hurricane risk)
- Accessibility and complexity of repair
- Property age and typical system lifespan
- Current market conditions and contractor availability

Return your estimate in the specified JSON format with detailed reasoning."""
        
        return prompt.strip()
    
    def _build_batch_issue_prompt(
        self,
        issues: List[Dict[str, Any]],
        property_data: Dict[str, Any]
    ) -> str:
        """Build prompt for multiple issues."""
        
        prompt = f"""Analyze the following {len(issues)} issues and provide cost estimates for each.

Return a JSON array with one estimate object for each issue, in the same order as listed below.

Issues to estimate:

"""
        
        for idx, issue in enumerate(issues, 1):
            category = issue.get('category', 'General')
            item = issue.get('item', issue.get('component', 'Unknown'))
            description = issue.get('issue', issue.get('description', ''))
            severity = issue.get('severity', 'Unknown')
            action = issue.get('action', issue.get('suggested_action', 'Evaluate'))
            
            prompt += f"""
Issue {idx}:
- Category: {category}
- Item: {item}
- Description: {description}
- Severity: {severity}
- Action: {action}
"""
        
        prompt += f"""
Context:
- Property: {property_data.get('year_built', 2000)}-built home in Houston, TX
- These issues are from the same inspection report
- Consider any relationships or dependencies between issues
- Apply Houston market rates and climate factors to all estimates

Return a JSON array: [{{"item": "...", "estimated_low": ..., ...}}, {{"item": "...", ...}}]
Each estimate must include all required fields with detailed reasoning.
"""
        
        return prompt.strip()
    
    def _build_related_issues_context(
        self,
        category: str,
        related_issues: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """Build context about related issues."""
        
        context = ""
        
        # Add category-specific guidance
        category_key = category.lower().replace(' ', '_')
        if category_key in RELATED_ISSUES_PROMPTS:
            context += f"\n{RELATED_ISSUES_PROMPTS[category_key]}"
        
        # Add specific related issues
        if related_issues and len(related_issues) > 0:
            context += f"\n\nRelated issues in this report:"
            for issue in related_issues[:3]:  # Limit to 3 most relevant
                item = issue.get('item', issue.get('component', 'Unknown'))
                desc = issue.get('issue', issue.get('description', ''))[:100]  # Truncate
                context += f"\n- {item}: {desc}"
        
        return context
    
    def _get_category_guidance(self, category: str) -> str:
        """Get category-specific estimation guidance."""
        
        guidance_map = {
            "foundation": """
Special considerations for foundation work:
- Always include structural engineer evaluation ($500-1200)
- Houston clay soil requires specialized piers (typically 8-12 piers needed)
- Include drainage improvements (critical for long-term stability)
- Consider plumbing leak testing (often contributes to settlement)
- Wide cost ranges are normal due to scope uncertainty""",
            
            "hvac": """
Special considerations for HVAC work:
- Houston systems run 8-9 months/year (shorter lifespan than national average)
- R-410A refrigerant is standard (older R-22 systems require conversion)
- Consider full replacement if unit is 12+ years old
- Include ductwork inspection and sealing
- Factor in humidity control needs""",
            
            "electrical": """
Special considerations for electrical work:
- Houston requires permits for most electrical work ($150-300)
- Federal Pacific and Zinsco panels are fire hazards (immediate replacement)
- Older homes often have inadequate service (100A vs modern 200A)
- GFCI outlets required in kitchens, bathrooms, outdoor areas
- Licensed electrician required (not handyman work)""",
            
            "plumbing": """
Special considerations for plumbing work:
- Pre-1980 Houston homes often have cast iron pipes (prone to corrosion)
- Slab foundation homes require special attention (under-slab leaks expensive)
- Water heater lifespan: 8-12 years in Houston (hard water)
- Include permit costs for major work ($100-200)
- Consider water quality testing if pipe corrosion evident""",
            
            "roofing": """
Special considerations for roofing work:
- Hurricane-rated shingles required in Houston area
- UV exposure is intense (shorter shingle lifespan)
- Check for proper attic ventilation (critical in Houston heat)
- Include underlayment and drip edge replacement
- Full tear-off typically required (vs overlay)""",
            
            "pest": """
Special considerations for pest issues:
- Houston has year-round termite activity (not seasonal)
- Subterranean termites are most common (require soil treatment)
- Include termite inspection by licensed inspector ($75-150)
- Wood-destroying insect reports required for many home sales
- Consider moisture control improvements (prevents recurrence)"""
        }
        
        return guidance_map.get(category, "")
    
    def add_custom_context(self, context: str) -> str:
        """
        Add custom context to system message.
        
        Args:
            context: Additional context to append
        
        Returns:
            Updated system context
        """
        self.system_context = f"{self.system_context}\n\n{context}"
        return self.system_context
    
    def get_stats(self) -> Dict[str, Any]:
        """Get prompt builder statistics."""
        return {
            "version": self.version,
            "prompts_built": self.prompt_count,
            "temperature": self.temperature,
            "includes_examples": self.include_examples
        }

