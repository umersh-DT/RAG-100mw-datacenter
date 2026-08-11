# Import os module for operating system file operations
import os
# Import yaml module to parse central pipeline configurations
import yaml
# Import Path from pathlib for safe cross-platform folder paths
from pathlib import Path
# Import letter page size specification from ReportLab
from reportlab.lib.pagesizes import letter
# Import ReportLab flowables for rendering structured PDFs
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
# Import default ReportLab styles container
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
# Import colors module for custom table palette rendering
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

# Resolve target destination path for financial and regulatory raw data
OUTPUT_DIR = Path(config["paths"]["financial_regulatory_dir"])
# Ensure target output directory exists on disk
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# Define function to generate a multi-table Time-Of-Use (TOU) power invoice
def generate_sample_invoice():
    """Generates a detailed synthetic TOU Power Invoice PDF with line items and metadata."""
    # Define full file path for output invoice PDF
    pdf_filename = OUTPUT_DIR / "INV_2025_Q1_GridCo_100MW.pdf"
    
    # Instantiate SimpleDocTemplate with letter size and standard 0.75-inch margins
    doc = SimpleDocTemplate(
        str(pdf_filename),
        pagesize=letter,
        rightMargin=54, leftMargin=54, topMargin=54, bottomMargin=54
    )
    
    # Extract base styles container from ReportLab
    styles = getSampleStyleSheet()
    # Create custom ParagraphStyle for header title text
    title_style = ParagraphStyle('DocTitle', parent=styles['Heading1'], fontSize=16, leading=20, alignment=1)
    # Create custom ParagraphStyle for section headings
    heading_style = ParagraphStyle('SectionHeading', parent=styles['Heading2'], fontSize=12, leading=16, spaceBefore=10)
    # Create custom ParagraphStyle for normal body text
    body_style = ParagraphStyle('Body', parent=styles['Normal'], fontSize=10, leading=14, spaceBefore=6)
    
    # Initialize empty list to collect PDF flowable objects
    story = []
    
    # Append top-level document title to story
    story.append(Paragraph("UTILITY BILLING & TIME-OF-USE (TOU) INVOICE", title_style))
    # Append invoice tracking reference code
    story.append(Paragraph("<b>Invoice Number:</b> INV-GRIDCO-2025-Q1-0882", body_style))
    # Add vertical spacing of 10 points
    story.append(Spacer(1, 10))
    
    # Define metadata summary block table data
    metadata_data = [
        ["Metadata Attribute", "Value"],
        ["Document Type", "TOU Power Invoice"],
        ["Billing Entity", "GridCo State Power Authority"],
        ["Customer Name", config["project"]["entity_name"]],
        ["Billing Period", "Jan 01, 2025 - Mar 31, 2025"],
        ["Tax Year", "2025"],
        ["Department", "Financial Operations"]
    ]
    
    # Initialize metadata summary table with explicit column widths
    meta_table = Table(metadata_data, colWidths=[180, 320])
    # Apply visual styling rules to metadata table
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#2C3E50")), # Dark charcoal header background
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),          # White text for header block
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),             # Bold text styling for header row
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),                # Grey gridlines across all cells
        ('BACKGROUND', (0,1), (-1,-1), colors.HexColor("#ECF0F1")), # Off-white background for values
    ]))
    # Append metadata table to flowable story
    story.append(meta_table)
    # Add vertical gap of 15 points
    story.append(Spacer(1, 15))
    
    # Add section header for itemized billing calculations
    story.append(Paragraph("1. Time-Of-Use Consumption & Tariff Breakdown", heading_style))
    
    # Define line-item financial calculation table data
    line_items_data = [
        ["Tariff Tier / Demand Block", "Usage (kWh)", "Rate ($/kWh)", "Subtotal ($)"],
        ["Peak Demand (12:00 - 18:00)", "12,500,000", "$0.085", "$1,062,500.00"],
        ["Off-Peak Demand (22:00 - 06:00)", "25,000,000", "$0.042", "$1,050,000.00"],
        ["Shoulder Demand (06:00 - 12:00)", "18,000,000", "$0.058", "$1,044,000.00"],
        ["Transformer Step-Down Surcharge", "N/A", "Flat Fee", "$45,000.00"],
        ["Subtotal Power Supply Charges", "", "", "$3,201,500.00"],
        ["Applicable Government Energy Tax (5%)", "", "", "$160,075.00"],
        ["TOTAL AMOUNT DUE", "", "", "$3,361,575.00"]
    ]
    
    # Initialize line items table with balanced column widths
    items_table = Table(line_items_data, colWidths=[200, 100, 100, 100])
    # Apply specialized financial styling to line-item table
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#16A085")), # Teal header background
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),          # White text header
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),             # Bold font for header
        ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),           # Subtle light grey interior borders
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),           # Bold text for TOTAL row
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor("#FCF3CF")), # Light yellow background for TOTAL row
    ]))
    # Append line item billing table to story
    story.append(items_table)
    # Add vertical gap of 15 points
    story.append(Spacer(1, 15))
    
    # Add section header for payment instructions and penalties
    story.append(Paragraph("2. Payment Terms & Statutory Compliance", heading_style))
    # Append explanatory legal clause regarding interest rates and payment windows
    story.append(Paragraph(
        "Payment is due within thirty (30) calendar days of invoice date. Late payments are subject to a cumulative "
        "interest rate of 1.5% per month. Equipment tax exemptions applied under Special Economic Zone Duty Exemption "
        "Certificate SEZ-2024-99-DC.",
        body_style
    ))
    
    # Write and render physical PDF document to file path
    doc.build(story)
    # Print execution success log to terminal
    print(f"[SUCCESS] Sample Invoice generated at: {pdf_filename.resolve()}")


# Check if script is run directly from command line
if __name__ == "__main__":
    # Run invoice generation function
    generate_sample_invoice()