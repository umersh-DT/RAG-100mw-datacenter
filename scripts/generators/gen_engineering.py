# Import os module for operating system file operations
import os
# Import yaml module to parse central pipeline configurations
import yaml
# Import Path from pathlib for safe cross-platform folder paths
from pathlib import Path
# Import landscape orientation and letter size from ReportLab
from reportlab.lib.pagesizes import letter, landscape
# Import ReportLab flowables for rendering structured drawings and tables
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
# Import ReportLab drawing and shape primitives for drawing schematic vectors
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Circle
# Import default ReportLab styles container
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
# Import colors module for custom CAD drawing palette rendering
from reportlab.lib import colors

# Define local path variable pointing to central YAML configuration
CONFIG_PATH = Path("config/pipeline_config.yaml")

# Verify configuration file exists before executing logic
if not CONFIG_PATH.exists():
    # Raise descriptive FileNotFoundError if config path is broken
    raise FileNotFoundError(f"Configuration file not found at {CONFIG_PATH.resolve()}")

# Open central configuration YAML file in read mode
with open(CONFIG_PATH, "r") as f:
    # Parse YAML contents into a structured Python dictionary
    config = yaml.safe_load(f)

# Resolve target destination path for engineering drawings raw data
OUTPUT_DIR = Path(config["paths"]["engineering_drawings_dir"])
# Ensure target output directory exists on disk
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# Define function to generate a landscape Single-Line Diagram (SLD) schematic PDF
def generate_sample_sld():
    """Generates a landscape Single-Line Diagram (SLD) PDF with vector schematics and equipment schedules."""
    # Define full file path for output engineering PDF
    pdf_filename = OUTPUT_DIR / "SLD_132kV_Substation_01.pdf"
    
    # Instantiate SimpleDocTemplate with LANDSCAPE letter size (11x8.5 inches) and 36pt margins
    doc = SimpleDocTemplate(
        str(pdf_filename),
        pagesize=landscape(letter),
        rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36
    )
    
    # Extract base styles container from ReportLab
    styles = getSampleStyleSheet()
    # Create custom ParagraphStyle for drawing header title text
    title_style = ParagraphStyle('DrawingTitle', parent=styles['Heading1'], fontSize=14, leading=18, alignment=0)
    # Create custom ParagraphStyle for drawing section headings
    heading_style = ParagraphStyle('SectionHeading', parent=styles['Heading2'], fontSize=11, leading=14, spaceBefore=6)
    # Create custom ParagraphStyle for compact schedule text
    body_style = ParagraphStyle('CompactBody', parent=styles['Normal'], fontSize=8, leading=10)
    
    # Initialize empty list to collect PDF flowable objects
    story = []
    
    # Append drawing title header to story
    story.append(Paragraph("132kV / 33kV SUBSTATION SINGLE-LINE DIAGRAM (SLD)", title_style))
    # Append drawing reference ID and project tag
    story.append(Paragraph("<b>Drawing No:</b> E-SLD-100MW-001-REV2 | <b>Facility:</b> HyperScale Infrastructure LLC", body_style))
    # Add vertical spacing of 8 points
    story.append(Spacer(1, 8))
    
    # Construct a vector schematic drawing (width=720pt, height=180pt)
    d = Drawing(720, 180)
    
    # Draw background box for the vector drawing area
    d.add(Rect(0, 0, 720, 180, fillColor=colors.HexColor("#F8FAFC"), strokeColor=colors.HexColor("#CBD5E1"), strokeWidth=1))
    
    # Draw High Voltage Busbar (132kV Main Bus)
    d.add(Line(50, 150, 670, 150, strokeColor=colors.HexColor("#DC2626"), strokeWidth=3))
    d.add(String(60, 158, "132kV MAIN UTILITY BUSBAR (INCOMING GRID)", fontSize=9, fontName="Helvetica-Bold", fillColor=colors.HexColor("#DC2626")))
    
    # Draw Transformer 1 Feeder Branch
    d.add(Line(180, 150, 180, 100, strokeColor=colors.HexColor("#1E293B"), strokeWidth=2))
    d.add(Rect(165, 110, 30, 20, fillColor=colors.HexColor("#FEF08A"), strokeColor=colors.black, strokeWidth=1))
    d.add(String(168, 116, "CB-132-A1", fontSize=6, fontName="Helvetica-Bold")) # Breaker Tag
    d.add(Circle(180, 90, 12, fillColor=colors.whitesmoke, strokeColor=colors.HexColor("#0284C7"), strokeWidth=2))
    d.add(Circle(180, 75, 12, fillColor=colors.whitesmoke, strokeColor=colors.HexColor("#0284C7"), strokeWidth=2))
    d.add(String(200, 80, "XFRM-01 (50 MVA 132/33kV)", fontSize=8, fontName="Helvetica-Bold"))
    d.add(Line(180, 63, 180, 20, strokeColor=colors.HexColor("#1E293B"), strokeWidth=2))
    
    # Draw Transformer 2 Feeder Branch (N+1 Redundancy)
    d.add(Line(540, 150, 540, 100, strokeColor=colors.HexColor("#1E293B"), strokeWidth=2))
    d.add(Rect(525, 110, 30, 20, fillColor=colors.HexColor("#FEF08A"), strokeColor=colors.black, strokeWidth=1))
    d.add(String(528, 116, "CB-132-B1", fontSize=6, fontName="Helvetica-Bold")) # Breaker Tag
    d.add(Circle(540, 90, 12, fillColor=colors.whitesmoke, strokeColor=colors.HexColor("#0284C7"), strokeWidth=2))
    d.add(Circle(540, 75, 12, fillColor=colors.whitesmoke, strokeColor=colors.HexColor("#0284C7"), strokeWidth=2))
    d.add(String(560, 80, "XFRM-02 (50 MVA 132/33kV)", fontSize=8, fontName="Helvetica-Bold"))
    d.add(Line(540, 63, 540, 20, strokeColor=colors.HexColor("#1E293B"), strokeWidth=2))
    
    # Draw 33kV Distribution Busbar
    d.add(Line(100, 20, 620, 20, strokeColor=colors.HexColor("#2563EB"), strokeWidth=3))
    d.add(String(110, 8, "33kV MEDIUM VOLTAGE DISTRIBUTION BUSBAR TO DATA HALL PODS", fontSize=9, fontName="Helvetica-Bold", fillColor=colors.HexColor("#2563EB")))
    
    # Append schematic drawing object to flowable story
    story.append(d)
    # Add vertical spacing of 10 points
    story.append(Spacer(1, 10))
    
    # Add section header for embedded equipment schedule table
    story.append(Paragraph("Substation Major Equipment Schedule & Protection Ratings", heading_style))
    
    # Define equipment schedule table data matrix
    equipment_schedule = [
        ["Equipment Tag", "Description / Function", "Rating / Capacity", "Fault Current (kA)", "Protection Relay"],
        ["XFRM-01", "Primary Step-Down Transformer", "50 MVA, 132kV/33kV", "40 kA (1 sec)", "SEL-787 Differential"],
        ["XFRM-02", "Secondary Redundant Transformer", "50 MVA, 132kV/33kV", "40 kA (1 sec)", "SEL-787 Differential"],
        ["CB-132-A1", "SF6 Gas Circuit Breaker", "2000A Continuous", "50 kA Interrupting", "SEL-751 Overcurrent"],
        ["CB-132-B1", "SF6 Gas Circuit Breaker", "2000A Continuous", "50 kA Interrupting", "SEL-751 Overcurrent"],
        ["33kV-SWG-01", "Air-Insulated Switchgear Bus", "3150A Main Bus", "25 kA Bus Rating", "Arc Flash Optical Sensor"]
    ]
    
    # Initialize schedule table with wide landscape column widths
    schedule_table = Table(equipment_schedule, colWidths=[90, 200, 150, 130, 150])
    # Apply CAD drawing schedule styling to the table
    schedule_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#0F172A")), # Dark slate header background
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),          # White header text
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),             # Bold font for header
        ('FONTSIZE', (0,0), (-1,-1), 8),                           # 8pt compact font size for dense engineering data
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#94A3B8")), # Slate grey grid lines
        ('BACKGROUND', (0,1), (-1,-1), colors.HexColor("#F8FAFC")), # Light off-white data rows
    ]))
    
    # Append equipment schedule table to story
    story.append(schedule_table)
    
    # Build and render physical landscape PDF document
    doc.build(story)
    # Print execution success log to terminal
    print(f"[SUCCESS] Sample SLD generated at: {pdf_filename.resolve()}")


# Check if script is executed directly from CLI
if __name__ == "__main__":
    # Run Single-Line Diagram generation function
    generate_sample_sld()