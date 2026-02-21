#!/usr/bin/env bash
# orchestrate.sh — Start or terminate the Semantic Search stack.
#
# Usage:
#   ./orchestrate.sh --action start
#   ./orchestrate.sh --action terminate
#
# start     : Build image (if needed) and launch all containers in the background.
# terminate : Stop and remove all containers, volumes, and networks.
#             ChromaDB data is fully wiped on terminate.

set -euo pipefail

# ── Parse arguments ────────────────────────────────────────────────────────────

ACTION=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --action)
            ACTION="$2"
            shift 2
            ;;
        *)
            echo "Unknown argument: $1" >&2
            exit 1
            ;;
    esac
done

if [[ -z "$ACTION" ]]; then
    echo "Usage: $0 --action <start|terminate>" >&2
    exit 1
fi

# ── Helpers ────────────────────────────────────────────────────────────────────

free_port() {
    local port=8000
    # fuser returns exit code 1 when nothing is on the port — suppress that.
    if fuser "${port}/tcp" &>/dev/null; then
        echo "⚠  Port ${port} is in use — killing the process..."
        fuser -k "${port}/tcp" &>/dev/null || true
        sleep 1   # give the OS a moment to release the socket
        echo "   Port ${port} is now free."
    fi
}

# ── Actions ────────────────────────────────────────────────────────────────────

start() {
    free_port
    echo "▶  Building and starting Semantic Search stack..."
    docker compose up --build -d
    echo ""
    echo "✅ Stack is running."
    echo "   API: http://localhost:8000"
    echo "   Health: http://localhost:8000/health"
    echo ""
    echo "   Logs: docker compose logs -f"
}

terminate() {
    echo "⏹  Stopping Semantic Search stack and removing all data..."
    docker compose down --volumes --remove-orphans
    echo ""
    echo "✅ Stack terminated. All containers, volumes, and networks removed."
    echo "   ChromaDB data has been wiped."
}

# ── Dispatch ───────────────────────────────────────────────────────────────────

case "$ACTION" in
    start)
        start
        ;;
    terminate)
        terminate
        ;;
    *)
        echo "Error: unknown action '$ACTION'. Valid actions: start, terminate." >&2
        exit 1
        ;;
esac
