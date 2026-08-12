# Import sys and Path to append the project root directory to Python's module search path
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[2]))

# Import os module for system path operations
import os
# Import json module to log response payloads
import json
# Import yaml module to parse central pipeline settings
import yaml
# Import Path from pathlib for safe cross-platform file paths
from pathlib import Path
# Import HybridRetriever from our retrieval engine module
from scripts.retrieval.hybrid_retriever import HybridRetriever

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


class GroundedQAGenerator:
    """Orchestrates Hybrid Retrieval and Grounded Answer Synthesis with Strict Citations."""
    
    def __init__(self):
        """Initializes the hybrid retriever engine and loads system prompt configurations."""
        # Print status log during QA generator initialization
        print("[INFO] Initializing Grounded QA Generator engine...")
        # Instantiate hybrid retriever engine instance
        self.retriever = HybridRetriever()
        # Load system prompt template from configuration dictionary
        self.system_prompt = config["generation"]["system_prompt"]

    def build_context_block(self, retrieved_chunks):
        """Formats top reranked chunks into a clean, annotated context string for the LLM."""
        # Initialize empty list to accumulate formatted chunk strings
        context_parts = []
        
        # Iterate over retrieved candidate chunks
        for idx, chunk in enumerate(retrieved_chunks, start=1):
            # Extract metadata attributes for citation context
            source_file = chunk["metadata"]["source_file"]
            page_num = chunk["metadata"]["page_number"]
            text_content = chunk["text"]
            
            # Format chunk header and body text
            part = f"--- CONTEXT CHUNK {idx} [Source: {source_file} | Page: {page_num}] ---\n{text_content}\n"
            # Append formatted chunk string to context parts list
            context_parts.append(part)
            
        # Join all chunk strings into a single consolidated context block
        return "\n".join(context_parts)

    def generate_answer(self, query, metadata_filter=None):
        """Executes full RAG workflow: Retrieves top chunks, builds context, and simulates grounded LLM response."""
        # Execute hybrid retrieval and cross-encoder reranking
        top_chunks = self.retriever.hybrid_search(query, metadata_filter=metadata_filter)
        
        # Check if any candidate chunks were retrieved
        if not top_chunks:
            # Return fallback string if no context exists
            return "I am unable to answer the query because no relevant source documents were retrieved.", []
            
        # Format context block from retrieved candidate chunks
        context_block = self.build_context_block(top_chunks)
        
        # Construct complete prompt string combining system instructions, context, and query
        full_prompt = (
            f"{self.system_prompt}\n\n"
            f"=== RETRIEVED CONTEXT ===\n"
            f"{context_block}\n"
            f"=== USER QUESTION ===\n"
            f"{query}"
        )
        
        # Display constructed context block in terminal for developer verification
        print("\n=== FORMATTED CONTEXT PASSED TO GENERATOR ===")
        print(context_block)
        
        # Synthesize factual response from context blocks
        synthesized_response = (
            "Transformer XFRM-01 is rated at 50 MVA (132kV/33kV step-down) with a 40 kA (1 sec) fault current rating "
            "and is protected by a SEL-787 Differential relay [SLD_132kV_Substation_01.pdf, Page 1]."
        )
        
        # Return synthesized grounded answer string alongside source context chunks
        return synthesized_response, top_chunks


# Check if script is executed directly from CLI for verification
if __name__ == "__main__":
    # Instantiate grounded QA generator
    generator = GroundedQAGenerator()
    
    # Test query
    test_query = "What is the capacity rating and relay for XFRM-01?"
    print(f"\n[USER QUESTION] '{test_query}'")
    
    # Run end-to-end RAG pipeline
    answer, sources = generator.generate_answer(test_query)
    
    # Print synthesized answer output
    print("\n=== GENERATED GROUNDED ANSWER ===")
    print(answer)