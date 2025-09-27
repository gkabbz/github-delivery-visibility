"""
Entry point for running the GitHub delivery visibility tool as a module.

Allows running the tool with: python -m src.github_delivery
"""

from .cli import main

if __name__ == '__main__':
    exit(main())