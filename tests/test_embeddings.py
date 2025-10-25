#!/usr/bin/env python3
"""
Test script for EmbeddingGenerator.

This demonstrates how text becomes vectors and how similar texts
have similar embeddings.
"""

from src.github_delivery.embeddings import EmbeddingGenerator
import numpy as np

# Configuration
PROJECT_ID = "mozdata"  # Using mozdata project with Gemini API access


def cosine_similarity(vec1: list, vec2: list) -> float:
    """
    Calculate cosine similarity between two vectors.

    Cosine similarity measures how similar two vectors are:
    - 1.0 = identical
    - 0.0 = completely different
    - -1.0 = opposite

    Args:
        vec1: First vector
        vec2: Second vector

    Returns:
        Similarity score between -1 and 1
    """
    # Convert to numpy arrays for easier math
    v1 = np.array(vec1)
    v2 = np.array(vec2)

    # Cosine similarity = dot product / (magnitude1 * magnitude2)
    dot_product = np.dot(v1, v2)
    magnitude1 = np.linalg.norm(v1)
    magnitude2 = np.linalg.norm(v2)

    return dot_product / (magnitude1 * magnitude2)


def main():
    print("\n🧪 Testing EmbeddingGenerator\n")
    print("=" * 60)

    # Initialize the generator
    print("\n1. Initializing EmbeddingGenerator...")
    gen = EmbeddingGenerator(project_id=PROJECT_ID)
    print(f"   ✓ Using model: {gen.MODEL_NAME}")
    print(f"   ✓ Embedding dimension: {gen.EMBEDDING_DIMENSION}")

    # Test 1: Single embedding
    print("\n2. Generating single embedding...")
    text = "Fix authentication bug in login flow"
    embedding = gen.generate_embedding(text)

    print(f"   Text: '{text}'")
    print(f"   Embedding length: {len(embedding)}")
    print(f"   First 5 values: {embedding[:5]}")
    print(f"   Last 5 values: {embedding[-5:]}")

    # Test 2: Batch embeddings
    print("\n3. Generating batch embeddings...")
    texts = [
        "Fix authentication bug",           # Similar to each other
        "Resolve login issue",              # Similar to above
        "Add database migration script",    # Different topic
        "Update documentation",             # Different topic
        "",                                 # Empty (should return None)
    ]

    embeddings = gen.generate_batch_embeddings(texts)

    print(f"   Generated {len(embeddings)} embeddings:")
    for i, (text, emb) in enumerate(zip(texts, embeddings)):
        if emb:
            print(f"   [{i}] ✓ '{text[:40]}' → {len(emb)} dims")
        else:
            print(f"   [{i}] ✗ '{text[:40]}' → None (empty text)")

    # Test 3: Similarity comparison
    print("\n4. Comparing similarity between texts...")
    print("\n   Testing: Do similar texts have similar embeddings?")

    # Get embeddings for comparison (skip empty text)
    valid_texts = [t for t in texts if t.strip()]
    valid_embeddings = [e for e in embeddings if e is not None]

    if len(valid_embeddings) >= 2:
        # Compare first two (both about authentication/login)
        sim_similar = cosine_similarity(valid_embeddings[0], valid_embeddings[1])
        print(f"\n   '{texts[0]}'")
        print(f"   vs")
        print(f"   '{texts[1]}'")
        print(f"   Similarity: {sim_similar:.4f} (close to 1.0 = very similar)")

        if len(valid_embeddings) >= 3:
            # Compare first and third (different topics)
            sim_different = cosine_similarity(valid_embeddings[0], valid_embeddings[2])
            print(f"\n   '{texts[0]}'")
            print(f"   vs")
            print(f"   '{texts[2]}'")
            print(f"   Similarity: {sim_different:.4f} (lower = less similar)")

    print("\n" + "=" * 60)
    print("✅ Embedding generation works!")
    print("\n💡 Key Takeaway:")
    print("   - Similar texts have similar vectors (high cosine similarity)")
    print("   - This enables semantic search in BigQuery!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()