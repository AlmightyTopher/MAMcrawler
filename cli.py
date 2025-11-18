import faiss
import numpy as np
import sqlite3
from sentence_transformers import SentenceTransformer
import anthropic
import sys
import os
import database

def main():
    # Check for required files
    if not os.path.exists("index.faiss") or not os.path.exists("metadata.sqlite"):
        print("Error: index.faiss or metadata.sqlite not found. Please run python ingest.py first.")
        sys.exit(1)

    # Load models and indexes
    try:
        index = faiss.read_index("index.faiss")
        model = SentenceTransformer('all-MiniLM-L6-v2')
        client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
    except Exception as e:
        print(f"Error loading models/index: {e}")
        sys.exit(1)

    # Get query from CLI arguments
    if len(sys.argv) < 2:
        print("Usage: python cli.py <your query>")
        sys.exit(1)

    user_query = " ".join(sys.argv[1:])

    # Check for --context-only flag
    context_only = "--context-only" in sys.argv
    if context_only:
        user_query = user_query.replace("--context-only", "").strip()

    if not user_query:
        print("Usage: python cli.py <your query>")
        sys.exit(1)

    # Embed query
    query_vector = model.encode([user_query])
    faiss.normalize_L2(query_vector.astype(np.float32))

    # Search FAISS
    k = 5
    D, I = index.search(query_vector.astype(np.float32), k)
    chunk_ids = tuple(I[0])  # I is 2D array, take first row

    if not any(chunk_ids):  # Check if all are 0 (no results)
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

    # Build prompt
    system_prompt = (
        "You are an expert developer assistant. Answer the user's question based *only* "
        "on the provided context. If the answer is not in the context, state that "
        "you cannot answer based on the provided information. Cite the source file "
        "and section when possible."
    )

    final_prompt = f"{context_str}User Question: {user_query}"

    # Call Claude
    try:
        message = client.messages.create(
            model="claude-haiku-4-5",  # Use Haiku for cost/speed
            system=system_prompt,
            messages=[{"role": "user", "content": final_prompt}],
            max_tokens=1500,
            temperature=0.0  # Deterministic
        )
        print(message.content[0].text)
    except anthropic.APIError as e:
        print(f"Error calling Claude API: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    main()