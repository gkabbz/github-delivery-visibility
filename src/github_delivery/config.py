#!/usr/bin/env python3
"""
Project-wide configuration settings.

Update model versions and other settings here as they change.
"""

# Anthropic Model Configuration
# Update this as new models are released
DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-4-20250514"

# Model Pricing (USD per 1M tokens)
ANTHROPIC_PRICING = {
    "claude-sonnet-4-20250514": {"input": 3.0, "output": 15.0},
    "claude-3-5-sonnet-20241022": {"input": 3.0, "output": 15.0},
    "claude-3-5-haiku-20241022": {"input": 0.8, "output": 4.0},
}
