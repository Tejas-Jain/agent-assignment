import os

import pytest

os.environ.setdefault("LLM_PROVIDER", "gemini")
os.environ.setdefault("GEMINI_API_KEY", "test-key-for-pytest")
os.environ.setdefault("OPENAI_API_KEY", "test-key-for-pytest")
