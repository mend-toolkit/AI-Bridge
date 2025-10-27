"""
OAuth2 API Adapter Example

This example shows how to integrate with APIs that use OAuth2 authentication.
Copy this file to adapter.py and customize as needed.

Required environment variables:
- CLIENT_ID: Your OAuth2 client ID
- CLIENT_SECRET: Your OAuth2 client secret
- TOKEN_URL: OAuth2 token endpoint
- API_URL: Your API endpoint
"""

import requests
import time
from typing import Tuple, Optional, Dict, Any


class BridgeAdapter:
    """OAuth2 API integration for Mend AI Bridge"""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize OAuth2 adapter"""
        # OAuth2 configuration
        self.api_url = config.get("api", {}).get("url", "")
        self.client_id = config.get("api", {}).get("client_id", "")
        self.client_secret = config.get("api", {}).get("client_secret", "")
        self.token_url = config.get("api", {}).get("token_url", "")
        self.scope = config.get("api", {}).get("scope", "api")
        self.timeout = config.get("api", {}).get("timeout", 30)
        
        # Token management
        self._access_token = None
        self._token_expires_at = 0
        
        # Validate required configuration
        if not all([self.api_url, self.client_id, self.client_secret, self.token_url]):
            raise ValueError("OAuth2 requires: API_URL, CLIENT_ID, CLIENT_SECRET, TOKEN_URL")
        
        print(f"OAuth2 adapter initialized for API: {self.api_url}")
    
    def _get_access_token(self) -> str:
        """Get or refresh OAuth2 access token"""
        # Check if current token is still valid (with 5 minute buffer)
        if self._access_token and time.time() < (self._token_expires_at - 300):
            return self._access_token
        
        # Get new access token
        try:
            payload = {
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "scope": self.scope
            }
            
            response = requests.post(
                self.token_url,
                data=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            token_data = response.json()
            self._access_token = token_data["access_token"]
            
            # Calculate expiration time
            expires_in = token_data.get("expires_in", 3600)  # Default 1 hour
            self._token_expires_at = time.time() + expires_in
            
            print(f"OAuth2 token refreshed, expires in {expires_in} seconds")
            return self._access_token
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"OAuth2 token request failed: {str(e)}")
        except KeyError as e:
            raise Exception(f"Invalid OAuth2 token response: missing {str(e)}")
    
    def send_message(self, message: str, session_id: str, session_data: Dict[str, Any]) -> Dict[str, str]:
        """Send message to OAuth2 protected API"""
        try:
            # Get valid access token
            access_token = self._get_access_token()
            
            # Format request for your API (customize this section)
            payload = {
                "message": message,
                "session_id": session_id,
                # Add your API's specific fields here
                # "model": "your-model",
                # "max_tokens": 1000,
                # "temperature": 0.7
            }
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}"
            }
            
            # Make API request
            response = requests.post(
                self.api_url,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            # Extract response (customize based on your API's response format)
            result = response.json()
            
            # Common response formats:
            # ai_response = result["response"]  # Simple format
            # ai_response = result["choices"][0]["text"]  # OpenAI-like format
            # ai_response = result["data"]["output"]  # Nested format
            
            ai_response = result.get("response", result.get("output", "No response from API"))
            
            # Update session data
            session_data["message_count"] = session_data.get("message_count", 0) + 1
            session_data["last_message_time"] = time.time()
            
            return {"response": ai_response}
            
        except requests.exceptions.RequestException as e:
            return {"response": f"API request failed: {str(e)}"}
        except Exception as e:
            return {"response": f"Error: {str(e)}"}
    
    def open_session(self, session_id: str, request_data: Dict[str, Any]) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
        """Initialize session with OAuth2 authentication"""
        try:
            # Authenticate and get access token
            access_token = self._get_access_token()
            
            # Optional: Create API session if your API supports it
            # session_response = self._create_api_session(access_token, session_id)
            
            # Initialize session data
            initial_session_data = {
                "created_at": time.time(),
                "message_count": 0,
                "auth_method": "oauth2",
                # "api_session_id": session_response.get("session_id")  # If API supports sessions
            }
            
            # Response to Mend AI
            response_to_mend_ai = {
                "status": "authenticated",
                "session_id": session_id,
                "auth_method": "oauth2",
                "token_expires_at": self._token_expires_at
            }
            
            return response_to_mend_ai, initial_session_data
            
        except Exception as e:
            return {
                "status": "auth_failed",
                "error": f"OAuth2 authentication failed: {str(e)}",
                "session_id": session_id
            }, None
    
    def close_session(self, session_id: str, session_data: Dict[str, Any], request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Clean up OAuth2 authenticated session"""
        try:
            # Optional: Close API session if your API supports it
            # api_session_id = session_data.get("api_session_id")
            # if api_session_id:
            #     self._close_api_session(api_session_id)
            
            # Calculate session statistics
            message_count = session_data.get("message_count", 0)
            duration = time.time() - session_data.get("created_at", time.time())
            
            # Optional: Revoke access token if desired (uncomment if needed)
            # self._revoke_token()
            
            return {
                "status": "closed",
                "session_id": session_id,
                "message_count": message_count,
                "duration_seconds": int(duration),
                "auth_method": "oauth2"
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": f"Session cleanup failed: {str(e)}",
                "session_id": session_id
            }
    
    def _revoke_token(self):
        """Optional: Revoke the current access token"""
        if not self._access_token:
            return
            
        try:
            # Some OAuth2 providers support token revocation
            revoke_url = self.token_url.replace("/token", "/revoke")  # Common pattern
            
            response = requests.post(
                revoke_url,
                data={"token": self._access_token},
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                print("OAuth2 token revoked successfully")
            
        except Exception as e:
            print(f"Token revocation failed: {e}")
        finally:
            # Clear token regardless of revocation success
            self._access_token = None
            self._token_expires_at = 0 
