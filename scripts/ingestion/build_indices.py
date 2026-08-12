# Import os module for operating system level path handling
import os
# Import json module to read processed chunk payloads
import json
# Import pickle module to serialize the sparse BM25 index to disk
import pickle
# Import yaml module to parse central pipeline configurations
import yaml
# Import Path from pathlib for safe cross-platform file path handling
from pathlib import Path
# Import ChromaDB client for local persistent vector store management
import chromadb
# Import SentenceTransformer to generate dense vector embeddings locally
from sentence_transformers import SentenceTransformer
# Import BM25Okapi for sparse keyword-matching indexing
from rank_bm25 import BM25Okapi

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

# Resolve path for processed chunks input JSON file
CHUNKS_FILE = Path(config["ingestion"]["processed_chunks_file"])
# Resolve target path for persistent ChromaDB storage directory
VECTOR_DB_DIR = Path(config["indexing"]["vector_db_dir"])
# Resolve target path for serialized BM25 index output file
BM25_INDEX_FILE = Path(config["indexing"]["bm25_index_file"])

# Ensure output directory exists on disk before building indices
VECTOR_DB_DIR.parent.mkdir(parents=True, exist_ok=True)


def build_dual_indices():
    """Loads chunks.json and builds both a ChromaDB vector store and a BM25 sparse index."""
    # Check if input chunks file exists before proceeding
    if not CHUNKS_FILE.exists():
        # Raise error if chunks.json has not been generated yet
        raise FileNotFoundError(f"Processed chunks file missing at {CHUNKS_FILE.resolve()}. Run parse_documents.py first.")
        
    # Open and load processed chunks JSON file
    with open(CHUNKS_FILE, "r", encoding="utf-8") as f:
        # Load JSON array into a list of chunk record dictionaries
        chunks_data = json.load(f)
        
    # Print progress status for chunk loading
    print(f"[INFO] Loaded {len(chunks_data)} chunks for indexing.")
    
    # ---------------------------------------------------------
    # 1. BUILD DENSE VECTOR INDEX (ChromaDB + SentenceTransformers)
    # ---------------------------------------------------------
    # Print status log for embedding model initialization
    print(f"[INFO] Loading embedding model: {config['indexing']['embedding_model']}...")
    # Initialize local sentence-transformer embedding model
    embedder = SentenceTransformer(config["indexing"]["embedding_model"])
    
    # Instantiate persistent ChromaDB client pointing to target output directory
    chroma_client = chromadb.PersistentClient(path=str(VECTOR_DB_DIR))
    # Get or create a dedicated collection for data center document chunks
    collection = chroma_client.get_or_create_collection(name="datacenter_docs")
    
    # Extract text strings from chunk records for vector embedding generation
    chunk_texts = [item["text"] for item in chunks_data]
    # Extract unique chunk IDs for ChromaDB tracking
    chunk_ids = [item["chunk_id"] for item in chunks_data]
    # Extract metadata payload dictionaries for ChromaDB metadata filtering
    chunk_metadatas = [item["metadata"] for item in chunks_data]
    
    # Generate dense vector embeddings for all chunk texts
    embeddings = embedder.encode(chunk_texts, show_progress_bar=False).tolist()
    
    # Upsert chunk records, embeddings, and metadata into ChromaDB collection
    collection.add(
        ids=chunk_ids,
        embeddings=embeddings,
        documents=chunk_texts,
        metadatas=chunk_metadatas
    )
    # Print completion log for vector store building
    print(f"[SUCCESS] ChromaDB dense vector index built with {collection.count()} vectors at: {VECTOR_DB_DIR.resolve()}")
    
    # ---------------------------------------------------------
    # 2. BUILD SPARSE KEYWORD INDEX (BM25)
    # ---------------------------------------------------------
    # Tokenize chunk text strings by splitting into lowercase words for BM25
    tokenized_corpus = [text.lower().split() for text in chunk_texts]
    # Initialize BM25Okapi sparse index with tokenized corpus
    bm25 = BM25Okapi(tokenized_corpus)
    
    # Structure full BM25 artifact containing index model and mapped chunk IDs
    bm25_payload = {
        "bm25_model": bm25,
        "chunk_ids": chunk_ids,
        "chunks_lookup": {item["chunk_id"]: item for item in chunks_data}
    }
    
    # Open BM25 output file in write-binary mode
    with open(BM25_INDEX_FILE, "wb") as f:
        # Pickle and serialize BM25 payload to disk
        pickle.dump(bm25_payload, f)
        
    # Print completion log for sparse index building
    print(f"[SUCCESS] BM25 sparse keyword index built at: {BM25_INDEX_FILE.resolve()}")


# Check if script is executed directly from CLI
if __name__ == "__main__":
    # Execute dual indexing pipeline
    build_dual_indices()