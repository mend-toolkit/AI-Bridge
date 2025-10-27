"""
Azure OpenAI API Adapter Example

This example shows how to integrate with Azure OpenAI service.
Copy this file to adapter.py and customize as needed.

Required environment variables:
- AZURE_OPENAI_API_KEY: Your Azure OpenAI API key
- AZURE_OPENAI_ENDPOINT: Your Azure OpenAI endpoint (e.g., https://myresource.openai.azure.com)
- AZURE_OPENAI_DEPLOYMENT: Your deployment name (e.g., gpt-4)
- AZURE_OPENAI_API_VERSION: API version (e.g., 2024-02-15-preview)
"""

import requests
import time
from typing import Tuple, Optional, Dict, Any


class BridgeAdapter:
    """Azure OpenAI API integration for Mend AI Bridge"""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize Azure OpenAI adapter"""
        # Azure OpenAI configuration
        self.api_key = config.get("api", {}).get("api_key", "")
        self.endpoint = config.get("api", {}).get("endpoint", "")
        self.deployment = config.get("api", {}).get("deployment", "")
        self.api_version = config.get("api", {}).get("api_version", "2024-02-15-preview")
        self.timeout = config.get("api", {}).get("timeout", 30)
        
        # Generation parameters
        self.max_tokens = int(config.get("api", {}).get("max_tokens", 1000))
        self.temperature = float(config.get("api", {}).get("temperature", 0.7))
        
        # Validate required configuration
        if not all([self.api_key, self.endpoint, self.deployment]):
            raise ValueError("Azure OpenAI requires: AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_DEPLOYMENT")
        
        # Build the full API URL
        # Format: https://{endpoint}/openai/deployments/{deployment}/chat/completions?api-version={version}
        base_endpoint = self.endpoint.rstrip('/')
        self.api_url = f"{base_endpoint}/openai/deployments/{self.deployment}/chat/completions?api-version={self.api_version}"
        
        print(f"Azure OpenAI adapter initialized - Endpoint: {base_endpoint}, Deployment: {self.deployment}")
    
    def send_message(self, message: str, session_id: str, session_data: Dict[str, Any]) -> Dict[str, str]:
        """Send message to Azure OpenAI API"""
        try:
            # Get conversation history from session
            conversation_history = session_data.get("conversation_history", [])
            
            # Build messages array for Azure OpenAI (same format as OpenAI)
            messages = []
            
            # Add conversation history
            for entry in conversation_history:
                messages.append({"role": "user", "content": entry["user"]})
                messages.append({"role": "assistant", "content": entry["assistant"]})
            
            # Add current message
            messages.append({"role": "user", "content": message})
            
            # Azure OpenAI API request format
            payload = {
                "messages": messages,
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                # Note: Azure OpenAI doesn't use "model" parameter - it's specified in the URL via deployment
            }
            
            # Azure OpenAI uses api-key header instead of Authorization Bearer
            headers = {
                "Content-Type": "application/json",
                "api-key": self.api_key
            }
            
            # Make API request
            response = requests.post(
                self.api_url,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            # Extract response (same format as OpenAI)
            result = response.json()
            ai_response = result["choices"][0]["message"]["content"]
            
            # Update conversation history in session
            conversation_history.append({
                "user": message,
                "assistant": ai_response
            })
            session_data["conversation_history"] = conversation_history
            session_data["message_count"] = session_data.get("message_count", 0) + 1
            
            return {"response": ai_response}
            
        except requests.exceptions.RequestException as e:
            return {"response": f"Azure OpenAI API error: {str(e)}"}
        except KeyError as e:
            return {"response": f"Unexpected Azure OpenAI response format: {str(e)}"}
        except Exception as e:
            return {"response": f"Error: {str(e)}"}
    
    def open_session(self, session_id: str, request_data: Dict[str, Any]) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
        """Initialize session for Azure OpenAI conversation"""
        try:
            # Optional: Validate deployment availability
            # You can uncomment this to test connectivity during session open
            # health_url = f"{self.endpoint.rstrip('/')}/openai/deployments?api-version={self.api_version}"
            # health_response = requests.get(
            #     health_url,
            #     headers={"api-key": self.api_key},
            #     timeout=5
            # )
            # if health_response.status_code != 200:
            #     return {
            #         "status": "error",
            #         "error": "Azure OpenAI deployment not accessible"
            #     }, None
            
            # Initialize session data
            initial_session_data = {
                "created_at": time.time(),
                "message_count": 0,
                "conversation_history": [],
                "deployment": self.deployment,
                "api_version": self.api_version
            }
            
            # Response to Mend AI
            response_to_mend_ai = {
                "status": "success",
                "session_id": session_id,
                "deployment": self.deployment,
                "api_version": self.api_version,
                "provider": "azure-openai",
                "endpoint": self.endpoint
            }
            
            return response_to_mend_ai, initial_session_data
            
        except Exception as e:
            return {
                "status": "error",
                "error": f"Session initialization failed: {str(e)}",
                "session_id": session_id
            }, None
    
    def close_session(self, session_id: str, session_data: Dict[str, Any], request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Clean up Azure OpenAI session"""
        try:
            # Calculate session statistics
            message_count = session_data.get("message_count", 0)
            duration = time.time() - session_data.get("created_at", time.time())
            conversation_history = session_data.get("conversation_history", [])
            
            # Optional: Log conversation for analysis
            if conversation_history:
                print(f"Azure OpenAI session {session_id} completed: {message_count} messages, {len(conversation_history)} exchanges")
            
            return {
                "status": "closed",
                "session_id": session_id,
                "message_count": message_count,
                "conversation_length": len(conversation_history),
                "duration_seconds": int(duration),
                "deployment": session_data.get("deployment", self.deployment),
                "provider": "azure-openai"
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": f"Session cleanup failed: {str(e)}",
                "session_id": session_id
            } 