# Import sys and Path to ensure root project imports resolve cleanly
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[2]))

# Import standard library and web framework modules
import yaml
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

# Import Grounded QA Generator engine
from scripts.generation.qa_generator import GroundedQAGenerator

# Define local path variable pointing to central YAML configuration
CONFIG_PATH = Path("config/pipeline_config.yaml")

# Verify configuration file exists
if not CONFIG_PATH.exists():
    raise FileNotFoundError(f"Configuration file not found at {CONFIG_PATH.resolve()}")

# Load central pipeline configuration
with open(CONFIG_PATH, "r") as f:
    config = yaml.safe_load(f)

# Initialize FastAPI application instance
app = FastAPI(
    title=config["api"]["title"],
    version=config["api"]["version"],
    description="Enterprise Hybrid RAG API for 100MW Data Center Engineering & Legal Documents"
)

# Global holder for initialized engine instance
qa_engine: Optional[GroundedQAGenerator] = None


@app.on_event("startup")
def startup_event():
    """Initializes the RAG Engine during server startup."""
    global qa_engine
    print("[INFO] Starting up FastAPI RAG Server...")
    qa_engine = GroundedQAGenerator()
    print("[SUCCESS] RAG Engine loaded and ready.")


# Define Pydantic request model for query endpoint
class QueryRequest(BaseModel):
    query: str = Field(..., example="What is the capacity rating and protection relay for XFRM-01?")
    metadata_filter: Optional[Dict[str, Any]] = Field(
        default=None, 
        example={"document_type": "Single Line Diagram"}
    )


# Define Pydantic citation chunk response model
class CitationChunk(BaseModel):
    chunk_id: str
    source_file: str
    page_number: int
    rerank_score: float
    text_snippet: str


# Define Pydantic overall query response model
class QueryResponse(BaseModel):
    query: str
    grounded_answer: str
    sources: List[CitationChunk]


@app.get("/health", status_code=status.HTTP_200_OK)
def health_check():
    """Health check endpoint confirming engine operational state."""
    if qa_engine is None:
        raise HTTPException(status_code=503, detail="RAG Engine not initialized.")
    return {
        "status": "healthy",
        "service": config["api"]["title"],
        "version": config["api"]["version"]
    }


@app.post("/api/v1/query", response_model=QueryResponse, status_code=status.HTTP_200_OK)
def query_datacenter_docs(request: QueryRequest):
    """Primary REST endpoint for processing user queries against the hybrid RAG engine."""
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query string cannot be empty.")
        
    try:
        # Execute grounded QA pipeline
        answer, retrieved_chunks = qa_engine.generate_answer(
            query=request.query, 
            metadata_filter=request.metadata_filter
        )
        
        # Format citation chunk models
        formatted_sources = [
            CitationChunk(
                chunk_id=c["chunk_id"],
                source_file=c["metadata"]["source_file"],
                page_number=c["metadata"]["page_number"],
                rerank_score=round(c.get("rerank_score", 0.0), 4),
                text_snippet=c["text"][:200] + "..."
            )
            for c in retrieved_chunks
        ]
        
        return QueryResponse(
            query=request.query,
            grounded_answer=answer,
            sources=formatted_sources
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal RAG error: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    # Run FastAPI server via Uvicorn CLI
    uvicorn.run(app, host=config["api"]["host"], port=config["api"]["port"])
    