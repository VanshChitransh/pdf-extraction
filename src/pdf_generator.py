"""
PDF report generator for cost estimates.
"""
import logging
from datetime import datetime
from typing import List
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from src.models import EstimationResult, RepairEstimate

logger = logging.getLogger(__name__)


class PDFGenerator:
    """Generates professional PDF reports for cost estimates."""
    
    def __init__(self):
        """Initialize PDF generator."""
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
        logger.info("Initialized PDF Generator")
    
    def _setup_custom_styles(self):
        """Setup custom paragraph styles."""
        # Title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Title'],
            fontSize=24,
            textColor=colors.HexColor('#1a365d'),
            spaceAfter=30,
            alignment=TA_CENTER
        ))
        
        # Subtitle style
        self.styles.add(ParagraphStyle(
            name='CustomSubtitle',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#2d3748'),
            spaceAfter=12
        ))
        
        # Section header
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor('#2c5282'),
            spaceAfter=12,
            spaceBefore=20
        ))
        
        # Subsection header
        self.styles.add(ParagraphStyle(
            name='SubsectionHeader',
            parent=self.styles['Heading2'],
            fontSize=12,
            textColor=colors.HexColor('#4a5568'),
            spaceAfter=8,
            spaceBefore=10
        ))
        
        # Body text
        self.styles.add(ParagraphStyle(
            name='CustomBody',
            parent=self.styles['BodyText'],
            fontSize=10,
            leading=14
        ))
        
        # Small text
        self.styles.add(ParagraphStyle(
            name='SmallText',
            parent=self.styles['BodyText'],
            fontSize=8,
            textColor=colors.HexColor('#718096')
        ))
    
    def generate_report(self, result: EstimationResult, output_path: str):
        """
        Generate PDF report from estimation result.
        
        Args:
            result: EstimationResult object
            output_path: Path to save PDF
        """
        logger.info(f"Generating PDF report: {output_path}")
        
        # Create document
        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch
        )
        
        # Build content
        story = []
        
        # Cover page
        story.extend(self._create_cover_page(result))
        story.append(PageBreak())
        
        # Executive summary
        story.extend(self._create_executive_summary(result))
        story.append(PageBreak())
        
        # Detailed estimates by section
        story.extend(self._create_detailed_section(result))
        
        # Houston considerations
        story.append(PageBreak())
        story.extend(self._create_houston_section(result))
        
        # Disclaimer
        story.extend(self._create_disclaimer())
        
        # Build PDF
        doc.build(story)
        logger.info(f"PDF report generated successfully: {output_path}")
    
    def _create_cover_page(self, result: EstimationResult) -> List:
        """Create cover page."""
        elements = []
        
        # Title
        elements.append(Spacer(1, 1.5*inch))
        elements.append(Paragraph(
            "Home Repair Cost Estimate",
            self.styles['CustomTitle']
        ))
        
        elements.append(Spacer(1, 0.5*inch))
        
        # Property info
        property_info = [
            ["Property Address:", result.property_address],
            ["Inspection Date:", result.inspection_date],
            ["Report Generated:", datetime.fromisoformat(result.generated_at).strftime("%B %d, %Y %I:%M %p")],
            ["Location:", "Houston, Texas"]
        ]
        
        info_table = Table(property_info, colWidths=[2*inch, 4*inch])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#2d3748')),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        elements.append(info_table)
        elements.append(Spacer(1, 0.5*inch))
        
        # Cost summary box
        elements.append(Paragraph("Estimated Total Cost", self.styles['CustomSubtitle']))
        
        cost_text = f"${result.total_cost_min:,.0f} - ${result.total_cost_max:,.0f}"
        cost_para = Paragraph(
            f"<font size=32 color='#2c5282'><b>{cost_text}</b></font>",
            ParagraphStyle('CostStyle', alignment=TA_CENTER)
        )
        elements.append(cost_para)
        elements.append(Spacer(1, 0.3*inch))
        
        # Summary stats
        stats = [
            [f"<b>{result.total_issues}</b><br/>Total Issues", 
             f"<b>{result.deficient_issues}</b><br/>Need Repair",
             f"<b>{len(result.top_priorities)}</b><br/>High Priority"]
        ]
        
        stats_table = Table(stats, colWidths=[2*inch, 2*inch, 2*inch])
        stats_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#2d3748')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#cbd5e0')),
            ('INNERGRID', (0, 0), (-1, -1), 1, colors.HexColor('#cbd5e0')),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#edf2f7')),
            ('TOPPADDING', (0, 0), (-1, -1), 15),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
        ]))
        
        elements.append(stats_table)
        
        return elements
    
    def _create_executive_summary(self, result: EstimationResult) -> List:
        """Create executive summary page."""
        elements = []
        
        elements.append(Paragraph("Executive Summary", self.styles['SectionHeader']))
        elements.append(Spacer(1, 0.2*inch))
        
        # Top priorities
        elements.append(Paragraph("Top Priority Repairs", self.styles['SubsectionHeader']))
        
        if result.top_priorities:
            priority_data = [["Priority", "Repair", "Estimated Cost", "Urgency"]]
            
            for i, estimate in enumerate(result.top_priorities[:5], 1):
                cost_range = f"${estimate.cost_breakdown.total_min:,.0f} - ${estimate.cost_breakdown.total_max:,.0f}"
                urgency_color = self._get_urgency_color(estimate.urgency)
                
                priority_data.append([
                    str(i),
                    Paragraph(estimate.repair_name[:60], self.styles['CustomBody']),
                    cost_range,
                    f"<font color='{urgency_color}'>{estimate.urgency.upper()}</font>"
                ])
            
            priority_table = Table(priority_data, colWidths=[0.5*inch, 3.5*inch, 1.5*inch, 1*inch])
            priority_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c5282')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('ALIGN', (0, 0), (0, -1), 'CENTER'),
                ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
                ('ALIGN', (3, 0), (3, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f7fafc')]),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ]))
            
            elements.append(priority_table)
        
        elements.append(Spacer(1, 0.3*inch))
        
        # Cost by section
        elements.append(Paragraph("Cost Breakdown by Section", self.styles['SubsectionHeader']))
        
        if result.summary_by_section:
            section_data = [["Section", "Estimated Cost"]]
            
            for section, costs in sorted(result.summary_by_section.items()):
                cost_range = f"${costs['min']:,.0f} - ${costs['max']:,.0f}"
                section_name = self._clean_section_name(section)
                section_data.append([section_name, cost_range])
            
            # Add total
            section_data.append([
                "<b>TOTAL</b>",
                f"<b>${result.total_cost_min:,.0f} - ${result.total_cost_max:,.0f}</b>"
            ])
            
            section_table = Table(section_data, colWidths=[4.5*inch, 2*inch])
            section_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c5282')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#f7fafc')]),
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#edf2f7')),
                ('LINEABOVE', (0, -1), (-1, -1), 2, colors.HexColor('#2c5282')),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ]))
            
            elements.append(section_table)
        
        return elements
    
    def _create_detailed_section(self, result: EstimationResult) -> List:
        """Create detailed estimates section."""
        elements = []
        
        elements.append(Paragraph("Detailed Repair Estimates", self.styles['SectionHeader']))
        elements.append(Spacer(1, 0.2*inch))
        
        # Group estimates by section
        by_section = {}
        for estimate in result.estimates:
            # Extract section from issue_id (simplified)
            section = estimate.issue_id.split('_')[0] if '_' in estimate.issue_id else "Other"
            if section not in by_section:
                by_section[section] = []
            by_section[section].append(estimate)
        
        # Create section-by-section breakdown
        for section, estimates in sorted(by_section.items()):
            section_elements = []
            
            # Section header
            section_elements.append(Paragraph(
                self._clean_section_name(section),
                self.styles['SubsectionHeader']
            ))
            
            # Estimates in this section
            for estimate in estimates:
                section_elements.extend(self._create_estimate_detail(estimate))
            
            # Keep section together if possible
            elements.append(KeepTogether(section_elements))
            elements.append(Spacer(1, 0.2*inch))
        
        return elements
    
    def _create_estimate_detail(self, estimate: RepairEstimate) -> List:
        """Create detail view for single estimate."""
        elements = []
        
        # Repair name with urgency badge
        urgency_color = self._get_urgency_color(estimate.urgency)
        name_text = f"<b>{estimate.repair_name}</b> " \
                   f"<font color='{urgency_color}'>[{estimate.urgency.upper()}]</font>"
        elements.append(Paragraph(name_text, self.styles['CustomBody']))
        
        # Cost breakdown table
        cost_data = [
            ["Labor:", f"${estimate.cost_breakdown.labor_min:,.0f} - ${estimate.cost_breakdown.labor_max:,.0f}"],
            ["Materials:", f"${estimate.cost_breakdown.materials_min:,.0f} - ${estimate.cost_breakdown.materials_max:,.0f}"],
            ["<b>Total:</b>", f"<b>${estimate.cost_breakdown.total_min:,.0f} - ${estimate.cost_breakdown.total_max:,.0f}</b>"]
        ]
        
        cost_table = Table(cost_data, colWidths=[1.5*inch, 2*inch])
        cost_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        
        elements.append(cost_table)
        
        # Details
        details_text = f"<b>Timeline:</b> {estimate.timeline_days_min}-{estimate.timeline_days_max} days | " \
                      f"<b>Contractor:</b> {estimate.contractor_type}"
        elements.append(Paragraph(details_text, self.styles['SmallText']))
        
        # Explanation
        if estimate.explanation:
            elements.append(Paragraph(f"<i>{estimate.explanation[:200]}...</i>", self.styles['SmallText']))
        
        # Houston notes
        if estimate.houston_notes:
            elements.append(Paragraph(
                f"<b>Houston Note:</b> {estimate.houston_notes}",
                self.styles['SmallText']
            ))
        
        elements.append(Spacer(1, 0.15*inch))
        
        return elements
    
    def _create_houston_section(self, result: EstimationResult) -> List:
        """Create Houston considerations section."""
        elements = []
        
        elements.append(Paragraph("Houston Market Considerations", self.styles['SectionHeader']))
        elements.append(Spacer(1, 0.2*inch))
        
        intro = ("These estimates are based on current Houston, Texas market rates and local conditions. "
                "Houston's unique climate and housing characteristics have been considered in these estimates.")
        elements.append(Paragraph(intro, self.styles['CustomBody']))
        elements.append(Spacer(1, 0.15*inch))
        
        if result.houston_considerations:
            for consideration in result.houston_considerations:
                bullet = f"• {consideration}"
                elements.append(Paragraph(bullet, self.styles['CustomBody']))
                elements.append(Spacer(1, 0.1*inch))
        
        return elements
    
    def _create_disclaimer(self) -> List:
        """Create disclaimer section."""
        elements = []
        
        elements.append(Spacer(1, 0.5*inch))
        elements.append(Paragraph("Important Disclaimer", self.styles['SubsectionHeader']))
        
        disclaimer_text = (
            "These cost estimates are provided for general planning purposes only and are based on typical Houston-area "
            "pricing and the information provided in the inspection report. Actual costs may vary significantly based on "
            "specific conditions, contractor selection, material choices, and market conditions at the time of repair. "
            "<br/><br/>"
            "We strongly recommend obtaining multiple detailed quotes from licensed, insured contractors before proceeding "
            "with any repairs. These estimates do not constitute professional advice and should not be solely relied upon "
            "for making financial decisions."
            "<br/><br/>"
            "<b>Always consult with qualified professionals for specific repair recommendations and accurate cost quotes.</b>"
        )
        
        elements.append(Paragraph(disclaimer_text, self.styles['SmallText']))
        
        return elements
    
    def _get_urgency_color(self, urgency: str) -> str:
        """Get color for urgency level."""
        colors_map = {
            'critical': '#c53030',
            'high': '#dd6b20',
            'medium': '#d69e2e',
            'low': '#38a169',
            'info': '#3182ce'
        }
        return colors_map.get(urgency.lower(), '#4a5568')
    
    def _clean_section_name(self, section: str) -> str:
        """Clean section name for display."""
        # Remove roman numerals and periods at start
        cleaned = section.strip()
        if len(cleaned) > 2 and cleaned[0].isalpha() and cleaned[1] == '.':
            cleaned = cleaned[3:].strip()
        return cleaned if len(cleaned) < 60 else cleaned[:57] + "..."

