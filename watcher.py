"""
File system watcher for automatic RAG index updates.
Uses modular components from mamcrawler package.
"""

import os
import time
import hashlib
import numpy as np
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

import database
from mamcrawler.rag import MarkdownChunker, EmbeddingService, FAISSIndexManager


class MarkdownHandler(FileSystemEventHandler):
    """Handles markdown file changes and updates the RAG index."""

    def __init__(self, target_dir: str = 'guides_output'):
        """
        Initialize the handler.

        Args:
            target_dir: Directory to watch
        """
        self.target_dir = target_dir

        # Initialize modular components (singletons)
        self.chunker = MarkdownChunker()
        self.embedding_service = EmbeddingService()
        self.index_manager = FAISSIndexManager()

    def on_created(self, event):
        """Handle new file creation."""
        if event.is_directory or not event.src_path.endswith('.md'):
            return
        print(f"New file detected: {event.src_path}")
        self._process_file(event.src_path)

    def on_modified(self, event):
        """Handle file modification."""
        if event.is_directory or not event.src_path.endswith('.md'):
            return
        print(f"Modified file detected: {event.src_path}")
        self._update_file(event.src_path)

    def on_deleted(self, event):
        """Handle file deletion."""
        if event.is_directory or not event.src_path.endswith('.md'):
            return
        print(f"Deleted file detected: {event.src_path}")
        self._delete_file(event.src_path)

    def _process_file(self, path: str):
        """Process new file and add to index."""
        chunks, chunk_ids = self._chunk_file(path)
        if chunks:
            embeddings = self.embedding_service.encode(chunks)
            self.index_manager.add(embeddings, np.array(chunk_ids))
            self.index_manager.save()
            print(f"Added {len(chunks)} chunks from {path}")

    def _update_file(self, path: str):
        """Update existing file in index."""
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
            self.index_manager.remove(np.array(chunk_ids))

        # Delete old records
        database.delete_file_records(file_id)

        # Process as new
        self._process_file(path)

    def _delete_file(self, path: str):
        """Delete file from index."""
        existing = database.get_file_details(path)
        if existing:
            file_id, _ = existing
            chunk_ids = database.get_chunk_ids_for_file(file_id)
            if chunk_ids:
                self.index_manager.remove(np.array(chunk_ids))
            database.delete_file_records(file_id)
            self.index_manager.save()
            print(f"Removed {len(chunk_ids)} chunks for {path}")

    def _chunk_file(self, path: str) -> tuple:
        """
        Chunk file and return chunks with IDs.

        Args:
            path: Path to markdown file

        Returns:
            Tuple of (chunks_to_embed, chunk_ids)
        """
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        file_hash = hashlib.sha256(content.encode()).hexdigest()
        file_id = database.insert_or_update_file(path, os.path.getmtime(path), file_hash)

        # Use unified chunker
        chunk_data = self.chunker.chunk(content)

        chunks = []
        chunk_ids = []

        for text_to_embed, raw_text, header_context in chunk_data:
            chunk_id = database.insert_chunk(file_id, raw_text, header_context)
            chunks.append(text_to_embed)
            chunk_ids.append(chunk_id)

        return chunks, chunk_ids


def main():
    """Main entry point for file watcher."""
    database.create_tables()

    target_dir = 'guides_output'
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)

    event_handler = MarkdownHandler(target_dir)
    observer = Observer()
    observer.schedule(event_handler, target_dir, recursive=True)
    observer.start()

    print(f"Watching {target_dir} for changes...")
    print("Press Ctrl+C to stop")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("\nStopping watcher...")
    observer.join()


if __name__ == "__main__":
    main()
