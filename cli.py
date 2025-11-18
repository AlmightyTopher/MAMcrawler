"""
CLI query interface for RAG system.
Uses modular components from mamcrawler package.
"""

import sys
import os
import anthropic

import database
from mamcrawler.rag import EmbeddingService, FAISSIndexManager
from mamcrawler.config import DEFAULT_RAG_CONFIG


def main():
    """Main CLI entry point."""
    config = DEFAULT_RAG_CONFIG

    # Check for required files
    if not os.path.exists(config.index_path) or not os.path.exists(config.db_path):
        print(f"Error: {config.index_path} or {config.db_path} not found.")
        print("Please run 'python ingest.py' first.")
        sys.exit(1)

    # Initialize modular components
    try:
        embedding_service = EmbeddingService()
        index_manager = FAISSIndexManager()
        client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
    except Exception as e:
        print(f"Error initializing components: {e}")
        sys.exit(1)

    # Get query from CLI arguments
    if len(sys.argv) < 2:
        print("Usage: python cli.py <your query> [--context-only]")
        sys.exit(1)

    # Check for --context-only flag
    context_only = "--context-only" in sys.argv
    args = [arg for arg in sys.argv[1:] if arg != "--context-only"]
    user_query = " ".join(args)

    if not user_query:
        print("Usage: python cli.py <your query> [--context-only]")
        sys.exit(1)

    # Embed query using embedding service
    query_vector = embedding_service.encode_query(user_query)

    # Search FAISS using index manager
    D, I = index_manager.search(query_vector, k=config.top_k)
    chunk_ids = tuple(I[0])  # I is 2D array, take first row

    if not any(cid > 0 for cid in chunk_ids):
        print("Could not find any relevant context.")
        sys.exit(0)

    # Get text and metadata from SQLite
    results = database.get_chunks_by_ids(chunk_ids)

    # Build context string
    context_str = ""
    for row in results:
        text, path, headers = row
        context_str += f"--- CONTEXT (Source: {path}, Section: {headers}) ---\n{text}\n\n"

    if context_only:
        print(context_str)
        sys.exit(0)

    # Build prompt for Claude
    system_prompt = (
        "You are an expert developer assistant. Answer the user's question based *only* "
        "on the provided context. If the answer is not in the context, state that "
        "you cannot answer based on the provided information. Cite the source file "
        "and section when possible."
    )

    final_prompt = f"{context_str}User Question: {user_query}"

    # Call Claude API
    try:
        message = client.messages.create(
            model=config.llm_model,
            system=system_prompt,
            messages=[{"role": "user", "content": final_prompt}],
            max_tokens=config.max_tokens,
            temperature=0.0  # Deterministic
        )
        print(message.content[0].text)
    except anthropic.APIError as e:
        print(f"Error calling Claude API: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
