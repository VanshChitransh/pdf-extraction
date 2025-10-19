"""
Main cost estimation engine.
Orchestrates the estimation process from data loading to result generation.
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from src.models import (
    InspectionIssue, RepairEstimate, CostBreakdown,
    EstimationResult, StructuredReport
)
from src.ai_estimator import GeminiEstimator
from src.data_preparer import DataPreparer
from src.chunk_manager import ChunkManager
from src.prompts import (
    SYSTEM_PROMPT, create_estimation_prompt,
    create_batch_estimation_prompt, HOUSTON_CONSIDERATIONS_PROMPT
)

logger = logging.getLogger(__name__)


class CostEstimationEngine:
    """Main engine for cost estimation."""
    
    def __init__(
        self,
        api_key: str,
        location: str = "Houston, TX",
        use_batch: bool = True,
        max_workers: int = 3
    ):
        """
        Initialize cost estimation engine.
        
        Args:
            api_key: Gemini API key
            location: Property location for context
            use_batch: Whether to use batch processing
            max_workers: Max concurrent API calls
        """
        self.location = location
        self.use_batch = use_batch
        self.max_workers = max_workers
        
        # Initialize components
        self.ai_estimator = GeminiEstimator(api_key=api_key)
        self.data_preparer = DataPreparer(location=location)
        self.chunk_manager = ChunkManager()
        
        logger.info(f"Initialized CostEstimationEngine for {location}")
        logger.info(f"Batch processing: {use_batch}, Max workers: {max_workers}")
    
    def estimate_report(
        self,
        report: StructuredReport,
        progress_callback: Optional[callable] = None
    ) -> EstimationResult:
        """
        Generate cost estimates for entire report.
        
        Args:
            report: StructuredReport object
            progress_callback: Optional callback(current, total, message)
            
        Returns:
            EstimationResult with all estimates
        """
        logger.info("Starting cost estimation for report")
        
        # Get deficient issues
        deficient_issues = self.data_preparer.filter_deficient_issues(report)
        
        if not deficient_issues:
            logger.warning("No deficient issues found in report")
            return self._create_empty_result(report)
        
        logger.info(f"Found {len(deficient_issues)} deficient issues to estimate")
        
        # Get property context
        property_context = self.data_preparer.get_property_context(report)
        
        # Generate estimates
        if self.use_batch:
            estimates = self._estimate_batch(
                deficient_issues,
                property_context,
                progress_callback
            )
        else:
            estimates = self._estimate_sequential(
                deficient_issues,
                property_context,
                progress_callback
            )
        
        logger.info(f"Generated {len(estimates)} estimates")
        
        # Get Houston considerations
        houston_considerations = self._get_houston_considerations(report)
        
        # Aggregate results
        result = self._aggregate_results(
            report=report,
            estimates=estimates,
            houston_considerations=houston_considerations
        )
        
        logger.info(f"Estimation complete: ${result.total_cost_min:.0f} - ${result.total_cost_max:.0f}")
        
        return result
    
    def _estimate_batch(
        self,
        issues: List[InspectionIssue],
        property_context: Dict[str, str],
        progress_callback: Optional[callable] = None
    ) -> List[RepairEstimate]:
        """
        Estimate costs using batch processing.
        
        Args:
            issues: List of issues to estimate
            property_context: Property context info
            progress_callback: Optional progress callback
            
        Returns:
            List of RepairEstimate objects
        """
        # Chunk issues
        chunks = self.chunk_manager.chunk_issues(issues, strategy="section")
        logger.info(f"Split into {len(chunks)} chunks for batch processing")
        
        all_estimates = []
        completed = 0
        total = len(chunks)
        
        # Process chunks in parallel
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all chunks
            future_to_chunk = {
                executor.submit(
                    self._process_chunk,
                    chunk,
                    property_context
                ): i
                for i, chunk in enumerate(chunks)
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_chunk):
                chunk_idx = future_to_chunk[future]
                try:
                    chunk_estimates = future.result()
                    all_estimates.extend(chunk_estimates)
                    completed += 1
                    
                    if progress_callback:
                        progress_callback(
                            completed,
                            total,
                            f"Processed chunk {completed}/{total}"
                        )
                    
                    logger.info(f"Chunk {chunk_idx + 1}/{total} complete: {len(chunk_estimates)} estimates")
                    
                except Exception as e:
                    logger.error(f"Chunk {chunk_idx} failed: {e}")
                    # Continue with other chunks
        
        return all_estimates
    
    def _estimate_sequential(
        self,
        issues: List[InspectionIssue],
        property_context: Dict[str, str],
        progress_callback: Optional[callable] = None
    ) -> List[RepairEstimate]:
        """
        Estimate costs sequentially (one issue at a time).
        
        Args:
            issues: List of issues to estimate
            property_context: Property context info
            progress_callback: Optional progress callback
            
        Returns:
            List of RepairEstimate objects
        """
        estimates = []
        total = len(issues)
        
        for i, issue in enumerate(issues):
            try:
                if progress_callback:
                    progress_callback(i + 1, total, f"Estimating issue {i + 1}/{total}")
                
                estimate = self._estimate_single_issue(issue, property_context)
                estimates.append(estimate)
                
                logger.info(f"Estimated {i + 1}/{total}: {estimate.repair_name}")
                
            except Exception as e:
                logger.error(f"Failed to estimate issue {issue.id}: {e}")
                # Create fallback estimate
                estimates.append(self._create_fallback_estimate(issue))
        
        return estimates
    
    def _process_chunk(
        self,
        chunk: List[InspectionIssue],
        property_context: Dict[str, str]
    ) -> List[RepairEstimate]:
        """
        Process a chunk of issues.
        
        Args:
            chunk: List of issues
            property_context: Property context
            
        Returns:
            List of RepairEstimate objects
        """
        # Prepare issue data
        issues_data = self.data_preparer.prepare_batch_data(
            chunk,
            property_location=property_context['location'],
            inspection_date=property_context['inspection_date']
        )
        
        # Create prompt
        user_prompt = create_batch_estimation_prompt(issues_data)
        
        # Call API
        try:
            results = self.ai_estimator.estimate_batch_issues(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=user_prompt
            )
            
            # Convert to RepairEstimate objects
            estimates = []
            for result in results:
                try:
                    estimate = self._parse_estimate_result(result)
                    estimates.append(estimate)
                except Exception as e:
                    logger.error(f"Failed to parse estimate: {e}")
                    # Use the issue ID from the result or find matching issue
                    issue_id = result.get('issue_id', chunk[len(estimates)].id if len(estimates) < len(chunk) else 'unknown')
                    # Find the corresponding issue
                    issue = next((iss for iss in chunk if iss.id == issue_id), chunk[len(estimates)] if len(estimates) < len(chunk) else None)
                    if issue:
                        estimates.append(self._create_fallback_estimate(issue))
            
            return estimates
            
        except Exception as e:
            logger.error(f"Chunk processing failed: {e}")
            # Return fallback estimates for all issues in chunk
            return [self._create_fallback_estimate(issue) for issue in chunk]
    
    def _estimate_single_issue(
        self,
        issue: InspectionIssue,
        property_context: Dict[str, str]
    ) -> RepairEstimate:
        """
        Estimate cost for a single issue.
        
        Args:
            issue: InspectionIssue object
            property_context: Property context
            
        Returns:
            RepairEstimate object
        """
        # Prepare issue data
        issue_data = self.data_preparer.prepare_issue_data(
            issue,
            property_location=property_context['location'],
            inspection_date=property_context['inspection_date']
        )
        
        # Create prompt
        user_prompt = create_estimation_prompt(issue_data)
        
        # Call API
        result = self.ai_estimator.estimate_single_issue(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt
        )
        
        # Convert to RepairEstimate
        estimate = self._parse_estimate_result(result, issue_id=issue.id)
        
        return estimate
    
    def _parse_estimate_result(
        self,
        result: Dict[str, Any],
        issue_id: Optional[str] = None
    ) -> RepairEstimate:
        """
        Parse API result into RepairEstimate object.
        
        Args:
            result: API response dict
            issue_id: Optional issue ID override
            
        Returns:
            RepairEstimate object
        """
        cost_data = result['cost_breakdown']
        
        cost_breakdown = CostBreakdown(
            labor_min=float(cost_data['labor_min']),
            labor_max=float(cost_data['labor_max']),
            materials_min=float(cost_data['materials_min']),
            materials_max=float(cost_data['materials_max']),
            total_min=float(cost_data['total_min']),
            total_max=float(cost_data['total_max'])
        )
        
        return RepairEstimate(
            issue_id=issue_id or result.get('issue_id', 'unknown'),
            repair_name=result['repair_name'],
            cost_breakdown=cost_breakdown,
            timeline_days_min=int(result['timeline_days_min']),
            timeline_days_max=int(result['timeline_days_max']),
            urgency=result['urgency'],
            contractor_type=result['contractor_type'],
            houston_notes=result['houston_notes'],
            explanation=result['explanation'],
            confidence_score=float(result['confidence_score'])
        )
    
    def _create_fallback_estimate(self, issue: InspectionIssue) -> RepairEstimate:
        """Create fallback estimate when AI fails."""
        return RepairEstimate(
            issue_id=issue.id,
            repair_name=issue.title[:100],
            cost_breakdown=CostBreakdown(
                labor_min=100.0,
                labor_max=500.0,
                materials_min=50.0,
                materials_max=200.0,
                total_min=150.0,
                total_max=700.0
            ),
            timeline_days_min=1,
            timeline_days_max=3,
            urgency=issue.priority,
            contractor_type="Licensed Professional",
            houston_notes="Unable to generate specific estimate. Consult professional.",
            explanation="Automated estimate unavailable. Professional inspection recommended.",
            confidence_score=0.1
        )
    
    def _get_houston_considerations(self, report: StructuredReport) -> List[str]:
        """Get Houston-specific considerations."""
        try:
            result = self.ai_estimator.estimate_single_issue(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=HOUSTON_CONSIDERATIONS_PROMPT
            )
            
            if isinstance(result, list):
                return result
            return []
            
        except Exception as e:
            logger.error(f"Failed to get Houston considerations: {e}")
            return [
                "Houston's high humidity requires attention to moisture issues",
                "AC systems are critical - address HVAC issues promptly",
                "Foundation issues common due to expansive clay soil",
                "Schedule exterior work during October-April for best weather",
                "Hurricane season (June-November) may impact material availability"
            ]
    
    def _aggregate_results(
        self,
        report: StructuredReport,
        estimates: List[RepairEstimate],
        houston_considerations: List[str]
    ) -> EstimationResult:
        """
        Aggregate estimates into final result.
        
        Args:
            report: Original report
            estimates: List of estimates
            houston_considerations: Houston-specific notes
            
        Returns:
            EstimationResult object
        """
        # Calculate totals
        total_min = sum(est.cost_breakdown.total_min for est in estimates)
        total_max = sum(est.cost_breakdown.total_max for est in estimates)
        
        # Group by section
        summary_by_section = {}
        for estimate in estimates:
            # Find the issue to get section
            issue = next(
                (iss for iss in report.issues if iss.id == estimate.issue_id),
                None
            )
            
            if issue:
                section = issue.section
                if section not in summary_by_section:
                    summary_by_section[section] = {'min': 0.0, 'max': 0.0}
                
                summary_by_section[section]['min'] += estimate.cost_breakdown.total_min
                summary_by_section[section]['max'] += estimate.cost_breakdown.total_max
        
        # Get top priorities (highest urgency and cost)
        urgency_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        top_priorities = sorted(
            estimates,
            key=lambda x: (
                urgency_order.get(x.urgency, 999),
                -(x.cost_breakdown.total_max)
            )
        )[:10]
        
        return EstimationResult(
            property_address=report.metadata.property_address or "Unknown",
            inspection_date=report.metadata.inspection_date or "Unknown",
            total_issues=len(report.issues),
            deficient_issues=len(estimates),
            estimates=estimates,
            total_cost_min=total_min,
            total_cost_max=total_max,
            summary_by_section=summary_by_section,
            top_priorities=top_priorities,
            houston_considerations=houston_considerations,
            generated_at=datetime.now().isoformat()
        )
    
    def _create_empty_result(self, report: StructuredReport) -> EstimationResult:
        """Create empty result when no deficient issues found."""
        return EstimationResult(
            property_address=report.metadata.property_address or "Unknown",
            inspection_date=report.metadata.inspection_date or "Unknown",
            total_issues=len(report.issues),
            deficient_issues=0,
            estimates=[],
            total_cost_min=0.0,
            total_cost_max=0.0,
            summary_by_section={},
            top_priorities=[],
            houston_considerations=[],
            generated_at=datetime.now().isoformat()
        )
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get API usage statistics."""
        return self.ai_estimator.get_usage_stats()

