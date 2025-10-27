"""
OpenAI API Adapter Example

This example shows how to integrate with OpenAI's chat completions API.
Copy this file to adapter.py and customize as needed.

Required environment variables:
- API_KEY: Your OpenAI API key
- MODEL: OpenAI model to use (optional, defaults to gpt-4)
"""

import requests
import time
from typing import Tuple, Optional, Dict, Any


class BridgeAdapter:
    """OpenAI API integration for Mend AI Bridge"""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize OpenAI adapter"""
        # OpenAI configuration
        self.api_url = "https://api.openai.com/v1/chat/completions"
        self.api_key = config.get("api", {}).get("api_key", "")
        self.model = config.get("api", {}).get("model", "gpt-4")
        self.timeout = config.get("api", {}).get("timeout", 30)
        
        # Generation parameters
        self.max_tokens = config.get("api", {}).get("max_tokens", 1000)
        self.temperature = config.get("api", {}).get("temperature", 0.7)
        
        if not self.api_key:
            raise ValueError("OpenAI API key is required. Set API_KEY environment variable.")
        
        print(f"OpenAI adapter initialized - Model: {self.model}")
    
    def send_message(self, message: str, session_id: str, session_data: Dict[str, Any]) -> Dict[str, str]:
        """Send message to OpenAI API"""
        try:
            # Get conversation history from session
            conversation_history = session_data.get("conversation_history", [])
            
            # Build messages array for OpenAI
            messages = []
            
            # Add conversation history
            for entry in conversation_history:
                messages.append({"role": "user", "content": entry["user"]})
                messages.append({"role": "assistant", "content": entry["assistant"]})
            
            # Add current message
            messages.append({"role": "user", "content": message})
            
            # OpenAI API request format
            payload = {
                "model": self.model,
                "messages": messages,
                "max_tokens": self.max_tokens,
                "temperature": self.temperature
            }
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            # Make API request
            response = requests.post(
                self.api_url,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            # Extract response from OpenAI format
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
            return {"response": f"OpenAI API error: {str(e)}"}
        except KeyError as e:
            return {"response": f"Unexpected OpenAI response format: {str(e)}"}
        except Exception as e:
            return {"response": f"Error: {str(e)}"}
    
    def open_session(self, session_id: str, request_data: Dict[str, Any]) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
        """Initialize session for OpenAI conversation"""
        try:
            # Initialize session data
            initial_session_data = {
                "created_at": time.time(),
                "message_count": 0,
                "conversation_history": [],
                "model": self.model
            }
            
            # Response to Mend AI
            response_to_mend_ai = {
                "status": "success",
                "session_id": session_id,
                "model": self.model,
                "provider": "openai"
            }
            
            return response_to_mend_ai, initial_session_data
            
        except Exception as e:
            return {
                "status": "error",
                "error": f"Session initialization failed: {str(e)}",
                "session_id": session_id
            }, None
    
    def close_session(self, session_id: str, session_data: Dict[str, Any], request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Clean up OpenAI session"""
        try:
            # Calculate session statistics
            message_count = session_data.get("message_count", 0)
            duration = time.time() - session_data.get("created_at", time.time())
            conversation_history = session_data.get("conversation_history", [])
            
            # Optional: Log conversation for analysis
            if conversation_history:
                print(f"Session {session_id} completed: {message_count} messages, {len(conversation_history)} exchanges")
            
            return {
                "status": "closed",
                "session_id": session_id,
                "message_count": message_count,
                "conversation_length": len(conversation_history),
                "duration_seconds": int(duration),
                "model": session_data.get("model", self.model)
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": f"Session cleanup failed: {str(e)}",
                "session_id": session_id
            } 
