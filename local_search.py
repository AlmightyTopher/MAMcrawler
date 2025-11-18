"""
Local-only RAG search system (no external APIs)
Uses FAISS for vector similarity search and SQLite for metadata retrieval.
Returns raw context chunks that can be used directly in VS Code or other tools.
"""

import faiss
import numpy as np
import sqlite3
import sys
import os
from sentence_transformers import SentenceTransformer
import database


def search_local(query: str, top_k: int = 10, output_format: str = "markdown"):
    """
    Search the local knowledge base without external API calls.

    Args:
        query: The search query
        top_k: Number of results to return (default 10)
        output_format: "markdown", "json", or "text"

    Returns:
        Formatted search results with source attribution
    """
    # Check for required files
    if not os.path.exists("index.faiss"):
        print("ERROR: index.faiss not found. Run: python ingest.py")
        sys.exit(1)

    if not os.path.exists("metadata.sqlite"):
        print("ERROR: metadata.sqlite not found. Run: python ingest.py")
        sys.exit(1)

    # Load models and indexes
    try:
        print(f"Loading FAISS index and embedding model...", file=sys.stderr)
        index = faiss.read_index("index.faiss")
        model = SentenceTransformer('all-MiniLM-L6-v2')
        print(f"Model loaded. Searching for: '{query}'", file=sys.stderr)
    except Exception as e:
        print(f"ERROR loading models/index: {e}", file=sys.stderr)
        sys.exit(1)

    # Embed query
    query_vector = model.encode([query])
    faiss.normalize_L2(query_vector.astype(np.float32))

    # Search FAISS
    D, I = index.search(query_vector.astype(np.float32), top_k)
    chunk_ids = tuple(I[0])

    if not any(chunk_ids):
        print("No results found.", file=sys.stderr)
        return None

    # Get text and metadata from SQLite
    results = database.get_chunks_by_ids(chunk_ids)

    if not results:
        print("No chunks found in database.", file=sys.stderr)
        return None

    print(f"Found {len(results)} results", file=sys.stderr)

    # Format output based on requested format
    if output_format == "json":
        import json
        output = []
        for i, (text, path, headers) in enumerate(results):
            output.append({
                "rank": i + 1,
                "source": path,
                "section": headers,
                "content": text,
                "score": float(D[0][i])  # Distance score (lower = more similar)
            })
        return json.dumps(output, indent=2)

    elif output_format == "text":
        output_lines = []
        for i, (text, path, headers) in enumerate(results):
            output_lines.append(f"=== Result {i+1} ===")
            output_lines.append(f"Source: {path}")
            output_lines.append(f"Section: {headers}")
            output_lines.append(f"Score: {D[0][i]:.4f}")
            output_lines.append("")
            output_lines.append(text)
            output_lines.append("")
        return "\n".join(output_lines)

    else:  # markdown (default)
        output_lines = [f"# Search Results: {query}\n"]
        output_lines.append(f"Found {len(results)} relevant chunks\n")
        output_lines.append("---\n")

        for i, (text, path, headers) in enumerate(results):
            output_lines.append(f"## Result {i+1}\n")
            output_lines.append(f"**Source:** `{path}`  ")
            output_lines.append(f"**Section:** {headers}  ")
            output_lines.append(f"**Similarity:** {1 - D[0][i]:.4f}  \n")  # Convert distance to similarity
            output_lines.append("### Content\n")
            output_lines.append(f"{text}\n")
            output_lines.append("---\n")

        return "\n".join(output_lines)


def main():
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: python local_search.py <query> [--top-k N] [--format markdown|json|text]")
        print("")
        print("Examples:")
        print("  python local_search.py 'qbittorrent settings'")
        print("  python local_search.py 'how to configure qbit' --top-k 5")
        print("  python local_search.py 'port forwarding' --format json")
        sys.exit(1)

    # Parse arguments
    args = sys.argv[1:]
    top_k = 10
    output_format = "markdown"
    query_parts = []

    i = 0
    while i < len(args):
        if args[i] == "--top-k" and i + 1 < len(args):
            top_k = int(args[i + 1])
            i += 2
        elif args[i] == "--format" and i + 1 < len(args):
            output_format = args[i + 1]
            i += 2
        else:
            query_parts.append(args[i])
            i += 1

    query = " ".join(query_parts)

    if not query:
        print("ERROR: No query provided", file=sys.stderr)
        sys.exit(1)

    # Perform search
    result = search_local(query, top_k=top_k, output_format=output_format)

    if result:
        print(result)
    else:
        print("No results found.")


if __name__ == "__main__":
    main()
