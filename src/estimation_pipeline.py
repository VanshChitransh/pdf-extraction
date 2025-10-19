"""
Main estimation pipeline integrating all components.
"""
import logging
import os
from typing import Optional, Dict, Any
from src.models import StructuredReport, EstimationResult
from src.cost_estimator import CostEstimationEngine
from src.data_preparer import DataPreparer
from src.pdf_generator import PDFGenerator
from src.ui_data_formatter import UIDataFormatter

logger = logging.getLogger(__name__)


class EstimationPipeline:
    """End-to-end pipeline for cost estimation."""
    
    def __init__(
        self,
        gemini_api_key: str,
        location: str = "Houston, TX",
        output_dir: str = "./estimates",
        use_batch: bool = True,
        max_workers: int = 3
    ):
        """
        Initialize estimation pipeline.
        
        Args:
            gemini_api_key: Google Gemini API key
            location: Property location for context
            output_dir: Directory for output files
            use_batch: Whether to use batch processing
            max_workers: Max concurrent API calls
        """
        self.location = location
        self.output_dir = output_dir
        
        # Create output directory if needed
        os.makedirs(output_dir, exist_ok=True)
        
        # Initialize components
        self.cost_estimator = CostEstimationEngine(
            api_key=gemini_api_key,
            location=location,
            use_batch=use_batch,
            max_workers=max_workers
        )
        self.data_preparer = DataPreparer(location=location)
        self.pdf_generator = PDFGenerator()
        self.ui_formatter = UIDataFormatter()
        
        logger.info(f"Initialized EstimationPipeline for {location}")
        logger.info(f"Output directory: {output_dir}")
    
    def estimate_costs(
        self,
        json_path: str,
        progress_callback: Optional[callable] = None
    ) -> EstimationResult:
        """
        Generate cost estimates from inspection report JSON.
        
        Args:
            json_path: Path to extracted inspection JSON
            progress_callback: Optional callback(current, total, message)
            
        Returns:
            EstimationResult object
        """
        logger.info(f"Starting cost estimation for: {json_path}")
        
        # Load report
        if progress_callback:
            progress_callback(0, 100, "Loading inspection report...")
        
        report = self.data_preparer.load_report(json_path)
        logger.info(f"Loaded report: {report.metadata.filename}")
        
        # Get summary stats
        stats = self.data_preparer.get_summary_stats(report)
        logger.info(f"Report stats: {stats}")
        
        if progress_callback:
            progress_callback(10, 100, "Analyzing deficient issues...")
        
        # Generate estimates
        if progress_callback:
            # Wrap progress callback to scale to 10-90%
            def scaled_progress(current, total, message):
                percent = 10 + int((current / total) * 80)
                progress_callback(percent, 100, message)
            
            result = self.cost_estimator.estimate_report(report, scaled_progress)
        else:
            result = self.cost_estimator.estimate_report(report)
        
        if progress_callback:
            progress_callback(90, 100, "Estimation complete")
        
        # Log statistics
        api_stats = self.cost_estimator.get_statistics()
        logger.info(f"API Usage: {api_stats}")
        
        if progress_callback:
            progress_callback(100, 100, "Done")
        
        return result
    
    def generate_pdf(
        self,
        result: EstimationResult,
        output_path: Optional[str] = None
    ) -> str:
        """
        Generate PDF report from estimation result.
        
        Args:
            result: EstimationResult object
            output_path: Optional custom output path
            
        Returns:
            Path to generated PDF
        """
        if output_path is None:
            # Generate default filename
            timestamp = result.generated_at.replace(':', '-').split('.')[0]
            filename = f"cost_estimate_{timestamp}.pdf"
            output_path = os.path.join(self.output_dir, filename)
        
        logger.info(f"Generating PDF report: {output_path}")
        self.pdf_generator.generate_report(result, output_path)
        
        return output_path
    
    def generate_ui_data(
        self,
        result: EstimationResult,
        output_path: Optional[str] = None
    ) -> str:
        """
        Generate UI JSON data from estimation result.
        
        Args:
            result: EstimationResult object
            output_path: Optional custom output path
            
        Returns:
            Path to generated JSON
        """
        if output_path is None:
            # Generate default filename
            timestamp = result.generated_at.replace(':', '-').split('.')[0]
            filename = f"estimate_ui_{timestamp}.json"
            output_path = os.path.join(self.output_dir, filename)
        
        logger.info(f"Generating UI data: {output_path}")
        self.ui_formatter.save_to_json(result, output_path)
        
        return output_path
    
    def process_full_pipeline(
        self,
        json_path: str,
        pdf_output: Optional[str] = None,
        ui_output: Optional[str] = None,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Run full pipeline: estimate costs, generate PDF and UI data.
        
        Args:
            json_path: Path to inspection JSON
            pdf_output: Optional PDF output path
            ui_output: Optional UI JSON output path
            progress_callback: Optional progress callback
            
        Returns:
            Dict with paths and result
        """
        logger.info("Running full estimation pipeline")
        
        # Estimate costs
        result = self.estimate_costs(json_path, progress_callback)
        
        # Generate outputs
        pdf_path = self.generate_pdf(result, pdf_output)
        ui_path = self.generate_ui_data(result, ui_output)
        
        # Save raw result as JSON
        result_path = os.path.join(
            self.output_dir,
            f"estimate_result_{result.generated_at.replace(':', '-').split('.')[0]}.json"
        )
        result.to_json(result_path)
        
        logger.info("Full pipeline complete")
        logger.info(f"  PDF Report: {pdf_path}")
        logger.info(f"  UI Data: {ui_path}")
        logger.info(f"  Raw Result: {result_path}")
        
        return {
            "result": result,
            "pdf_path": pdf_path,
            "ui_path": ui_path,
            "result_path": result_path,
            "summary": {
                "total_cost_min": result.total_cost_min,
                "total_cost_max": result.total_cost_max,
                "deficient_issues": result.deficient_issues,
                "estimates_generated": len(result.estimates)
            }
        }
    
    def get_api_statistics(self) -> Dict[str, Any]:
        """Get API usage statistics."""
        return self.cost_estimator.get_statistics()
    
    def reset_statistics(self):
        """Reset API usage statistics."""
        self.cost_estimator.ai_estimator.reset_stats()
        logger.info("Reset API usage statistics")


def create_pipeline_from_env(
    location: str = "Houston, TX",
    output_dir: str = "./estimates"
) -> EstimationPipeline:
    """
    Create pipeline using API key from environment variable.
    
    Args:
        location: Property location
        output_dir: Output directory
        
    Returns:
        EstimationPipeline instance
    """
    import os
    from dotenv import load_dotenv
    
    # Try to load .env file
    load_dotenv()
    
    api_key = os.getenv('GEMINI_API_KEY')
    
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY not found in environment. "
            "Set it in .env file or environment variable."
        )
    
    return EstimationPipeline(
        gemini_api_key=api_key,
        location=location,
        output_dir=output_dir
    )

