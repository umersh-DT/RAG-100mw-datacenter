# Import sys and Path to ensure root project imports resolve cleanly
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[2]))

import json
import pickle
import yaml
import chromadb
from chromadb.config import Settings
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

# Define local path variable pointing to central YAML configuration
CONFIG_PATH = Path("config/pipeline_config.yaml")

if not CONFIG_PATH.exists():
    raise FileNotFoundError(f"Configuration file missing at {CONFIG_PATH.resolve()}")

with open(CONFIG_PATH, "r") as f:
    config = yaml.safe_load(f)

# Resolve path references
PROCESSED_DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "processed" / "chunks.json"
CHROMA_DB_DIR = Path(__file__).resolve().parents[2] / config["indexing"]["vector_db_dir"]
BM25_INDEX_FILE = Path(__file__).resolve().parents[2] / config["indexing"]["bm25_index_file"]

CHROMA_DB_DIR.mkdir(parents=True, exist_ok=True)
BM25_INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)

MODEL_NAME = config["indexing"].get("embedding_model", "all-MiniLM-L6-v2")
BATCH_SIZE = 64


def build_vector_and_keyword_indices():
    """Generates batched ChromaDB vector embeddings and BM25 sparse index."""
    if not PROCESSED_DATA_FILE.exists():
        raise FileNotFoundError(f"Processed chunks not found at {PROCESSED_DATA_FILE.resolve()}")

    with open(PROCESSED_DATA_FILE, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    if not chunks:
        print("[WARNING] No chunks found in JSON payload.")
        return

    print(f"[INFO] Loaded {len(chunks)} chunks for indexing.")
    print(f"[INFO] Loading embedding model: {MODEL_NAME}...")
    embedder = SentenceTransformer(MODEL_NAME)

    # 1. Build ChromaDB Dense Vector Index in Batches
    print(f"[INFO] Initializing ChromaDB persistent storage at {CHROMA_DB_DIR.resolve()}...")
    chroma_client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))
    
    # Reset collection if present
    try:
        chroma_client.delete_collection("datacenter_docs")
    except Exception:
        pass

    collection = chroma_client.create_collection(
        name="datacenter_docs",
        metadata={"hnsw:space": "cosine"}
    )

    print(f"[INFO] Generating dense embeddings in batches of {BATCH_SIZE}...")
    for i in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[i : i + BATCH_SIZE]
        batch_texts = [c["text"] for c in batch]
        batch_ids = [c["chunk_id"] for c in batch]
        batch_meta = [c["metadata"] for c in batch]

        # Generate vectors
        batch_embeddings = embedder.encode(batch_texts, show_progress_bar=False).tolist()

        # Add to Chroma collection
        collection.add(
            ids=batch_ids,
            embeddings=batch_embeddings,
            metadatas=batch_meta,
            documents=batch_texts
        )
        print(f"  --> Indexed batch {i // BATCH_SIZE + 1}/{(len(chunks) + BATCH_SIZE - 1) // BATCH_SIZE} ({len(batch)} vectors)")

    print(f"[SUCCESS] Dense Vector Index built with {collection.count()} vectors.")

    # 2. Build BM25 Sparse Keyword Index
    print(f"[INFO] Tokenizing corpus for BM25 sparse index...")
    corpus = [c["text"].lower().split() for c in chunks]
    bm25 = BM25Okapi(corpus)

    # Payload matching both chunk references and ID arrays
    bm25_payload = {
        "bm25_model": bm25,
        "chunks": chunks,
        "chunk_ids": [c["chunk_id"] for c in chunks]
    }

    with open(BM25_INDEX_FILE, "wb") as f:
        pickle.dump(bm25_payload, f)

    print(f"[SUCCESS] BM25 Sparse Keyword Index built at {BM25_INDEX_FILE.resolve()}")


if __name__ == "__main__":
    build_vector_and_keyword_indices()