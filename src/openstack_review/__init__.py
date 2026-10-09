"""
OpenStack Review - Automated code review for OpenStack Gerrit changes.

A comprehensive Claude-powered skill for reviewing OpenStack Gerrit changes
with automated checks and best practices enforcement.
"""

__version__ = "2.3.0"
__author__ = "Gregory Thiemonge"
__license__ = "Apache License 2.0"

from .review_config import get_model_config, list_presets

__all__ = ["get_model_config", "list_presets", "__version__"]
