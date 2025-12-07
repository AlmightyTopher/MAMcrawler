# test_rag_system.py
# Comprehensive validation of the RAG system (chunking, embeddings, indexing)

import sys
import os
import tempfile
import numpy as np
from pathlib import Path

sys.path.insert(0, os.path.abspath('.'))

from mamcrawler.rag.chunking import MarkdownChunker, get_chunker
from mamcrawler.rag.embeddings import EmbeddingService, get_embedding_service
from mamcrawler.rag.indexing import FAISSIndexManager, reset_manager
from mamcrawler.config import RAGConfig, DEFAULT_RAG_CONFIG

# Sample markdown content for testing
SAMPLE_MARKDOWN = """# Main Title

This is introductory content under the main title.

## Section 1

Content for section 1 with some details.

### Subsection 1.1

Detailed content in subsection 1.1.

### Subsection 1.2

More detailed content here.

## Section 2

Content for section 2.

# Another Main Title

Content under another main title.
"""

def test_markdown_chunking():
    """Test markdown chunking functionality"""
    print("\n=== Testing Markdown Chunking ===")

    # Test 1: Basic chunking
    print("\n  Test 1: Basic markdown chunking")
    chunker = MarkdownChunker()
    chunks = chunker.chunk(SAMPLE_MARKDOWN)

    if len(chunks) == 0:
        print("    ❌ FAIL: No chunks generated")
        return False

    print(f"    ✓ Generated {len(chunks)} chunks")

    # Verify chunk structure
    first_chunk = chunks[0]
    if len(first_chunk) != 3:
        print(f"    ❌ FAIL: Chunk should have 3 elements, got {len(first_chunk)}")
        return False

    text_to_embed, raw_text, header_context = first_chunk
    print(f"    ✓ Chunk structure valid")
    print(f"    ✓ Header context example: '{header_context[:50]}'")

    # Test 2: Empty content
    print("\n  Test 2: Empty content")
    empty_chunks = chunker.chunk("")
    print(f"    ✓ Empty content handled: {len(empty_chunks)} chunks")

    # Test 3: Content with no headers
    print("\n  Test 3: Content with no headers")
    no_header_content = "Just plain text without any headers."
    no_header_chunks = chunker.chunk(no_header_content)
    print(f"    ✓ No-header content handled: {len(no_header_chunks)} chunks")

    # Test 4: Nested headers (verify context is built)
    print("\n  Test 4: Nested header context")
    nested_markdown = """# Level 1
## Level 2
### Level 3
Content at level 3"""

    nested_chunks = chunker.chunk(nested_markdown)
    if len(nested_chunks) > 0:
        _, _, context = nested_chunks[-1]
        if ">" in context:  # Should have breadcrumb
            print(f"    ✓ Header breadcrumb built: '{context}'")
        else:
            print(f"    ⚠️  Single level context: '{context}'")
    else:
        print(f"    ⚠️  No chunks generated from nested markdown")

    # Test 5: Unicode content
    print("\n  Test 5: Unicode content")
    unicode_markdown = """# 日本語タイトル

Content with émojis 🎵 and spëcial çharacters."""

    unicode_chunks = chunker.chunk(unicode_markdown)
    print(f"    ✓ Unicode content handled: {len(unicode_chunks)} chunks")

    # Test 6: Singleton behavior
    print("\n  Test 6: Chunker singleton")
    chunker1 = get_chunker()
    chunker2 = get_chunker()
    if chunker1 is chunker2:
        print("    ✓ get_chunker() returns singleton")
    else:
        print("    ⚠️  get_chunker() creates new instances")

    print("\n  ✓ All chunking tests passed")
    return True

