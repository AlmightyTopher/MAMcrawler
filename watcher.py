import os
import time
import hashlib
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import database

class MarkdownHandler(FileSystemEventHandler):
    def __init__(self, target_dir='guides_output'):
        self.target_dir = target_dir
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.dimension = 384

        # Load or create index
        if os.path.exists("index.faiss"):
            self.index = faiss.read_index("index.faiss")
        else:
            base_index = faiss.IndexFlatL2(self.dimension)
            self.index = faiss.IndexIDMap(base_index)

    def on_created(self, event):
        if event.is_directory or not event.src_path.endswith('.md'):
            return
        print(f"New file detected: {event.src_path}")
        self._process_file(event.src_path)

    def on_modified(self, event):
        if event.is_directory or not event.src_path.endswith('.md'):
            return
        print(f"Modified file detected: {event.src_path}")
        self._update_file(event.src_path)

    def on_deleted(self, event):
        if event.is_directory or not event.src_path.endswith('.md'):
            return
        print(f"Deleted file detected: {event.src_path}")
        self._delete_file(event.src_path)

    def _process_file(self, path):
        """Process new file."""
        chunks, chunk_ids = self._chunk_file(path)
        if chunks:
            embeddings = self.model.encode(chunks)
            faiss.normalize_L2(embeddings.astype(np.float32))
            self.index.add_with_ids(embeddings.astype(np.float32), np.array(chunk_ids))
            faiss.write_index(self.index, "index.faiss")

    def _update_file(self, path):
        """Update existing file."""
        # Get existing file_id and chunk_ids
        existing = database.get_file_details(path)
        if not existing:
            # New file, treat as created
            self._process_file(path)
            return

        file_id, old_hash = existing

        # Check if actually changed
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        new_hash = hashlib.sha256(content.encode()).hexdigest()

        if new_hash == old_hash:
            return  # No change

        # Remove old chunks from index
        chunk_ids = database.get_chunk_ids_for_file(file_id)
        if chunk_ids:
            self.index.remove_ids(np.array(chunk_ids))

        # Delete old records
        database.delete_file_records(file_id)

        # Process as new
        self._process_file(path)

    def _delete_file(self, path):
        """Delete file from index."""
        existing = database.get_file_details(path)
        if existing:
            file_id, _ = existing
            chunk_ids = database.get_chunk_ids_for_file(file_id)
            if chunk_ids:
                self.index.remove_ids(np.array(chunk_ids))
            database.delete_file_records(file_id)
            faiss.write_index(self.index, "index.faiss")

    def _chunk_file(self, path):
        """Chunk file and return chunks with IDs."""
        from langchain_text_splitters.markdown import MarkdownHeaderTextSplitter

        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        file_hash = hashlib.sha256(content.encode()).hexdigest()
        file_id = database.insert_or_update_file(path, os.path.getmtime(path), file_hash)

        headers_to_split_on = [("#", "H1"), ("##", "H2"), ("###", "H3")]
        splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=headers_to_split_on, strip_headers=False
        )
        splits = splitter.split_text(content)

        chunks = []
        chunk_ids = []

        for split in splits:
            header_context = " > ".join(split.metadata.values())
            text_to_embed = f"CONTEXT: {header_context}\n\nCONTENT:\n{split.page_content}"
            chunk_id = database.insert_chunk(file_id, split.page_content, header_context)
            chunks.append(text_to_embed)
            chunk_ids.append(chunk_id)

        return chunks, chunk_ids

def main():
    database.create_tables()

    target_dir = 'guides_output'
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)

    event_handler = MarkdownHandler(target_dir)
    observer = Observer()
    observer.schedule(event_handler, target_dir, recursive=True)
    observer.start()

    print(f"Watching {target_dir} for changes...")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("\nStopping watcher...")
    observer.join()

if __name__ == "__main__":
    main()