# Import the os module for operating system level interactions
import os
# Import yaml to parse our central pipeline configuration file
import yaml
# Import Path from pathlib for clean, cross-platform file path handling
from pathlib import Path
# Import letter page size from ReportLab for standard PDF dimensions
from reportlab.lib.pagesizes import letter
# Import core document building block classes from ReportLab Platypus
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
# Import default stylesheet containers from ReportLab
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
# Import colors module for styling tables and text elements
from reportlab.lib import colors

# Define the path to our central pipeline YAML configuration file
CONFIG_PATH = Path("config/pipeline_config.yaml")

# Check if the configuration file exists at the specified path
if not CONFIG_PATH.exists():
    # Raise an error with the absolute path if the configuration file is missing
    raise FileNotFoundError(f"Configuration file not found at {CONFIG_PATH.resolve()}")

# Open the pipeline configuration file in read-only mode
with open(CONFIG_PATH, "r") as f:
    # Load and parse the YAML content into a Python dictionary
    config = yaml.safe_load(f)

# Resolve the target output directory for commercial and legal documents from config
OUTPUT_DIR = Path(config["paths"]["commercial_legal_dir"])
# Create the output directory and any necessary parent directories if they do not exist
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# Define a function to generate a sample Power Purchase Agreement PDF
def generate_sample_ppa():
    """Generates a sample 2-page Power Purchase Agreement PDF with embedded metadata."""
    # Define the output PDF file path inside the designated output folder
    pdf_filename = OUTPUT_DIR / "PPA_GridCo_100MW_2025.pdf"
    
    # Initialize the SimpleDocTemplate with page size and 0.75-inch (54 pt) margins
    doc = SimpleDocTemplate(
        str(pdf_filename),
        pagesize=letter,
        rightMargin=54, leftMargin=54, topMargin=54, bottomMargin=54
    )
    
    # Retrieve default sample style sheet from ReportLab
    styles = getSampleStyleSheet()
    # Define a custom paragraph style for the document title
    title_style = ParagraphStyle('DocTitle', parent=styles['Heading1'], fontSize=16, leading=20, alignment=1)
    # Define a custom paragraph style for section headings
    heading_style = ParagraphStyle('SectionHeading', parent=styles['Heading2'], fontSize=12, leading=16, spaceBefore=10)
    # Define a custom paragraph style for standard body text
    body_style = ParagraphStyle('Body', parent=styles['Normal'], fontSize=10, leading=14, spaceBefore=6)
    
    # Initialize an empty list to hold the document elements (story)
    story = []
    
    # Append the main title paragraph to the document story
    story.append(Paragraph("POWER PURCHASE AGREEMENT (PPA)", title_style))
    # Append the contract ID paragraph to the document story
    story.append(Paragraph("<b>Contract ID:</b> PPA-100MW-GRIDCO-2025-A1", body_style))
    # Add vertical spacing of 12 points below the title block
    story.append(Spacer(1, 12))
    
    # Define two-dimensional matrix holding document metadata attributes
    metadata_data = [
        ["Metadata Attribute", "Value"],
        ["Document Type", "Power Purchase Agreement"],
        ["Primary Entity", config["project"]["entity_name"]],
        ["Counterparty", "GridCo State Power Authority"],
        ["Contracted Capacity", "100 MW continuous supply"],
        ["Effective Year", "2025"],
        ["Department", "Legal & Compliance"]
    ]
    
    # Instantiate a Table flowable with explicitly defined column widths (200pt and 300pt)
    meta_table = Table(metadata_data, colWidths=[200, 300])
    # Apply visual styles to the table including background colors, grid lines, and fonts
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1A365D")), # Dark blue header background
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),          # White text color for headers
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),             # Bold font for headers
        ('BOTTOMPADDING', (0,0), (-1,0), 6),                       # Padding for header row
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),                # Grey border lines around cells
        ('BACKGROUND', (0,1), (-1,-1), colors.HexColor("#F7FAFC")), # Light grey background for data rows
    ]))
    # Append the styled metadata table to the document story
    story.append(meta_table)
    # Add vertical spacing of 18 points below the metadata table
    story.append(Spacer(1, 18))
    
    # Append Section 1 heading paragraph to the document story
    story.append(Paragraph("1. Commercial Terms & Capacity", heading_style))
    # Append Section 1 body clause text to the document story
    story.append(Paragraph(
        "This Power Purchase Agreement ('Agreement') is entered into as of January 15, 2025, by and between "
        "GridCo State Power Authority ('Seller') and HyperScale Infrastructure LLC ('Buyer'). Seller agrees to sell "
        "and deliver, and Buyer agrees to purchase, firm electric energy for the 100MW Data Center facility.",
        body_style
    ))
    
    # Append Section 2 heading paragraph to the document story
    story.append(Paragraph("2. Tariff Structure & Curtailment Clause", heading_style))
    # Append Section 2 body clause text to the document story
    story.append(Paragraph(
        "The base electricity tariff shall be locked at $0.058 per kWh for the first five (5) operating years. "
        "In the event of grid frequency drift below 49.8 Hz, Seller reserves the right to execute forced curtailment "
        "up to a maximum limit of 40 cumulative hours per calendar year without penalty.",
        body_style
    ))
    
    # Build the physical PDF document by writing all accumulated story flowables
    doc.build(story)
    # Print success confirmation message to console with absolute file path
    print(f"[SUCCESS] Sample PPA generated at: {pdf_filename.resolve()}")


# Check if the script is being executed directly from CLI
if __name__ == "__main__":
    # Call the sample PPA generation function
    generate_sample_ppa()