"""
UI data formatter for cost estimates.
Formats estimation results for frontend consumption.
"""
import json
import logging
from typing import Dict, Any, List
from datetime import datetime
from src.models import EstimationResult, RepairEstimate

logger = logging.getLogger(__name__)


class UIDataFormatter:
    """Formats estimation results for UI display."""
    
    def __init__(self):
        """Initialize UI data formatter."""
        logger.info("Initialized UI Data Formatter")
    
    def format_for_ui(self, result: EstimationResult) -> Dict[str, Any]:
        """
        Format estimation result for UI consumption.
        
        Args:
            result: EstimationResult object
            
        Returns:
            Dict formatted for frontend
        """
        logger.info("Formatting data for UI")
        
        return {
            "metadata": self._format_metadata(result),
            "summary": self._format_summary(result),
            "sections": self._format_sections(result),
            "top_priorities": self._format_top_priorities(result),
            "houston_considerations": result.houston_considerations,
            "charts": self._format_chart_data(result)
        }
    
    def _format_metadata(self, result: EstimationResult) -> Dict[str, Any]:
        """Format metadata section."""
        return {
            "property_address": result.property_address,
            "inspection_date": result.inspection_date,
            "generated_at": result.generated_at,
            "generated_at_formatted": datetime.fromisoformat(
                result.generated_at
            ).strftime("%B %d, %Y at %I:%M %p"),
            "location": "Houston, TX"
        }
    
    def _format_summary(self, result: EstimationResult) -> Dict[str, Any]:
        """Format summary statistics."""
        # Calculate priority breakdown
        priority_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        for estimate in result.estimates:
            urgency = estimate.urgency.lower()
            if urgency in priority_counts:
                priority_counts[urgency] += 1
        
        # Calculate average cost
        avg_min = result.total_cost_min / len(result.estimates) if result.estimates else 0
        avg_max = result.total_cost_max / len(result.estimates) if result.estimates else 0
        
        return {
            "total_issues": result.total_issues,
            "deficient_issues": result.deficient_issues,
            "estimated_total": {
                "min": result.total_cost_min,
                "max": result.total_cost_max,
                "formatted_min": f"${result.total_cost_min:,.0f}",
                "formatted_max": f"${result.total_cost_max:,.0f}",
                "formatted_range": f"${result.total_cost_min:,.0f} - ${result.total_cost_max:,.0f}"
            },
            "average_cost": {
                "min": avg_min,
                "max": avg_max,
                "formatted": f"${avg_min:,.0f} - ${avg_max:,.0f}"
            },
            "priority_breakdown": priority_counts,
            "total_sections": len(result.summary_by_section)
        }
    
    def _format_sections(self, result: EstimationResult) -> List[Dict[str, Any]]:
        """Format sections with their estimates."""
        sections = []
        
        # Group estimates by section
        estimates_by_section = {}
        for estimate in result.estimates:
            # Extract section from issue_id
            section = estimate.issue_id.split('_')[0] if '_' in estimate.issue_id else "Other"
            if section not in estimates_by_section:
                estimates_by_section[section] = []
            estimates_by_section[section].append(estimate)
        
        # Format each section
        for section_name in sorted(estimates_by_section.keys()):
            section_estimates = estimates_by_section[section_name]
            
            # Calculate section totals
            section_min = sum(e.cost_breakdown.total_min for e in section_estimates)
            section_max = sum(e.cost_breakdown.total_max for e in section_estimates)
            
            # Count by urgency
            urgency_counts = {}
            for estimate in section_estimates:
                urgency = estimate.urgency
                urgency_counts[urgency] = urgency_counts.get(urgency, 0) + 1
            
            sections.append({
                "section_name": self._clean_section_name(section_name),
                "section_id": section_name,
                "total_cost": {
                    "min": section_min,
                    "max": section_max,
                    "formatted": f"${section_min:,.0f} - ${section_max:,.0f}"
                },
                "issue_count": len(section_estimates),
                "urgency_breakdown": urgency_counts,
                "estimates": [self._format_estimate(e) for e in section_estimates]
            })
        
        # Sort by total cost (descending)
        sections.sort(key=lambda x: x['total_cost']['max'], reverse=True)
        
        return sections
    
    def _format_top_priorities(self, result: EstimationResult) -> List[Dict[str, Any]]:
        """Format top priority items."""
        return [
            self._format_estimate(estimate, include_full_details=True)
            for estimate in result.top_priorities[:10]
        ]
    
    def _format_estimate(
        self,
        estimate: RepairEstimate,
        include_full_details: bool = False
    ) -> Dict[str, Any]:
        """Format a single estimate."""
        formatted = {
            "id": estimate.issue_id,
            "repair_name": estimate.repair_name,
            "cost": {
                "labor": {
                    "min": estimate.cost_breakdown.labor_min,
                    "max": estimate.cost_breakdown.labor_max,
                    "formatted": f"${estimate.cost_breakdown.labor_min:,.0f} - ${estimate.cost_breakdown.labor_max:,.0f}"
                },
                "materials": {
                    "min": estimate.cost_breakdown.materials_min,
                    "max": estimate.cost_breakdown.materials_max,
                    "formatted": f"${estimate.cost_breakdown.materials_min:,.0f} - ${estimate.cost_breakdown.materials_max:,.0f}"
                },
                "total": {
                    "min": estimate.cost_breakdown.total_min,
                    "max": estimate.cost_breakdown.total_max,
                    "formatted": f"${estimate.cost_breakdown.total_min:,.0f} - ${estimate.cost_breakdown.total_max:,.0f}"
                }
            },
            "timeline": {
                "min_days": estimate.timeline_days_min,
                "max_days": estimate.timeline_days_max,
                "formatted": f"{estimate.timeline_days_min}-{estimate.timeline_days_max} days"
            },
            "urgency": estimate.urgency,
            "urgency_color": self._get_urgency_color(estimate.urgency),
            "contractor_type": estimate.contractor_type,
            "confidence_score": estimate.confidence_score
        }
        
        if include_full_details:
            formatted.update({
                "houston_notes": estimate.houston_notes,
                "explanation": estimate.explanation
            })
        
        return formatted
    
    def _format_chart_data(self, result: EstimationResult) -> Dict[str, Any]:
        """Format data for charts and visualizations."""
        # Cost by section for pie chart
        section_costs = []
        for section, costs in result.summary_by_section.items():
            section_costs.append({
                "section": self._clean_section_name(section),
                "value": (costs['min'] + costs['max']) / 2,  # Average
                "min": costs['min'],
                "max": costs['max']
            })
        
        # Sort by value
        section_costs.sort(key=lambda x: x['value'], reverse=True)
        
        # Priority distribution for bar chart
        priority_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for estimate in result.estimates:
            urgency = estimate.urgency.lower()
            if urgency in priority_counts:
                priority_counts[urgency] += 1
        
        # Cost distribution (buckets)
        cost_buckets = {
            "0-500": 0,
            "500-1000": 0,
            "1000-2500": 0,
            "2500-5000": 0,
            "5000+": 0
        }
        
        for estimate in result.estimates:
            avg_cost = (estimate.cost_breakdown.total_min + estimate.cost_breakdown.total_max) / 2
            if avg_cost <= 500:
                cost_buckets["0-500"] += 1
            elif avg_cost <= 1000:
                cost_buckets["500-1000"] += 1
            elif avg_cost <= 2500:
                cost_buckets["1000-2500"] += 1
            elif avg_cost <= 5000:
                cost_buckets["2500-5000"] += 1
            else:
                cost_buckets["5000+"] += 1
        
        return {
            "cost_by_section": section_costs,
            "priority_distribution": [
                {"priority": k, "count": v, "color": self._get_urgency_color(k)}
                for k, v in priority_counts.items()
            ],
            "cost_distribution": [
                {"range": k, "count": v}
                for k, v in cost_buckets.items()
            ]
        }
    
    def _get_urgency_color(self, urgency: str) -> str:
        """Get color code for urgency level."""
        colors = {
            'critical': '#c53030',
            'high': '#dd6b20',
            'medium': '#d69e2e',
            'low': '#38a169',
            'info': '#3182ce'
        }
        return colors.get(urgency.lower(), '#4a5568')
    
    def _clean_section_name(self, section: str) -> str:
        """Clean section name for display."""
        # Remove roman numerals and periods at start
        cleaned = section.strip()
        parts = cleaned.split('.')
        if len(parts) > 1 and len(parts[0]) <= 3:
            cleaned = '.'.join(parts[1:]).strip()
        return cleaned
    
    def save_to_json(self, result: EstimationResult, output_path: str):
        """
        Save formatted UI data to JSON file.
        
        Args:
            result: EstimationResult object
            output_path: Path to save JSON file
        """
        logger.info(f"Saving UI data to: {output_path}")
        
        ui_data = self.format_for_ui(result)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(ui_data, f, indent=2)
        
        logger.info("UI data saved successfully")