def test_embedding_service():
    """Test embedding generation"""
    print("\n=== Testing Embedding Service ===")

    # Test 1: Initialize service
    print("\n  Test 1: Initialize embedding service")
    print("    (This will download the model if not cached - may take time)")
    service = EmbeddingService()
    print(f"    ✓ Service initialized")
    print(f"    ✓ Model dimension: {service.dimension}")

    if service.dimension != 384:
        print(f"    ❌ FAIL: Expected dimension 384, got {service.dimension}")
        return False

    # Test 2: Encode single text
    print("\n  Test 2: Encode single text")
    texts = ["This is a test sentence for embedding."]
    embeddings = service.encode(texts)

    if embeddings.shape != (1, 384):
        print(f"    ❌ FAIL: Wrong shape {embeddings.shape}, expected (1, 384)")
        return False
    print(f"    ✓ Embedding shape: {embeddings.shape}")
    print(f"    ✓ Embedding dtype: {embeddings.dtype}")

    # Test 3: Verify normalization
    print("\n  Test 3: Verify L2 normalization")
    norm = np.linalg.norm(embeddings[0])
    if not np.isclose(norm, 1.0, atol=1e-5):
        print(f"    ❌ FAIL: Embedding not normalized, norm={norm}")
        return False
    print(f"    ✓ Embedding normalized: norm={norm:.6f}")

    # Test 4: Encode multiple texts
    print("\n  Test 4: Encode multiple texts")
    multi_texts = [
        "First sentence.",
        "Second sentence.",
        "Third sentence."
    ]
    multi_embeddings = service.encode(multi_texts)

    if multi_embeddings.shape != (3, 384):
        print(f"    ❌ FAIL: Wrong shape {multi_embeddings.shape}, expected (3, 384)")
        return False
    print(f"    ✓ Multiple embeddings: {multi_embeddings.shape}")

    # Test 5: Encode query (convenience method)
    print("\n  Test 5: Encode query")
    query_embedding = service.encode_query("What is this about?")
    if query_embedding.shape != (1, 384):
        print(f"    ❌ FAIL: Query shape {query_embedding.shape}, expected (1, 384)")
        return False
    print(f"    ✓ Query embedding: {query_embedding.shape}")

    # Test 6: Empty list handling
    print("\n  Test 6: Empty text list")
    empty_embeddings = service.encode([])
    if empty_embeddings.shape != (0, 384):
        print(f"    ❌ FAIL: Empty shape {empty_embeddings.shape}, expected (0, 384)")
        return False
    print(f"    ✓ Empty list handled: {empty_embeddings.shape}")

    # Test 7: Singleton behavior
    print("\n  Test 7: Embedding service singleton")
    service2 = EmbeddingService()
    if service is not service2:
        print("    ❌ FAIL: EmbeddingService is not a singleton")
        return False
    print("    ✓ EmbeddingService is a singleton")

    # Test 8: Unicode handling
    print("\n  Test 8: Unicode text encoding")
    unicode_text = ["日本語のテキスト with émojis 🎵"]
    unicode_emb = service.encode(unicode_text)
    if unicode_emb.shape != (1, 384):
        print(f"    ❌ FAIL: Unicode encoding failed")
        return False
    print(f"    ✓ Unicode text encoded: {unicode_emb.shape}")

    print("\n  ✓ All embedding tests passed")
    return True

