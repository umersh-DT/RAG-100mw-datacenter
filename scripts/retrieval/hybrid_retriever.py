# Import sys and Path to ensure root project imports resolve cleanly
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[2]))

import pickle
import yaml
import chromadb
from sentence_transformers import SentenceTransformer, CrossEncoder

# Define local path variable pointing to central YAML configuration
CONFIG_PATH = Path("config/pipeline_config.yaml")

if not CONFIG_PATH.exists():
    raise FileNotFoundError(f"Configuration file missing at {CONFIG_PATH.resolve()}")

with open(CONFIG_PATH, "r") as f:
    config = yaml.safe_load(f)

# Resolve path references
CHROMA_DB_DIR = Path(__file__).resolve().parents[2] / config["indexing"]["vector_db_dir"]
BM25_INDEX_FILE = Path(__file__).resolve().parents[2] / config["indexing"]["bm25_index_file"]

EMBEDDING_MODEL_NAME = config["indexing"].get("embedding_model", "all-MiniLM-L6-v2")
RERANKER_MODEL_NAME = config["retrieval"].get("reranker_model", "cross-encoder/ms-marco-MiniLM-L-6-v2")


class HybridRetriever:
    """Executes dense vector search, sparse keyword search, RRF fusion, and Cross-Encoder reranking."""

    def __init__(self):
        print("[INFO] Initializing Hybrid Retriever engine...")
        
        # Load Dense Vector Database
        self.chroma_client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))
        self.collection = self.chroma_client.get_collection(name="datacenter_docs")
        self.embedder = SentenceTransformer(EMBEDDING_MODEL_NAME)

        # Load Sparse BM25 Index
        if not BM25_INDEX_FILE.exists():
            raise FileNotFoundError(f"BM25 index missing at {BM25_INDEX_FILE.resolve()}")

        with open(BM25_INDEX_FILE, "rb") as f:
            bm25_payload = pickle.load(f)

        self.bm25 = bm25_payload["bm25_model"]
        self.chunks = bm25_payload.get("chunks", [])
        
        # Build lookup dictionary mapping chunk_id to chunk object
        self.chunk_map = {c["chunk_id"]: c for c in self.chunks}

        # Load Reranker Model
        print(f"[INFO] Loading Cross-Encoder reranker: {RERANKER_MODEL_NAME}...")
        self.reranker = CrossEncoder(RERANKER_MODEL_NAME)

    def dense_search(self, query: str, top_k: int = 10, metadata_filter: dict = None):
        """Performs semantic search via ChromaDB vector embeddings."""
        query_vector = self.embedder.encode(query).tolist()
        
        where_clause = None
        if metadata_filter and metadata_filter.get("document_type") and metadata_filter["document_type"] != "All":
            where_clause = {"document_type": metadata_filter["document_type"]}

        results = self.collection.query(
            query_embeddings=[query_vector],
            n_results=top_k,
            where=where_clause
        )

        dense_hits = []
        if results["ids"] and results["ids"][0]:
            for chunk_id, doc_text, meta in zip(results["ids"][0], results["documents"][0], results["metadatas"][0]):
                dense_hits.append({
                    "chunk_id": chunk_id,
                    "text": doc_text,
                    "metadata": meta
                })
        return dense_hits

    def sparse_search(self, query: str, top_k: int = 10):
        """Performs lexical search via BM25."""
        tokenized_query = query.lower().split()
        scores = self.bm25.get_scores(tokenized_query)
        
        # Get top indices
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        
        sparse_hits = []
        for idx in top_indices:
            if scores[idx] > 0:
                sparse_hits.append(self.chunks[idx])
        return sparse_hits

    def reciprocal_rank_fusion(self, dense_hits: list, sparse_hits: list, k: int = 60):
        """Merges vector and keyword hits using Reciprocal Rank Fusion (RRF)."""
        rrf_scores = {}

        for rank, hit in enumerate(dense_hits, start=1):
            cid = hit["chunk_id"]
            rrf_scores[cid] = rrf_scores.get(cid, 0) + (1.0 / (k + rank))

        for rank, hit in enumerate(sparse_hits, start=1):
            cid = hit["chunk_id"]
            rrf_scores[cid] = rrf_scores.get(cid, 0) + (1.0 / (k + rank))

        # Sort chunk IDs by fused score
        sorted_cids = sorted(rrf_scores.keys(), key=lambda cid: rrf_scores[cid], reverse=True)
        return [self.chunk_map[cid] for cid in sorted_cids if cid in self.chunk_map]

    def hybrid_search(self, query: str, top_k: int = 3, metadata_filter: dict = None):
        """Executes full hybrid search pipeline: Dense + Sparse -> RRF -> Cross-Encoder Rerank."""
        dense_hits = self.dense_search(query, top_k=10, metadata_filter=metadata_filter)
        sparse_hits = self.sparse_search(query, top_k=10)

        fused_candidates = self.reciprocal_rank_fusion(dense_hits, sparse_hits)

        if not fused_candidates:
            return []

        # Rerank candidates using Cross-Encoder
        pairs = [[query, candidate["text"]] for candidate in fused_candidates]
        scores = self.reranker.predict(pairs)

        for candidate, score in zip(fused_candidates, scores):
            candidate["rerank_score"] = float(score)

        # Sort candidates by reranker score
        reranked_hits = sorted(fused_candidates, key=lambda x: x["rerank_score"], reverse=True)
        return reranked_hits[:top_k]


if __name__ == "__main__":
    retriever = HybridRetriever()
    hits = retriever.hybrid_search("how many 50MVA transformer we are using")
    print(f"\n[SUCCESS] Retrieved {len(hits)} reranked chunks:")
    for h in hits:
        print(f" - {h['chunk_id']} (Score: {h['rerank_score']:.4f})")