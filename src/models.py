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
class ExtractedImage:
    """Extracted image with context and metadata."""
    page_num: int
    image_index: int
    image_data: bytes  # Raw image data
    image_path: str  # Saved path
    caption: Optional[str]
    related_section: str
    related_text: str  # Text near the image
    bbox: Optional[Tuple[float, float, float, float]]
    ocr_text: Optional[str]  # Text extracted from image via OCR
    
    def to_dict(self) -> Dict[str, Any]:
        # Convert bytes to base64 for JSON serialization
        import base64
        data = asdict(self)
        if data['image_data']:
            data['image_data'] = base64.b64encode(data['image_data']).decode('utf-8')
        return data


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
    related_images: List[str]  # Paths to images
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
    images: List[ExtractedImage]
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
        
        # Handle images with base64 decoding
        images = []
        for img_data in data['images']:
            if img_data['image_data']:
                import base64
                img_data['image_data'] = base64.b64decode(img_data['image_data'])
            images.append(ExtractedImage(**img_data))
        
        return cls(
            metadata=metadata,
            issues=issues,
            tables=tables,
            images=images,
            raw_sections=data['raw_sections']
        )


@dataclass
class CostBreakdown:
    """Cost breakdown for a repair estimate."""
    labor_min: float
    labor_max: float
    materials_min: float
    materials_max: float
    total_min: float
    total_max: float
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RepairEstimate:
    """AI-generated repair cost estimate for an issue."""
    issue_id: str
    repair_name: str
    cost_breakdown: CostBreakdown
    timeline_days_min: int
    timeline_days_max: int
    urgency: str  # 'critical', 'high', 'medium', 'low'
    contractor_type: str
    houston_notes: str
    explanation: str
    confidence_score: float  # 0.0 to 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class EstimationResult:
    """Complete cost estimation result for a report."""
    property_address: str
    inspection_date: str
    total_issues: int
    deficient_issues: int
    estimates: List[RepairEstimate]
    total_cost_min: float
    total_cost_max: float
    summary_by_section: Dict[str, Dict[str, float]]  # section -> {min, max}
    top_priorities: List[RepairEstimate]
    houston_considerations: List[str]
    generated_at: str
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    def to_json(self, filepath: str) -> None:
        """Save estimation result to JSON file."""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, default=str)
