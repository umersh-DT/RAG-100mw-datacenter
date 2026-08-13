# Import sys and Path to ensure root project imports resolve cleanly
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[2]))

import os
import yaml
from google import genai

# Import Hybrid Retriever engine
from scripts.retrieval.hybrid_retriever import HybridRetriever

# Define local path variable pointing to central YAML configuration
CONFIG_PATH = Path("config/pipeline_config.yaml")

if not CONFIG_PATH.exists():
    raise FileNotFoundError(f"Configuration file not found at {CONFIG_PATH.resolve()}")

with open(CONFIG_PATH, "r") as f:
    config = yaml.safe_load(f)


class GroundedQAGenerator:
    """Retrieves context chunks and synthesizes direct grounded answers using Google Gemini."""

    def __init__(self):
        """Initializes the hybrid retriever and Google GenAI client with explicit API key routing."""
        print("[INFO] Initializing Grounded QA Generator engine (Gemini)...")
        self.retriever = HybridRetriever()
        
        # Explicitly pull GEMINI_API_KEY from environment to prevent GOOGLE_API_KEY override
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError(
                "Gemini API key not found. Please set $env:GEMINI_API_KEY in your terminal."
            )
            
        # Initialize Google GenAI client with explicit API key
        self.client = genai.Client(api_key=api_key)
        # Using active Gemini Flash model endpoint
        self.model_name = "gemini-2.5-flash"

    def generate_answer(self, query: str, metadata_filter: dict = None):
        """Retrieves context chunks and generates a direct response using Gemini."""
        # Step 1: Execute hybrid search + reranking
        retrieved_chunks = self.retriever.hybrid_search(query, metadata_filter=metadata_filter)
        
        if not retrieved_chunks:
            return "No relevant information found in the indexed documents to answer this query.", []

        # Step 2: Format context text
        context_blocks = []
        for idx, chunk in enumerate(retrieved_chunks, start=1):
            source = chunk["metadata"]["source_file"]
            page = chunk["metadata"]["page_number"]
            context_blocks.append(f"--- CONTEXT CHUNK {idx} (Source: {source}, Page {page}) ---\n{chunk['text'].strip()}")
            
        context_str = "\n\n".join(context_blocks)

        # Step 3: Construct Prompt
        prompt = (
            "You are an expert infrastructure analyst for a 100MW data center.\n"
            "Answer the user's question directly, accurately, and concisely (1 to 3 sentences max) "
            "using ONLY the provided context documents.\n\n"
            f"Context Documents:\n{context_str}\n\n"
            f"User Question: {query}\n\n"
            "Direct Answer:"
        )

        # Step 4: Generate Direct Answer
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            grounded_answer = response.text.strip()
        except Exception as e:
            grounded_answer = f"[Gemini API Error: {str(e)}]"

        return grounded_answer, retrieved_chunks


if __name__ == "__main__":
    generator = GroundedQAGenerator()
    test_query = "how many 50MVA transformer we are using"
    answer, sources = generator.generate_answer(test_query)
    print("\n--- SYNTHESIZED GEMINI ANSWER ---")
    print(answer)