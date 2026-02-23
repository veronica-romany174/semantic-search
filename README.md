# Semantic Search

This project is a **Semantic Search API** designed to ingest PDF documents, process their content into searchable "chunks", and enable natural-language queries using vector embeddings.

## Project Structure

```text
├── app/
│   ├── api/             # API controllers (FastAPI routers)
│   ├── chunker/         # PDF parsing and text chunking logic
│   ├── core/            # Configuration, logging, and exceptions
│   ├── embedder/        # ML model wrappers for vector embeddings
│   ├── models/          # Pydantic models for request/response
│   ├── services/        # Business logic orchestration
│   └── vector_store/    # ChromaDB integration
├── data/                # Local storage for ChromaDB (persistent)
├── tests/               # Unit and integration tests
├── orchestrate.sh       # Main CLI tool for stack management
└── docker-compose.yml   # Container orchestration
```

## Layered Architecture

The project is organized into four distinct layers to ensure separation of concerns:

1.  **API Layer (`app/api`)**: Responsible for HTTP handling, request validation, and translating application results into JSON responses.
2.  **Service Layer (`app/services`)**: The orchestration heart of the system. It coordinates the data flow between the reader, chunker, embedder, and vector store.
3.  **Domain Logic (`app/chunker`, `app/embedder`)**: Contains the "heavy lifting" logic for extracting text from PDFs and transforming it into high-dimensional vectors.
4.  **Data Layer (`app/vector_store`)**: Abstracts the interaction with **ChromaDB**, handling the persistence and similarity search queries.

## Core Functionality
- **PDF Ingestion**: Upload individual PDF files, multiple files, or a directory path to the system.
- **Text Chunking**: Automatically breaks down large documents into smaller pieces with overlap for better context retention.
- **Semantic Search**: Uses machine learning models to understand the *meaning* of your search query rather than just matching keywords.
- **Vector Storage**: Persistently stores embeddings in **ChromaDB**.

## Tech Stack Deep-Dive

- **Framework**: [FastAPI](https://fastapi.tiangolo.com/) - High-performance Python web framework for building APIs.
- **Vector Database**: **ChromaDB** - Selected for being a lightweight, AI-native, and open-source vector database that allows for efficient similarity searches without the overhead of a managed service.
- **Embeddings**: **Sentence-Transformers** (`all-MiniLM-L6-v2`) - A compact, high-performance model that provides an excellent balance between embedding quality and inference speed, making it ideal for real-time semantic search.
- **PDF Processing**: [PyMuPDF](https://pymupdf.readthedocs.io/) - Used for fast and robust text extraction directly from raw PDF bytes.

## Design Decisions

### Image Processing & OCR
Currently, the `PDFReader` extracts only plain text. If a PDF contains only images or scanned text without an OCR layer, it will be skipped (logged as "no extractable text"). This preserves performance and avoids dependencies on heavy OCR engines like Tesseract.

### Directory Ingestion & Docker
When running via Docker, the API cannot directly access directory paths on the host machine. 
- **The Challenge**: If you pass a local path like `/home/user/pdfs` to a containerized API, that path doesn't exist inside the container.
- **The Solution**: The `orchestrate.sh` script handles this by using `docker cp` to stage the files into a temporary directory inside the container's volume, and then triggers the ingestion using the internal container path.

### Partial Success Semantics
The ingestion pipeline is designed for robustness. If a batch of files is uploaded and one file fails (e.g., due to corruption), the system logs the error and continues processing the remaining files in the batch.

## User Guide
For detailed instructions on how to start, ingest, search, and view logs, please refer to the [User Guide](USER_GUIDE.md).
