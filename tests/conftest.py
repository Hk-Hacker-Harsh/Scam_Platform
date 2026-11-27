"""Shared test settings."""
import os

# Tests never call the real local model (slow and non-deterministic); assistant tests stub it where needed.
os.environ.setdefault("PS01_LLM", "0")
