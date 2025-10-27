"""
Simple REST API Adapter Example

This example shows how to integrate with simple REST APIs using API key authentication.
Copy this file to adapter.py and customize as needed.

Required environment variables:
- API_KEY: Your API key
- API_URL: Your API endpoint
"""

import requests
import time
from typing import Tuple, Optional, Dict, Any


class BridgeAdapter:
    """Simple REST API integration for Mend AI Bridge"""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize simple REST adapter"""
        # API configuration
        self.api_url = config.get("api", {}).get("url", "")
        self.api_key = config.get("api", {}).get("api_key", "")
        self.timeout = config.get("api", {}).get("timeout", 30)
        
        # Optional parameters
        self.auth_header = config.get("api", {}).get("auth_header", "Authorization")
        self.auth_prefix = config.get("api", {}).get("auth_prefix", "Bearer")
        
        if not self.api_url:
            raise ValueError("API_URL is required")
        if not self.api_key:
            raise ValueError("API_KEY is required")
        
        print(f"Simple REST adapter initialized for API: {self.api_url}")
    
    def send_message(self, message: str, session_id: str, session_data: Dict[str, Any]) -> Dict[str, str]:
        """Send message to simple REST API"""
        try:
            # Simple request payload (customize for your API)
            payload = {
                "message": message,
                "session_id": session_id
            }
            
            # Add any additional fields your API needs
            # payload["model"] = "your-default-model"
            # payload["max_tokens"] = 1000
            # payload["temperature"] = 0.7
            
            # Setup headers
            headers = {
                "Content-Type": "application/json"
            }
            
            # Add API key authentication
            # Common patterns:
            if self.auth_prefix:
                headers[self.auth_header] = f"{self.auth_prefix} {self.api_key}"
            else:
                headers[self.auth_header] = self.api_key
            
            # Alternative authentication methods (uncomment as needed):
            # headers["X-API-Key"] = self.api_key  # Header-based API key
            # payload["api_key"] = self.api_key    # Body-based API key
            
            # Make API request
            response = requests.post(
                self.api_url,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            # Parse response
            result = response.json()
            
            # Extract AI response (customize based on your API's response format)
            # Common patterns:
            ai_response = (
                result.get("response") or           # {"response": "text"}
                result.get("output") or             # {"output": "text"}  
                result.get("reply") or              # {"reply": "text"}
                result.get("text") or               # {"text": "text"}
                result.get("message") or            # {"message": "text"}
                result.get("content") or            # {"content": "text"}
                str(result)                         # Fallback: convert whole response
            )
            
            # Update session tracking
            session_data["message_count"] = session_data.get("message_count", 0) + 1
            session_data["last_message"] = message
            session_data["last_response"] = ai_response
            session_data["last_message_time"] = time.time()
            
            return {"response": ai_response}
            
        except requests.exceptions.RequestException as e:
            return {"response": f"API connection error: {str(e)}"}
        except (KeyError, ValueError) as e:
            return {"response": f"Response parsing error: {str(e)}"}
        except Exception as e:
            return {"response": f"Unexpected error: {str(e)}"}
    
    def open_session(self, session_id: str, request_data: Dict[str, Any]) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
        """Initialize simple session"""
        try:
            # Basic session initialization
            initial_session_data = {
                "created_at": time.time(),
                "message_count": 0,
                "auth_method": "api_key"
            }
            
            # Optional: Test API connectivity during session open
            # You can uncomment this to verify the API is accessible
            # test_response = requests.get(
            #     f"{self.api_url}/health",  # Adjust endpoint as needed
            #     headers={self.auth_header: f"{self.auth_prefix} {self.api_key}"},
            #     timeout=5
            # )
            # if test_response.status_code != 200:
            #     return {
            #         "status": "error",
            #         "error": "API connectivity test failed"
            #     }, None
            
            # Success response to Mend AI
            response_to_mend_ai = {
                "status": "ready",
                "session_id": session_id,
                "api_endpoint": self.api_url
            }
            
            return response_to_mend_ai, initial_session_data
            
        except Exception as e:
            return {
                "status": "error",
                "error": f"Session initialization failed: {str(e)}",
                "session_id": session_id
            }, None
    
    def close_session(self, session_id: str, session_data: Dict[str, Any], request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Clean up simple session"""
        try:
            # Calculate session statistics
            message_count = session_data.get("message_count", 0)
            duration = time.time() - session_data.get("created_at", time.time())
            
            # Optional: Log session summary
            if message_count > 0:
                print(f"Session {session_id}: {message_count} messages in {int(duration)} seconds")
            
            return {
                "status": "closed",
                "session_id": session_id,
                "message_count": message_count,
                "duration_seconds": int(duration),
                "api_endpoint": self.api_url
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": f"Session cleanup failed: {str(e)}",
                "session_id": session_id
            } 
