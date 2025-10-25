#!/usr/bin/env python3
"""
Test LLMClient implementation.
"""

import os
from dotenv import load_dotenv
from src.github_delivery.llm_client import AnthropicLLMClient

# Load environment variables
load_dotenv()


def main():
    print("\n🧪 Testing LLMClient\n")
    print("=" * 60)

    # Initialize client (uses default model from config)
    print("\n1. Initializing AnthropicLLMClient...")
    client = AnthropicLLMClient()
    print(f"   ✓ Client initialized with model: {client.model}")

    # Test simple generation
    print("\n2. Testing simple generation...")
    prompt = "What is 2+2? Answer in one sentence."

    response = client.generate(
        prompt=prompt,
        system_prompt="You are a helpful assistant.",
        temperature=0.0,
        max_tokens=100
    )

    print(f"\n   Prompt: {prompt}")
    print(f"   Response: {response.content}")
    print(f"\n   Metrics:")
    print(f"     Model: {response.model}")
    print(f"     Input tokens: {response.input_tokens}")
    print(f"     Output tokens: {response.output_tokens}")
    print(f"     Cost: ${response.cost_usd:.6f}")
    print(f"     Latency: {response.latency_seconds:.2f}s")

    print("\n" + "=" * 60)
    print("✅ Test complete!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
