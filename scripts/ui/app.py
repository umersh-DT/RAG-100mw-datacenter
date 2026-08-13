# Import sys and Path to ensure root project imports resolve cleanly
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[2]))

# Import standard library and UI framework modules
import json
import requests
import streamlit as st

# Configure Streamlit page layout
st.set_page_config(
    page_title="HyperScale 100MW Data Center RAG Platform",
    page_icon="⚡",
    layout="wide"
)

# API Endpoint definition
API_URL = "http://127.0.0.1:8000/api/v1/query"

# Title Header
st.title("⚡ 100MW Data Center Knowledge Engine")
st.caption("Hybrid RAG Interface for Technical, Legal & Financial Infrastructure Records")

# Sidebar Controls
st.sidebar.header("🔍 Document Metadata Filters")
doc_type_filter = st.sidebar.selectbox(
    "Filter by Document Type",
    options=["All", "Single Line Diagram", "TOU Power Invoice", "Power Purchase Agreement"]
)

# Build metadata filter dictionary
metadata_filter = None
if doc_type_filter != "All":
    metadata_filter = {"document_type": doc_type_filter}

# Sample Queries
st.sidebar.markdown("---")
st.sidebar.subheader("💡 Sample Benchmarks")
if st.sidebar.button("Query XFRM-01 Transformer"):
    st.session_state["query_input"] = "What is the capacity rating and protection relay for XFRM-01?"
if st.sidebar.button("Query Base Tariff & Curtailment"):
    st.session_state["query_input"] = "What is the base electricity tariff and maximum curtailment hours?"
if st.sidebar.button("Query Q1 Invoice Total"):
    st.session_state["query_input"] = "What is the total amount due for the Q1 2025 utility invoice?"

# User Input Box
user_query = st.text_input(
    "Enter your engineering or legal query:",
    value=st.session_state.get("query_input", ""),
    placeholder="e.g., What protection relay is assigned to circuit breaker CB-132-A1?"
)

# Query Execution Logic
if st.button("Run Search Query", type="primary"):
    if not user_query.strip():
        st.warning("Please enter a valid query string.")
    else:
        payload = {
            "query": user_query,
            "metadata_filter": metadata_filter
        }
        
        with st.spinner("Executing hybrid retrieval and reranking..."):
            try:
                response = requests.post(API_URL, json=payload, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    st.markdown("### 📝 Grounded Response")
                    st.markdown(data["grounded_answer"])
                    
                    st.markdown("---")
                    st.markdown("### 📚 Retained Source Citations")
                    
                    for idx, source in enumerate(data["sources"], start=1):
                        with st.expander(f"Source {idx}: {source['source_file']} (Page {source['page_number']}) — Rerank Score: {source['rerank_score']:.4f}"):
                            st.write(f"**Chunk ID:** `{source['chunk_id']}`")
                            st.code(source["text_snippet"], language="text")
                else:
                    st.error(f"API Error ({response.status_code}): {response.text}")
            except requests.exceptions.ConnectionError:
                st.error("Could not connect to FastAPI server. Make sure `python scripts/api/main.py` is running on port 8000.")