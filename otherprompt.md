"""## Task: Extract NBN Internet Plan Details (JSON Output)

Visit the website, extract details of the NBN internet plan that matches the specified download speed. The latest price as shown on the website for the *same plan* with the matching speed is required.

**Target Download Speed:** 100 Mbps

**Instructions:**

1.  **Fetch and Parse HTML:** Access the website and view the HTML content from the URL. Use **semantic** HTML parsing techniques to understand the structure of the document. Pay close attention to how the plan information is grouped and associated within the HTML structure (e.g., within `div` elements, `tables`, or `list items`). Focus on extracting the relevant plan information from the website's body, avoiding headers, footers, svg, scripts and promotional banners where possible.

2.  **Identify Matching Plan:** Analyze the parsed HTML to find a *complete* NBN internet plan where the download speed is **exactly** 100 Mbps`. Ensure that all extracted information (price, plan name, speeds, promotion, details) is sourced from the same plan description or container element. Do not infer any details from other plans or sections of the page, **Do not extract the price from a different plan**, even if it appears nearby in the HTML. The extracted information must be directly associated with the matching speed value. Carefully examine the HTML structure to ensure data integrity.

3.  **Extract Key Details:** For the identified plan, extract the following information *precisely as presented on the website* from the plan details that match the speed specified above:

    *   **plan_name:** (String) The official NBN/Internet plan name (e.g., "NBN 250/25").
    *   **price:** (Number) The numerical price value (e.g., 119.0).  Extract the number only, without currency symbols. .
    *   **price_string:** (String) The full price string as displayed on the website (e.g., "$119.00/month").
    *   **download_speed:** (String) The download speed as displayed (e.g., "100Mbps").
    *   **upload_speed:** (String) The upload speed as displayed (e.g., "20Mbps").
    *   **promotion_details:** (String or Null)  Any promotion details. If no promotion is mentioned for the plan, return "Null" (e.g., "For 6 months then $110/mnt").
    *   **plan_details:** (String) Any other relevant details about the plan (e.g., "Unlimited data", "No setup fee").

**Search Strategy (Prioritized):**

1.  **Tables:** Look for `<table>` elements, especially those with `class='table'`, as these often contain structured plan data. If plan details are reliably found in tables, you may remove the other search strategies.
2.  **Swipers:** Inspect `<div>` elements with `class='swiper'` and their inner `<div>` elements with `class='swiper-slide'`, which are commonly used for displaying plans in a carousel format.

**Output Format: JSON REQUIRED**


**Please return the ENTIRE response as a valid JSON object.**  The JSON should strictly adhere to the following structure:

```json
{{
    "plan_name": "[plan_name]",
    "price": [price as number],
    "price_string": "[price_string]",
    "download_speed": "[download_speed]",
    "upload_speed": "[upload_speed]",
    "promotion_details": "[promotion_details or Null]",
    "plan_details": "[plan_details]",
    "verified": true,
    "confidence": [Confidence score between 0.0 and 1.0 indicating match quality. Aim for >= 0.8 for verification.],
    "match_criteria": {{
        "speed_match": [Boolean - True if download speed is exactly 100Mbps, otherwise False]
    }}
   }}
```"""