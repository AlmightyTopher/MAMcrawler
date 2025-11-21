"""
Memory-Efficient Audio Processing Components
Implements proper resource management, memory leak prevention, and comprehensive exception handling.
"""

import asyncio
import gc
import logging
import os
import psutil
import time
from typing import Dict, List, Optional, Any, Generator, Iterator
from dataclasses import dataclass
from contextlib import asynccontextmanager, contextmanager
from pathlib import Path
import weakref
import threading
from queue import Queue, Empty
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

class MemoryMonitor:
    """Monitor memory usage and prevent memory leaks."""
    
    def __init__(self, warning_threshold_mb: int = 500):
        self.warning_threshold_mb = warning_threshold_mb
        self.baseline_memory = self._get_memory_usage()
        self.peak_memory = self.baseline_memory
        self.allocations = []
        self._lock = threading.Lock()
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / 1024 / 1024
    
    def record_allocation(self, size: int, context: str):
        """Record memory allocation for tracking."""
        with self._lock:
            self.allocations.append({
                'size': size,
                'context': context,
                'timestamp': time.time(),
                'thread_id': threading.get_ident()
            })
            
            # Keep only last 1000 allocations
            if len(self.allocations) > 1000:
                self.allocations = self.allocations[-1000:]
            
            current_memory = self._get_memory_usage()
            if current_memory > self.peak_memory:
                self.peak_memory = current_memory
    
    def check_memory_health(self) -> Dict[str, Any]:
        """Check current memory health and return status."""
        current_memory = self._get_memory_usage()
        memory_growth = current_memory - self.baseline_memory
        
        status = {
            'current_mb': round(current_memory, 2),
            'baseline_mb': round(self.baseline_memory, 2),
            'peak_mb': round(self.peak_memory, 2),
            'growth_mb': round(memory_growth, 2),
            'warning_threshold_mb': self.warning_threshold_mb,
            'status': 'healthy'
        }
        
        if memory_growth > self.warning_threshold_mb:
            status['status'] = 'warning'
        elif memory_growth > self.warning_threshold_mb * 2:
            status['status'] = 'critical'
        
        return status
    
    def force_garbage_collection(self):
        """Force garbage collection and log results."""
        before_memory = self._get_memory_usage()
        gc.collect()
        after_memory = self._get_memory_usage()
        
        logger.info(f"GC: Memory before {before_memory:.2f}MB, after {after_memory:.2f}MB")
        return after_memory - before_memory

# Global memory monitor
memory_monitor = MemoryMonitor()

class AudioProcessingError(Exception):
    """Base exception for audio processing errors."""
    pass

