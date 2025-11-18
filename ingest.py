"""
RAG indexing pipeline for MAMcrawler.
Uses modular components from mamcrawler package.
"""

import os
import hashlib
import numpy as np
import database

# Import from new modular package
from mamcrawler.rag import MarkdownChunker, EmbeddingService, FAISSIndexManager
from mamcrawler.config import DEFAULT_RAG_CONFIG
from mamcrawler.utils import safe_read_markdown


def process_file(path: str, chunker: MarkdownChunker) -> tuple:
    """
    Process a single file: chunk, and prepare for embedding.

    Args:
        path: Path to markdown file
        chunker: MarkdownChunker instance

    Returns:
        Tuple of (chunks_to_embed, chunk_ids)
    """
    markdown_content = safe_read_markdown(path)

    # Check if file is new or modified
    file_hash = hashlib.sha256(markdown_content.encode()).hexdigest()
    existing = database.get_file_details(path)
    if existing and existing[1] == file_hash:
        return [], []  # No change

    # Add/update file record in SQLite
    file_id = database.insert_or_update_file(path, os.path.getmtime(path), file_hash)

    # Chunk the document using unified chunker
    chunks = chunker.chunk(markdown_content)

    chunks_to_embed = []
    chunk_ids = []

    for text_to_embed, raw_text, header_context in chunks:
        # Save chunk to SQLite and get its ID
        chunk_id = database.insert_chunk(file_id, raw_text, header_context)
        chunk_ids.append(chunk_id)
        chunks_to_embed.append(text_to_embed)

    return chunks_to_embed, chunk_ids


def main(target_dir: str = "guides_output"):
    """
    Main ingestion function.

    Args:
        target_dir: Directory containing markdown files to index
    """
    # Initialize database
    database.create_tables()

    # Initialize modular components
    chunker = MarkdownChunker()
    embedding_service = EmbeddingService()
    index_manager = FAISSIndexManager()

    # Process all .md files
    all_chunks = []
    all_chunk_ids = []
    files_processed = 0

    for root, dirs, files in os.walk(target_dir):
        for file in files:
            if file.endswith(".md"):
                path = os.path.join(root, file)
                print(f"Processing {path}")
                chunks, chunk_ids = process_file(path, chunker)
                if chunks:
                    files_processed += 1
                all_chunks.extend(chunks)
                all_chunk_ids.extend(chunk_ids)

    # Embed and index
    if all_chunks:
        print(f"Embedding {len(all_chunks)} chunks...")
        embeddings = embedding_service.encode(all_chunks)
        index_manager.add(embeddings, np.array(all_chunk_ids))
        index_manager.save()

    print(f"Indexed {len(all_chunks)} chunks from {files_processed} files")
    print(f"Total vectors in index: {index_manager.total_vectors}")


if __name__ == "__main__":
    main()
