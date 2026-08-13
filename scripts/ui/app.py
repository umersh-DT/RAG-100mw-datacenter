import streamlit as st
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parents[2]))

# Import generator directly instead of using requests to localhost
from scripts.generation.qa_generator import GroundedQAGenerator

st.set_page_config(page_title="100MW Data Center RAG", layout="wide")
st.title("⚡ 100MW Data Center Intelligence Engine")

# Cache generator initialization so it loads models once
@st.cache_resource
def load_generator():
    return GroundedQAGenerator()

try:
    generator = load_generator()
except Exception as e:
    st.error(f"Failed to initialize RAG Engine: {str(e)}")
    st.stop()

# Query UI
user_query = st.text_input("Ask a question about data center infrastructure, contracts, or invoices:")

if st.button("Submit Query") and user_query:
    with st.spinner("Retrieving context & synthesizing answer..."):
        answer, sources = generator.generate_answer(user_query)
        
        st.markdown("### Answer")
        st.write(answer)
        
        st.markdown("### Sources")
        for idx, src in enumerate(sources, start=1):
            with st.expander(f"Source {idx}: {src['metadata']['source_file']} (Page {src['metadata']['page_number']})"):
                st.write(src['text'])