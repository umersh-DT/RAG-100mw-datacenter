# Import os module for system path manipulation
import os
# Import json module to display retrieved results neatly
import json
# Import pickle module to deserialize the BM25 index artifact
import pickle
# Import yaml module to read central pipeline settings
import yaml
# Import Path from pathlib for safe cross-platform file path handling
from pathlib import Path
# Import ChromaDB client to query persistent vector storage
import chromadb
# Import SentenceTransformer and CrossEncoder for dense search and reranking
from sentence_transformers import SentenceTransformer, CrossEncoder

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

# Resolve path for ChromaDB storage directory
VECTOR_DB_DIR = Path(config["indexing"]["vector_db_dir"])
# Resolve path for serialized BM25 index file
BM25_INDEX_FILE = Path(config["indexing"]["bm25_index_file"])


class HybridRetriever:
    """Combines Dense Vector Search (ChromaDB), Sparse Search (BM25), and Cross-Encoder Reranking."""
    
    def __init__(self):
        """Initializes ChromaDB connection, BM25 model, dense embedder, and cross-encoder reranker."""
        # Print status log during retriever engine initialization
        print("[INFO] Initializing Hybrid Retriever engine...")
        
        # Load local dense embedding model for query encoding
        self.embedder = SentenceTransformer(config["indexing"]["embedding_model"])
        
        # Initialize persistent ChromaDB client
        self.chroma_client = chromadb.PersistentClient(path=str(VECTOR_DB_DIR))
        # Retrieve target document collection from ChromaDB
        self.collection = self.chroma_client.get_collection(name="datacenter_docs")
        
        # Open and deserialize BM25 index payload from pickle file
        with open(BM25_INDEX_FILE, "rb") as f:
            bm25_data = pickle.load(f)
            # Extract BM25 model object
            self.bm25 = bm25_data["bm25_model"]
            # Extract list of ordered chunk IDs
            self.bm25_chunk_ids = bm25_data["chunk_ids"]
            # Extract full lookup dictionary mapping IDs to chunk records
            self.chunks_lookup = bm25_data["chunks_lookup"]
            
        # Initialize Cross-Encoder model for precision reranking
        print(f"[INFO] Loading reranker model: {config['retrieval']['reranker_model']}...")
        self.reranker = CrossEncoder(config["retrieval"]["reranker_model"])

    def dense_search(self, query, top_k=5, metadata_filter=None):
        """Executes semantic vector search in ChromaDB with optional metadata payload filtering."""
        # Generate dense vector embedding for user query string
        query_embedding = self.embedder.encode(query).tolist()
        
        # Build ChromaDB query arguments
        query_args = {
            "query_embeddings": [query_embedding],
            "n_results": top_k
        }
        
        # Attach metadata filter dict if provided
        if metadata_filter:
            query_args["where"] = metadata_filter
            
        # Execute query against ChromaDB collection
        results = self.collection.query(**query_args)
        
        # Extract list of retrieved chunk IDs from response
        retrieved_ids = results["ids"][0] if results["ids"] else []
        # Return list of corresponding chunk record dictionaries
        return [self.chunks_lookup[cid] for cid in retrieved_ids if cid in self.chunks_lookup]

    def sparse_search(self, query, top_k=5):
        """Executes BM25 keyword matching against tokenized corpus."""
        # Tokenize user query string into lowercase words
        tokenized_query = query.lower().split()
        # Calculate BM25 relevance scores for query across all indexed chunks
        scores = self.bm25.get_scores(tokenized_query)
        
        # Pair each chunk ID with its corresponding BM25 score
        scored_ids = list(zip(self.bm25_chunk_ids, scores))
        # Sort scored chunks in descending order of BM25 relevance
        scored_ids.sort(key=lambda x: x[1], reverse=True)
        
        # Slice top-k highest scoring chunk IDs
        top_ids = [cid for cid, score in scored_ids[:top_k] if score > 0]
        # Return list of corresponding chunk record dictionaries
        return [self.chunks_lookup[cid] for cid in top_ids if cid in self.chunks_lookup]

    def hybrid_search(self, query, metadata_filter=None):
        """Executes hybrid retrieval, deduplicates candidates, and reranks using Cross-Encoder."""
        # Execute dense vector search using configured top_k_vector depth
        dense_results = self.dense_search(
            query, 
            top_k=config["retrieval"]["top_k_vector"], 
            metadata_filter=metadata_filter
        )
        
        # Execute sparse BM25 search using configured top_k_bm25 depth
        sparse_results = self.sparse_search(
            query, 
            top_k=config["retrieval"]["top_k_bm25"]
        )
        
        # Combine dense and sparse candidate chunks into a single list
        combined_candidates = dense_results + sparse_results
        
        # Deduplicate candidates using unique chunk_id as key
        deduped_lookup = {item["chunk_id"]: item for item in combined_candidates}
        unique_candidates = list(deduped_lookup.values())
        
        # If no candidates found, return empty list early
        if not unique_candidates:
            return []
            
        # Construct sentence pairs list for Cross-Encoder scoring: [ (query, chunk_text), ... ]
        pair_inputs = [(query, item["text"]) for item in unique_candidates]
        
        # Compute joint relevance scores using Cross-Encoder model
        rerank_scores = self.reranker.predict(pair_inputs)
        
        # Attach computed rerank scores to candidate dictionaries
        for idx, item in enumerate(unique_candidates):
            item["rerank_score"] = float(rerank_scores[idx])
            
        # Sort candidates in descending order based on Cross-Encoder score
        unique_candidates.sort(key=lambda x: x["rerank_score"], reverse=True)
        
        # Slice final top_k_final chunks for LLM context window
        final_top_k = config["retrieval"]["top_k_final"]
        return unique_candidates[:final_top_k]


# Check if script is run directly from CLI for verification
if __name__ == "__main__":
    # Instantiate hybrid retriever engine
    retriever = HybridRetriever()
    
    # Test sample query
    test_query = "What is the capacity rating and relay for XFRM-01?"
    print(f"\n[TEST QUERY] '{test_query}'")
    
    # Run hybrid retrieval pipeline
    top_chunks = retriever.hybrid_search(test_query)
    
    # Print retrieved and reranked candidate chunks
    print(f"\n[RETRIEVED {len(top_chunks)} RERANKED CHUNKS]:")
    for rank, chunk in enumerate(top_chunks, start=1):
        print(f"\n--- Rank {rank} | Rerank Score: {chunk['rerank_score']:.4f} ---")
        print(f"Source File: {chunk['metadata']['source_file']} (Page {chunk['metadata']['page_number']})")
        print(f"Text Snippet: {chunk['text'][:180]}...")