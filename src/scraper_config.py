from scrapegraph_ai.scrapegraphai.graphs import SmartScraperGraph
import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()


## https://docs.scrapegraphai.com/services/additional-parameters/headers
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    "Cookie": "country=AU; language=en; currency=AUD; theme=dark; notifications=enabled"
}

#### Gemini model supported Arguments
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

# Define the configuration for the scraping pipeline
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

# Create the SmartScraperGraph instance
### SmartScraperGraphAttributes:
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

smart_scraper_graph = SmartScraperGraph(
    prompt="""## Task: Extract NBN Internet Plan Details (JSON Output)

    Visit the website, extract details of the NBN internet plan that matches the specified download speed. The latest price as shown on the website for the *same plan* with the matching speed is required. Focus on the website's body, avoiding headers, footers, svg, scripts and promotional banners.

    **Target Download Speed:** 250 Mbps

    **Instructions:**
    1. Fetch and Parse HTML from the specified URL
    2. Find the NBN plan with exactly 100 Mbps download speed
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
    source="https://www.aussiebroadband.com.au/internet/nbn-plans/",
    config=graph_config
)

# source="https://www.telstra.com.au/internet/nbn/",

def run_scraper():
    """Run the scraper and return results"""
    try:
        result = smart_scraper_graph.run()
        ## How can I add a result to extract the self.execution_info from src\scrapegraph_ai\scrapegraphai\graphs\smart_scraper_graph.py self.final_state, self.execution_info = self.graph.execute(inputs)
        return result
    except Exception as e:
        print(f"Error running scraper: {e}")
        return None

if __name__ == "__main__":
    result = run_scraper()
    if result:
        import json
        print(json.dumps(result, indent=4))
# Maybe use these output and store in database?
# retuirned from self.execution_info
                # "node_name": "TOTAL RESULT",
                # "total_tokens": cb_total["total_tokens"],
                # "prompt_tokens": cb_total["prompt_tokens"],
                # "completion_tokens": cb_total["completion_tokens"],
                # "successful_requests": cb_total["successful_requests"],
                # "total_cost_USD": cb_total["total_cost_USD"],
                # "exec_time": total_exec_time,




### Maybe change the chunk size
            # chunks = split_text_into_chunks(
            #     text=docs_transformed.page_content,
            #     chunk_size=self.chunk_size - 250,
            # )

 

#    prompt="""## Task: Extract NBN Internet Plan Details (JSON Output)

# Visit the website, extract details of the NBN internet plan that matches the specified download speed. The latest price as shown on the website for the *same plan* with the matching speed is required.

# **Target Download Speed:** 100 Mbps

# **Instructions:**

# 1.  **Fetch and Parse HTML:** Access the website and view the HTML content from the URL. Use **semantic** HTML parsing techniques to understand the structure of the document. Pay close attention to how the plan information is grouped and associated within the HTML structure (e.g., within `div` elements, `tables`, or `list items`). Focus on extracting the relevant plan information from the website's body, avoiding headers, footers, svg, scripts and promotional banners where possible.

# 2.  **Identify Matching Plan:** Analyze the parsed HTML to find a *complete* NBN internet plan where the download speed is **exactly** 100 Mbps`. Ensure that all extracted information (price, plan name, speeds, promotion, details) is sourced from the same plan description or container element. Do not infer any details from other plans or sections of the page, **Do not extract the price from a different plan**, even if it appears nearby in the HTML. The extracted information must be directly associated with the matching speed value. Carefully examine the HTML structure to ensure data integrity.

# 3.  **Extract Key Details:** For the identified plan, extract the following information *precisely as presented on the website* from the plan details that match the speed specified above:

#     *   **plan_name:** (String) The official NBN/Internet plan name (e.g., "NBN 250/25").
#     *   **price:** (Number) The numerical price value (e.g., 119.0).  Extract the number only, without currency symbols. .
#     *   **price_string:** (String) The full price string as displayed on the website (e.g., "$119.00/month").
#     *   **download_speed:** (String) The download speed as displayed (e.g., "100Mbps").
#     *   **upload_speed:** (String) The upload speed as displayed (e.g., "20Mbps").
#     *   **promotion_details:** (String or Null)  Any promotion details. If no promotion is mentioned for the plan, return "Null" (e.g., "For 6 months then $110/mnt").
#     *   **plan_details:** (String) Any other relevant details about the plan (e.g., "Unlimited data", "No setup fee").

# **Search Strategy (Prioritized):**

# 1.  **Tables:** Look for `<table>` elements, especially those with `class='table'`, as these often contain structured plan data. If plan details are reliably found in tables, you may remove the other search strategies.
# 2.  **Swipers:** Inspect `<div>` elements with `class='swiper'` and their inner `<div>` elements with `class='swiper-slide'`, which are commonly used for displaying plans in a carousel format.

# **Output Format: JSON REQUIRED**


# **Please return the ENTIRE response as a valid JSON object.**  The JSON should strictly adhere to the following structure:

# ```json
# {{
#     "plan_name": "[plan_name]",
#     "price": [price as number],
#     "price_string": "[price_string]",
#     "download_speed": "[download_speed]",
#     "upload_speed": "[upload_speed]",
#     "promotion_details": "[promotion_details or Null]",
#     "plan_details": "[plan_details]",
#     "verified": true,
#     "confidence": [Confidence score between 0.0 and 1.0 indicating match quality. Aim for >= 0.8 for verification.],
#     "match_criteria": {{
#         "speed_match": [Boolean - True if download speed is exactly 100Mbps, otherwise False]
#     }}
#    }}
# ```""",
