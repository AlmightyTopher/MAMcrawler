import os
import hashlib
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from langchain_text_splitters.markdown import MarkdownHeaderTextSplitter
import database

def process_file(path, db_conn):
    """Process a single file: chunk, embed, and store."""
    with open(path, 'r', encoding='utf-8') as f:
        markdown_content = f.read()

    # 1. Check if file is new or modified
    file_hash = hashlib.sha256(markdown_content.encode()).hexdigest()
    existing = database.get_file_details(path)
    if existing and existing[1] == file_hash:
        return [], []  # No change

    # 2. Add/update file record in SQLite
    file_id = database.insert_or_update_file(path, os.path.getmtime(path), file_hash)

    # 3. Chunk the document
    headers_to_split_on = [("#", "H1"), ("##", "H2"), ("###", "H3")]
    markdown_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=headers_to_split_on, strip_headers=False
    )
    splits = markdown_splitter.split_text(markdown_content)

    chunks_to_embed = []
    chunk_ids = []

    for split in splits:
        header_context = " > ".join(split.metadata.values())

        # This is the "Embed the Headers" pattern
        text_to_embed = f"CONTEXT: {header_context}\n\nCONTENT:\n{split.page_content}"

        # 4. Save chunk to SQLite and get its ID
        chunk_id = database.insert_chunk(file_id, split.page_content, header_context)
        chunk_ids.append(chunk_id)
        chunks_to_embed.append(text_to_embed)

    return chunks_to_embed, chunk_ids

def main(target_dir='guides_output'):
    """Main ingestion function."""
    # Initialize database
    database.create_tables()

    # Load or create FAISS index
    dimension = 384  # all-MiniLM-L6-v2 dimension
    if os.path.exists("index.faiss"):
        index = faiss.read_index("index.faiss")
    else:
        base_index = faiss.IndexFlatL2(dimension)
        index = faiss.IndexIDMap(base_index)

    # Load embedding model
    model = SentenceTransformer('all-MiniLM-L6-v2')

    # Process all .md files
    all_chunks = []
    all_chunk_ids = []

    for root, dirs, files in os.walk(target_dir):
        for file in files:
            if file.endswith('.md'):
                path = os.path.join(root, file)
                print(f"Processing {path}")
                chunks, chunk_ids = process_file(path, None)  # db_conn handled inside
                all_chunks.extend(chunks)
                all_chunk_ids.extend(chunk_ids)

    # Embed and index
    if all_chunks:
        embeddings = model.encode(all_chunks)
        faiss.normalize_L2(embeddings.astype(np.float32))
        index.add_with_ids(embeddings.astype(np.float32), np.array(all_chunk_ids))

    # Save index
    faiss.write_index(index, "index.faiss")
    print(f"Indexed {len(all_chunks)} chunks from {len(all_chunk_ids)} files")

if __name__ == "__main__":
    main()