# User Guide

This guide provides detailed instructions on how to use the Semantic Search API.

## Quick Start Guide

### 1. Start the Stack
This will build the Docker images and launch the API and database in the background.
```bash
./orchestrate.sh --action start
```
*The API will be available at `http://localhost:8000`.*

### 2. Ingest Documents

#### Using `curl` (Individual Files)
You can upload one or more PDF files directly using `curl`.

**Single File:**
```bash
curl -X POST http://localhost:8000/ingest/ \
     -F "input=@path/to/your/file.pdf"
```

**Multiple Files:**
```bash
curl -X POST http://localhost:8000/ingest/ \
     -F "input=@file1.pdf" \
     -F "input=@file2.pdf"
```

#### Using `orchestrate.sh` (Directory)
Ingesting a whole directory is managed by the `orchestrate.sh` script, which handles copying files into the container and triggering the ingestion.
```bash
./orchestrate.sh --action ingest --path /path/to/your/pdf_directory/
```

### 3. Search
Perform semantic searches by sending a POST request to the `/search/` endpoint.

```bash
curl -X POST http://localhost:8000/search/ \
     -H "Content-Type: application/json" \
     -d '{
       "query": "Explain the concept of neural networks",
       "top_k": 5
     }'
```

- **`query`** (Required): The natural-language question or phrase you want to search for.
- **`top_k`** (Optional): The number of results to return. Must be between **1 and 100**. If not provided, it will use the default configured value (usually 5).

### 4. Viewing Logs
You can access the logs from the running containers to monitor ingestion progress or debug issues.

**Follow all logs:**
```bash
docker compose logs -f
```

**View logs for the API specifically:**
```bash
docker compose logs -f semantic-search-app
```

### 5. Stop and Clean Up
To stop the containers and remove all data (including the vector store):
```bash
./orchestrate.sh --action terminate
```
