"""
Amazon Bedrock Converse API Adapter Example

This example shows how to integrate with Amazon Bedrock using the Converse API.
Copy this file to adapter.py and customize as needed.

Required environment variables:
- AWS_ACCESS_KEY_ID: Your AWS access key
- AWS_SECRET_ACCESS_KEY: Your AWS secret key
- AWS_REGION: Your AWS region (e.g., us-east-1)
- BEDROCK_MODEL_ID: Your Bedrock model ID (e.g., anthropic.claude-3-sonnet-20240229-v1:0)

The Converse API handles conversation history automatically through the conversationId parameter.
"""

import boto3
import json
import time
from typing import Tuple, Optional, Dict, Any
from botocore.exceptions import ClientError, NoCredentialsError


class BridgeAdapter:
    """Amazon Bedrock Converse API integration for Mend AI Bridge"""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize Amazon Bedrock adapter"""
        # AWS/Bedrock configuration
        self.region = config.get("api", {}).get("region", "us-east-1")
        self.model_id = config.get("api", {}).get("model_id", "")
        self.timeout = config.get("api", {}).get("timeout", 30)
        
        # Generation parameters
        self.max_tokens = int(config.get("api", {}).get("max_tokens", 1000))
        self.temperature = float(config.get("api", {}).get("temperature", 0.7))
        
        # Validate required configuration
        if not self.model_id:
            raise ValueError("Amazon Bedrock requires: BEDROCK_MODEL_ID")
        
        # Initialize Bedrock client
        try:
            self.bedrock_client = boto3.client(
                'bedrock-runtime',
                region_name=self.region
            )
            print(f"Amazon Bedrock adapter initialized - Model: {self.model_id}, Region: {self.region}")
        except NoCredentialsError:
            raise ValueError("AWS credentials not found. Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY")
        except Exception as e:
            raise ValueError(f"Failed to initialize Bedrock client: {str(e)}")
    
    def send_message(self, message: str, session_id: str, session_data: Dict[str, Any]) -> Dict[str, str]:
        """Send message to Amazon Bedrock Converse API"""
        try:
            # Prepare the message for Bedrock Converse API
            # The Converse API expects a specific message format
            bedrock_message = [{
                "role": "user",
                "content": [
                    {
                        "text": message
                    }
                ]
            }]
            
            # Build the Converse API request
            inference_config = {
                "maxTokens": self.max_tokens,
                "temperature": self.temperature,
            }
                        
            # Make the API request
            response = self.bedrock_client.converse(
                modelId=self.model_id,
                messages=bedrock_message,
                inferenceConfig=inference_config
            )
            
            # Extract the AI response
            ai_response = response['output']['message']['content'][0]['text']
            
            # Store conversation history for our own tracking (optional)
            conversation_history = session_data.get("conversation_history", [])
            conversation_history.append({
                "user": message,
                "assistant": ai_response,
                "timestamp": time.time()
            })
            session_data["conversation_history"] = conversation_history
            session_data["message_count"] = session_data.get("message_count", 0) + 1
            
            return {"response": ai_response}
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            return {"response": f"Bedrock API error ({error_code}): {error_message}"}
        except KeyError as e:
            return {"response": f"Unexpected Bedrock response format: {str(e)}"}
        except Exception as e:
            return {"response": f"Error: {str(e)}"}
    
    def open_session(self, session_id: str, request_data: Dict[str, Any]) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
        """Initialize session for Amazon Bedrock conversation"""
        try:
            # Optional: Test Bedrock connectivity during session open
            # You can uncomment this to validate the model is accessible
            # test_response = self.bedrock_client.converse(
            #     modelId=self.model_id,
            #     body=json.dumps({
            #         "anthropic_version": "bedrock-2023-05-31",
            #         "max_tokens": 1,
            #         "messages": [{"role": "user", "content": [{"type": "text", "text": "test"}]}]
            #     })
            # )
            # if test_response['ResponseMetadata']['HTTPStatusCode'] != 200:
            #     return {
            #         "status": "error",
            #         "error": "Bedrock model not accessible"
            #     }, None
            
            # Initialize session data
            initial_session_data = {
                "created_at": time.time(),
                "message_count": 0,
                "conversation_history": [],
                "model_id": self.model_id,
                "region": self.region,
                "conversation_id": None  # Will be set by Bedrock on first message
            }
            
            # Response to Mend AI
            response_to_mend_ai = {
                "status": "success",
                "session_id": session_id,
                "model_id": self.model_id,
                "region": self.region,
                "provider": "amazon-bedrock",
                "api": "converse"
            }
            
            return response_to_mend_ai, initial_session_data
            
        except Exception as e:
            return {
                "status": "error",
                "error": f"Session initialization failed: {str(e)}",
                "session_id": session_id
            }, None
    
    def close_session(self, session_id: str, session_data: Dict[str, Any], request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Clean up Amazon Bedrock session"""
        try:
            # Calculate session statistics
            message_count = session_data.get("message_count", 0)
            duration = time.time() - session_data.get("created_at", time.time())
            conversation_history = session_data.get("conversation_history", [])
            conversation_id = session_data.get("conversation_id")
            
            # Optional: Log conversation for analysis
            if conversation_history:
                print(f"Bedrock session {session_id} completed: {message_count} messages, {len(conversation_history)} exchanges")
                if conversation_id:
                    print(f"Conversation ID: {conversation_id}")
            
            return {
                "status": "closed",
                "session_id": session_id,
                "message_count": message_count,
                "conversation_length": len(conversation_history),
                "duration_seconds": int(duration),
                "model_id": session_data.get("model_id", self.model_id),
                "conversation_id": conversation_id,
                "provider": "amazon-bedrock"
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": f"Session cleanup failed: {str(e)}",
                "session_id": session_id
            }
