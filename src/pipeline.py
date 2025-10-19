"""
Main PDF extraction pipeline orchestrator.
"""
import os
import json
import hashlib
import logging
from typing import Optional
from .models import StructuredReport
from .metadata_extractor import extract_metadata, extract_additional_metadata
from .text_extractor import extract_structured_text, group_text_by_section
from .table_extractor import extract_tables
# from .image_extractor import extract_images_with_context  # Image extraction disabled
from .data_structurer import structure_extraction_results, validate_extraction, get_extraction_summary


class PDFExtractionPipeline:
    """
    Main pipeline orchestrator for PDF extraction.
    """
    
    def __init__(self, output_dir: str = "./extracted_data", enable_caching: bool = True):
        self.output_dir = output_dir
        self.cache_dir = os.path.join(output_dir, "cache")
        self.enable_caching = enable_caching
        
        # Create directories
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def process_pdf(self, pdf_path: str, force_reprocess: bool = False) -> StructuredReport:
        """
        Run full extraction pipeline.
        """
        self.logger.info(f"Processing: {pdf_path}")
        
        # Check cache if enabled
        if self.enable_caching and not force_reprocess:
            cached_result = self._load_from_cache(pdf_path)
            if cached_result:
                self.logger.info("Using cached result")
                return cached_result
        
        try:
            # Step 1: Metadata
            self.logger.info("→ Extracting metadata...")
            metadata = extract_metadata(pdf_path)
            additional_metadata = extract_additional_metadata(pdf_path)
            
            # Step 2: Text with structure
            self.logger.info("→ Extracting structured text...")
            text_blocks = extract_structured_text(pdf_path)
            
            # Step 3: Tables
            self.logger.info("→ Extracting tables...")
            tables = extract_tables(pdf_path)
            
            # Step 4: Images (disabled)
            self.logger.info("→ Skipping image extraction (disabled)...")
            images = []  # Image extraction disabled
            
            # Step 5: Structure
            self.logger.info("→ Structuring data...")
            structured_report = structure_extraction_results(metadata, text_blocks, tables, images)
            
            # Step 6: Validation
            self.logger.info("→ Validating extraction...")
            is_valid = validate_extraction(structured_report)
            if not is_valid:
                self.logger.warning("Extraction validation failed, but continuing...")
            
            # Step 7: Save to JSON
            output_path = os.path.join(self.output_dir, f"{metadata.filename.replace('.pdf', '')}.json")
            structured_report.to_json(output_path)
            self.logger.info(f"✓ Saved to: {output_path}")
            
            # Step 8: Save cache if enabled
            if self.enable_caching:
                self._save_to_cache(pdf_path, structured_report)
            
            # Step 9: Generate summary
            summary = get_extraction_summary(structured_report)
            self.logger.info(f"Extraction summary: {summary}")
            
            return structured_report
            
        except Exception as e:
            self.logger.error(f"Error processing {pdf_path}: {e}")
            raise
    
    def _get_pdf_hash(self, pdf_path: str) -> str:
        """Generate hash for PDF file for caching."""
        with open(pdf_path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    
    def _get_cache_path(self, pdf_path: str) -> str:
        """Get cache file path for PDF."""
        pdf_hash = self._get_pdf_hash(pdf_path)
        return os.path.join(self.cache_dir, f"{pdf_hash}.json")
    
    def _load_from_cache(self, pdf_path: str) -> Optional[StructuredReport]:
        """Load structured report from cache."""
        try:
            cache_path = self._get_cache_path(pdf_path)
            if os.path.exists(cache_path):
                return StructuredReport.from_json(cache_path)
        except Exception as e:
            self.logger.warning(f"Error loading from cache: {e}")
        return None
    
    def _save_to_cache(self, pdf_path: str, report: StructuredReport) -> None:
        """Save structured report to cache."""
        try:
            cache_path = self._get_cache_path(pdf_path)
            report.to_json(cache_path)
        except Exception as e:
            self.logger.warning(f"Error saving to cache: {e}")
    
    def clear_cache(self) -> None:
        """Clear all cached results."""
        try:
            for file in os.listdir(self.cache_dir):
                if file.endswith('.json'):
                    os.remove(os.path.join(self.cache_dir, file))
            self.logger.info("Cache cleared")
        except Exception as e:
            self.logger.error(f"Error clearing cache: {e}")
    
    def get_processing_stats(self) -> dict:
        """Get statistics about processed files."""
        try:
            json_files = [f for f in os.listdir(self.output_dir) if f.endswith('.json')]
            cache_files = [f for f in os.listdir(self.cache_dir) if f.endswith('.json')]
            
            return {
                'processed_files': len(json_files),
                'cached_files': len(cache_files),
                'output_directory': self.output_dir,
                'cache_directory': self.cache_dir
            }
        except Exception as e:
            self.logger.error(f"Error getting stats: {e}")
            return {}


def main():
    """
    Example usage of the PDF extraction pipeline.
    """
    # Initialize pipeline
    pipeline = PDFExtractionPipeline()
    
    # Process a PDF file
    pdf_path = "7-report.pdf"  # Update with your PDF path
    if os.path.exists(pdf_path):
        try:
            report = pipeline.process_pdf(pdf_path)
            print(f"Successfully processed {pdf_path}")
            print(f"Extracted {len(report.issues)} issues")
            print(f"Extracted {len(report.tables)} tables")
        except Exception as e:
            print(f"Error processing {pdf_path}: {e}")
    else:
        print(f"PDF file not found: {pdf_path}")


if __name__ == "__main__":
    main()
