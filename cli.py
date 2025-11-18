"""
CLI query interface for RAG system.
Uses modular components from mamcrawler package.
Supports three modes for remote API:
- "off": never call Anthropic
- "ask": ask before each call
- "on": call automatically
"""

import sys
import os
import json
import anthropic

import database
from mamcrawler.rag import EmbeddingService, FAISSIndexManager
from mamcrawler.config import DEFAULT_RAG_CONFIG, REMOTE_MODE


def ask_permission():
    """Ask user for permission to make remote API call."""
    while True:
        choice = (
            input("This will call the Anthropic API. Continue? (y/n): ").strip().lower()
        )
        if choice in ["y", "yes"]:
            return True
        if choice in ["n", "no"]:
            return False
        print("Please enter y or n.")


def main():
    if len(sys.argv) < 2:
        print("Usage: python cli.py <query>")
        return

    query = sys.argv[1]
    config = DEFAULT_RAG_CONFIG

    if not os.path.exists(config.index_path) or not os.path.exists(config.db_path):
        print("ERROR: index.faiss or database missing. Run: python ingest.py")
        return

    print("Loading embedding model:", config.model_name)
    embeddings = EmbeddingService(config)
    index_mgr = FAISSIndexManager(config)

    print("Embedding query…")
    qvec = embeddings.encode_query(query)

    print("Searching index…")
    distances, ids = index_mgr.search(qvec, config.top_k)
    top_ids = ids[0]  # Get first row
    top_scores = distances[0]  # Get first row

    print("Retrieving chunks…")
    # Filter out invalid IDs (0 or negative)
    valid_ids = [int(id) for id in top_ids if id > 0]
    chunks = database.get_chunks_by_ids(valid_ids)

    # Always display local RAG results
    rag_json = {
        "query": query,
        "results": [
            {
                "chunk_id": chunk_id,
                "file": chunk_data[1],  # path
                "content": chunk_data[0],  # text
                "score": float(score),
            }
            for chunk_id, chunk_data, score in zip(
                valid_ids, chunks, top_scores[: len(valid_ids)]
            )
        ],
    }

    print("\nLocal RAG results:")
    print(json.dumps(rag_json, indent=2))

    # Now check API mode
    api_key = os.getenv("ANTHROPIC_API_KEY")

    if REMOTE_MODE == "off":
        print("\nREMOTE_MODE is off. Skipping Anthropic API completely.")
        return

    if not api_key:
        print("\nNo Anthropic API key found. Running in local-only mode.")
        return

    if REMOTE_MODE == "ask":
        print("\nREMOTE_MODE is set to ask.")
        if not ask_permission():
            print("Skipping cloud API.")
            return

    # If REMOTE_MODE == "on", no prompt
    print("\nCalling Anthropic API…")

    client = anthropic.Anthropic(api_key=api_key)

    try:
        response = client.messages.create(
            model="claude-3-5-sonnet-latest",
            max_tokens=400,
            messages=[
                {
                    "role": "user",
                    "content": f"Use the following chunks as context to answer the query.\nQuery: {query}\n\nChunks:\n{json.dumps(rag_json, indent=2)}",
                }
            ],
        )
        print("\nAnthropic Response:\n")
        print(response.content[0].text)
    except Exception as e:
        print(f"\nError calling Anthropic API: {e}")
        print("Falling back to local-only mode.")


if __name__ == "__main__":
    main()
