#!/usr/bin/env python3
"""
Mend AI Red Teaming Bridge - Main Application

This is the core bridge server that connects Mend AI to your AI API.
Users customize adapter.py for their specific integration.
"""

import os
import sys
import importlib.util
import logging
from typing import Dict, Any, Optional, Tuple
from contextlib import asynccontextmanager

import yaml
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn


# ============================================================================
# Configuration and Setup
# ============================================================================

def load_config() -> Dict[str, Any]:
    """Load configuration from config.yml with environment variable substitution"""
    config_path = os.getenv("CONFIG_PATH", "config.yml")
    
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Substitute environment variables
        config = substitute_env_vars(config)
        return config
    except FileNotFoundError:
        logging.warning(f"Config file {config_path} not found, using defaults")
        return get_default_config()
    except Exception as e:
        logging.error(f"Error loading config: {e}")
        return get_default_config()


def substitute_env_vars(obj: Any) -> Any:
    """Recursively substitute ${VAR} patterns with environment variables"""
    if isinstance(obj, dict):
        return {k: substitute_env_vars(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [substitute_env_vars(item) for item in obj]
    elif isinstance(obj, str) and obj.startswith("${") and obj.endswith("}"):
        var_name = obj[2:-1]
        return os.getenv(var_name, obj)  # Return original if env var not found
    return obj


def get_default_config() -> Dict[str, Any]:
    """Default configuration when config.yml is not found"""
    return {
        "bridge": {
            "host": os.getenv("BRIDGE_HOST", "0.0.0.0"),
            "port": int(os.getenv("BRIDGE_PORT", 8000)),
            "cors_origins": ["*"]
        },
        "api": {
            "url": os.getenv("API_URL", "https://api.example.com/v1/chat"),
            "api_key": os.getenv("API_KEY", ""),
            "timeout": int(os.getenv("API_TIMEOUT", 30))
        },
        "logging": {
            "level": os.getenv("LOG_LEVEL", "INFO")
        }
    }


def setup_logging(config: Dict[str, Any]):
    """Setup logging configuration"""
    log_level = config.get("logging", {}).get("level", "INFO")
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )


def load_adapter():
    """Dynamically load the user's adapter.py file"""
    adapter_path = "adapter.py"
    
    if not os.path.exists(adapter_path):
        raise FileNotFoundError(f"Adapter file {adapter_path} not found")
    
    # Load the adapter module
    spec = importlib.util.spec_from_file_location("adapter", adapter_path)
    adapter_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(adapter_module)
    
    # Get the BridgeAdapter class
    if not hasattr(adapter_module, 'BridgeAdapter'):
        raise AttributeError("adapter.py must contain a BridgeAdapter class")
    
    return adapter_module.BridgeAdapter


def print_mend_ai_configuration_guide(config: Dict[str, Any]):
    """Display Mend AI configuration guide on startup"""
    bridge_config = config.get("bridge", {})
    host = bridge_config.get("host", "0.0.0.0")
    port = bridge_config.get("port", 8000)
    
    # Determine the display URL (localhost for local development)
    display_host = "localhost" if host == "0.0.0.0" else host
    base_url = f"http://{display_host}:{port}"
    
    print("\n" + "="*88)
    print("🚀 MEND AI RED TEAMING BRIDGE - CONFIGURATION GUIDE")
    print("="*88)
    print("Configure your Mend AI target with these exact settings:")
    print()
    
    print("🎯 MEND AI TARGET CONFIGURATION:")
    print("   Target URL:       https://<some-public-domain>/chat")
    print('   Request Body:     {"message": "{message}", "session_id": "{session_id}"}')
    print("   Response Path:    response")
    print("   Session Open URL: https://<some-public-domain>/session/open") 
    print("   Session Close URL: https://<some-public-domain>/session/close")
    print()
    
    print("⚡ Bridge Status: READY FOR MEND AI CONNECTION")
    print("="*88)
    print()


# ============================================================================
# Simple Session Management
# ============================================================================

# In-memory session storage - simple and effective for most use cases
sessions: Dict[str, Dict[str, Any]] = {}


def get_session(session_id: str) -> Dict[str, Any]:
    """Get session data by session ID"""
    return sessions.get(session_id, {})


def update_session(session_id: str, data: Dict[str, Any]):
    """Update session data"""
    sessions[session_id] = data


def delete_session(session_id: str):
    """Delete session data"""
    sessions.pop(session_id, None)


# ============================================================================
# Request/Response Models
# ============================================================================

class ChatRequest(BaseModel):
    message: str
    session_id: str


class SessionOpenRequest(BaseModel):
    session_id: str
    # Additional fields can be passed by Mend AI and forwarded to adapter
    

class SessionCloseRequest(BaseModel):
    session_id: str
    # Additional fields can be passed by Mend AI and forwarded to adapter


class ChatResponse(BaseModel):
    response: str


class SessionResponse(BaseModel):
    status: str
    session_id: Optional[str] = None
    error: Optional[str] = None


# ============================================================================
# FastAPI Application
# ============================================================================

# Global variables for app lifecycle
config = {}
adapter_class = None
adapter_instance = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown"""
    global config, adapter_class, adapter_instance
    
    # Startup
    logging.info("Starting Mend AI Bridge...")
    
    # Load configuration
    config = load_config()
    setup_logging(config)
    
    # Load user's adapter
    try:
        adapter_class = load_adapter()
        adapter_instance = adapter_class(config)
        logging.info(f"Loaded adapter: {adapter_class.__name__}")
    except Exception as e:
        logging.error(f"Failed to load adapter: {e}")
        sys.exit(1)
    
    # Display Mend AI configuration guide
    print_mend_ai_configuration_guide(config)
    
    logging.info("Mend AI Bridge started successfully")
    yield
    
    # Shutdown
    logging.info("Shutting down Mend AI Bridge...")


# Load config early for CORS setup
_config = load_config()
_cors_origins = _config.get("bridge", {}).get("cors_origins", ["*"])

# Create FastAPI app
app = FastAPI(
    title="Mend AI Red Teaming Bridge",
    description="Bridge for connecting Mend AI to AI APIs with custom authentication and formatting",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware with proper origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Mend AI-Compatible Endpoints
# ============================================================================

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main chat endpoint for Mend AI
    
    Mend AI sends: {"message": "attack message", "session_id": "abc123"}
    Returns: {"response": "AI response"}
    """
    try:
        # Get current session data
        session_data = get_session(request.session_id)
        
        # Call user's adapter
        response = adapter_instance.send_message(
            message=request.message,
            session_id=request.session_id,
            session_data=session_data
        )
        
        # Update session data (adapter may have modified it)
        update_session(request.session_id, session_data)
        
        # Ensure response format
        if not isinstance(response, dict) or "response" not in response:
            raise ValueError("Adapter must return dict with 'response' key")
        
        return ChatResponse(response=response["response"])
        
    except Exception as e:
        logging.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/session/open")
async def session_open(request: SessionOpenRequest):
    """
    Session open endpoint for Mend AI
    
    Called when Mend AI starts a new testing session.
    Allows custom authentication and session initialization.
    """
    try:
        # Convert Pydantic model to dict for adapter
        request_data = request.dict()
        
        # Call user's adapter for session initialization
        response_data, initial_session_data = adapter_instance.open_session(
            session_id=request.session_id,
            request_data=request_data
        )
        
        # Store initial session data if provided
        if initial_session_data is not None:
            update_session(request.session_id, initial_session_data)
        
        # Return adapter's response to Mend AI
        return response_data
        
    except Exception as e:
        logging.error(f"Session open error: {e}")
        return {
            "status": "error",
            "error": str(e),
            "session_id": request.session_id
        }


@app.post("/session/close")
async def session_close(request: SessionCloseRequest):
    """
    Session close endpoint for Mend AI
    
    Called when Mend AI finishes a testing session.
    Allows custom cleanup and resource management.
    """
    try:
        # Get final session data
        session_data = get_session(request.session_id)
        
        # Convert Pydantic model to dict for adapter
        request_data = request.dict()
        
        # Call user's adapter for cleanup
        response_data = adapter_instance.close_session(
            session_id=request.session_id,
            session_data=session_data,
            request_data=request_data
        )
        
        # Clean up session from memory
        delete_session(request.session_id)
        
        # Return adapter's response to Mend AI
        return response_data
        
    except Exception as e:
        logging.error(f"Session close error: {e}")
        return {
            "status": "error",
            "error": str(e),
            "session_id": request.session_id
        }


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring and Docker"""
    return {
        "status": "healthy",
        "service": "mend-ai-bridge",
        "adapter": adapter_class.__name__ if adapter_class else "not_loaded"
    }


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    # Load config for server settings
    config = load_config()
    setup_logging(config)
    
    # Get server settings
    bridge_config = config.get("bridge", {})
    host = bridge_config.get("host", "0.0.0.0")
    port = bridge_config.get("port", 8000)
    
    # CORS origins are already configured during app creation
    
    logging.info(f"Starting server on {host}:{port}")
    
    # Run the server
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=False,  # Don't use reload in production
        log_level=config.get("logging", {}).get("level", "info").lower()
    ) 