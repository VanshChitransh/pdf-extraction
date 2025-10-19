"""
Gemini API client for cost estimation.
"""
import json
import logging
import time
from typing import Dict, List, Optional, Any
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import google.generativeai as genai

logger = logging.getLogger(__name__)


class APIError(Exception):
    """Custom exception for API errors."""
    pass


class GeminiEstimator:
    """Client for Gemini API cost estimation."""
    
    def __init__(
        self,
        api_key: str,
        model_name: str = "gemini-2.0-flash-exp",
        temperature: float = 0.3,
        timeout: int = 60
    ):
        """
        Initialize Gemini API client.
        
        Args:
            api_key: Google API key
            model_name: Gemini model to use
            temperature: Response randomness (0.0-1.0, lower = more deterministic)
            timeout: Request timeout in seconds
        """
        self.api_key = api_key
        self.model_name = model_name
        self.temperature = temperature
        self.timeout = timeout
        
        # Configure Gemini
        genai.configure(api_key=api_key)
        
        # Initialize model with JSON response mode
        generation_config = {
            "temperature": temperature,
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 8192,
            "response_mime_type": "application/json",
        }
        
        self.model = genai.GenerativeModel(
            model_name=model_name,
            generation_config=generation_config,
        )
        
        # Track API usage
        self.request_count = 0
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.last_request_time = 0
        self.min_request_interval = 1.0  # Minimum seconds between requests
        
        logger.info(f"Initialized Gemini API client with model: {model_name}")
    
    def _rate_limit(self):
        """Implement simple rate limiting."""
        if self.last_request_time > 0:
            elapsed = time.time() - self.last_request_time
            if elapsed < self.min_request_interval:
                sleep_time = self.min_request_interval - elapsed
                logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s")
                time.sleep(sleep_time)
        self.last_request_time = time.time()
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((APIError, Exception)),
        reraise=True
    )
    def estimate_single_issue(
        self,
        system_prompt: str,
        user_prompt: str
    ) -> Dict[str, Any]:
        """
        Get cost estimate for a single issue.
        
        Args:
            system_prompt: System instructions
            user_prompt: User query with issue details
            
        Returns:
            Dict containing cost estimate
            
        Raises:
            APIError: If API call fails
        """
        self._rate_limit()
        
        try:
            # Combine system and user prompts
            full_prompt = f"{system_prompt}\n\n{user_prompt}"
            
            logger.debug(f"Sending request to Gemini API (attempt {self.request_count + 1})")
            
            # Make API call
            response = self.model.generate_content(full_prompt)
            
            # Track usage
            self.request_count += 1
            if hasattr(response, 'usage_metadata'):
                self.total_input_tokens += getattr(response.usage_metadata, 'prompt_token_count', 0)
                self.total_output_tokens += getattr(response.usage_metadata, 'candidates_token_count', 0)
            
            # Parse JSON response
            result = json.loads(response.text)
            
            logger.debug(f"Successfully received estimate: {result.get('repair_name', 'Unknown')}")
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Response text: {response.text if 'response' in locals() else 'N/A'}")
            raise APIError(f"Invalid JSON response from API: {e}")
            
        except Exception as e:
            logger.error(f"API request failed: {e}")
            raise APIError(f"Gemini API error: {e}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((APIError, Exception)),
        reraise=True
    )
    def estimate_batch_issues(
        self,
        system_prompt: str,
        user_prompt: str
    ) -> List[Dict[str, Any]]:
        """
        Get cost estimates for multiple issues in one call.
        
        Args:
            system_prompt: System instructions
            user_prompt: User query with multiple issues
            
        Returns:
            List of dicts containing cost estimates
            
        Raises:
            APIError: If API call fails
        """
        self._rate_limit()
        
        try:
            # Combine system and user prompts
            full_prompt = f"{system_prompt}\n\n{user_prompt}"
            
            logger.debug(f"Sending batch request to Gemini API")
            
            # Make API call
            response = self.model.generate_content(full_prompt)
            
            # Track usage
            self.request_count += 1
            if hasattr(response, 'usage_metadata'):
                self.total_input_tokens += getattr(response.usage_metadata, 'prompt_token_count', 0)
                self.total_output_tokens += getattr(response.usage_metadata, 'candidates_token_count', 0)
            
            # Parse JSON response (should be array)
            result = json.loads(response.text)
            
            if not isinstance(result, list):
                raise APIError("Expected array response for batch estimation")
            
            logger.debug(f"Successfully received {len(result)} estimates")
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Response text: {response.text if 'response' in locals() else 'N/A'}")
            raise APIError(f"Invalid JSON response from API: {e}")
            
        except Exception as e:
            logger.error(f"API request failed: {e}")
            raise APIError(f"Gemini API error: {e}")
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get API usage statistics."""
        return {
            "request_count": self.request_count,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "estimated_cost_usd": self._estimate_cost()
        }
    
    def _estimate_cost(self) -> float:
        """
        Estimate API cost based on token usage.
        Gemini 2.0 Flash pricing (as of 2025):
        - Input: $0.075 per 1M tokens
        - Output: $0.30 per 1M tokens
        """
        input_cost = (self.total_input_tokens / 1_000_000) * 0.075
        output_cost = (self.total_output_tokens / 1_000_000) * 0.30
        return input_cost + output_cost
    
    def reset_stats(self):
        """Reset usage statistics."""
        self.request_count = 0
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        logger.info("Reset API usage statistics")

