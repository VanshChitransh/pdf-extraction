"""
Data models for PDF extraction pipeline.
"""
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Tuple, Any
import json


@dataclass
class PDFMetadata:
    """Basic metadata extracted from PDF."""
    filename: str
    total_pages: int
    report_type: str  # 'inspection' or 'estimate'
    report_number: Optional[str]
    inspection_date: Optional[str]
    property_address: Optional[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TextBlock:
    """Structured text block with formatting and context."""
    page_num: int
    section: str  # e.g., "I. STRUCTURAL SYSTEMS"
    subsection: str  # e.g., "A. Foundations"
    status: Optional[str]  # I, NI, NP, D
    content: str
    bbox: Tuple[float, float, float, float]  # (x0, y0, x1, y1)
    formatting: Dict[str, bool]  # {'bold': True, 'italic': False}
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ExtractedTable:
    """Extracted table with semantic classification."""
    page_num: int
    section: str
    table_data: List[List[str]]
    column_headers: List[str]
    table_type: str  # 'elevation_survey', 'cost_estimate', 'checklist'
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class InspectionIssue:
    """Structured inspection issue with all related data."""
    id: str  # Unique identifier
    section: str  # e.g., "I. STRUCTURAL SYSTEMS"
    subsection: str  # e.g., "A. Foundations"
    status: str  # D=Deficient, I=Inspected, etc.
    priority: str  # 'high', 'medium', 'low', 'info'
    title: str  # Short description
    description: str  # Full text
    page_numbers: List[int]
    estimated_cost: Optional[Dict[str, float]]  # {'min': 500, 'max': 700}
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class StructuredReport:
    """Complete structured report combining all extracted data."""
    metadata: PDFMetadata
    issues: List[InspectionIssue]
    tables: List[ExtractedTable]
    raw_sections: Dict[str, str]  # Section → Full text
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    def to_json(self, filepath: str) -> None:
        """Save structured report to JSON file."""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, default=str)
    
    @classmethod
    def from_json(cls, filepath: str) -> 'StructuredReport':
        """Load structured report from JSON file."""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Convert back to proper types
        metadata = PDFMetadata(**data['metadata'])
        
        issues = [InspectionIssue(**issue) for issue in data['issues']]
        tables = [ExtractedTable(**table) for table in data['tables']]
        
        return cls(
            metadata=metadata,
            issues=issues,
            tables=tables,
            raw_sections=data['raw_sections']
        )