class MemoryEfficientAudioProcessor:
    """Memory-efficient audio processor with comprehensive resource management."""
    
    def __init__(self, chunk_size: int = 8192, max_memory_mb: int = 200):
        self.chunk_size = chunk_size
        self.max_memory_mb = max_memory_mb
        self._active_processors = weakref.WeakSet()
        self._shutdown_event = asyncio.Event()
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="AudioProcessor")
        
        # Register for cleanup
        self._active_processors.add(self)
        
        logger.info(f"Initialized AudioProcessor with chunk_size={chunk_size}, max_memory_mb={max_memory_mb}")
    
    def __del__(self):
        """Cleanup when processor is destroyed."""
        self.shutdown()
    
    async def shutdown(self):
        """Shutdown the audio processor and cleanup resources."""
        if not self._shutdown_event.is_set():
            self._shutdown_event.set()
            
        if hasattr(self, '_executor'):
            self._executor.shutdown(wait=True)
        
        logger.info("AudioProcessor shutdown complete")
    
    @asynccontextmanager
    async def process_audio_stream(self, audio_data: bytes):
        """Process audio data in a memory-efficient streaming manner."""
        processor_id = id(self)
        self._active_processors.add(self)
        
        try:
            # Check memory before processing
            memory_status = memory_monitor.check_memory_health()
            if memory_status['current_mb'] > self.max_memory_mb:
                logger.warning(f"Memory usage high: {memory_status['current_mb']}MB")
                await self._cleanup_memory()
            
            yield self._process_audio_chunks(audio_data)
            
        except Exception as e:
            logger.error(f"Audio processing failed: {e}")
            raise AudioProcessingError(f"Failed to process audio: {e}")
        finally:
            # Force cleanup after processing
            await self._cleanup_memory()
    
    def _process_audio_chunks(self, audio_data: bytes) -> Iterator[bytes]:
        """Process audio data in chunks to minimize memory usage."""
        offset = 0
        total_size = len(audio_data)
        
        while offset < total_size:
            # Calculate chunk size (don't exceed max memory)
            remaining_size = total_size - offset
            chunk_size = min(self.chunk_size, remaining_size, self.max_memory_mb * 1024 * 1024)
            
            # Extract chunk
            chunk = audio_data[offset:offset + chunk_size]
            offset += chunk_size
            
            # Record allocation
            memory_monitor.record_allocation(len(chunk), f"audio_chunk_{len(chunk)}")
            
            # Yield chunk for processing
            yield chunk
            
            # Force garbage collection periodically
            if offset % (self.chunk_size * 10) == 0:
                gc.collect()
    
    async def _cleanup_memory(self):
        """Cleanup memory and check for leaks."""
        memory_freed = memory_monitor.force_garbage_collection()
        
        # Check for leaks
        active_processors = len(self._active_processors)
        if active_processors > 10:
            logger.warning(f"High number of active processors: {active_processors}")
        
        return memory_freed
    
    async def process_audio_batch(self, audio_files: List[Path]) -> Dict[str, Any]:
        """Process multiple audio files efficiently with concurrency control."""
        results = {}
        semaphore = asyncio.Semaphore(3)  # Limit concurrent processing
        
        async def process_single_file(file_path: Path):
            async with semaphore:
                try:
                    return await self._process_single_audio_file(file_path)
                except Exception as e:
                    logger.error(f"Failed to process {file_path}: {e}")
                    return {
                        'file': str(file_path),
                        'success': False,
                        'error': str(e)
                    }
        
        # Process files with controlled concurrency
        tasks = [process_single_file(file_path) for file_path in audio_files]
        file_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Compile results
        for result in file_results:
            if isinstance(result, dict):
                results[result.get('file', 'unknown')] = result
        
        return results
    
    async def _process_single_audio_file(self, file_path: Path) -> Dict[str, Any]:
        """Process a single audio file with proper error handling."""
        start_time = time.time()
        
        try:
            # Validate file
            if not file_path.exists():
                raise FileNotFoundError(f"Audio file not found: {file_path}")
            
            file_size = file_path.stat().st_size
            if file_size > 100 * 1024 * 1024:  # 100MB limit
                raise ValueError(f"Audio file too large: {file_size / 1024 / 1024:.2f}MB")
            
            # Read file in chunks to minimize memory usage
            processed_data = b""
            chunk_count = 0
            
            with open(file_path, 'rb') as audio_file:
                async with self.process_audio_stream(b"") as chunk_processor:
                    while True:
                        chunk = audio_file.read(self.chunk_size)
                        if not chunk:
                            break
                        
                        # Process chunk
                        processed_chunk = await self._process_audio_chunk(chunk)
                        processed_data += processed_chunk
                        chunk_count += 1
                        
                        # Memory check every 100 chunks
                        if chunk_count % 100 == 0:
                            memory_status = memory_monitor.check_memory_health()
                            if memory_status['current_mb'] > self.max_memory_mb * 1.5:
                                logger.warning("Memory usage critical, forcing cleanup")
                                await self._cleanup_memory()
            
            processing_time = time.time() - start_time
            
            # Record memory allocation
            memory_monitor.record_allocation(
                len(processed_data), 
                f"processed_audio_{file_path.name}"
            )
            
            logger.info(f"Successfully processed {file_path.name}: "
                       f"{chunk_count} chunks, {processing_time:.2f}s")
            
            return {
                'file': str(file_path),
                'success': True,
                'file_size': file_size,
                'processed_size': len(processed_data),
                'chunks_processed': chunk_count,
                'processing_time': processing_time,
                'memory_usage': memory_monitor.check_memory_health()
            }
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Error processing {file_path}: {e}")
            
            return {
                'file': str(file_path),
                'success': False,
                'error': str(e),
                'processing_time': processing_time
            }
    
    async def _process_audio_chunk(self, chunk: bytes) -> bytes:
        """Process a single audio chunk (placeholder for actual audio processing)."""
        # Simulate audio processing
        await asyncio.sleep(0.001)  # Simulate processing time
        
        # Return processed chunk (in real implementation, this would be actual audio processing)
        return chunk

