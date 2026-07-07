"""Centralized configuration constants for AI-Money-Mentor.

This module provides a single source of truth for shared configuration
values (model identifiers, default thresholds, etc.) so individual modules
do not hard-code string literals and drift apart over time.

For environment-driven values (API keys, secrets, host/port), continue to
use the `.env` file via `python-dotenv` / `os.getenv`. Only constants that
do **not** change per deployment belong here.
"""

#: Default Groq chat-completion model used by agents.py, the multi-agent
#: system and the BaseAgent helper. Centralized here so future model
#: upgrades are a one-line change.
GROQ_MODEL: str = "llama-3.1-8b-instant"
