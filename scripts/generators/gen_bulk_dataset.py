# Import sys and Path to ensure root project imports resolve cleanly
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[2]))

import random
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

# Root raw data directory
RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"

# Target subdirectories
FOLDERS = {
    "legal": RAW_DIR / "01_commercial_legal",
    "financial": RAW_DIR / "02_financial_regulatory",
    "communications": RAW_DIR / "03_communications",
    "engineering": RAW_DIR / "04_engineering_drawings"
}

for folder in FOLDERS.values():
    folder.mkdir(parents=True, exist_ok=True)

styles = getSampleStyleSheet()
title_style = styles["Heading1"]
body_style = styles["BodyText"]


def create_legal_pdf(filename, file_id):
    doc = SimpleDocTemplate(str(filename), pagesize=letter)
    facility_name = f"HyperScale Sub-Station {chr(65 + (file_id % 26))}"
    tariff = 0.040 + (file_id * 0.002)
    max_curtailment = 20 + (file_id * 5)
    
    story = [
        Paragraph(f"POWER PURCHASE AGREEMENT - FACILITY {file_id:03d}", title_style),
        Spacer(1, 12),
        Paragraph(f"Contract Reference ID: PPA-2025-FAC-{file_id:03d}", body_style),
        Paragraph(f"Primary Operating Entity: {facility_name}", body_style),
        Spacer(1, 12),
    ]
    for page in range(1, 6):
        story.append(Paragraph(f"Section {page}: Commercial Terms & Tariff Structures", styles["Heading2"]))
        story.append(Paragraph(
            f"The agreed base electricity tariff for {facility_name} is strictly locked at "
            f"<b>${tariff:.3f} per kWh</b> for operating year 2025. "
            f"GridCo State Power Authority reserves forced curtailment rights capped at "
            f"<b>{max_curtailment} cumulative hours</b> per calendar year under emergency frequency drift below 49.5 Hz.", 
            body_style
        ))
        story.append(Spacer(1, 12))
    doc.build(story)


def create_financial_pdf(filename, file_id):
    doc = SimpleDocTemplate(str(filename), pagesize=letter)
    invoice_num = f"INV-2025-Q{(file_id % 4) + 1}-{file_id:04d}"
    tax_rate = 5.0 + (file_id * 0.1)
    
    story = [
        Paragraph(f"UTILITY TOU INVOICE #{invoice_num}", title_style),
        Spacer(1, 12),
        Paragraph(f"Billing Account: HyperScale Facility Zone {file_id}", body_style),
        Spacer(1, 12)
    ]
    
    table_data = [["Demand Block / Tier", "Usage (kWh)", "Rate ($/kWh)", "Subtotal ($)"]]
    base_usage = 8000000 + (file_id * 300000)
    
    for i in range(1, 6):
        usage = base_usage + (i * 100000)
        rate = 0.035 + (i * 0.008) + (file_id * 0.001)
        table_data.append([f"Tier {i} Demand Block", f"{usage:,}", f"${rate:.3f}", f"${usage*rate:,.2f}"])
        
    t = Table(table_data)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1f2937")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
    ]))
    story.append(t)
    story.append(Spacer(1, 12))
    story.append(Paragraph(f"Applicable Statutory Government Energy Tax: <b>{tax_rate:.1f}%</b>", body_style))
    doc.build(story)


def create_engineering_pdf(filename, file_id):
    doc = SimpleDocTemplate(str(filename), pagesize=letter)
    station_tag = f"SUBSTATION-{file_id:02d}"
    # Vary the transformer count dynamically (1 to 4 transformers per facility)
    xfrm_count = (file_id % 4) + 1
    mva_rating = 25 + ((file_id % 3) * 25)  # 25 MVA, 50 MVA, or 75 MVA
    
    story = [
        Paragraph(f"SINGLE-LINE DIAGRAM SCHEDULE - {station_tag}", title_style),
        Spacer(1, 12),
        Paragraph(f"Drawing Reference: E-SLD-{file_id:03d}-REV1 | Facility: Zone {file_id}", body_style),
        Spacer(1, 12)
    ]
    
    table_data = [["Equipment Tag", "Description / Function", "Rating / Capacity", "Protection Relay"]]
    
    for x in range(1, xfrm_count + 1):
        table_data.append([
            f"XFRM-{x:02d}", 
            f"Step-Down Power Transformer Unit {x}", 
            f"{mva_rating} MVA, 132kV/33kV", 
            f"SEL-787 Differential"
        ])
        
    for cb in range(1, xfrm_count * 2 + 1):
        table_data.append([
            f"CB-132-{chr(65 + cb)}1", 
            f"SF6 Main Circuit Breaker {cb}", 
            f"{1500 + (cb*200)}A Continuous", 
            f"SEL-751 Overcurrent"
        ])
        
    t = Table(table_data)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#0f172a")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
    ]))
    story.append(t)
    story.append(Spacer(1, 12))
    story.append(Paragraph(f"Total Operational Transformer Count for {station_tag}: <b>{xfrm_count} units</b> rated at <b>{mva_rating} MVA</b>.", body_style))
    doc.build(story)


def generate_all_bulk_docs(count=15):
    print(f"[INFO] Generating {count * 3} multi-page UNIQUE synthetic PDFs...")
    for i in range(1, count + 1):
        create_legal_pdf(FOLDERS["legal"] / f"PPA_Contract_Bulk_{i:03d}.pdf", i)
        create_financial_pdf(FOLDERS["financial"] / f"Invoice_Bulk_{i:03d}.pdf", i)
        create_engineering_pdf(FOLDERS["engineering"] / f"SLD_Engineering_Bulk_{i:03d}.pdf", i)
    print(f"[SUCCESS] Generated unique synthetic PDFs inside {RAW_DIR.resolve()}")


if __name__ == "__main__":
    generate_all_bulk_docs(count=15)