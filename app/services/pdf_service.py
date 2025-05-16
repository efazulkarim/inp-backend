import os
import tempfile
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image

async def generate_report_pdf(report_data, idea_name):
    """Generate a PDF report from the report data"""
    # Create a temporary file
    temp_dir = tempfile.gettempdir()
    output_path = os.path.join(temp_dir, f"{idea_name.replace(' ', '_')}_Report.pdf")
    
    # Create the PDF document
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72
    )
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = styles["Title"]
    heading_style = styles["Heading1"]
    subheading_style = styles["Heading2"]
    normal_style = styles["Normal"]
    
    # Create custom styles
    styles.add(ParagraphStyle(
        name='SectionTitle',
        parent=styles['Heading2'],
        textColor=colors.white,
        backColor=colors.lightblue,
        borderPadding=5
    ))
    
    # Build the PDF content
    elements = []
    
    # Title
    elements.append(Paragraph(f"InsightPilot Report: {report_data['idea_name']}", title_style))
    elements.append(Spacer(1, 12))
    
    # Date
    elements.append(Paragraph(f"Generated on: {datetime.utcnow().strftime('%Y-%m-%d')}", normal_style))
    elements.append(Spacer(1, 24))
    
    # Overall score
    elements.append(Paragraph(f"Overall Score: {report_data['overall_score']}/120", heading_style))
    elements.append(Spacer(1, 12))
    
    # Report overview
    elements.append(Paragraph("Report Overview", heading_style))
    elements.append(Paragraph(report_data['report_overview'], normal_style))
    elements.append(Spacer(1, 24))
    
    # Section scores table
    elements.append(Paragraph("Category Scores", heading_style))
    elements.append(Spacer(1, 12))
    
    # Create table for section scores
    table_data = [["Category", "Score", "Weighted Score"]]
    for section in report_data['sections']:
        table_data.append([
            section['category'],
            section['score'],
            section['weighted_score']
        ])
    
    table = Table(table_data, colWidths=[doc.width * 0.5, doc.width * 0.25, doc.width * 0.25])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 24))
    
    # Detailed section analysis
    elements.append(Paragraph("Detailed Analysis", heading_style))
    elements.append(Spacer(1, 12))
    
    for section in report_data['sections']:
        # Section title with background
        elements.append(Paragraph(f"{section['category']}: Score {section['score']}/15", styles['SectionTitle']))
        elements.append(Spacer(1, 6))
        
        # Insight
        elements.append(Paragraph("<b>Insight:</b>", normal_style))
        elements.append(Paragraph(section['insight'], normal_style))
        elements.append(Spacer(1, 6))
        
        # Recommendations
        elements.append(Paragraph("<b>Recommendations:</b>", normal_style))
        for rec in section['recommendations']:
            elements.append(Paragraph(f"• {rec}", normal_style))
        
        elements.append(Spacer(1, 18))
    
    # Strategic next steps
    elements.append(Paragraph("Strategic Next Steps", heading_style))
    elements.append(Spacer(1, 12))
    
    for i, step in enumerate(report_data['strategic_next_steps']):
        elements.append(Paragraph(f"{i+1}. {step}", normal_style))
        elements.append(Spacer(1, 6))
    
    # Add page numbers to every page
    def add_page_number(canvas, doc):
        canvas.saveState()
        canvas.setFont('Helvetica', 8)
        page_num = canvas.getPageNumber()
        text = f"Page {page_num}"
        canvas.drawRightString(doc.width + doc.rightMargin - 20, doc.bottomMargin/2, text)
        canvas.restoreState()

    # Build the PDF
    doc.build(elements, onFirstPage=add_page_number, onLaterPages=add_page_number)
    
    return output_path