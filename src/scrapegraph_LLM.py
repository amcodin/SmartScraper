from scrapegraph_ai.scrapegraphai.graphs import SmartScraperGraph
from scrapegraphai import telemetry
telemetry.disable_telemetry()
from typing import Dict, Optional, Any
from scrapegraph_LLM_utils import get_total_result_metrics, get_default_config

def run_scrapegraph_LLM(
    prompt: str,
    url: str,
    graph_config: Optional[Dict] = None,
    model: str = "google_genai/gemini-2.0-flash"
) -> Dict[str, Any]:
    """
    Execute a scraping task using SmartScraperGraph with the given parameters.
    
    Args:
        prompt (str): The prompt/instructions for the scraping task.
        url (str): The target URL to scrape.
        graph_config (Optional[Dict]): Custom configuration for the graph.
                                     If None, uses default config.
        model (str): Model identifier to use if using default config.
    
    Returns:
        Dict[str, Any]: Dictionary containing:
            - scrape_result: The result from the scraping operation
            - execution_metrics: Performance metrics from the operation
    
    Raises:
        Exception: If TOTAL RESULT metrics are not found in execution info.
    """
    # Use provided config or default
    config = graph_config if graph_config is not None else get_default_config(model)
    
    # Initialize and configure the scraper
    scraper = SmartScraperGraph(
        prompt=prompt,
        source=url,
        config=config
    )
    
    try:
        # Execute the scraping operation
        result, execution_info = scraper.run()
        
        # Extract performance metrics
        total_metrics = get_total_result_metrics(execution_info)
        
        if total_metrics is None:
            raise Exception("Failed to find TOTAL RESULT metrics")
        
        return {
            "scrape_result": result,
            "execution_metrics": total_metrics
        }
        
    except Exception as e:
        print(f"Error during scraping operation: {e}")
        return None

if __name__ == "__main__":
    # Example usage
    example_prompt = """
    Visit the website and extract the following information:
    - Main heading
    - First paragraph
    - Any contact information
    
    Return as JSON with appropriate fields.
    """
    
    example_url = "https://www.google.com"
    
    results = run_scrapegraph_LLM(
        prompt=example_prompt,
        url=example_url
    )
    
    if results:
        import json
        print("\nScraping Result:")
        print(json.dumps(results["scrape_result"], indent=4))
        print("\nExecution Metrics:")
        print(json.dumps(results["execution_metrics"], indent=4))
