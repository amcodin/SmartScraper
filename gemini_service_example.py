from typing import Dict, Optional, List, Tuple
import google.generativeai as genai
from datetime import datetime, timedelta
from os import getenv
from dotenv import load_dotenv
import json
import uuid
from functools import lru_cache
import asyncio
import time
from utils import get_logger

logger = get_logger(__name__)

def generate_request_id() -> str:
    """Generate a unique request ID for tracking."""
    return str(uuid.uuid4())

class GeminiService:
    """Service for interacting with Google's Gemini API for price verification with enhanced validation."""
    
    def __init__(self, cache_timeout: int = 3600):
        """
        Initialize the Gemini service with API configuration and caching.
        
        Args:
            cache_timeout: Number of seconds to cache verification results (default 1 hour)
        """
        logger.info("Initializing GeminiService with cache timeout: %d seconds", cache_timeout)
        load_dotenv()
        api_key = getenv('GOOGLE_API_KEY')
        if not api_key:
            logger.error("Missing GOOGLE_API_KEY environment variable")
            raise ValueError("GOOGLE_API_KEY environment variable is required")
            
        # Configure the Gemini API
        logger.debug("Configuring Gemini API")
        genai.configure(api_key=api_key)

        # Configure generation config for flash content
        generate_flash2base_content_config = genai.GenerationConfig(
                                        temperature=0.2,
                                        top_p=0.2,
                                        top_k=40,
                                        max_output_tokens=400,
                                        )
        
        # Define gemini-2.0-flash JSON response schema in
        schema_flash2base = {  
            "type": "object",
            "properties": {
            "plan_name": {"type": "string"},
            "price": {"type": "number", "format": "float"},
            "price_string": {"type": "string"},
            "download_speed": {"type": "integer"},
            "upload_speed": {"type": "integer"},
            "promotion_details": {"type": "string"},
            "plan_details": {"type": "string"},
            "verified": {"type": "boolean"},
            "confidence": {"type": "number", "format": "float"},
            "match_criteria": {
                "type": "object",
                "properties": {
                "speed_match": {"type": "boolean"}
                },
                "required": ["speed_match"]
            }
            },
            "required": ["plan_name", "price", "price_string", "verified", "confidence", "match_criteria"]
        }
        
        # Properly construct the tools list
        tools_flash2base = [
            {  # Remove Tool class
                "function_declarations": [
                    {  # Remove FunctionDeclaration Class
                        "name": "parse_html_content",
                        "description": "Visit the website, extract price of an internet plan that matches the specified download speed.",
                        "parameters": schema_flash2base,
                    }
                ]
            }
        ]

        # Model 1 with schema and content config
        self.model = genai.GenerativeModel(
            model_name='gemini-2.0-flash',
            generation_config=generate_flash2base_content_config,
            tools=tools_flash2base  # Use tools parameter instead of response_schema
        )

        # Model 2
        self.model2 = genai.GenerativeModel(
            model_name='gemini-2.0-flash-lite',
            generation_config=generate_flash2base_content_config
        )
        # self.model2 = genai.GenerativeModel(
        #     model_name='gemini-1.5-pro',
        #     generation_config=generate_flash2base_content_config,
        #     tools=tools_flash2base  # Use tools parameter instead of response_schema
        # )
        

        logger.info("Gemini API configured successfully")
        
        # Configure caching
        self.cache_timeout = cache_timeout
        self._verification_cache = {}
        
    async def verify_price(self, provider_url: str, plan_details: Dict, retry_count: int = 2, correlation_id: Optional[str] = None) -> Dict:
        """
        Verify NBN plan price and details against provider website with enhanced validation.
        
        Args:
            provider_url: URL of the provider's website
            plan_details: Dictionary containing current plan details from database
            retry_count: Number of retry attempts for failed verifications
            
        Returns:
            Dict containing verification results:
            {
                'verified': bool,
                'confidence_score': float,
                'current_price': float,
                'promo_details': Optional[str],
                'verification_date': datetime,
                'error': Optional[str],
                'error_type': Optional[str],
                'match_details': Dict
            }
        """
        request_id = generate_request_id()
        correlation_id = correlation_id or request_id
        start_time = time.time()

        logger.info(
            "Starting price verification",
            correlation_id=correlation_id,
            extra={
                'event_type': 'verification_start',
                'request_id': request_id,
                'provider_url': provider_url,
                'plan_name': plan_details.get('providers_plan_name'),
                'speed': f"{plan_details.get('download_speed')}/{plan_details.get('upload_speed')}"
            }
        )

        # Check cache first
        cache_key = self._generate_cache_key(provider_url, plan_details)
        logger.debug(
            "Checking cache",
            correlation_id=correlation_id,
            extra={
                'event_type': 'cache_check',
                'cache_key': cache_key,
                'request_id': request_id
            }
        )
        cached_result = self._get_cached_result(cache_key)
        if cached_result:
            logger.info(
                "Cache hit for plan verification",
                correlation_id=correlation_id,
                extra={
                    'event_type': 'cache_hit',
                    'request_id': request_id,
                    'cache_age': time.time() - cached_result.get('verification_date', 0)
                }
            )
            return cached_result
            
        logger.debug(
            "Cache miss, proceeding with verification",
            correlation_id=correlation_id,
            extra={
                'event_type': 'cache_miss',
                'request_id': request_id
            }
        )
        retry_attempt = 0
        last_error = None
        
        while retry_attempt < retry_count:
            try:
                # Generate prompt with confidence validation
                prompt = self._create_verification_prompt(provider_url, plan_details)
                api_start_time = time.time()
                logger.debug(
                    "Sending requests to Gemini API models",
                    correlation_id=correlation_id,
                    extra={
                        'event_type': 'api_request',
                        'request_id': request_id,
                        'retry_attempt': retry_attempt
                    }
                )
                
                # Get responses from both models concurrently
                responses = await asyncio.gather(
                    asyncio.to_thread(self.model.generate_content, prompt),
                    asyncio.to_thread(self.model2.generate_content, prompt)
                )
                api_duration = time.time() - api_start_time
                
                logger.debug(
                    "Received Gemini API responses",
                    correlation_id=correlation_id,
                    extra={
                        'event_type': 'api_responses',
                        'request_id': request_id,
                        'duration_ms': int(api_duration * 1000)
                    }
                )
                
                # Parse both responses
                result1 = self._parse_verification_response(responses[0].text, correlation_id, request_id)
                result2 = self._parse_verification_response(responses[1].text, correlation_id, request_id)
              
                # If prices from models don't match
                if result1['current_price'] != result2['current_price']:
                    logger.info(
                        "Price mismatch between models",
                        correlation_id=correlation_id,
                        extra={
                            'event_type': 'price_mismatch',
                            'request_id': request_id,
                            'price1': result1['current_price'],
                            'price2': result2['current_price'],
                            'confidence1': result1['confidence_score'],
                            'confidence2': result2['confidence_score']
                        }
                    )

                    # Determine which model has lower confidence
                    if result1['confidence_score'] == result2['confidence_score']:
                        # When confidence scores are equal, first check if either matches original price
                        original_price = plan_details.get('price', None)
                        
                        # Check results price against original price (if available)
                        price1_matches = original_price is not None and result1['current_price'] == original_price
                        price2_matches = original_price is not None and result2['current_price'] == original_price
                        if price1_matches and not price2_matches:
                            lower_confidence_model = self.model2  # Model 2 doesn't match original price
                        elif price2_matches and not price1_matches:
                            lower_confidence_model = self.model  # Model 1 doesn't match original price
                        else:
                            # If both match or both don't match, retry the entire attempt
                            logger.warning(
                                "Equal confidence scores with unclear match quality - restarting attempt",
                                correlation_id=correlation_id,
                                extra={
                                    'event_type': 'equal_confidence_retry',
                                    'request_id': request_id,
                                    'confidence_score': result1['confidence_score'],
                                    'retry_attempt': retry_attempt
                                }
                            )
                            # Break the try block and increment retry_attempt
                            raise ValueError("Equal confidence with unclear match quality requires full retry")
                    else:
                        # Traditional confidence comparison
                        lower_confidence_model = self.model2 if result1['confidence_score'] > result2['confidence_score'] else self.model
                    
                    # Retry with lower confidence model
                    logger.debug(
                        "Retrying with lower confidence model",
                        correlation_id=correlation_id,
                        extra={
                            'event_type': 'model_retry',
                            'request_id': request_id
                        }
                    )
                    retry_response = await asyncio.to_thread(lower_confidence_model.generate_content, prompt)
                    retry_result = self._parse_verification_response(retry_response.text, correlation_id, request_id)
                    
                    # Select result with highest confidence score
                    result = max([result1, result2, retry_result], key=lambda x: x['confidence_score'])
                else:
                    # If prices match, use the result with higher confidence
                    result = result1 if result1['confidence_score'] >= result2['confidence_score'] else result2
                
                # Add result to cache if valid
                if result['verified'] and result['confidence_score'] > 0.8:
                    logger.info(
                        "Valid result received, caching",
                        correlation_id=correlation_id,
                        extra={
                            'event_type': 'verification_success',
                            'request_id': request_id,
                            'confidence_score': result['confidence_score'],
                            'price': result['current_price'],
                            'duration_ms': int((time.time() - start_time) * 1000)
                        }
                    )
                    self._cache_result(cache_key, result)
                
                return result
                
            except Exception as e:
                last_error = str(e)
                retry_attempt += 1
                logger.warning(
                    "Verification attempt failed",
                    correlation_id=correlation_id,
                    extra={
                        'event_type': 'verification_retry',
                        'request_id': request_id,
                        'error': str(e),
                        'attempt': retry_attempt,
                        'max_attempts': retry_count,
                        'duration_ms': int((time.time() - start_time) * 1000),
                        'exception': str(e),
                        'traceback': f"{e.__class__.__name__}: {str(e)}"
                    }
                )
                # Use exponential backoff for retries
                await self._handle_retry_delay(retry_attempt)
        
        # Return error response after all retries exhausted
        logger.error(
            "All retry attempts exhausted",
            correlation_id=correlation_id,
            extra={
                'event_type': 'verification_failed',
                'request_id': request_id,
                'error': last_error,
                'total_attempts': retry_count,
                'duration_ms': int((time.time() - start_time) * 1000)
            }
        )
        return {
            'verified': False,
            'confidence_score': 0.0,
            'current_price': None,
            'promo_details': None,
            'verification_date': datetime.now(),
            'error': last_error,
            'error_type': 'VERIFICATION_FAILED',
            'match_details': {}
        }
            
    def _create_verification_prompt(self, provider_url: str, plan_details: Dict) -> str:
        """Create a structured prompt for price verification based on geminiprompt.md template."""
        return f"""## Task: Extract NBN Internet Plan Details (JSON Output)

Visit the website, extract details of the NBN internet plan that matches the specified download speed. The latest price as shown on the website for the *same plan* with the matching speed is required.

**Website Content:** {provider_url}

**Target Download Speed:** {plan_details.get('download_speed')} Mbps

**Instructions:**

1.  **Fetch and Parse HTML:** Access the website and view the HTML content from the URL provided in `{provider_url}`. Use **semantic** HTML parsing techniques to understand the structure of the document. Pay close attention to how the plan information is grouped and associated within the HTML structure (e.g., within `div` elements, `tables`, or `list items`). Focus on extracting the relevant plan information from the website's body, avoiding headers, footers, svg, scripts and promotional banners where possible.

2.  **Identify Matching Plan:** Analyze the parsed HTML to find a *complete* NBN internet plan where the download speed is **exactly** `{plan_details.get('download_speed')} Mbps`. Ensure that all extracted information (price, plan name, speeds, promotion, details) is sourced from the same plan description or container element. Do not infer any details from other plans or sections of the page, **Do not extract the price from a different plan**, even if it appears nearby in the HTML. The extracted information must be directly associated with the matching speed value. Carefully examine the HTML structure to ensure data integrity.

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
             
    def _clean_plan_details(self, plan_details: Optional[str]) -> str:
        """Clean and validate plan details string.
        
        Args:
            plan_details: Raw plan details string
            
        Returns:
            Cleaned plan details string, truncated to 50 chars with no consecutive special chars
        """
        if not plan_details:
            return "No details available"
            
        # Truncate to 50 characters
        cleaned = plan_details[:50]
        
        # Remove consecutive special characters
        import re
        cleaned = re.sub(r'[^a-zA-Z0-9\s](?=[^a-zA-Z0-9\s])', '', cleaned)
        
        return cleaned.strip()

    def _parse_verification_response(self, response_text: str, correlation_id: str, request_id: str) -> Dict:
        """Parse and validate the verification response with enhanced error handling."""
        parse_start = time.time()
        logger.debug(
            "Starting response parsing",
            correlation_id=correlation_id,
            extra={
                'event_type': 'parse_start',
                'request_id': request_id
            }
        )
        try:
            # Preprocessing: Handle markdown-formatted JSON response
            logger.debug(
                "Preprocessing response text",
                correlation_id=correlation_id,
                extra={
                    'event_type': 'response_preprocessing',
                    'request_id': request_id,
                    'raw_length': len(response_text),
                    'contains_markdown': '```json' in response_text
                }
            )
            
            # Clean up markdown formatting if present
            if '```json' in response_text:
                response_text = response_text.split('```json\n')[1].split('\n```')[0]
            
            # Remove any remaining newlines and whitespace
            response_text = response_text.strip()
            
            logger.debug(
                "Cleaned response text",
                correlation_id=correlation_id,
                extra={
                    'event_type': 'response_cleaned',
                    'request_id': request_id,
                    'cleaned_length': len(response_text)
                }
            )

            # Parse the cleaned JSON
            data = json.loads(response_text)
            
            # Clean plan details
            data['plan_details'] = self._clean_plan_details(data.get('plan_details'))
            
            # Clean Promo details
            data['promotion_details'] = self._clean_plan_details(data.get('promotion_details'))
            
            # Validate response format
            required_fields = {'price', 'verified', 'confidence', 'match_criteria'}
            missing_fields = [f for f in required_fields if f not in data]
            if missing_fields:
                logger.error(
                    "Invalid response format",
                    correlation_id=correlation_id,
                    extra={
                        'event_type': 'parse_error',
                        'request_id': request_id,
                        'error_type': 'missing_fields',
                        'missing_fields': missing_fields
                    }
                )
                raise ValueError(f'Missing required fields: {", ".join(missing_fields)}')
                
            result = {
                'verification_date': datetime.now(),
                'verified': bool(data['verified']),
                'confidence_score': float(data['confidence']),
                'current_price': float(data['price']) if data['price'] is not None else None,
                'promo_details': data.get('promo'),
                'plan_details': data.get('plan_details'),
                'error': None,
                'error_type': None,
                'match_details': data['match_criteria']
            }
            
            # Validate confidence threshold
            if result['verified'] and result['confidence_score'] < 0.8:
                logger.warning(
                    "Confidence score below threshold",
                    correlation_id=correlation_id,
                    extra={
                        'event_type': 'low_confidence',
                        'request_id': request_id,
                        'confidence_score': result['confidence_score'],
                        'threshold': 0.8
                    }
                )
                result['verified'] = False
                result['error_type'] = 'LOW_CONFIDENCE'
                result['error'] = 'Confidence score below threshold'

            parse_duration = time.time() - parse_start
            logger.debug(
                "Response parsing complete",
                correlation_id=correlation_id,
                extra={
                    'event_type': 'parse_complete',
                    'request_id': request_id,
                    'duration_ms': int(parse_duration * 1000),
                    'verified': result['verified'],
                    'confidence_score': result['confidence_score']
                }
            )
            return result
            
        except json.JSONDecodeError as e:
            logger.error(
                "JSON parse error",
                correlation_id=correlation_id,
                extra={
                    'event_type': 'json_error',
                    'request_id': request_id,
                    'error_details': str(e),
                    'duration_ms': int((time.time() - parse_start) * 1000)
                }
            )
            return self._create_error_response('INVALID_JSON', 'Failed to parse JSON response', correlation_id, request_id)
        except ValueError as e:
            logger.error(
                "Validation error",
                correlation_id=correlation_id,
                extra={
                    'event_type': 'validation_error',
                    'request_id': request_id,
                    'error_details': str(e),
                    'duration_ms': int((time.time() - parse_start) * 1000)
                }
            )
            return self._create_error_response('VALIDATION_ERROR', str(e), correlation_id, request_id)
        except Exception as e:
            logger.error(
                "Processing error",
                correlation_id=correlation_id,
                extra={
                    'event_type': 'processing_error',
                    'request_id': request_id,
                    'error_details': str(e),
                    'duration_ms': int((time.time() - parse_start) * 1000)
                },
                exc_info=True
            )
            return self._create_error_response('PROCESSING_ERROR', f'Failed to process response: {str(e)}', correlation_id, request_id)

    def _create_error_response(self, error_type: str, error_message: str, correlation_id: Optional[str] = None, request_id: Optional[str] = None) -> Dict:
        """Create a standardized error response."""
        response = {
            'verified': False,
            'confidence_score': 0.0,
            'current_price': None,
            'promo_details': None,
            'verification_date': datetime.now(),
            'error': error_message,
            'error_type': error_type,
            'match_details': {}
        }
        
        if correlation_id and request_id:
            logger.error(
                "Creating error response",
                correlation_id=correlation_id,
                extra={
                    'event_type': 'error_response',
                    'request_id': request_id,
                    'error_type': error_type,
                    'error_message': error_message
                }
            )
            
        return response

    def _generate_cache_key(self, provider_url: str, plan_details: Dict) -> str:
        """Generate a unique cache key for the verification request."""
        key_parts = [
            provider_url,
            str(plan_details.get('providers_plan_name')),
            str(plan_details.get('download_speed')),
            str(plan_details.get('upload_speed'))
        ]
        return '_'.join(key_parts)

    def _get_cached_result(self, cache_key: str, correlation_id: Optional[str] = None, request_id: Optional[str] = None) -> Optional[Dict]:
        """Retrieve a cached verification result if available and not expired."""
        if cache_key in self._verification_cache:
            result, timestamp = self._verification_cache[cache_key]
            age_seconds = (datetime.now() - timestamp).total_seconds()
            if age_seconds < self.cache_timeout:
                logger.info(
                    "Cache hit",
                    correlation_id=correlation_id,
                    extra={
                        'event_type': 'cache_hit',
                        'request_id': request_id,
                        'cache_key': cache_key,
                        'age_seconds': age_seconds,
                        'timeout': self.cache_timeout,
                        'confidence_score': result.get('confidence_score'),
                        'verified': result.get('verified')
                    }
                )
                return result
            else:
                logger.info(
                    "Cache entry expired",
                    correlation_id=correlation_id,
                    extra={
                        'event_type': 'cache_expired',
                        'request_id': request_id,
                        'cache_key': cache_key,
                        'age_seconds': age_seconds,
                        'timeout': self.cache_timeout
                    }
                )
                del self._verification_cache[cache_key]
                
        logger.debug(
            "Cache miss",
            correlation_id=correlation_id,
            extra={
                'event_type': 'cache_miss',
                'request_id': request_id,
                'cache_key': cache_key
            }
        )
        return None

    def _cache_result(self, cache_key: str, result: Dict, correlation_id: Optional[str] = None, request_id: Optional[str] = None) -> None:
        """Cache a verification result with timestamp."""
        timestamp = datetime.now()
        self._verification_cache[cache_key] = (result, timestamp)
        
        logger.info(
            "Caching verification result",
            correlation_id=correlation_id,
            extra={
                'event_type': 'cache_store',
                'request_id': request_id,
                'cache_key': cache_key,
                'expiry': timestamp + timedelta(seconds=self.cache_timeout),
                'verified': result.get('verified'),
                'confidence_score': result.get('confidence_score'),
                'cache_entries': len(self._verification_cache)
            }
        )

    async def _handle_retry_delay(self, attempt: int, correlation_id: Optional[str] = None, request_id: Optional[str] = None) -> None:
        """Implement exponential backoff for retries."""
        delay = min(300, (2 ** attempt) * 30)  # Max delay of 5 minutes
        logger.debug(
            "Applying retry delay",
            correlation_id=correlation_id,
            extra={
                'event_type': 'retry_delay',
                'request_id': request_id,
                'attempt': attempt,
                'delay_seconds': delay
            }
        )
        await asyncio.sleep(delay)
