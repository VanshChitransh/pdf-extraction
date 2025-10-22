"""
Enhanced Cost Estimation Pipeline

Integrates Phase 1 enhancements:
- Multi-dimensional confidence scoring
- Houston cost database lookup
- Relationship analysis for bundled estimates
- Specialist prompts
- Advanced quality assurance

Usage:
    python enhanced_cost_estimator.py --input enriched_data/6-report_enriched.json
"""

import os
import sys
import json
import argparse
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from estimation.confidence_scorer import AdvancedConfidenceScorer
from estimation.cost_database import HoustonCostDatabase
from estimation.relationship_analyzer import IssueRelationshipAnalyzer
from prompting.specialist_prompts import SpecialistPromptSelector
from prompting.prompt_builder import EstimationPromptBuilder
from prompting.output_validator import OutputValidator
from validation.data_quality_validator import DataQualityValidator
from validation.estimation_validator import EstimationValidator

# AI API imports
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


class EnhancedCostEstimator:
    """
    Enhanced cost estimation pipeline with Phase 1 improvements.
    
    Features:
    - Multi-dimensional confidence scoring
    - Houston cost database integration
    - Relationship analysis
    - Specialist prompts
    - Hybrid estimation (database + AI)
    """
    
    def __init__(
        self,
        model: str = "gemini-2.5-flash",  # Gemini 2.5 Flash: Best for complex reasoning (FREE TIER: 5 req/min, 100 req/day)
        api_key: Optional[str] = None,
        temperature: float = 0.3,
        enable_database_lookup: bool = True,
        enable_relationship_analysis: bool = True,
        enable_specialist_prompts: bool = True
    ):
        """
        Initialize enhanced estimator.
        
        Args:
            model: AI model name (gemini-2.5-flash recommended for cost estimation)
            api_key: API key (or set GEMINI_API_KEY env var)
            temperature: AI temperature
            enable_database_lookup: Use cost database when possible
            enable_relationship_analysis: Analyze issue relationships
            enable_specialist_prompts: Use category-specific prompts
            
        Free tier limits:
            - gemini-2.5-flash: 5 requests/min, 100 requests/day
            - System automatically enforces rate limiting
        """
        self.model = model
        self.temperature = temperature
        self.enable_database_lookup = enable_database_lookup
        self.enable_relationship_analysis = enable_relationship_analysis
        self.enable_specialist_prompts = enable_specialist_prompts
        
        # Initialize components
        self.confidence_scorer = AdvancedConfidenceScorer()
        self.cost_db = HoustonCostDatabase()
        self.relationship_analyzer = IssueRelationshipAnalyzer()
        self.specialist_selector = SpecialistPromptSelector()
        self.prompt_builder = EstimationPromptBuilder(temperature=temperature)
        self.validator = OutputValidator(
            manual_review_threshold=65  # Lower threshold for stricter review
        )
        
        # Phase 1 Enhanced Validators
        self.data_quality_validator = DataQualityValidator(strict_mode=False)
        self.estimation_validator = EstimationValidator(strict_mode=False, auto_correct=True)
        
        # Initialize AI client
        if GEMINI_AVAILABLE:
            api_key = api_key or os.environ.get("GEMINI_API_KEY")
            if api_key:
                # Validate API key format
                if not api_key.startswith("AIza"):
                    print(f"⚠️ Warning: API key format looks incorrect")
                    print(f"  Key should start with 'AIza' (got: {api_key[:4]}...)")
                    print(f"  Length should be ~39 chars (got: {len(api_key)})")
                    self._log_error("API key validation", f"Key format looks incorrect: starts with {api_key[:4]}, length {len(api_key)}")
                
                try:
                    genai.configure(api_key=api_key)
                    self.client = genai.GenerativeModel(model)
                    # Track API calls for rate limiting
                    # Free tier limits: gemini-2.5-flash=5/min, 100/day
                    self.api_call_times = []
                    self.max_calls_per_minute = self._get_rate_limit(model)
                    
                    # Track daily quota (100 requests/day for free tier)
                    self.daily_quota_file = Path("daily_api_usage.json")
                    self.max_daily_requests = 100
                    self._load_daily_quota()
                    
                    # Verify API connection with a simple test
                    self._verify_api_connection()
                except Exception as e:
                    self.client = None
                    error_msg = str(e)
                    print(f"❌ Error initializing API client: {error_msg}")
                    self._log_error("API client initialization failed", error_msg)
                    print("Falling back to database-only mode.")
            else:
                self.client = None
                self._log_error("API key missing", "GEMINI_API_KEY not set in environment or constructor")
                print("❌ Warning: GEMINI_API_KEY not set. Database-only mode.")
                print("  Set with: export GEMINI_API_KEY=your_key_here")
                print("  Or run: python test_api_connection.py for diagnostics")
        else:
            self.client = None
            self._log_error("API library missing", "google-generativeai package not installed")
            print("❌ Warning: google-generativeai not installed. Database-only mode.")
            print("  Install with: pip install google-generativeai")
        
        # Statistics
        self.stats = {
            "total_issues": 0,
            "database_matches": 0,
            "ai_estimates": 0,
            "hybrid_estimates": 0,
            "high_confidence": 0,
            "needs_review": 0,
            "bundles_identified": 0,
            # Phase 1 Enhanced Stats
            "data_quality_excluded": 0,
            "data_quality_flagged": 0,
            "estimation_auto_corrected": 0,
            "estimation_validation_failed": 0
        }
    
    def _get_rate_limit(self, model: str) -> int:
        """
        Get appropriate rate limit for model.
        
        Free tier limits (as of October 2025):
        - gemini-2.5-flash: 5 requests/minute, 100 requests/day
        - gemini-1.5-flash: 15 requests/minute
        - gemini-1.5-pro: 2 requests/minute
        
        Returns conservative limit to avoid hitting quota.
        We use 4 requests/min for 5/min limit (leave buffer).
        """
        if "2.5-flash" in model.lower():
            # Gemini 2.5 Flash: 5 req/min free tier
            # Use 4 to be safe (15 seconds between calls)
            return 4
        elif "1.5-flash" in model.lower():
            return 12  # Conservative: stay under 15/min
        elif "1.5-pro" in model.lower():
            return 1  # Very conservative for 2/min limit
        else:
            return 4  # Default: assume 5/min limit
    
    def estimate_report(
        self,
        enriched_data_path: str,
        output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a full report with enhanced estimation.
        
        Args:
            enriched_data_path: Path to enriched JSON
            output_path: Output path (auto-generated if None)
        
        Returns:
            Results dict with estimates and statistics
        """
        print(f"Loading enriched data from: {enriched_data_path}")
        with open(enriched_data_path, 'r') as f:
            enriched_data = json.load(f)
        
        # Extract metadata and issues
        metadata = enriched_data.get("metadata", {})
        issues = enriched_data.get("issues", [])
        
        self.stats["total_issues"] = len(issues)
        print(f"Found {len(issues)} issues to estimate")
        
        # PHASE 1 ENHANCEMENT: Pre-estimation data quality validation
        print("\nValidating data quality...")
        quality_results = self.data_quality_validator.validate_batch(issues)
        
        valid_issues = quality_results['valid_issues']
        excluded_issues = quality_results['excluded_issues']
        flagged_issues = quality_results['flagged_issues']
        
        print(f"  ✓ Passed: {len(valid_issues)}/{len(issues)}")
        print(f"  ✗ Excluded: {len(excluded_issues)} (low quality)")
        print(f"  ⚠ Flagged for review: {len(flagged_issues)}")
        
        if excluded_issues:
            print("\n  Exclusion reasons:")
            for exc in excluded_issues[:5]:  # Show first 5
                print(f"    - {exc['reason']}")
            if len(excluded_issues) > 5:
                print(f"    ... and {len(excluded_issues) - 5} more")
        
        # Use only valid issues for estimation
        issues = valid_issues
        self.stats["data_quality_excluded"] = len(excluded_issues)
        self.stats["data_quality_flagged"] = len(flagged_issues)
        
        # Analyze relationships
        relationships = None
        if self.enable_relationship_analysis:
            print("\nAnalyzing issue relationships...")
            relationships = self.relationship_analyzer.analyze_all_issues(issues)
            self.stats["bundles_identified"] = len(relationships["bundles"])
            print(f"  - Found {len(relationships['causal_chains'])} causal chains")
            print(f"  - Identified {len(relationships['bundles'])} bundling opportunities")
            print(f"  - {len(relationships['isolated_issues'])} standalone issues")
        
        # Process each issue
        print("\nGenerating cost estimates...")
        results = []
        
        for idx, issue in enumerate(issues, 1):
            # Handle both dict and list formats - CHECK BEFORE ACCESSING
            if not isinstance(issue, dict):
                print(f"[{idx}/{len(issues)}] Invalid format (not a dict) ... ✗ Skipping")
                continue
            
            # Now safe to call .get()
            print(f"[{idx}/{len(issues)}] {issue.get('item', 'Unknown')}", end=" ... ")
            
            try:
                estimate = self._estimate_issue(
                    issue,
                    metadata,
                    all_issues=issues,
                    relationships=relationships
                )
                
                if estimate:
                    results.append(estimate)
                    
                    # Update stats
                    if estimate.get("estimation_method") == "database":
                        self.stats["database_matches"] += 1
                    elif estimate.get("estimation_method") == "ai":
                        self.stats["ai_estimates"] += 1
                    else:
                        self.stats["hybrid_estimates"] += 1
                    
                    confidence = estimate.get("confidence", {}).get("overall", 0)
                    if confidence >= 85:
                        self.stats["high_confidence"] += 1
                    
                    if estimate.get("validation", {}).get("needs_review"):
                        self.stats["needs_review"] += 1
                    
                    # Print result
                    low = estimate.get("estimated_low", 0)
                    high = estimate.get("estimated_high", 0)
                    conf = estimate.get("confidence", {}).get("overall", 0)
                    print(f"✓ ${low:.0f}-${high:.0f} (confidence: {conf:.0f})")
                else:
                    print("✗ Failed")
            
            except Exception as e:
                print(f"✗ Error: {str(e)}")
                continue
        
        # Save results
        if output_path is None:
            report_name = Path(enriched_data_path).stem.replace('_enriched', '')
            output_path = f"cost_estimates/{report_name}_enhanced_estimates.json"
        
        self._save_results(results, output_path, metadata, relationships)
        
        # Print summary
        self._print_summary()
        
        return {
            "output_file": output_path,
            "statistics": self.stats,
            "results": results
        }
    
    def _estimate_issue(
        self,
        issue: Dict[str, Any],
        metadata: Dict[str, Any],
        all_issues: List[Dict[str, Any]],
        relationships: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Estimate a single issue using hybrid approach."""
        
        # Validate issue is a dict
        if not isinstance(issue, dict):
            print(f"✗ Skipping invalid issue format (expected dict, got {type(issue).__name__})")
            return None
        
        # Validate/align classifications against original section to avoid enrichment mislabels
        try:
            self._validate_classification(issue)
        except Exception:
            # Non-fatal
            pass
        
        # Step 1: Try database lookup
        database_estimate = None
        if self.enable_database_lookup:
            database_estimate = self._try_database_lookup(issue, metadata)
        
        # Step 2: Try AI estimation (if database lookup failed or low confidence)
        ai_estimate = None
        use_ai = (
            self.client is not None and 
            (database_estimate is None or database_estimate.get("confidence", 0) < 0.75)
        )
        
        if use_ai:
            ai_estimate = self._try_ai_estimation(issue, metadata, all_issues)
        
        # Step 3: Combine or select best estimate
        if database_estimate and ai_estimate:
            # Hybrid: Use both
            final_estimate = self._combine_estimates(database_estimate, ai_estimate)
            estimation_method = "hybrid"
        elif database_estimate:
            final_estimate = database_estimate
            estimation_method = "database"
        elif ai_estimate:
            final_estimate = ai_estimate
            estimation_method = "ai"
        else:
            # Rule-based fallback to avoid silent failures
            fallback = self._generate_fallback_estimate(issue)
            if not fallback:
                return None
            final_estimate = fallback
            estimation_method = "fallback"
        
        # Step 4: Calculate multi-dimensional confidence
        property_age = self._get_property_age(metadata)
        
        confidence = self.confidence_scorer.calculate_confidence(
            estimate=final_estimate,
            issue=issue,
            property_age=property_age,
            has_photos=False,  # TODO: Check for photo references
            database_match_score=database_estimate.get("confidence", 0) if database_estimate else None
        )
        
        # Step 5: Analyze relationships
        bundle_info = None
        if self.enable_relationship_analysis and relationships:
            bundle_info = self.relationship_analyzer.group_for_bundled_estimate(
                issue,
                all_issues,
                max_bundle_size=3
            )
        
        # Step 6: Validate (old validator - kept for compatibility)
        validation = self.validator.validate_estimate(final_estimate, strict=False)
        
        # PHASE 1 ENHANCEMENT: Advanced estimation validation
        enhanced_validation = self.estimation_validator.validate_estimate(final_estimate, issue)
        
        # Use corrected estimate if available
        if enhanced_validation.corrected_estimate:
            final_estimate = enhanced_validation.corrected_estimate
        
        # Merge validation results
        all_errors = validation.get("errors", []) + enhanced_validation.errors
        all_warnings = validation.get("warnings", []) + enhanced_validation.warnings
        
        # Determine final review status
        needs_review = (
            validation.get("needs_review", False) or
            not enhanced_validation.valid or
            enhanced_validation.action.value in ['flag_for_review', 'regenerate_estimate']
        )
        
        # Assemble final result
        # CRITICAL: Ensure estimated_low/high are preserved at top level
        result = {
            "item": final_estimate.get("item", issue.get("item", "Unknown")),
            "issue_description": final_estimate.get("issue_description", issue.get("description", "")),
            "severity": final_estimate.get("severity", issue.get("severity", "Unknown")),
            "suggested_action": final_estimate.get("suggested_action", issue.get("action", "")),
            
            # CRITICAL: Cost estimates must be at top level for validation
            "estimated_low": final_estimate.get("estimated_low", 0),
            "estimated_high": final_estimate.get("estimated_high", 0),
            "confidence_score": final_estimate.get("confidence_score", 50),
            
            # Reasoning and assumptions
            "reasoning": final_estimate.get("reasoning", ""),
            "assumptions": final_estimate.get("assumptions", []),
            "risk_factors": final_estimate.get("risk_factors", []),
            
            # Metadata
            "original_issue": issue,
            "estimation_method": estimation_method,
            "confidence": confidence,  # Multi-dimensional confidence breakdown
            "validation": {
                "valid": validation["valid"] and enhanced_validation.valid,
                "needs_review": needs_review,
                "quality_score": validation["quality_score"],
                "errors": all_errors,
                "warnings": all_warnings,
                "enhanced_validation": {
                    "passed": enhanced_validation.valid,
                    "action": enhanced_validation.action.value,
                    "reason": enhanced_validation.reason
                }
            }
        }
        
        if bundle_info and bundle_info["should_estimate_together"]:
            # Safely extract related issue names
            related_names = []
            for r in bundle_info["related_issues"]:
                if isinstance(r, dict):
                    related_names.append(r.get("item", "Unknown"))
                else:
                    related_names.append(str(r))
            
            result["bundling"] = {
                "related_issues": related_names,
                "savings_pct": bundle_info["labor_savings_pct"],
                "recommendation": bundle_info["bundling_recommendation"]
            }
        
        return result
    
    def _try_database_lookup(
        self,
        issue: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Try to get estimate from cost database."""
        # Safety check
        if not isinstance(issue, dict):
            return None
            
        component = issue.get("item", "")
        description = issue.get("issue", "")
        
        # Try to extract specifications
        specifications = None
        # TODO: Extract specifications from description (e.g., "3 ton", "50 gallon")
        
        # Build context
        property_age = self._get_property_age(metadata)
        context = {
            "property_age": property_age,
            "access_difficulty": "normal",  # TODO: Infer from description
            "information_quality": "medium"
        }
        
        # Lookup in database
        estimate = self.cost_db.get_estimate(component, specifications, context)
        
        if estimate:
            # Enrich with issue details
            estimate["item"] = issue.get("item", "")
            estimate["issue_description"] = issue.get("issue", "")
            estimate["severity"] = issue.get("severity", "Unknown")
            estimate["suggested_action"] = issue.get("action", "Repair")
            estimate["reasoning"] = f"Based on Houston cost database for {component}. " + ", ".join(estimate.get("notes", []))
            estimate["assumptions"] = [
                "Based on Houston market rates (2024-2025)",
                "Standard difficulty and access",
                f"Property age: {property_age} years" if property_age else "Property age unknown"
            ]
            estimate["risk_factors"] = estimate.get("notes", [])
            
            # Use database confidence as confidence_score
            estimate["confidence_score"] = int(estimate.get("confidence", 0.8) * 100)
        
        return estimate
    
    def _load_daily_quota(self):
        """Load daily API usage tracking."""
        today = datetime.now().strftime("%Y-%m-%d")
        
        if self.daily_quota_file.exists():
            with open(self.daily_quota_file, 'r') as f:
                data = json.load(f)
                if data.get('date') == today:
                    self.daily_requests_made = data.get('count', 0)
                else:
                    # New day, reset counter
                    self.daily_requests_made = 0
        else:
            self.daily_requests_made = 0
    
    def _save_daily_quota(self):
        """Save daily API usage."""
        today = datetime.now().strftime("%Y-%m-%d")
        with open(self.daily_quota_file, 'w') as f:
            json.dump({
                'date': today,
                'count': self.daily_requests_made
            }, f)
    
    def _rate_limit_check(self):
        """Check and enforce rate limiting for API calls (per-minute and daily)."""
        if not hasattr(self, 'api_call_times'):
            return
        
        # Check daily quota first (100 requests/day for free tier)
        if self.daily_requests_made >= self.max_daily_requests:
            print(f"\n❌ Daily quota exceeded ({self.max_daily_requests} requests/day)")
            print("Free tier limit reached. Solutions:")
            print("  1. Wait until tomorrow (quota resets)")
            print("  2. Upgrade to paid tier")
            print("  3. Use a different API key")
            raise Exception(f"Daily quota exceeded: {self.daily_requests_made}/{self.max_daily_requests}")
        
        current_time = time.time()
        
        # Remove calls older than 60 seconds
        self.api_call_times = [t for t in self.api_call_times if current_time - t < 60]
        
        # Rate limiting based on model
        if "2.5-flash" in self.model.lower():
            # Gemini 2.5 Flash: 5 requests/min
            # We use 4/min to be safe → 15 seconds between calls
            if self.api_call_times:
                last_call = self.api_call_times[-1]
                time_since_last = current_time - last_call
                min_wait = 15  # 15 seconds for 4 req/min (safe under 5/min limit)
                
                if time_since_last < min_wait:
                    wait_time = min_wait - time_since_last
                    print(f"⏳ Waiting {wait_time:.0f}s (5 req/min limit)... ", end="", flush=True)
                    time.sleep(wait_time)
            
            # Also check if we're at the per-minute limit
            if len(self.api_call_times) >= self.max_calls_per_minute:
                oldest_call = self.api_call_times[0]
                wait_time = 60 - (current_time - oldest_call) + 2  # Add 2 second buffer
                if wait_time > 0:
                    print(f"⏳ Waiting {wait_time:.0f}s... ", end="", flush=True)
                    time.sleep(wait_time)
        elif "1.5-flash" in self.model.lower():
            # For Flash (15 requests/min): Use standard rate limit check with buffer
            # Keep 12 req/min (one every 5s) to stay safely under 15/min
            if len(self.api_call_times) >= self.max_calls_per_minute:
                oldest_call = self.api_call_times[0]
                wait_time = 60 - (current_time - oldest_call) + 1  # Add 1 second buffer
                if wait_time > 0:
                    print(f"⏳ Waiting {wait_time:.0f}s... ", end="", flush=True)
                    time.sleep(wait_time)
        else:
            # For other models: standard check
            if len(self.api_call_times) >= self.max_calls_per_minute:
                oldest_call = self.api_call_times[0]
                wait_time = 60 - (current_time - oldest_call) + 1
                if wait_time > 0:
                    print(f"⏳ Waiting {wait_time:.0f}s... ", end="", flush=True)
                    time.sleep(wait_time)
        
        # Record this call
        self.api_call_times.append(time.time())
        self.daily_requests_made += 1
        
        # Save daily quota
        self._save_daily_quota()
        
        # Show progress toward daily limit
        if self.daily_requests_made % 10 == 0:
            remaining = self.max_daily_requests - self.daily_requests_made
            print(f"\n📊 Daily quota: {self.daily_requests_made}/{self.max_daily_requests} used ({remaining} remaining)")
    
    def _try_ai_estimation(
        self,
        issue: Dict[str, Any],
        metadata: Dict[str, Any],
        all_issues: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Get estimate from AI model."""
        if not self.client:
            # ENHANCED: Log why client is None
            self._log_error("AI estimation skipped", "API client not initialized (API key not set or library not installed)")
            return None
        
        # Extra safety: Validate issue is a dict
        if not isinstance(issue, dict):
            print(f"Skipping non-dict issue in AI estimation")
            return None
        
        # Rate limiting check
        self._rate_limit_check()
        
        # Build property context (more robust fallbacks + age)
        property_data = {
            "year_built": metadata.get("year_built", metadata.get("property_year", 2000)),
            "type": metadata.get("property_type", metadata.get("type", "Single-family home")),
            "square_footage": metadata.get("square_footage", metadata.get("size", self._estimate_size_from_issues(all_issues))),
            "location": "Houston, TX",
            "age_years": (datetime.now().year - metadata.get("year_built", 2000))
        }
        
        # Add specialist context if enabled (derive category from original section)
        specialist_context = None
        if self.enable_specialist_prompts:
            property_age = self._get_property_age(metadata)
            section = issue.get('section', '')
            original_category = self._extract_category_from_section(section)
            specialist_context = self.specialist_selector.get_specialist_context(
                category=original_category,
                issue_data=issue,
                property_age=property_age
            )
        
        # Filter out any non-dict issues from all_issues
        valid_issues = [i for i in all_issues if isinstance(i, dict)]
        
        # Clean issue description to remove boilerplate
        cleaned_issue = self._clean_description_for_ai(issue)
        
        # Build prompt
        messages = self.prompt_builder.build_single_issue_prompt(
            issue=cleaned_issue,
            property_data=property_data,
            related_issues=self._find_related_issues(cleaned_issue, valid_issues)
        )
        
        # Add specialist context to prompt
        if specialist_context:
            # Check which message format we're using
            if len(messages) > 1:
                # Old format: [system, user]
                messages[1]["content"] = specialist_context + "\n\n" + messages[1]["content"]
            else:
                # Enhanced format: [user only]
                messages[0]["content"] = specialist_context + "\n\n" + messages[0]["content"]
        
        # Call AI with improved error handling and retries
        max_retries = 2
        retry_count = 0
        
        while retry_count <= max_retries:
            try:
                full_prompt = "\n\n".join(msg["content"] for msg in messages)
                
                # Log the attempt
                attempt_msg = "Initial attempt" if retry_count == 0 else f"Retry #{retry_count}"
                print(f"🔄 {attempt_msg} for issue: {issue.get('id', 'unknown')}")
                
                response = self.client.generate_content(
                    full_prompt,
                    generation_config={
                        "temperature": self.temperature,
                        "response_mime_type": "application/json"
                    }
                )
                
                # Parse response
                try:
                    estimate = json.loads(response.text)
                    
                    # Validate estimate structure - MUST have costs and reasoning
                    required_fields = ["estimated_low", "estimated_high"]
                    highly_recommended = ["reasoning", "confidence_score"]
                    
                    missing_required = [field for field in required_fields if field not in estimate or estimate.get(field, 0) <= 0]
                    missing_recommended = [field for field in highly_recommended if field not in estimate]
                    
                    if missing_required:
                        # CRITICAL: Cannot proceed without costs
                        missing_str = ", ".join(missing_required)
                        self._log_error("AI response validation", f"Missing CRITICAL fields: {missing_str} | Full response: {estimate}")
                        print(f"⚠️ AI response missing CRITICAL fields: {missing_str}")
                        
                        # If this is not the last retry, try again
                        if retry_count < max_retries:
                            retry_count += 1
                            print(f"Retrying ({retry_count}/{max_retries})...")
                            continue
                        
                        # On last retry, DO NOT return incomplete estimate - use fallback instead
                        print(f"❌ All retries exhausted, AI failed to provide costs. Using fallback estimate.")
                        return self._generate_fallback_estimate(issue)
                    
                    if missing_recommended:
                        # WARNING: Missing recommended fields
                        missing_str = ", ".join(missing_recommended)
                        self._log_error("AI response warning", f"Missing recommended fields: {missing_str}")
                        print(f"⚠️ AI response missing recommended fields: {missing_str} (proceeding anyway)")
                        
                        # Set defaults for missing recommended fields
                        if "reasoning" not in estimate:
                            estimate["reasoning"] = "AI did not provide detailed reasoning"
                        if "confidence_score" not in estimate:
                            estimate["confidence_score"] = 50  # Default to medium confidence
                    
                    # Success!
                    return estimate
                    
                except json.JSONDecodeError as e:
                    # JSON parsing failed
                    error_msg = f"JSON parsing failed: {str(e)}"
                    raw_text = getattr(response, 'text', '<no text>')
                    
                    self._log_error("AI response parsing error", 
                                   f"{error_msg} | Raw: {raw_text[:200]}")
                    
                    # Save problematic response for debugging
                    try:
                        debug_dir = Path("estimation_errors")
                        debug_dir.mkdir(exist_ok=True)
                        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
                        issue_id = issue.get('id', 'unknown') if isinstance(issue, dict) else 'unknown'
                        (debug_dir / f"failed_response_{issue_id}_{ts}.txt").write_text(raw_text)
                    except Exception:
                        pass
                    
                    print(f"✗ {error_msg[:100]}")
                    
                    # If this is not the last retry, try again with higher temperature
                    if retry_count < max_retries:
                        retry_count += 1
                        print(f"Retrying with higher temperature ({retry_count}/{max_retries})...")
                        continue
                    
                    # On last retry, fall back to rule-based estimate
                    return self._generate_fallback_estimate(issue)
            
            except Exception as e:
                error_msg = str(e)
                
                # Handle rate limiting
                if "429" in error_msg or "quota" in error_msg.lower() or "rate" in error_msg.lower():
                    # Extract suggested wait time
                    retry_delay = 60  # Default: wait 60 seconds
                    if "retry in" in error_msg.lower():
                        import re
                        match = re.search(r'retry in ([\d.]+)s', error_msg.lower())
                        if match:
                            retry_delay = float(match.group(1)) + 5  # Add 5s buffer
                    
                    self._log_error("AI rate limiting", f"Rate limited: {error_msg}")
                    print(f"⏳ Rate limited, waiting {retry_delay:.0f}s...", end="", flush=True)
                    time.sleep(retry_delay)
                    
                    # Don't increment retry count for rate limiting
                    continue
                
                # Handle authentication errors
                elif "403" in error_msg or "authentication" in error_msg.lower() or "unauthorized" in error_msg.lower():
                    self._log_error("AI authentication error", f"Auth failed: {error_msg}")
                    print(f"❌ Authentication error: {error_msg[:100]}")
                    print("  • Check that your API key is correct")
                    print("  • Run: python test_api_connection.py for diagnostics")
                    
                    # Authentication errors won't be fixed by retrying
                    return self._generate_fallback_estimate(issue)
                
                # Other errors
                else:
                    self._log_error("AI estimation error", error_msg)
                    print(f"❌ AI estimation error: {error_msg[:100]}")
                    
                    # If this is not the last retry, try again
                    if retry_count < max_retries:
                        retry_count += 1
                        print(f"Retrying ({retry_count}/{max_retries})...")
                        continue
                    
                    # On last retry, fall back to rule-based estimate
                    return self._generate_fallback_estimate(issue)
            
            # If we get here, we've exhausted all retries
            retry_count += 1
        
        # If all retries failed, return fallback estimate
        print("⚠️ All AI estimation attempts failed, using fallback estimate")
        return self._generate_fallback_estimate(issue)
    
    def _log_error(self, error_type: str, error_message: str):
        """Log errors to file for debugging."""
        try:
            log_file = Path("estimation_errors.log")
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(log_file, 'a') as f:
                f.write(f"[{timestamp}] {error_type}: {error_message}\n")
        except Exception:
            # Don't fail if logging fails
            pass
            
    def _verify_api_connection(self):
        """Verify API connection with a simple test request."""
        if not self.client:
            return False
            
        try:
            # Simple test prompt that should return valid JSON
            test_prompt = "Return only the JSON: {\"status\": \"success\"}"
            response = self.client.generate_content(
                test_prompt,
                generation_config={
                    "temperature": 0.1,
                    "response_mime_type": "application/json"
                }
            )
            
            # Try to parse the response
            try:
                result = json.loads(response.text)
                if isinstance(result, dict) and result.get("status") == "success":
                    print("✅ API connection verified successfully")
                    return True
                else:
                    print(f"⚠️ API connection test: unexpected response format")
                    self._log_error("API verification", f"Unexpected response format: {response.text[:100]}")
                    return False
            except json.JSONDecodeError:
                print(f"⚠️ API connection test: invalid JSON response")
                self._log_error("API verification", f"Invalid JSON response: {response.text[:100]}")
                return False
                
        except Exception as e:
            error_msg = str(e)
            print(f"❌ API connection test failed: {error_msg}")
            self._log_error("API verification failed", error_msg)
            
            # Provide helpful diagnostics based on error
            if "429" in error_msg or "quota" in error_msg.lower():
                print("  • Rate limiting or quota issue detected")
                print("  • Free tier limits: 5 req/min, 100 req/day for gemini-2.5-flash")
            elif "403" in error_msg or "authentication" in error_msg.lower():
                print("  • Authentication failure detected")
                print("  • Check that your API key is correct")
            
            return False
    
    def _combine_estimates(
        self,
        database_estimate: Dict[str, Any],
        ai_estimate: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Combine database and AI estimates (hybrid approach)."""
        # Weight toward database if it has high confidence
        db_confidence = database_estimate.get("confidence", 0.8)
        
        if db_confidence > 0.85:
            weight_db = 0.7
        elif db_confidence > 0.7:
            weight_db = 0.6
        else:
            weight_db = 0.5
        
        weight_ai = 1.0 - weight_db
        
        # Combine cost estimates
        combined_low = (
            database_estimate.get("estimated_low", 0) * weight_db +
            ai_estimate.get("estimated_low", 0) * weight_ai
        )
        
        combined_high = (
            database_estimate.get("estimated_high", 0) * weight_db +
            ai_estimate.get("estimated_high", 0) * weight_ai
        )
        
        # Combine confidence
        db_conf = database_estimate.get("confidence_score", 80)
        ai_conf = ai_estimate.get("confidence_score", 70)
        combined_conf = int(db_conf * weight_db + ai_conf * weight_ai)
        
        # Take best parts from both
        combined = {
            "item": ai_estimate.get("item", database_estimate.get("item", "")),
            "issue_description": ai_estimate.get("issue_description", ""),
            "severity": ai_estimate.get("severity", "Unknown"),
            "suggested_action": ai_estimate.get("suggested_action", ""),
            "estimated_low": round(combined_low, 2),
            "estimated_high": round(combined_high, 2),
            "confidence_score": combined_conf,
            "reasoning": f"Hybrid estimate combining Houston cost database ({weight_db*100:.0f}% weight) and AI analysis ({weight_ai*100:.0f}% weight). Database: {database_estimate.get('reasoning', '')} AI: {ai_estimate.get('reasoning', '')}",
            "assumptions": list(set(
                database_estimate.get("assumptions", []) +
                ai_estimate.get("assumptions", [])
            )),
            "risk_factors": list(set(
                database_estimate.get("risk_factors", []) +
                ai_estimate.get("risk_factors", [])
            )),
            "confidence": database_estimate.get("confidence", 0.8)  # For database match score
        }
        
        return combined
    
    def _find_related_issues(
        self,
        issue: Dict[str, Any],
        all_issues: List[Dict[str, Any]],
        max_related: int = 3
    ) -> List[Dict[str, Any]]:
        """Find related issues for context."""
        if not isinstance(issue, dict):
            return []
        
        category = issue.get("category", "")
        related = []
        
        for other in all_issues:
            # Skip if not a dict
            if not isinstance(other, dict):
                continue
                
            if other == issue:
                continue
            
            if other.get("category", "") == category:
                related.append(other)
                if len(related) >= max_related:
                    break
        
        return related
    
    def _extract_category_from_section(self, section: str) -> str:
        """Extract a coarse category from the inspection report section string."""
        s = (section or '').lower()
        if 'roof' in s or 'structural' in s:
            return 'Roofing' if 'roof' in s else 'Structural'
        if 'electrical' in s:
            return 'Electrical'
        if 'hvac' in s or 'heating' in s or 'cooling' in s:
            return 'HVAC'
        if 'plumbing' in s:
            return 'Plumbing'
        if 'grounds' in s or 'exterior' in s:
            return 'Grounds/Exterior'
        if 'foundation' in s:
            return 'Foundation'
        return 'General'
    
    def _validate_classification(self, issue: Dict[str, Any]) -> None:
        """Align enrichment classification with original section heuristics."""
        try:
            section = (issue.get('section') or '').lower()
            em = issue.setdefault('enrichment_metadata', {})
            tax = em.setdefault('component_taxonomy', {})
            enriched_cat = (tax.get('category') or '').lower()
            # Roof
            if 'roof' in section and enriched_cat not in ['roofing', 'structural']:
                tax['category'] = 'Roofing'
                tax['confidence'] = 0.95
            # HVAC
            if ('hvac' in section or 'heating' in section or 'cooling' in section) and enriched_cat not in ['hvac', 'heating', 'cooling']:
                tax['category'] = 'HVAC'
                tax['confidence'] = 0.95
        except Exception:
            pass
    
    def _get_property_age(self, metadata: Dict[str, Any]) -> Optional[int]:
        """Get property age in years."""
        year_built = metadata.get("year_built")
        
        if isinstance(year_built, str):
            try:
                year_built = int(year_built)
            except ValueError:
                return None
        
        if year_built and isinstance(year_built, int) and year_built > 1800:
            return datetime.now().year - year_built
        
        return None
    
    def _estimate_size_from_issues(self, issues: List[Dict[str, Any]]) -> str:
        """Heuristic property size estimate derived from issue count."""
        try:
            count = len([i for i in issues if isinstance(i, dict)])
        except Exception:
            count = 0
        if count < 10:
            return "1,500 sq ft (small home)"
        elif count < 20:
            return "2,000 sq ft (medium home)"
        return "2,500+ sq ft (large home)"
    
    def _clean_description_for_ai(self, issue: Dict[str, Any]) -> Dict[str, Any]:
        """Remove boilerplate/legal text from description to reduce noise for AI."""
        import re as _re
        cleaned_issue = dict(issue) if isinstance(issue, dict) else {}
        desc = (cleaned_issue.get('description') or cleaned_issue.get('issue') or '')
        patterns = [
            r'Page \d+ of \d+',
            r'REI \d+-\d+ \(\d+/\d+/\d+\)',
            r'Promulgated by the Texas Real Estate Commission',
            r'www\.trec\.texas\.gov',
            r'Report Identification: \S+',
            r'I=Inspected NI=Not Inspected NP=Not Present D=Deficient',
            r'\(512\) \d+-\d+',
        ]
        for pat in patterns:
            desc = _re.sub(pat, '', desc, flags=_re.IGNORECASE)
        desc = ' '.join(desc.split())
        cleaned_issue['description'] = desc
        return cleaned_issue
    
    def _generate_fallback_estimate(self, issue: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Basic rule-based estimate when DB/AI unavailable."""
        try:
            category_src = (issue.get('standard_category') or issue.get('section') or issue.get('category') or '').lower()
            severity = (issue.get('severity') or issue.get('standard_severity') or 'medium').lower()
            title = issue.get('title') or issue.get('item') or 'Unknown issue'
            description = issue.get('description') or issue.get('issue') or ''
        except Exception:
            return None
        CATEGORY_RANGES = {
            'roof': (500, 15000), 'roofing': (500, 15000),
            'hvac': (300, 8000),
            'plumbing': (200, 5000),
            'electrical': (150, 3000),
            'foundation': (1000, 25000),
            'structural': (500, 10000),
        }
        base_low, base_high = (500, 3000)
        for key, rng in CATEGORY_RANGES.items():
            if key in category_src:
                base_low, base_high = rng
                break
        SEVERITY_MULT = {
            'critical': 1.5,
            'high': 1.2,
            'medium': 1.0,
            'low': 0.6,
        }
        mult = SEVERITY_MULT.get(severity, 1.0)
        est_low = int(base_low * mult)
        est_high = int(base_high * mult)
        return {
            "item": title,
            "issue_description": description[:200],
            "severity": severity.capitalize(),
            "suggested_action": "Professional evaluation recommended",
            "estimated_low": est_low,
            "estimated_high": est_high,
            "confidence_score": 40,
            "reasoning": f"Rule-based fallback for {category_src} issue with {severity} severity. Houston market heuristics.",
            "assumptions": [
                "Standard difficulty and access",
                "No hidden damage or complications",
                "Based on typical Houston labor and material costs",
            ],
            "risk_factors": [
                "Unknown scope without on-site inspection",
                "Hidden damage may increase costs",
            ],
        }
    
    def _save_results(
        self,
        results: List[Dict[str, Any]],
        output_path: str,
        metadata: Dict[str, Any],
        relationships: Optional[Dict[str, Any]]
    ):
        """Save enhanced results to JSON."""
        output_data = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "model": self.model,
                "temperature": self.temperature,
                "pipeline_version": "enhanced_v1.0",
                "features_enabled": {
                    "database_lookup": self.enable_database_lookup,
                    "relationship_analysis": self.enable_relationship_analysis,
                    "specialist_prompts": self.enable_specialist_prompts
                },
                "property_data": metadata
            },
            "summary": {
                **self.stats,
                "total_estimated_low": sum(r.get("estimated_low", 0) for r in results),
                "total_estimated_high": sum(r.get("estimated_high", 0) for r in results),
                "average_confidence": sum(
                    r.get("confidence", {}).get("overall", 0) for r in results
                ) / len(results) if results else 0
            },
            "relationships": relationships,
            "cost_estimates": results
        }
        
        # Ensure output directory exists
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        print(f"\n✓ Results saved to: {output_path}")
    
    def _print_summary(self):
        """Print pipeline summary."""
        print("\n" + "="*70)
        print("ENHANCED COST ESTIMATION SUMMARY")
        print("="*70)
        print(f"Total issues:           {self.stats['total_issues']}")
        print(f"Data quality excluded:  {self.stats['data_quality_excluded']}")
        print(f"Data quality flagged:   {self.stats['data_quality_flagged']}")
        print(f"Database matches:       {self.stats['database_matches']}")
        print(f"AI estimates:           {self.stats['ai_estimates']}")
        print(f"Hybrid estimates:       {self.stats['hybrid_estimates']}")
        print(f"High confidence (85+):  {self.stats['high_confidence']}")
        print(f"Needs manual review:    {self.stats['needs_review']}")
        print(f"Auto-corrected:         {self.stats['estimation_auto_corrected']}")
        print(f"Validation failed:      {self.stats['estimation_validation_failed']}")
        print(f"Bundles identified:     {self.stats['bundles_identified']}")
        print("="*70)
        
        # Data quality summary
        if self.data_quality_validator:
            dq_stats = self.data_quality_validator.get_stats_summary()
            print("\nDATA QUALITY DETAILS:")
            print(f"  Pass rate: {dq_stats['pass_rate']:.1f}%")
            if dq_stats['failure_reasons']:
                print("  Top exclusion reasons:")
                for reason, count in sorted(dq_stats['failure_reasons'].items(), key=lambda x: x[1], reverse=True)[:3]:
                    print(f"    - {reason}: {count}")
        
        # Estimation validation summary
        if self.estimation_validator:
            ev_stats = self.estimation_validator.get_stats_summary()
            print("\nESTIMATION VALIDATION DETAILS:")
            print(f"  Pass rate: {ev_stats['pass_rate']:.1f}%")
            print(f"  Auto-corrected: {ev_stats['auto_corrected']}")
            if ev_stats['error_types']:
                print("  Top error types:")
                for error_type, count in sorted(ev_stats['error_types'].items(), key=lambda x: x[1], reverse=True)[:3]:
                    print(f"    - {error_type}: {count}")
        
        print("="*70)


def main():
    """Command-line interface."""
    parser = argparse.ArgumentParser(
        description="Enhanced cost estimation with Phase 1 improvements"
    )
    
    parser.add_argument(
        "--input", "-i",
        required=True,
        help="Path to enriched JSON data"
    )
    
    parser.add_argument(
        "--output", "-o",
        help="Output path (auto-generated if not specified)"
    )
    
    parser.add_argument(
        "--model", "-m",
        default="gemini-2.5-flash",
        help="AI model to use (default: gemini-2.5-flash for best reasoning. Free tier: 5 req/min, 100 req/day)"
    )
    
    parser.add_argument(
        "--api-key",
        help="API key (or set GEMINI_API_KEY env var)"
    )
    
    parser.add_argument(
        "--temperature", "-t",
        type=float,
        default=0.3,
        help="AI temperature"
    )
    
    parser.add_argument(
        "--no-database",
        action="store_true",
        help="Disable database lookup"
    )
    
    parser.add_argument(
        "--no-relationships",
        action="store_true",
        help="Disable relationship analysis"
    )
    
    parser.add_argument(
        "--no-specialist-prompts",
        action="store_true",
        help="Disable specialist prompts"
    )
    
    args = parser.parse_args()
    
    # Initialize pipeline
    estimator = EnhancedCostEstimator(
        model=args.model,
        api_key=args.api_key,
        temperature=args.temperature,
        enable_database_lookup=not args.no_database,
        enable_relationship_analysis=not args.no_relationships,
        enable_specialist_prompts=not args.no_specialist_prompts
    )
    
    # Process report
    try:
        result = estimator.estimate_report(
            enriched_data_path=args.input,
            output_path=args.output
        )
        
        print(f"\n✓ Successfully generated enhanced cost estimates!")
        return 0
    
    except Exception as e:
        print(f"\n✗ Pipeline failed: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

