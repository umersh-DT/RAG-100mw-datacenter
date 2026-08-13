import sys
from pathlib import Path
import json
import yaml
from pypdf import PdfReader

# Resolve project root dynamically (RAG-100mw-datacenter)
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Define paths relative to ROOT_DIR
CONFIG_PATH = ROOT_DIR / "config" / "pipeline_config.yaml"
RAW_DATA_DIR = ROOT_DIR / "data" / "raw"
PROCESSED_DATA_FILE = ROOT_DIR / "data" / "processed" / "chunks.json"

# Verify configuration file exists
if not CONFIG_PATH.exists():
    raise FileNotFoundError(f"Configuration file not found at {CONFIG_PATH.resolve()}")

# Load central pipeline configuration
with open(CONFIG_PATH, "r") as f:
    config = yaml.safe_load(f)

PROCESSED_DATA_FILE.parent.mkdir(parents=True, exist_ok=True)

# Pull chunking configuration values from pipeline_config.yaml
CHUNK_SIZE = config["indexing"].get("chunk_size", 700)
CHUNK_OVERLAP = config["indexing"].get("chunk_overlap", 150)


def split_text_into_chunks(text: str, chunk_size: int, chunk_overlap: int) -> list:
    """Splits a body of text into overlapping character windows."""
    chunks = []
    start = 0
    text_length = len(text)
    
    while start < text_length:
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        # Advance the sliding window by chunk_size minus overlap
        start += (chunk_size - chunk_overlap)
        
    return chunks


def infer_document_type(source_file: str) -> str:
    """Dynamically categorizes document types based on file naming patterns."""
    source_upper = source_file.upper()
    if "SLD" in source_upper or "ENGINEERING" in source_upper:
        return "Single Line Diagram"
    elif "INV" in source_upper or "INVOICE" in source_upper:
        return "TOU Power Invoice"
    elif "PPA" in source_upper or "CONTRACT" in source_upper:
        return "Power Purchase Agreement"
    return "General Infrastructure Record"


def parse_and_chunk_documents():
    """Parses raw PDF files recursively, extracts text/metadata, and generates chunk records."""
    all_chunks = []
    
    # Recursively locate all PDF files across subfolders in data/raw/
    pdf_files = list(RAW_DATA_DIR.rglob("*.pdf"))
    if not pdf_files:
        print(f"[WARNING] No PDF files found in {RAW_DATA_DIR.resolve()}")
        return

    print(f"[INFO] Processing {len(pdf_files)} PDFs across subdirectories...")
    print(f"[INFO] Chunking Settings: Size={CHUNK_SIZE} chars, Overlap={CHUNK_OVERLAP} chars.")

    processed_pages = 0

    for idx, pdf_path in enumerate(pdf_files, start=1):
        try:
            reader = PdfReader(pdf_path)
            source_file = pdf_path.name
            doc_type = infer_document_type(source_file)

            for page_idx, page in enumerate(reader.pages, start=1):
                processed_pages += 1
                text = page.extract_text()
                if not text or not text.strip():
                    continue

                # Split page text into sliding character chunks
                page_chunks = split_text_into_chunks(text, CHUNK_SIZE, CHUNK_OVERLAP)

                for chunk_idx, chunk_text in enumerate(page_chunks):
                    chunk_id = f"{pdf_path.stem}_p{page_idx}_c{chunk_idx}"
                    
                    metadata = {
                        "source_file": source_file,
                        "page_number": page_idx,
                        "document_type": doc_type,
                        "folder_category": pdf_path.parent.name
                    }

                    all_chunks.append({
                        "chunk_id": chunk_id,
                        "text": chunk_text,
                        "metadata": metadata
                    })

            # Print batch ingestion status every 10 files
            if idx % 10 == 0 or idx == len(pdf_files):
                print(f"  --> Progress: Processed {idx}/{len(pdf_files)} files ({len(all_chunks)} chunks generated)")

        except Exception as e:
            print(f"[ERROR] Failed to process {pdf_path.name}: {str(e)}")

    # Write output to processed chunks file
    with open(PROCESSED_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, indent=2)

    print(f"\n[SUCCESS] Ingestion Complete!")
    print(f"  * Total PDFs Processed: {len(pdf_files)}")
    print(f"  * Total Pages Extracted: {processed_pages}")
    print(f"  * Total Chunks Generated: {len(all_chunks)}")
    print(f"  * Payload Saved To: {PROCESSED_DATA_FILE.resolve()}")


if __name__ == "__main__":
    parse_and_chunk_documents()