class AudioMetadataExtractor:
    """Memory-efficient audio metadata extractor."""
    
    def __init__(self):
        self._cache = {}
        self._cache_size_limit = 100
        self._extraction_lock = asyncio.Lock()
    
    async def extract_metadata(self, audio_file: Path) -> Dict[str, Any]:
        """Extract metadata from audio file with caching."""
        file_key = str(audio_file.resolve())
        
        async with self._extraction_lock:
            # Check cache
            if file_key in self._cache:
                cache_entry = self._cache[file_key]
                if time.time() - cache_entry['timestamp'] < 3600:  # 1 hour cache
                    logger.debug(f"Cache hit for {audio_file.name}")
                    return cache_entry['metadata']
            
            # Extract metadata
            try:
                metadata = await self._extract_metadata_unsafe(audio_file)
                
                # Cache result
                self._cache[file_key] = {
                    'metadata': metadata,
                    'timestamp': time.time()
                }
                
                # Limit cache size
                if len(self._cache) > self._cache_size_limit:
                    oldest_key = min(self._cache.keys(), 
                                   key=lambda k: self._cache[k]['timestamp'])
                    del self._cache[oldest_key]
                
                return metadata
                
            except Exception as e:
                logger.error(f"Failed to extract metadata from {audio_file}: {e}")
                raise
    
    async def _extract_metadata_unsafe(self, audio_file: Path) -> Dict[str, Any]:
        """Extract metadata without caching (actual implementation)."""
        # Placeholder implementation
        # In real implementation, this would use mutagen or similar library
        
        await asyncio.sleep(0.01)  # Simulate extraction time
        
        return {
            'title': audio_file.stem,
            'format': audio_file.suffix.lower(),
            'size': audio_file.stat().st_size,
            'modified': audio_file.stat().st_mtime,
            'duration': 0,  # Would be extracted from audio file
            'bitrate': 0,   # Would be extracted from audio file
            'sample_rate': 0  # Would be extracted from audio file
        }
    
    def clear_cache(self):
        """Clear metadata cache."""
        self._cache.clear()
        logger.info("Metadata cache cleared")

@contextmanager
def audio_processing_context(max_memory_mb: int = 200):
    """Context manager for safe audio processing with memory monitoring."""
    processor = None
    try:
        processor = MemoryEfficientAudioProcessor(max_memory_mb=max_memory_mb)
        logger.info("Audio processing context started")
        yield processor
    except Exception as e:
        logger.error(f"Audio processing context error: {e}")
        raise
    finally:
        if processor:
            # Cleanup resources
            asyncio.create_task(processor.shutdown())
        logger.info("Audio processing context ended")

async def process_audio_directory(directory: Path) -> Dict[str, Any]:
    """Process all audio files in a directory with memory management."""
    if not directory.exists():
        raise ValueError(f"Directory does not exist: {directory}")
    
    # Find audio files
    audio_extensions = {'.mp3', '.flac', '.wav', '.m4a', '.aac', '.ogg'}
    audio_files = [f for f in directory.iterdir() 
                  if f.is_file() and f.suffix.lower() in audio_extensions]
    
    if not audio_files:
        logger.warning(f"No audio files found in {directory}")
        return {'files_processed': 0, 'results': {}}
    
    logger.info(f"Found {len(audio_files)} audio files to process")
    
    # Process with memory management
    with audio_processing_context(max_memory_mb=300) as processor:
        results = await processor.process_audio_batch(audio_files)
        
        # Final memory cleanup
        memory_status = memory_monitor.check_memory_health()
        logger.info(f"Processing complete. Final memory status: {memory_status}")
        
        return {
            'files_found': len(audio_files),
            'files_processed': len(results),
            'results': results,
            'memory_status': memory_status
        }

if __name__ == "__main__":
    # Example usage
    async def main():
        test_dir = Path("test_audio")
        test_dir.mkdir(exist_ok=True)
        
        try:
            results = await process_audio_directory(test_dir)
            print(json.dumps(results, indent=2))
        except Exception as e:
            print(f"Error: {e}")
    
    asyncio.run(main())