"""
SmartScraper package initialization.
Exports core functionality for web scraping with LLM integration.
"""

from .scrapegraph_LLM_utils import get_total_result_metrics, get_default_config

__all__ = [
    'run_scrapegraph_LLM',      # Main scraping function
    'get_total_result_metrics', # Metrics extraction
    'get_default_config'        # LLM Configuration helper
]
