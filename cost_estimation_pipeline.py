"""
Cost Estimation Pipeline

Complete pipeline for generating AI-powered cost estimates from enriched inspection data.

This pipeline:
1. Loads enriched inspection data
2. Builds optimized prompts with Houston market context
3. Calls AI API (Gemini 2.5 Flash) for cost estimation
4. Validates and cleans AI responses
5. Tracks prompt versions and performance
6. Saves cost estimates to JSON

Usage:
    python cost_estimation_pipeline.py --input enriched_data/6-report_enriched.json --output cost_estimates/6-report_costs.json
    
    # Or with batching:
    python cost_estimation_pipeline.py --input enriched_data/6-report_enriched.json --batch-size 10
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import time

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from prompting.prompt_builder import EstimationPromptBuilder
from prompting.context_manager import ContextManager
from prompting.output_validator import OutputValidator
from prompting.version_control import PromptVersionControl

# AI API imports
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("Warning: google-generativeai not installed. Install with: pip install google-generativeai")

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class CostEstimationPipeline:
    """
    Complete pipeline for AI-powered cost estimation.
    
    Features:
    - Flexible AI model support (Gemini, OpenAI)
    - Automatic batching and token management
    - Response validation and quality control
    - Prompt version tracking
    - Progress tracking and error recovery
    """
    
    def __init__(
        self,
        model: str = "gemini-2.5-flash",
        api_key: Optional[str] = None,
        temperature: float = 0.3,
        batch_size: int = 1,
        prompt_version: str = "v1.0",
        enable_logging: bool = True,
        output_dir: str = "cost_estimates"
    ):
        """
        Initialize cost estimation pipeline.
        
        Args:
            model: AI model to use ("gemini-2.5-flash", "gemini-pro", "gpt-4-turbo")
            api_key: API key (or set GEMINI_API_KEY or OPENAI_API_KEY env var)
            temperature: AI temperature (0.2-0.4 recommended for consistent estimates)
            batch_size: Issues per API call (1=individual, 10=batch)
            prompt_version: Version ID for tracking
            enable_logging: Enable prompt/response logging
            output_dir: Directory for cost estimate outputs
        """
        self.model = model
        self.temperature = temperature
        self.batch_size = batch_size
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.prompt_builder = EstimationPromptBuilder(
            version=prompt_version,
            include_examples=True,
            temperature=temperature
        )
        
        self.context_manager = ContextManager(
            max_tokens=100000,  # Conservative limit
            target_tokens=80000
        )
        
        self.validator = OutputValidator(
            min_cost=0,
            max_cost=50000,
            manual_review_threshold=60
        )
        
        self.version_control = PromptVersionControl(
            version_id=prompt_version,
            log_dir="prompt_logs",
            enable_logging=enable_logging
        )
        
        # Initialize AI client
        self.client = self._initialize_client(api_key)
        
        # Statistics
        self.stats = {
            "total_issues": 0,
            "estimated_issues": 0,
            "failed_issues": 0,
            "validation_passed": 0,
            "validation_failed": 0,
            "flagged_for_review": 0,
            "total_api_calls": 0,
            "total_cost_usd": 0.0,
            "start_time": None,
            "end_time": None
        }
    
    def _initialize_client(self, api_key: Optional[str]):
        """Initialize AI API client."""
        if self.model.startswith("gemini"):
            if not GEMINI_AVAILABLE:
                raise ImportError("google-generativeai not installed")
            
            api_key = api_key or os.environ.get("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY not set. Set environment variable or pass api_key parameter")
            
            genai.configure(api_key=api_key)
            return genai.GenerativeModel(self.model)
        
        elif self.model.startswith("gpt"):
            if not OPENAI_AVAILABLE:
                raise ImportError("openai not installed")
            
            api_key = api_key or os.environ.get("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not set")
            
            return OpenAI(api_key=api_key)
        
        else:
            raise ValueError(f"Unsupported model: {self.model}")
    
    def process_report(
        self,
        enriched_data_path: str,
        output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a full inspection report and generate cost estimates.
        
        Args:
            enriched_data_path: Path to enriched JSON data
            output_path: Path for output (auto-generated if None)
        
        Returns:
            Dict with results and statistics
        """
        self.stats["start_time"] = datetime.now()
        
        print(f"Loading enriched data from: {enriched_data_path}")
        with open(enriched_data_path, 'r') as f:
            enriched_data = json.load(f)
        
        # Extract property metadata and issues
        property_data = self._extract_property_metadata(enriched_data)
        issues = self._extract_issues(enriched_data)
        
        self.stats["total_issues"] = len(issues)
        print(f"Found {len(issues)} issues to estimate")
        
        # Prioritize issues
        print("Prioritizing issues by severity and complexity...")
        prioritized_issues = self.context_manager.prioritize_issues(issues)
        
        # Estimate API cost
        cost_estimate = self.context_manager.estimate_report_cost(
            issue_count=len(issues),
            batch_size=self.batch_size,
            model=self.model
        )
        print(f"Estimated API cost: ${cost_estimate['estimated_cost_usd']:.2f} "
              f"({cost_estimate['api_calls']} API calls)")
        
        # Process issues
        if self.batch_size == 1:
            results = self._process_individual(prioritized_issues, property_data)
        else:
            results = self._process_batched(prioritized_issues, property_data)
        
        # Generate output
        if output_path is None:
            report_name = Path(enriched_data_path).stem.replace('_enriched', '')
            output_path = self.output_dir / f"{report_name}_cost_estimates.json"
        
        self._save_results(results, output_path, property_data)
        
        self.stats["end_time"] = datetime.now()
        duration = (self.stats["end_time"] - self.stats["start_time"]).total_seconds()
        
        # Print summary
        self._print_summary(duration)
        
        return {
            "output_file": str(output_path),
            "statistics": self.stats,
            "results": results
        }
    
    def _extract_property_metadata(self, enriched_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract property metadata from enriched data."""
        metadata = enriched_data.get("metadata", {})
        
        # Count issues by severity
        issues = enriched_data.get("issues", [])
        issue_counts = {
            "total": len(issues),
            "critical": sum(1 for i in issues if i.get("severity", "").lower() == "critical"),
            "high": sum(1 for i in issues if i.get("severity", "").lower() == "high"),
            "medium": sum(1 for i in issues if i.get("severity", "").lower() == "medium"),
            "low": sum(1 for i in issues if i.get("severity", "").lower() == "low")
        }
        
        return {
            "year_built": metadata.get("year_built", metadata.get("property_year", 2000)),
            "type": metadata.get("property_type", "Single-family home"),
            "square_footage": metadata.get("square_footage", "Unknown"),
            "location": metadata.get("location", "Houston, TX"),
            "inspection_date": metadata.get("inspection_date", datetime.now().strftime("%B %Y")),
            "issue_counts": issue_counts
        }
    
    def _extract_issues(self, enriched_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract issues from enriched data."""
        return enriched_data.get("issues", [])
    
    def _process_individual(
        self,
        issues: List[Dict[str, Any]],
        property_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Process issues individually (one API call per issue)."""
        results = []
        
        print(f"\nProcessing {len(issues)} issues individually...")
        
        for idx, issue in enumerate(issues, 1):
            print(f"[{idx}/{len(issues)}] Estimating: {issue.get('item', 'Unknown')}", end=" ... ")
            
            try:
                # Build prompt
                messages = self.prompt_builder.build_single_issue_prompt(
                    issue=issue,
                    property_data=property_data,
                    related_issues=self._find_related_issues(issue, issues)
                )
                
                # Check token budget
                if not self.context_manager.fits_in_budget(messages):
                    print("SKIP (too large)")
                    self.stats["failed_issues"] += 1
                    continue
                
                # Call AI API
                response = self._call_api(messages)
                self.stats["total_api_calls"] += 1
                
                # Parse response
                estimate = self._parse_response(response)
                
                if estimate:
                    # Validate
                    validation = self.validator.validate_estimate(estimate, strict=False)
                    
                    # Log interaction
                    issue_id = f"{issue.get('category', 'Unknown')}_{issue.get('item', 'Unknown')}_{idx}"
                    self.version_control.log_interaction(
                        prompt=messages,
                        response=estimate,
                        issue_id=issue_id,
                        metadata={"model": self.model, "temperature": self.temperature},
                        validation_result=validation
                    )
                    
                    # Add to results
                    result = {
                        **estimate,
                        "original_issue": issue,
                        "validation": {
                            "valid": validation["valid"],
                            "needs_review": validation["needs_review"],
                            "quality_score": validation["quality_score"]
                        }
                    }
                    results.append(result)
                    
                    self.stats["estimated_issues"] += 1
                    if validation["valid"]:
                        self.stats["validation_passed"] += 1
                    else:
                        self.stats["validation_failed"] += 1
                    if validation["needs_review"]:
                        self.stats["flagged_for_review"] += 1
                    
                    print(f"✓ ${estimate.get('estimated_low', 0):.0f}-${estimate.get('estimated_high', 0):.0f} (confidence: {estimate.get('confidence_score', 0)})")
                else:
                    print("✗ Failed to parse response")
                    self.stats["failed_issues"] += 1
                
                # Rate limiting
                time.sleep(0.5)
                
            except Exception as e:
                print(f"✗ Error: {str(e)}")
                self.stats["failed_issues"] += 1
                continue
        
        return results
    
    def _process_batched(
        self,
        issues: List[Dict[str, Any]],
        property_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Process issues in batches (multiple issues per API call)."""
        results = []
        
        # Create batches
        batches = self.context_manager.create_batches(
            issues,
            batch_size=self.batch_size,
            group_by_category=True
        )
        
        print(f"\nProcessing {len(issues)} issues in {len(batches)} batches...")
        
        for batch_idx, batch in enumerate(batches, 1):
            print(f"[Batch {batch_idx}/{len(batches)}] Processing {len(batch)} issues", end=" ... ")
            
            try:
                # Build batch prompt
                messages = self.prompt_builder.build_batch_prompt(
                    issues=batch,
                    property_data=property_data
                )
                
                # Check token budget
                if not self.context_manager.fits_in_budget(messages):
                    print("SKIP (too large)")
                    self.stats["failed_issues"] += len(batch)
                    continue
                
                # Call AI API
                response = self._call_api(messages)
                self.stats["total_api_calls"] += 1
                
                # Parse batch response
                estimates = self._parse_batch_response(response, len(batch))
                
                if estimates and len(estimates) == len(batch):
                    # Validate all estimates
                    validations = []
                    for estimate in estimates:
                        validation = self.validator.validate_estimate(estimate, strict=False)
                        validations.append(validation)
                    
                    # Log batch interaction
                    issue_ids = [
                        f"{issue.get('category', 'Unknown')}_{issue.get('item', 'Unknown')}_{i}"
                        for i, issue in enumerate(batch)
                    ]
                    self.version_control.log_batch_interaction(
                        prompt=messages,
                        responses=estimates,
                        issue_ids=issue_ids,
                        metadata={"model": self.model, "temperature": self.temperature},
                        validation_results=validations
                    )
                    
                    # Add to results
                    for estimate, issue, validation in zip(estimates, batch, validations):
                        result = {
                            **estimate,
                            "original_issue": issue,
                            "validation": {
                                "valid": validation["valid"],
                                "needs_review": validation["needs_review"],
                                "quality_score": validation["quality_score"]
                            }
                        }
                        results.append(result)
                        
                        self.stats["estimated_issues"] += 1
                        if validation["valid"]:
                            self.stats["validation_passed"] += 1
                        else:
                            self.stats["validation_failed"] += 1
                        if validation["needs_review"]:
                            self.stats["flagged_for_review"] += 1
                    
                    print(f"✓ Completed {len(estimates)} estimates")
                else:
                    print(f"✗ Expected {len(batch)} estimates, got {len(estimates) if estimates else 0}")
                    self.stats["failed_issues"] += len(batch)
                
                # Rate limiting
                time.sleep(1.0)
                
            except Exception as e:
                print(f"✗ Error: {str(e)}")
                self.stats["failed_issues"] += len(batch)
                continue
        
        return results
    
    def _call_api(self, messages: List[Dict[str, str]]) -> str:
        """Call AI API with prompt messages."""
        if self.model.startswith("gemini"):
            # Combine system and user messages for Gemini
            full_prompt = ""
            for msg in messages:
                full_prompt += msg["content"] + "\n\n"
            
            response = self.client.generate_content(
                full_prompt,
                generation_config={
                    "temperature": self.temperature,
                    "response_mime_type": "application/json"
                }
            )
            
            return response.text
        
        elif self.model.startswith("gpt"):
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=self.temperature
            )
            
            return response.choices[0].message.content
        
        else:
            raise ValueError(f"Unsupported model: {self.model}")
    
    def _parse_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Parse AI response into estimate dict."""
        try:
            # Try direct JSON parse
            estimate = json.loads(response)
            return estimate
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks
            import re
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(1))
                except json.JSONDecodeError:
                    pass
            
            # Try to find any JSON object
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(0))
                except json.JSONDecodeError:
                    pass
            
            return None
    
    def _parse_batch_response(
        self,
        response: str,
        expected_count: int
    ) -> Optional[List[Dict[str, Any]]]:
        """Parse batch response into list of estimates."""
        try:
            # Try direct JSON parse
            data = json.loads(response)
            
            # Handle both array and object with array
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and "estimates" in data:
                return data["estimates"]
            elif isinstance(data, dict) and len(data) == 1:
                # Single key might be the array
                key = list(data.keys())[0]
                if isinstance(data[key], list):
                    return data[key]
            
            return None
        except json.JSONDecodeError:
            return None
    
    def _find_related_issues(
        self,
        issue: Dict[str, Any],
        all_issues: List[Dict[str, Any]],
        max_related: int = 3
    ) -> List[Dict[str, Any]]:
        """Find related issues for context."""
        category = issue.get("category", "")
        related = []
        
        for other in all_issues:
            if other == issue:
                continue
            
            # Same category
            if other.get("category", "") == category:
                related.append(other)
                if len(related) >= max_related:
                    break
        
        return related
    
    def _save_results(
        self,
        results: List[Dict[str, Any]],
        output_path: Path,
        property_data: Dict[str, Any]
    ):
        """Save cost estimates to JSON file."""
        output = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "model": self.model,
                "temperature": self.temperature,
                "prompt_version": self.prompt_builder.version,
                "property_data": property_data
            },
            "summary": {
                "total_issues": self.stats["total_issues"],
                "estimated_issues": self.stats["estimated_issues"],
                "failed_issues": self.stats["failed_issues"],
                "validation_passed": self.stats["validation_passed"],
                "flagged_for_review": self.stats["flagged_for_review"],
                "total_estimated_low": sum(r.get("estimated_low", 0) for r in results),
                "total_estimated_high": sum(r.get("estimated_high", 0) for r in results)
            },
            "cost_estimates": results
        }
        
        with open(output_path, 'w') as f:
            json.dump(output, f, indent=2)
        
        print(f"\nResults saved to: {output_path}")
    
    def _print_summary(self, duration: float):
        """Print pipeline summary statistics."""
        print("\n" + "="*70)
        print("COST ESTIMATION PIPELINE SUMMARY")
        print("="*70)
        print(f"Total issues:           {self.stats['total_issues']}")
        print(f"Successfully estimated: {self.stats['estimated_issues']}")
        print(f"Failed:                 {self.stats['failed_issues']}")
        print(f"Validation passed:      {self.stats['validation_passed']}")
        print(f"Validation failed:      {self.stats['validation_failed']}")
        print(f"Flagged for review:     {self.stats['flagged_for_review']}")
        print(f"Total API calls:        {self.stats['total_api_calls']}")
        print(f"Processing time:        {duration:.1f} seconds")
        print("="*70)


def main():
    """Command-line interface for cost estimation pipeline."""
    parser = argparse.ArgumentParser(
        description="Generate AI-powered cost estimates from enriched inspection data"
    )
    
    parser.add_argument(
        "--input",
        "-i",
        required=True,
        help="Path to enriched JSON data"
    )
    
    parser.add_argument(
        "--output",
        "-o",
        help="Path for output JSON (auto-generated if not specified)"
    )
    
    parser.add_argument(
        "--model",
        "-m",
        default="gemini-2.5-flash",
        choices=["gemini-2.5-flash", "gemini-pro", "gpt-4-turbo", "gpt-4"],
        help="AI model to use"
    )
    
    parser.add_argument(
        "--api-key",
        help="API key (or set GEMINI_API_KEY/OPENAI_API_KEY env var)"
    )
    
    parser.add_argument(
        "--temperature",
        "-t",
        type=float,
        default=0.3,
        help="AI temperature (0.2-0.4 recommended)"
    )
    
    parser.add_argument(
        "--batch-size",
        "-b",
        type=int,
        default=1,
        help="Issues per API call (1=individual, 10=batch)"
    )
    
    parser.add_argument(
        "--version",
        "-v",
        default="v1.0",
        help="Prompt version ID for tracking"
    )
    
    parser.add_argument(
        "--no-logging",
        action="store_true",
        help="Disable prompt/response logging"
    )
    
    parser.add_argument(
        "--output-dir",
        default="cost_estimates",
        help="Directory for output files"
    )
    
    args = parser.parse_args()
    
    # Initialize pipeline
    pipeline = CostEstimationPipeline(
        model=args.model,
        api_key=args.api_key,
        temperature=args.temperature,
        batch_size=args.batch_size,
        prompt_version=args.version,
        enable_logging=not args.no_logging,
        output_dir=args.output_dir
    )
    
    # Process report
    try:
        result = pipeline.process_report(
            enriched_data_path=args.input,
            output_path=args.output
        )
        
        print(f"\n✓ Successfully generated cost estimates!")
        print(f"Output file: {result['output_file']}")
        
        return 0
    
    except Exception as e:
        print(f"\n✗ Pipeline failed: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

