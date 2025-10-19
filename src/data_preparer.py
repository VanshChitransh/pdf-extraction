"""
Data preparation module for AI estimation.
Transforms extracted JSON data into AI-optimized format.
"""
import json
import logging
from typing import List, Dict, Any
from src.models import StructuredReport, InspectionIssue

logger = logging.getLogger(__name__)


class DataPreparer:
    """Prepares extracted inspection data for AI cost estimation."""
    
    def __init__(self, location: str = "Houston, TX"):
        """
        Initialize data preparer.
        
        Args:
            location: Property location for context
        """
        self.location = location
        logger.info(f"Initialized DataPreparer for location: {location}")
    
    def load_report(self, json_path: str) -> StructuredReport:
        """
        Load structured report from JSON file.
        
        Args:
            json_path: Path to JSON file
            
        Returns:
            StructuredReport object
        """
        logger.info(f"Loading report from: {json_path}")
        
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Create StructuredReport manually
        from src.models import PDFMetadata, InspectionIssue, ExtractedTable, ExtractedImage
        
        metadata = PDFMetadata(**data['metadata'])
        issues = [InspectionIssue(**issue) for issue in data['issues']]
        tables = [ExtractedTable(**table) for table in data.get('tables', [])]
        images = []  # Skip images for now
        raw_sections = data.get('raw_sections', {})
        
        report = StructuredReport(
            metadata=metadata,
            issues=issues,
            tables=tables,
            images=images,
            raw_sections=raw_sections
        )
        
        logger.info(f"Loaded report: {len(issues)} issues, {len(tables)} tables")
        return report
    
    def filter_deficient_issues(self, report: StructuredReport) -> List[InspectionIssue]:
        """
        Filter issues to only deficient ones (status 'D').
        
        Args:
            report: Structured report
            
        Returns:
            List of deficient issues
        """
        deficient = [issue for issue in report.issues if issue.status == 'D']
        
        # Filter out header issues and very generic items
        filtered = []
        for issue in deficient:
            # Skip header/boilerplate issues
            if issue.section == "HEADER":
                continue
            
            # Skip if description is too short (likely not actionable)
            if len(issue.description.strip()) < 50:
                continue
            
            filtered.append(issue)
        
        logger.info(f"Filtered {len(filtered)} deficient issues from {len(report.issues)} total")
        return filtered
    
    def prepare_issue_data(
        self,
        issue: InspectionIssue,
        property_location: str = None,
        inspection_date: str = None
    ) -> Dict[str, Any]:
        """
        Prepare issue data for AI estimation.
        
        Args:
            issue: InspectionIssue object
            property_location: Property location (override)
            inspection_date: Inspection date (override)
            
        Returns:
            Dict with formatted issue data
        """
        return {
            "id": issue.id,
            "property_location": property_location or self.location,
            "inspection_date": inspection_date or "N/A",
            "section": issue.section,
            "subsection": issue.subsection,
            "status": issue.status,
            "priority": issue.priority,
            "title": issue.title,
            "description": self._clean_description(issue.description)
        }
    
    def _clean_description(self, description: str) -> str:
        """
        Clean and truncate description for API efficiency.
        
        Args:
            description: Raw description text
            
        Returns:
            Cleaned description
        """
        # Remove excessive whitespace
        cleaned = " ".join(description.split())
        
        # Truncate if too long (keep under 1000 chars to manage token usage)
        if len(cleaned) > 1000:
            cleaned = cleaned[:997] + "..."
        
        return cleaned
    
    def group_issues_by_section(
        self,
        issues: List[InspectionIssue]
    ) -> Dict[str, List[InspectionIssue]]:
        """
        Group issues by section for batch processing.
        
        Args:
            issues: List of issues
            
        Returns:
            Dict mapping section names to issue lists
        """
        grouped = {}
        for issue in issues:
            section = issue.section
            if section not in grouped:
                grouped[section] = []
            grouped[section].append(issue)
        
        logger.info(f"Grouped {len(issues)} issues into {len(grouped)} sections")
        return grouped
    
    def get_property_context(self, report: StructuredReport) -> Dict[str, str]:
        """
        Extract property context from report metadata.
        
        Args:
            report: Structured report
            
        Returns:
            Dict with property context
        """
        return {
            "address": report.metadata.property_address or "Unknown",
            "location": self.location,
            "inspection_date": report.metadata.inspection_date or "Unknown",
            "report_type": report.metadata.report_type,
            "total_pages": str(report.metadata.total_pages)
        }
    
    def prepare_batch_data(
        self,
        issues: List[InspectionIssue],
        property_location: str = None,
        inspection_date: str = None
    ) -> List[Dict[str, Any]]:
        """
        Prepare multiple issues for batch estimation.
        
        Args:
            issues: List of InspectionIssue objects
            property_location: Property location (override)
            inspection_date: Inspection date (override)
            
        Returns:
            List of dicts with formatted issue data
        """
        return [
            self.prepare_issue_data(issue, property_location, inspection_date)
            for issue in issues
        ]
    
    def get_summary_stats(self, report: StructuredReport) -> Dict[str, Any]:
        """
        Get summary statistics for report.
        
        Args:
            report: Structured report
            
        Returns:
            Dict with summary stats
        """
        deficient = self.filter_deficient_issues(report)
        
        # Count by priority
        priority_counts = {}
        for issue in deficient:
            priority = issue.priority
            priority_counts[priority] = priority_counts.get(priority, 0) + 1
        
        # Count by section
        section_counts = {}
        for issue in deficient:
            section = issue.section
            section_counts[section] = section_counts.get(section, 0) + 1
        
        return {
            "total_issues": len(report.issues),
            "deficient_issues": len(deficient),
            "priority_breakdown": priority_counts,
            "section_breakdown": section_counts
        }

