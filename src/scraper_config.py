from scrapegraph_ai.scrapegraphai.graphs import SmartScraperGraph
from scrapegraphai import telemetry
telemetry.disable_telemetry()
import os
from dotenv import load_dotenv

load_dotenv()


# region ### Gemini model arguments
# 
# api_key: For API authentication
# credentials: Alternative auth method (Google credentials object)
# temperature: Controls randomness (0.0-1.0)
# top_p: Nucleus sampling parameter (0.0-1.0)
# top_k: Limits token selection to top K options
# max_output_tokens: Maximum response length (not max_tokens)
# model: The Gemini model name/version
# Also Supported
# safety_settings: Controls content filtering thresholds
#
# Not Standard Gemini Arguments
# timeout: Not in standard Gemini parameters (though might work in some clients)
# client_options: Not standard for direct Gemini API
# transport: Not standard for Gemini
# additional_headers: Not standard for Gemini
#
# The core generation parameters are temperature, top_p, top_k, and max_output_tokens.
# endregion
# Configuration scraping pipeline
graph_config = {
    "llm": {
        "api_key": os.getenv("GEMINI_API_KEY"),
        "model": "google_genai/gemini-2.0-flash",
        "model_tokens": 8192,
        "max_output_tokens": 250,
        "temperature": 0.1
    },
    "verbose": True,
    "headless": True
}


# region ### SmartScraperGraph Attributes:
#         prompt (str): The prompt for the graph.
#         source (str): The source of the graph.
#         config (dict): Configuration parameters for the graph.
#         schema (BaseModel): The schema for the graph output.
#         llm_model: An instance of a language model client, configured for generating answers.
#         embedder_model: An instance of an embedding model client,
#         configured for generating embeddings.
#         verbose (bool): A flag indicating whether to show print statements during execution.
#         headless (bool): A flag indicating whether to run the graph in headless mode.

#     Args:
#         prompt (str): The prompt for the graph.
#         source (str): The source of the graph.
#         config (dict): Configuration parameters for the graph.
#         schema (BaseModel): The schema for the graph output.
# endregion
# Create SmartScraperGraph instance
smart_scraper_graph = SmartScraperGraph(
    prompt="""## Task: Extract NBN Internet Plan Details (JSON Output)

    Visit the website, extract details of the NBN internet plan that matches the specified download speed. The latest price as shown on the website for the *same plan* with the matching speed is required.

    **Target Download Speed:** 50 Mbps

    **Instructions:**
    1. Fetch and Parse HTML from the specified URL
    2. Find the NBN plan with exactly 50 Mbps download speed
    3. Extract all plan details including:
    - Plan name (String)
    - NBN Type (String)
    - Price (numerical value)
    - Download speed (integer value)
    - Upload speed (integer value)
    - Promotion price (String)
    - Promotion details (String or Null)
    - Additional plan details (String)

    **Output Format Required:**
    Return a JSON object with the following structure:
    {
        "plan_name": "Plan name as shown",
        "nbn_type": "Denoted with NBN download_speed/upload_speed, e.g. nbn® 100/20",
        "price": 95.0,
        "download_speed": "100",
        "upload_speed": "20",
        "promotion_price": "Promotion price from promotion_details",
        "promotion_details": "Any current price promotion or null",
        "plan_details": "Additional plan features",
        "confidence": [Confidence score between 0.0 and 1.0 indicating match quality. Must be >= 0.9 for verification.],
        "match_criteria": {
        "speed_match": [Boolean - True if download speed is exactly 100Mbps, otherwise False]
    }
    }""",
    source="https://www.tpg.com.au/nbn",
    config=graph_config
)

def get_total_result_metrics(execution_info_list):
    """Extract TOTAL RESULT metrics from execution info list"""
    for info in execution_info_list:
        if info.get("node_name") == "TOTAL RESULT":
            return info
    return None

def run_scraper():
    """Run the scraper and return results with execution info"""
    try:
        result, execution_info = smart_scraper_graph.run()
        total_metrics = get_total_result_metrics(execution_info)
        
        if total_metrics is None:
            raise Exception("Failed to find TOTAL RESULT metrics")
            
        return {
            "scrape_result": result,
            "execution_metrics": total_metrics
        }
    except Exception as e:
        print(f"Error running scraper: {e}")
        return None

if __name__ == "__main__":
    results = run_scraper()
    if results:
        import json
        print("\nScraping Result:")
        print(json.dumps(results["scrape_result"], indent=4))
        print("\nExecution Metrics:")
        print(json.dumps(results["execution_metrics"], indent=4))

