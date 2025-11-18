"""
Enhanced ingestion pipeline that processes BOTH:
1. MAM guides (from guides_output/)
2. Forum qBittorrent posts (from forum_qbittorrent_output/)

Creates a unified FAISS + SQLite index for local searching.
"""

import os
import hashlib
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from langchain_text_splitters.markdown import MarkdownHeaderTextSplitter
import database
from pathlib import Path


def process_file(path, db_conn):
    """Process a single file: chunk, embed, and store."""
    with open(path, 'r', encoding='utf-8') as f:
        markdown_content = f.read()

    # Check if file is new or modified
    file_hash = hashlib.sha256(markdown_content.encode()).hexdigest()
    existing = database.get_file_details(path)
    if existing and existing[1] == file_hash:
        print(f"  Skipping (unchanged): {path}")
        return [], []

    # Add/update file record in SQLite
    file_id = database.insert_or_update_file(path, os.path.getmtime(path), file_hash)

    # Chunk the document
    headers_to_split_on = [("#", "H1"), ("##", "H2"), ("###", "H3")]
    markdown_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=headers_to_split_on, strip_headers=False
    )
    splits = markdown_splitter.split_text(markdown_content)

    chunks_to_embed = []
    chunk_ids = []

    for split in splits:
        header_context = " > ".join(split.metadata.values())

        # Embed the headers pattern for better retrieval
        text_to_embed = f"CONTEXT: {header_context}\n\nCONTENT:\n{split.page_content}"

        # Save chunk to SQLite and get its ID
        chunk_id = database.insert_chunk(file_id, split.page_content, header_context)
        chunk_ids.append(chunk_id)
        chunks_to_embed.append(text_to_embed)

    print(f"  Processed: {path} ({len(chunks_to_embed)} chunks)")
    return chunks_to_embed, chunk_ids


def main():
    """Main ingestion function for guides AND forum posts."""
    print("=" * 80)
    print("Enhanced RAG Ingestion - Guides + Forum Posts")
    print("=" * 80)

    # Initialize database
    database.create_tables()

    # Load or create FAISS index
    dimension = 384  # all-MiniLM-L6-v2 dimension
    if os.path.exists("index.faiss"):
        print("Loading existing FAISS index...")
        index = faiss.read_index("index.faiss")
    else:
        print("Creating new FAISS index...")
        base_index = faiss.IndexFlatL2(dimension)
        index = faiss.IndexIDMap(base_index)

    # Load embedding model
    print("Loading SentenceTransformer model (all-MiniLM-L6-v2)...")
    model = SentenceTransformer('all-MiniLM-L6-v2')

    # Define directories to process
    target_dirs = [
        'guides_output',           # MAM guides
        'forum_qbittorrent_output' # Forum posts
    ]

    all_chunks = []
    all_chunk_ids = []
    total_files = 0

    # Process all directories
    for target_dir in target_dirs:
        if not os.path.exists(target_dir):
            print(f"\nDirectory not found: {target_dir} (skipping)")
            continue

        print(f"\n{'=' * 80}")
        print(f"Processing directory: {target_dir}")
        print(f"{'=' * 80}")

        dir_files = 0
        for root, dirs, files in os.walk(target_dir):
            for file in files:
                if file.endswith('.md'):
                    path = os.path.join(root, file)
                    chunks, chunk_ids = process_file(path, None)
                    all_chunks.extend(chunks)
                    all_chunk_ids.extend(chunk_ids)
                    if chunks:
                        dir_files += 1
                        total_files += 1

        print(f"Processed {dir_files} files from {target_dir}")

    # Embed and index
    if all_chunks:
        print(f"\n{'=' * 80}")
        print(f"Embedding {len(all_chunks)} chunks...")
        embeddings = model.encode(all_chunks, show_progress_bar=True)

        print("Normalizing embeddings...")
        faiss.normalize_L2(embeddings.astype(np.float32))

        print("Adding to FAISS index...")
        index.add_with_ids(embeddings.astype(np.float32), np.array(all_chunk_ids))

        # Save index
        print("Saving FAISS index...")
        faiss.write_index(index, "index.faiss")

        print(f"\n{'=' * 80}")
        print("INDEXING COMPLETE")
        print(f"{'=' * 80}")
        print(f"Total files processed: {total_files}")
        print(f"Total chunks indexed: {len(all_chunks)}")
        print(f"Index saved to: index.faiss")
        print(f"Metadata saved to: metadata.sqlite")
        print(f"\nYou can now search with:")
        print(f"  python local_search.py 'your query'")
        print(f"{'=' * 80}")
    else:
        print("\nNo new content to index. All files are up to date.")


if __name__ == "__main__":
    main()
