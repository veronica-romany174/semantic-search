# Semantic Search

This project is a **Semantic Search API** designed to ingest PDF documents, process their content into searchable "chunks", and enable natural-language queries using vector embeddings.

## Core Functionality
- **PDF Ingestion**: Upload individual PDF files, multiple files, or a directory path to the system.
- **Text Chunking**: Automatically breaks down large documents into smaller pieces with overlap for better context retention.
- **Semantic Search**: Uses machine learning models to understand the *meaning* of your search query rather than just matching keywords.
- **Vector Storage**: Persistently stores embeddings in **ChromaDB**.

## Tech Stack
- **Framework**: [FastAPI](https://fastapi.tiangolo.com/) (Python)
- **Vector Database**: [ChromaDB](https://www.trychroma.com/)
- **Embeddings**: [Sentence-Transformers](https://sbert.net/) (`all-MiniLM-L6-v2`)
- **PDF Processing**: [PyMuPDF](https://pymupdf.readthedocs.io/)
- **Environment**: Docker & Docker Compose


## User Guide
For detailed instructions on how to start, ingest, search, and view logs, please refer to the [User Guide](USER_GUIDE.md).
