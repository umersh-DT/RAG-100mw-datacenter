# Import os module for file and directory navigation
import os
# Import json module to serialize processed chunk outputs
import json
# Import yaml module to read central pipeline settings
import yaml
# Import Path from pathlib for safe cross-platform file path handling
from pathlib import Path
# Import pypdf to extract raw text and page counts from generated PDFs
from pypdf import PdfReader

# Define local path variable pointing to central YAML configuration
CONFIG_PATH = Path("config/pipeline_config.yaml")

# Verify configuration file exists before proceeding
if not CONFIG_PATH.exists():
    # Raise descriptive FileNotFoundError if config path is broken
    raise FileNotFoundError(f"Configuration file not found at {CONFIG_PATH.resolve()}")

# Open central configuration YAML file in read mode
with open(CONFIG_PATH, "r") as f:
    # Parse YAML contents into a Python dictionary
    config = yaml.safe_load(f)

# Resolve path for raw data directory containing all generated subfolders
RAW_DATA_DIR = Path(config["paths"]["raw_data_dir"])
# Resolve target output path for processed chunks JSON file
PROCESSED_CHUNKS_FILE = Path(config["ingestion"]["processed_chunks_file"])
# Ensure the parent directory for processed chunks exists
PROCESSED_CHUNKS_FILE.parent.mkdir(parents=True, exist_ok=True)


def extract_metadata_from_filename(filename):
    """Infers document type, department, and tax year metadata based on file naming conventions."""
    # Convert filename string to lowercase for standardized matching
    fname = filename.lower()
    
    # Initialize default metadata payload
    meta = {
        "document_type": "Unknown",
        "department": "General",
        "tax_year": 2025
    }
    
    # Check if file is a Power Purchase Agreement
    if "ppa" in fname:
        meta["document_type"] = "Power Purchase Agreement"
        meta["department"] = "Legal & Compliance"
    # Check if file is an invoice or billing document
    elif "inv" in fname or "invoice" in fname:
        meta["document_type"] = "TOU Power Invoice"
        meta["department"] = "Financial Operations"
    # Check if file is a Single Line Diagram CAD drawing
    elif "sld" in fname:
        meta["document_type"] = "Single Line Diagram"
        meta["department"] = "Electrical Infrastructure"
        
    # Return extracted metadata dictionary
    return meta


def chunk_text(text, chunk_size=500, overlap=50):
    """Splits a long string into overlapping character chunks to preserve local semantic context."""
    # Initialize empty list to hold chunk strings
    chunks = []
    # Set starting character index pointer to 0
    start = 0
    # Store total character length of input text string
    text_len = len(text)
    
    # Loop until starting index exceeds overall text length
    while start < text_len:
        # Calculate ending character index for current chunk
        end = start + chunk_size
        # Slice substring from start to end index
        chunk = text[start:end]
        # Append sliced chunk to output list
        chunks.append(chunk)
        # Advance starting pointer by chunk_size minus overlap
        start += (chunk_size - overlap)
        
    # Return list of string chunks
    return chunks


def parse_all_documents():
    """Iterates through data/raw/, parses PDFs page-by-page, attaches metadata, and writes chunks.json."""
    # Initialize empty list to hold structured chunk dictionaries
    all_chunks = []
    # Counter for assigning globally unique chunk IDs
    chunk_counter = 0
    
    # Recursively find all PDF files inside the raw data directory
    pdf_files = list(RAW_DATA_DIR.rglob("*.pdf"))
    
    # Loop over every discovered PDF file
    for pdf_path in pdf_files:
        # Extract filename string from Path object
        filename = pdf_path.name
        # Extract metadata attributes based on file naming patterns
        doc_metadata = extract_metadata_from_filename(filename)
        
        # Open PDF using PyPDF reader
        reader = PdfReader(str(pdf_path))
        
        # Iterate over pages using 1-based indexing for standard citations
        for page_num, page in enumerate(reader.pages, start=1):
            # Extract raw text content from page object
            page_text = page.extract_text()
            
            # Skip page if text extraction returns empty string
            if not page_text or not page_text.strip():
                continue
                
            # Split page text into overlapping chunks using config chunk size
            raw_chunks = chunk_text(
                page_text, 
                chunk_size=config["chunking"]["chunk_size"],
                overlap=config["chunking"]["chunk_overlap"]
            )
            
            # Loop over generated string chunks for current page
            for chunk_idx, chunk_content in enumerate(raw_chunks):
                # Increment global chunk counter
                chunk_counter += 1
                
                # Construct structured chunk payload object
                chunk_record = {
                    "chunk_id": f"CHUNK_{chunk_counter:04d}",
                    "text": chunk_content.strip(),
                    "metadata": {
                        "source_file": filename,
                        "page_number": page_num,
                        "chunk_index": chunk_idx,
                        "document_type": doc_metadata["document_type"],
                        "department": doc_metadata["department"],
                        "tax_year": doc_metadata["tax_year"]
                    }
                }
                
                # Append structured chunk record to output list
                all_chunks.append(chunk_record)
                
    # Open target processed output file in write mode with UTF-8 encoding
    with open(PROCESSED_CHUNKS_FILE, "w", encoding="utf-8") as f:
        # Dump list of structured chunk records into formatted JSON
        json.dump(all_chunks, f, indent=2)
        
    # Print execution success log to terminal
    print(f"[SUCCESS] Parsed {len(pdf_files)} PDFs into {len(all_chunks)} chunks at: {PROCESSED_CHUNKS_FILE.resolve()}")


# Check if script is run directly from CLI
if __name__ == "__main__":
    # Execute document parsing pipeline
    parse_all_documents()