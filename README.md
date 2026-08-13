# ⚡ 100MW Data Center Intelligence Engine (Hybrid RAG)

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://share.streamlit.io/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![ChromaDB](https://img.shields.io/badge/Vector%20DB-ChromaDB-orange.svg)](https://www.trychroma.com/)
[![Gemini API](https://img.shields.io/badge/LLM-Google%20Gemini-green.svg)](https://ai.google.dev/)

A production-grade **Hybrid Retrieval-Augmented Generation (RAG) System** engineered to parse, index, and query complex technical data center engineering drawings (SLDs), time-of-use (TOU) power tariffs, and commercial power purchase agreements (PPAs).

---

## 💡 The Core Problem: Why Enterprise Technical Documents Need a Custom RAG Engine

Standard enterprise RAG applications work well for simple textual documents like corporate FAQs, HR handbooks, or basic policy guides. However, in heavy industrial, utility, and infrastructure domains—such as a **100MW Data Center facility**—off-the-shelf RAG systems fail. 

Technical documentation in these environments presents distinct engineering challenges:

* **Dense & Interconnected Technical Specifications:** Engineering single-line diagrams (SLDs), equipment schedules, and electrical schematics rely on precise numerical values, equipment IDs (e.g., `132kV-TR-01`), and tight specifications rather than natural prose.
* **Complex Legal & Commercial Contracts:** Power purchase agreements (PPAs) and Time-of-Use (TOU) tariff schedules contain nested clauses, tariff matrices, and strict legal compliance definitions that require exact retrieval rather than broad semantic approximations.
* **The Cost of Hallucination:** In infrastructure management, a hallucinated transformer rating or misread tariff window isn't just an error—it can lead to costly operational downtime, miscalculated energy margins, or legal non-compliance.

This engine was specifically designed as a **production-grade enterprise solution** for complex industrial documents where simple document readers fall short.

---

## 🧠 Technical Architecture & Engineering Rationale

### 1. Document Chunking Strategy (Why Character Sliding Windows?)
* **How It Works:** Raw PDF pages are extracted using `pypdf` and split into **700-character windows** with a **150-character overlap**. Each chunk retains metadata identifying its source document, page number, document type, and folder category.
* **Why This Approach:** Industrial PDFs contain dense tabular data, model numbers, and technical specs rather than fluid narrative paragraphs. Fixed character sliding windows prevent critical transformer specs or breaker ratings from getting split cleanly in half across arbitrary paragraph boundaries.

### 2. Why We Built a Custom Pipeline (And Skipped LangChain / LlamaIndex)
* **Zero Abstraction Overhead:** Frameworks like LangChain add multiple layers of abstraction that obscure underlying prompt flows, index operations, and exception handling.
* **Deterministic Control:** Building native Python modules (`scripts/ingestion`, `scripts/retrieval`, `scripts/generation`) gives complete control over path resolution, exact BM25 tokenization, vector collection schema, and error handling during cloud container cold-starts.
* **Lightweight Deployment:** Eliminating heavy orchestrator dependencies minimizes container setup size and avoids version-locking conflicts on Streamlit Cloud.

### 3. Why ChromaDB for Vector Storage?
* **Local & Embedded:** ChromaDB runs in-memory with lightweight local disk persistence (`output/chroma_db`), eliminating the need to host or pay for an external vector database server (like Pinecone or Weaviate).
* **Metadata Filtering:** Allows querying vector embeddings while maintaining full access to source metadata (file name, page number, document classification) for source attribution.

### 4. How Our Hybrid RAG Differs From Standard RAG
Standard RAG relies strictly on dense semantic embeddings. While semantic search is great for conceptual questions, it frequently fails on technical engineering datasets (e.g., misidentifying exact part codes or specific numeric voltage ratings).

Our pipeline combines **two complementary search layers** backed by a **reranker**:
1. **Dense Semantic Search (ChromaDB):** Captures high-level context, intent, and conceptual relationships across documents.
2. **Sparse Lexical Search (Rank-BM25):** Performs exact keyword matching for specific model names, numerical values, and component identifiers.
3. **Cross-Encoder Reranking:** Takes the combined top results from both retrievers and re-scores them using a Cross-Encoder model before passing context to the LLM. This eliminates low-relevance noise and reduces LLM context window cost.

### 5. LLM Integration (Google Gemini)
* **Grounded Direct Synthesis:** The reranked context chunks are passed into the Google Gemini API with explicit grounding instructions: synthesize direct answers strictly based on the provided technical context, citing source files and page numbers.
* **Zero-Hallucination Guardrails:** If retrieved context lacks the necessary specifications to answer a query, the model is prompted to state that the context is insufficient rather than generating plausible engineering assumptions.

  ## 📈 Enterprise Scalability & System Extension

While this repository demonstrates a lightweight, self-contained deployment for a 100MW data center infrastructure dataset, the modular architecture is designed to scale horizontally across large enterprises, multi-tenant organizations, and multi-facility industrial operations.

### How This Engine Scales for Large-Scale Enterprise Deployments

1. **Distributed Vector Database (ChromaDB Cloud / Qdrant / Milvus)**
   * **Current Setup:** Local embedded ChromaDB instance reading from persistent disk storage.
   * **Enterprise Scaling:** Swap the local vector store for a managed, distributed vector database cluster (e.g., **ChromaDB Cloud**, **Qdrant**, or **Milvus**). This enables multi-region indexing, sub-second search over millions of document chunks, and high availability across thousands of concurrent users.

2. **Asynchronous Document Processing Pipelines (Celery + Redis / Apache Kafka)**
   * **Current Setup:** In-memory PDF parsing and chunking on startup via `pypdf`.
   * **Enterprise Scaling:** Offload document ingestion to an asynchronous job queue using **Redis + Celery** or **Apache Kafka**. Incoming engineering drawings, invoices, and contracts uploaded via cloud storage (AWS S3 / Google Cloud Storage) are processed in parallel background worker pools without blocking application performance.

3. **Multi-Tenancy & Access Control (RBAC / Row-Level Security)**
   * **Current Setup:** Unified single-tenant access.
   * **Enterprise Scaling:** Implement Role-Based Access Control (RBAC) at the retrieval layer using metadata tags. Different departments (Engineering, Legal, Finance, Site Operations) query the same engine while automatically filtering results to only include documents they are authorized to view.

4. **REST API & Microservice Integration (FastAPI / Docker / Kubernetes)**
   * **Current Setup:** Direct native Python calls driving a Streamlit UI.
   * **Enterprise Scaling:** Expose the RAG engine via a high-performance **FastAPI microservice** containerized with **Docker** and orchestrated on **Kubernetes (EKS/GKE)**. This allows existing enterprise tools—such as internal Slack/Teams bots, ERP systems, or custom web portals—to leverage the intelligence engine via simple REST API endpoints.

5. **Advanced Multimodal PDF Parsing (Unstructured.io / Azure Layout Parser)**
   * **Current Setup:** Native text extraction with sliding character windows.
   * **Enterprise Scaling:** Integrate vision-language parsers or dedicated document AI tooling (**Unstructured.io**, **Azure AI Document Intelligence**) to extract complex multi-page tables, embedded CAD drawing legends, and inline circuit schematics into structured JSON nodes prior to vector embedding.

---

## 🏗️ End-to-End System Flow

```text
               ┌──────────────────────────────────────┐
               │  Raw Technical PDFs (data/raw/)     │
               └──────────────────┬───────────────────┘
                                  │
                                  ▼
               ┌──────────────────────────────────────┐
               │   pypdf Extraction & Custom Chunking │
               │   (700 Chars Window / 150 Overlap)   │
               └──────────────────┬───────────────────┘
                                  │
         ┌────────────────────────┴────────────────────────┐
         ▼                                                 ▼
┌─────────────────────────────────┐       ┌─────────────────────────────────┐
│     Dense Vector Retrieval      │       │     Sparse Lexical Retrieval    │
│     (ChromaDB Collection)       │       │          (Rank-BM25)            │
└────────────────┬────────────────┘       └────────────────┬────────────────┘
                 │                                         │
                 └────────────────┬────────────────────────┘
                                  │
                                  ▼
               ┌──────────────────────────────────────┐
               │    Cross-Encoder Reranking Layer     │
               └──────────────────┬───────────────────┘
                                  │
                                  ▼
               ┌──────────────────────────────────────┐
               │   Google Gemini Synthesis Engine     │
               └──────────────────┬───────────────────┘
                                  │
                                  ▼
               ┌──────────────────────────────────────┐
               │    Streamlit Cloud User Interface    │
               └──────────────────────────────────────┘


