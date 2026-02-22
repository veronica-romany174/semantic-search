#!/usr/bin/env bash
# orchestrate.sh — Manage the Semantic Search stack.
#
# Usage:
#   ./orchestrate.sh --action start
#   ./orchestrate.sh --action terminate
#   ./orchestrate.sh --action ingest --path <path> [--path <path> ...]
#
# start     : Build image and launch containers in the background.
# terminate : Stop and remove all containers, volumes, ChromaDB data, and any
#             staged upload files.
# ingest    : Upload PDFs to the running service. --path can be:
#               • A single PDF file   → sent over HTTP (curl @)
#               • Multiple PDF files  → all sent over HTTP in one request
#               • A directory of PDFs → copied into the container, ingested
#                                       via path string, then cleaned up.

set -euo pipefail

API_BASE="http://localhost:8000"
CONTAINER="semantic-search-app"
UPLOADS_DIR="/app/uploads"   # staging area inside the container (for directory mode)

# ── Parse arguments ────────────────────────────────────────────────────────────

ACTION=""
PATHS=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --action)
            ACTION="$2"
            shift 2
            ;;
        --path)
            PATHS+=("$2")
            shift 2
            ;;
        *)
            echo "Unknown argument: $1" >&2
            exit 1
            ;;
    esac
done

if [[ -z "$ACTION" ]]; then
    echo "Usage: $0 --action <start|terminate|ingest> [--path <path> ...]" >&2
    exit 1
fi

# ── Helpers ────────────────────────────────────────────────────────────────────

free_port() {
    local port=8000
    if fuser "${port}/tcp" &>/dev/null; then
        echo "⚠  Port ${port} is in use — killing the process..."
        fuser -k "${port}/tcp" &>/dev/null || true
        sleep 1
        echo "   Port ${port} is now free."
    fi
}

# Clean the uploads staging area inside the container (best-effort)
clean_uploads() {
    docker exec "${CONTAINER}" rm -rf "${UPLOADS_DIR:?}/"* 2>/dev/null || true
}

# Print response body nicely; fall back to raw output
pretty_print() {
    python3 -m json.tool 2>/dev/null || cat
}

# ── Actions ────────────────────────────────────────────────────────────────────

start() {
    free_port
    echo "▶  Building and starting Semantic Search stack..."
    docker compose up --build -d
    echo ""
    echo "✅ Stack is running."
    echo "   API:    ${API_BASE}"
    echo "   Health: ${API_BASE}/health"
    echo "   Logs:   docker compose logs -f"
}

terminate() {
    echo "⏹  Stopping Semantic Search stack and removing all data..."
    clean_uploads
    docker compose down --volumes --remove-orphans
    echo ""
    echo "✅ Stack terminated. All containers, volumes, and staged files removed."
    echo "   ChromaDB data has been wiped."
}

ingest() {
    # ── Validate --path arguments ──────────────────────────────────────────────
    if [[ ${#PATHS[@]} -eq 0 ]]; then
        echo "Error: --action ingest requires at least one --path argument." >&2
        echo "" >&2
        echo "  Single PDF:     $0 --action ingest --path /path/to/file.pdf" >&2
        echo "  Multiple PDFs:  $0 --action ingest --path a.pdf --path b.pdf" >&2
        echo "  Directory:      $0 --action ingest --path /path/to/pdfs/" >&2
        exit 1
    fi

    # ── Detect mode: directory vs file(s) ─────────────────────────────────────
    # If exactly one --path is given and it's a directory → directory mode.
    # Otherwise → file mode (one or more individual PDF files).

    if [[ ${#PATHS[@]} -eq 1 && -d "${PATHS[0]}" ]]; then
        # ── DIRECTORY MODE ─────────────────────────────────────────────────────
        # How it works:
        #   1. docker cp copies the directory contents into the container at
        #      /app/uploads — no permanent bind mount needed.
        #   2. curl sends -F "input=/app/uploads" (a path string) so the server
        #      walks the directory and ingests every PDF it finds.
        #   3. The staging area is cleaned up immediately after ingest.

        local dir="${PATHS[0]}"
        local pdf_count
        pdf_count=$(find "$dir" -maxdepth 1 -iname "*.pdf" | wc -l)

        if [[ "$pdf_count" -eq 0 ]]; then
            echo "Error: no PDF files found in directory: $dir" >&2
            exit 1
        fi

        echo "▶  Directory mode — found ${pdf_count} PDF(s) in: $dir"
        echo "   Copying into container..."
        # docker cp <src>/. <container>:<dest> copies contents, not the folder itself
        docker cp "${dir}/." "${CONTAINER}:${UPLOADS_DIR}/"

        echo "   Ingesting via path string..."
        response=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/ingest/" \
            -F "input=${UPLOADS_DIR}")
        http_code=$(echo "$response" | tail -n1)
        body=$(echo "$response" | head -n -1)

        echo "   Cleaning up staged files..."
        clean_uploads

    else
        # ── FILE MODE ──────────────────────────────────────────────────────────
        # How it works:
        #   curl reads each PDF from the HOST filesystem and streams the bytes
        #   over HTTP as a multipart upload. The container never needs to touch
        #   the host filesystem — it just receives raw file bytes.

        local curl_args=()
        for p in "${PATHS[@]}"; do
            if [[ ! -f "$p" ]]; then
                echo "Error: not a file: $p" >&2
                exit 1
            fi
            if [[ "${p,,}" != *.pdf ]]; then
                echo "Error: only PDF files are accepted: $p" >&2
                exit 1
            fi
            curl_args+=(-F "input=@$p")
            echo "   • $(basename "$p")"
        done

        echo "▶  File mode — uploading ${#PATHS[@]} PDF(s) over HTTP..."
        response=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/ingest/" \
            "${curl_args[@]}")
        http_code=$(echo "$response" | tail -n1)
        body=$(echo "$response" | head -n -1)
    fi

    # ── Print result ───────────────────────────────────────────────────────────
    if [[ "$http_code" == "200" ]]; then
        echo ""
        echo "✅ Ingest successful (HTTP ${http_code}):"
        echo "$body" | pretty_print
    else
        echo ""
        echo "❌ Ingest failed (HTTP ${http_code}):"
        echo "$body" | pretty_print
        exit 1
    fi
}

# ── Dispatch ───────────────────────────────────────────────────────────────────

case "$ACTION" in
    start)    start    ;;
    terminate) terminate ;;
    ingest)   ingest   ;;
    *)
        echo "Error: unknown action '$ACTION'. Valid: start, ingest, terminate." >&2
        exit 1
        ;;
esac
