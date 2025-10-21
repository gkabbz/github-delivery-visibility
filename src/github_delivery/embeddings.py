"""
Embedding generation using Vertex AI.

This module converts text into vector embeddings for semantic search.
Uses Google's text-embedding-004 model which produces 768-dimensional vectors.
"""

from typing import List, Optional
from google import genai
from google.genai import types


class EmbeddingGenerator:
    """
    Generates vector embeddings from text using Vertex AI.

    Vector embeddings are arrays of numbers that represent the semantic meaning
    of text. Similar texts will have similar vectors (measured by cosine similarity).

    Example:
        >>> gen = EmbeddingGenerator()  # Uses mozdata by default
        >>> embedding = gen.generate_embedding("Fix authentication bug")
        >>> len(embedding)
        768
    """

    # Model configuration
    MODEL_NAME = "text-embedding-004"
    EMBEDDING_DIMENSION = 768

    def __init__(
        self,
        project_id: str = "mozdata",
        location: str = "us-west1"
    ):
        """
        Initialize the embedding generator.

        Args:
            project_id: GCP project ID (default: "mozdata")
            location: GCP region for Vertex AI (default: "us-west1")

        Note:
            Uses the new google.genai SDK which works with Gemini API access.
        """
        self.project_id = project_id
        self.location = location

        # Initialize Vertex AI client using the new genai SDK
        # vertexai=True tells it to use Vertex AI backend (not direct API)
        # This works with the Gemini API permissions we have
        self.client = genai.Client(
            vertexai=True,
            project=project_id,
            location=location,
            http_options=types.HttpOptions(api_version="v1")
        )

        # Print confirmation (helpful for debugging)
        print(f"✓ EmbeddingGenerator initialized")
        print(f"  Project: {project_id}")
        print(f"  Region: {location}")
        print(f"  Model: {self.MODEL_NAME}")

    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate a 768-dimensional embedding for a single text.

        How it works:
        1. Text is sent to Vertex AI via the genai SDK
        2. The model processes it through neural network layers
        3. Returns a 768-number vector representing the meaning

        Args:
            text: Input text to embed (e.g., PR description)

        Returns:
            List of 768 floating-point numbers

        Raises:
            ValueError: If text is empty or None

        Example:
            >>> embedding = gen.generate_embedding("Add logging to API")
            >>> print(f"Embedding dimension: {len(embedding)}")
            Embedding dimension: 768
            >>> print(f"First 3 values: {embedding[:3]}")
            First 3 values: [0.0234, -0.0567, 0.0891]
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        # Call Vertex AI to get embedding using the new SDK
        # embed_content() is the new method (replaces get_embeddings)
        response = self.client.models.embed_content(
            model=self.MODEL_NAME,
            contents=[text]
        )

        # Extract the embedding from the response
        # The response contains a list of embeddings (one per input text)
        # We only sent one text, so we get the first embedding
        embedding = response.embeddings[0].values

        # Print for learning (shows what we got back)
        print(f"✓ Generated embedding for text (length: {len(text)} chars)")
        print(f"  Embedding dimension: {len(embedding)}")

        return embedding

    def generate_batch_embeddings(
        self,
        texts: List[str],
        batch_size: int = 5
    ) -> List[Optional[List[float]]]:
        """
        Generate embeddings for multiple texts in batches.

        Why batching?
        - API has rate limits (requests per minute)
        - Batching is more efficient than one-at-a-time
        - We use batch_size=5 as a conservative default

        Args:
            texts: List of texts to embed
            batch_size: Number of texts per API call (default: 5)

        Returns:
            List of embeddings (same order as input texts)
            None for any text that failed to embed

        Example:
            >>> texts = ["Fix bug", "Add feature", "Update docs"]
            >>> embeddings = gen.generate_batch_embeddings(texts)
            >>> len(embeddings)
            3
            >>> len(embeddings[0])  # Each embedding has 768 dimensions
            768
        """
        all_embeddings: List[Optional[List[float]]] = []

        print(f"✓ Generating embeddings for {len(texts)} texts in batches of {batch_size}")

        # Process texts in batches
        for i in range(0, len(texts), batch_size):
            # Get a batch of texts
            batch = texts[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(texts) + batch_size - 1) // batch_size

            print(f"  Processing batch {batch_num}/{total_batches}...")

            # Filter out empty strings (they would cause errors)
            # Keep track of which positions had valid text
            valid_texts = []
            valid_indices = []

            for j, text in enumerate(batch):
                if text and text.strip():
                    valid_texts.append(text)
                    valid_indices.append(j)

            # Generate embeddings for valid texts
            if valid_texts:
                try:
                    # Call Vertex AI with the batch
                    response = self.client.models.embed_content(
                        model=self.MODEL_NAME,
                        contents=valid_texts
                    )

                    # Create result list for this batch
                    # Initialize with None for all positions
                    batch_results: List[Optional[List[float]]] = [None] * len(batch)

                    # Fill in the embeddings for valid texts
                    for idx, embedding_obj in zip(valid_indices, response.embeddings):
                        batch_results[idx] = embedding_obj.values

                    all_embeddings.extend(batch_results)
                    print(f"    ✓ Generated {len(valid_texts)} embeddings")

                except Exception as e:
                    # If batch fails, return None for all texts in batch
                    print(f"    ✗ Error: {e}")
                    all_embeddings.extend([None] * len(batch))
            else:
                # No valid texts in this batch
                all_embeddings.extend([None] * len(batch))
                print(f"    ⊘ No valid texts in batch")

        return all_embeddings

    def get_embedding_dimension(self) -> int:
        """
        Get the dimensionality of embeddings produced by this generator.

        Returns:
            768 (the dimension of text-embedding-004)
        """
        return self.EMBEDDING_DIMENSION