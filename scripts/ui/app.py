import sys
from pathlib import Path
import streamlit as st

# Add project root directory to sys.path
root_dir = Path(__file__).resolve().parents[2]
if str(root_dir) not in sys.path:
    sys.path.append(str(root_dir))

# Resolve path references to check index existence
CHROMA_DB_DIR = root_dir / "output" / "chroma_db"
BM25_INDEX_FILE = root_dir / "output" / "bm25_index.pkl"

# Import ingestion, indexing, and generator scripts
from scripts.ingestion.parse_documents import parse_all_documents
from scripts.ingestion.build_indices import build_vector_and_keyword_indices
from scripts.generation.qa_generator import GroundedQAGenerator

st.set_page_config(
    page_title="100MW Data Center RAG Engine",
    page_icon="⚡",
    layout="wide"
)

st.title("⚡ 100MW Data Center Intelligence Engine")
st.markdown("Query engineering drawings, financial regulations, and commercial legal contracts.")

# Automatically build indices if missing on Cloud Container
@st.cache_resource(show_spinner="Initializing Database & Building Indices...")
def load_rag_engine():
    if not CHROMA_DB_DIR.exists() or not BM25_INDEX_FILE.exists():
        st.info("Indices not found. Parsing raw documents and generating ChromaDB + BM25 indices...")
        parse_all_documents()
        build_vector_and_keyword_indices()
    return GroundedQAGenerator()

try:
    generator = load_rag_engine()
except Exception as e:
    st.error(f"Failed to initialize RAG Engine: {str(e)}")
    st.stop()

# Search UI
user_query = st.text_input("Ask a question about data center operations, transformers, or tariffs:")

if st.button("Submit Query", type="primary") and user_query:
    with st.spinner("Retrieving grounded context & synthesizing response..."):
        answer, sources = generator.generate_answer(user_query)
        
        st.markdown("### Synthesized Direct Answer")
        st.success(answer)
        
        st.markdown("### Retrieved Grounded Context")
        if sources:
            for idx, chunk in enumerate(sources, start=1):
                source_file = chunk['metadata'].get('source_file', 'Unknown')
                page_num = chunk['metadata'].get('page_number', 'N/A')
                score = chunk.get('rerank_score', 0.0)
                
                with st.expander(f"Chunk {idx}: {source_file} (Page {page_num}) — Rerank Score: {score:.4f}"):
                    st.write(chunk['text'])
        else:
            st.info("No matching grounded context found.")