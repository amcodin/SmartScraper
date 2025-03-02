from typing import Dict, List, Optional
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_default_config(model: str = "google_genai/gemini-2.0-flash") -> Dict:
    """
    Generate default configuration for SmartScraperGraph.
    
    Args:
        model (str): Model identifier to use. Defaults to Gemini 2.0.
    
    Returns:
        Dict: Default configuration dictionary.
    """
    return {
        "llm": {
            "api_key": os.getenv("GEMINI_API_KEY"),
            "model": model
        },
        "verbose": True,
        "headless": True
    }

def get_total_result_metrics(execution_info_list: List[Dict]) -> Optional[Dict]:
    """
    Extract TOTAL RESULT metrics from execution info list.
    
    Args:
        execution_info_list (List[Dict]): List of execution information dictionaries
                                        containing metrics for different nodes.
    
    Returns:
        Optional[Dict]: Dictionary containing metrics for the TOTAL RESULT node,
                       or None if not found. The metrics include:
                       - node_name: str
                       - total_tokens: int
                       - prompt_tokens: int
                       - completion_tokens: int
                       - successful_requests: int
                       - total_cost_USD: float
                       - exec_time: float
    
    Example:
        >>> metrics = get_total_result_metrics(execution_info)
        >>> if metrics:
        >>>     print(f"Total tokens used: {metrics['total_tokens']}")
    """
    for info in execution_info_list:
        if info.get("node_name") == "TOTAL RESULT":
            return info
    return None
