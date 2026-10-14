"""
OpenStack Review - Automated code review for OpenStack Gerrit changes.

A comprehensive AI-powered skill for reviewing OpenStack Gerrit changes with
automated checks and best practices enforcement. Supports multiple providers
(Claude via the Claude Agent SDK, OpenAI via the Responses API).
"""

__version__ = "2.4.0"
__author__ = "Gregory Thiemonge"
__license__ = "Apache License 2.0"

from .review_config import get_model_config, list_presets

__all__ = ["get_model_config", "list_presets", "__version__"]