def test_faiss_indexing():
    """Test FAISS index operations"""
    print("\n=== Testing FAISS Indexing ===")

    # Use temporary directory for index
    with tempfile.TemporaryDirectory() as temp_dir:
        index_path = os.path.join(temp_dir, "test_index.faiss")
        print(f"\n  Using temp index: {index_path}")

        # Reset singleton to use temp path
        reset_manager()

        # Test 1: Create new index
        print("\n  Test 1: Create new index")
        manager = FAISSIndexManager(index_path=index_path)
        print(f"    ✓ Index created")
        print(f"    ✓ Initial vector count: {manager.total_vectors}")

        if manager.total_vectors != 0:
            print(f"    ❌ FAIL: New index should have 0 vectors")
            return False

        # Test 2: Add vectors
        print("\n  Test 2: Add vectors to index")
        # Create some dummy embeddings
        embeddings = np.random.rand(5, 384).astype(np.float32)
        # Normalize for FAISS
        import faiss
        faiss.normalize_L2(embeddings)

        ids = np.array([1, 2, 3, 4, 5], dtype=np.int64)
        manager.add(embeddings, ids)

        if manager.total_vectors != 5:
            print(f"    ❌ FAIL: Expected 5 vectors, got {manager.total_vectors}")
            return False
        print(f"    ✓ Added 5 vectors, total: {manager.total_vectors}")

        # Test 3: Search
        print("\n  Test 3: Search for similar vectors")
        # Use first embedding as query
        query = embeddings[0:1]
        distances, result_ids = manager.search(query, k=3)

        print(f"    ✓ Search returned: {distances.shape}")
        print(f"    ✓ Result IDs: {result_ids[0]}")
        print(f"    ✓ Distances: {distances[0]}")

        # First result should be itself (ID 1) with distance ~0
        if result_ids[0][0] != 1:
            print(f"    ⚠️  Expected first result to be ID 1, got {result_ids[0][0]}")
        elif distances[0][0] > 0.01:
            print(f"    ⚠️  Expected distance ~0 for self, got {distances[0][0]}")
        else:
            print(f"    ✓ Self-search correct: ID={result_ids[0][0]}, dist={distances[0][0]:.6f}")

        # Test 4: Save and load
        print("\n  Test 4: Save and load index")
        manager.save()

        if not Path(index_path).exists():
            print("    ❌ FAIL: Index file not saved")
            return False
        print(f"    ✓ Index saved to disk")

        # Load in new manager
        reset_manager()
        manager2 = FAISSIndexManager(index_path=index_path)

        if manager2.total_vectors != 5:
            print(f"    ❌ FAIL: Loaded index has {manager2.total_vectors} vectors, expected 5")
            return False
        print(f"    ✓ Index loaded: {manager2.total_vectors} vectors")

        # Test 5: Remove vectors
        print("\n  Test 5: Remove vectors")
        manager2.remove(np.array([2, 4], dtype=np.int64))

        if manager2.total_vectors != 3:
            print(f"    ❌ FAIL: Expected 3 vectors after removal, got {manager2.total_vectors}")
            return False
        print(f"    ✓ Removed 2 vectors, remaining: {manager2.total_vectors}")

        # Test 6: Empty operations
        print("\n  Test 6: Empty operations")
        manager2.add(np.array([]).reshape(0, 384).astype(np.float32), np.array([], dtype=np.int64))
        manager2.remove(np.array([], dtype=np.int64))
        print(f"    ✓ Empty operations handled")

        # Test 7: Search with 1D query
        print("\n  Test 7: Search with 1D query (auto-reshape)")
        query_1d = embeddings[0]  # 1D array
        distances, result_ids = manager2.search(query_1d, k=2)
        print(f"    ✓ 1D query handled: {distances.shape}")

    print("\n  ✓ All indexing tests passed")
    return True

def test_rag_integration():
    """Test integrated RAG pipeline"""
    print("\n=== Testing RAG Integration ===")

    # Test 1: Chunk → Embed → Index → Search pipeline
    print("\n  Test 1: Complete RAG pipeline")

    # Chunk markdown
    chunker = MarkdownChunker()
    chunks = chunker.chunk(SAMPLE_MARKDOWN)
    print(f"    ✓ Chunked markdown: {len(chunks)} chunks")

    if len(chunks) == 0:
        print("    ⚠️  No chunks to test pipeline")
        return True

    # Extract texts for embedding
    texts_to_embed = [chunk[0] for chunk in chunks]  # text_to_embed
    print(f"    ✓ Extracted {len(texts_to_embed)} texts")

    # Generate embeddings
    service = get_embedding_service()
    embeddings = service.encode(texts_to_embed[:3])  # Just test first 3
    print(f"    ✓ Generated embeddings: {embeddings.shape}")

    # Create temp index and add
    with tempfile.TemporaryDirectory() as temp_dir:
        reset_manager()
        index_path = os.path.join(temp_dir, "pipeline_test.faiss")
        manager = FAISSIndexManager(index_path=index_path)

        ids = np.array([100, 101, 102], dtype=np.int64)
        manager.add(embeddings, ids)
        print(f"    ✓ Indexed {manager.total_vectors} vectors")

        # Search with a query
        query = "What is section 1 about?"
        query_emb = service.encode_query(query)
        distances, result_ids = manager.search(query_emb, k=2)

        print(f"    ✓ Search results: IDs={result_ids[0]}, distances={distances[0]}")
        print(f"    ✓ Pipeline complete!")

    print("\n  ✓ RAG integration test passed")
    return True

def main():
    """Run all RAG system tests"""
    print("="*60)
    print("RAG System Validation")
    print("="*60)
    print("\nNote: First run will download embedding model (~80MB)")
    print("This may take a few minutes...")

    tests = [
        ("Markdown Chunking", test_markdown_chunking),
        ("Embedding Service", test_embedding_service),
        ("FAISS Indexing", test_faiss_indexing),
        ("RAG Integration", test_rag_integration),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ EXCEPTION in {name}: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))

    # Summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} | {name}")

    print("\n" + "="*60)
    print(f"Results: {passed}/{total} tests passed")
    print("="*60)

    if passed == total:
        print("\n🎉 All RAG system tests passed!")
        return True
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
