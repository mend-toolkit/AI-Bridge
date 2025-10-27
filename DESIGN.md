# Mend AI Red Teaming Bridge - Design Document

## Overview

This document outlines the architecture and design for a bridge template that enables Mend AI to connect to complex AI endpoints through a standardized, pluggable interface.

## Design Goals

1. **Mend AI Compatibility**: Present a clean REST API that Mend AI can easily integrate with
2. **Flexibility**: Handle diverse customer authentication and API requirements
3. **Simplicity**: Make it extremely easy for customers to set up their specific integration
4. **Extensibility**: Allow custom components for unique requirements
5. **Production Ready**: Include proper error handling, logging, and deployment support

## Architecture Components

### 1. Bridge Server (FastAPI)
**Purpose**: Central HTTP server that receives Mend AI requests and orchestrates the bridge logic

**Responsibilities**:
- Expose Mend AI-compatible REST endpoints (`/chat`, `/session/open`, `/session/close`)
- Handle HTTP request/response lifecycle
- Load and instantiate user's Bridge Adapter
- Provide health checks and monitoring endpoints

**Key Endpoints**:
```
POST /chat                 # Main chat endpoint for Mend AI
POST /session/open         # Mend AI session initialization  
POST /session/close        # Mend AI session cleanup
GET /health               # Health check
GET /config/validate      # Configuration validation
```

**Mend AI Session Support**:
- `/session/open`: Called by Mend AI to initialize a new testing session
- `/session/close`: Called by Mend AI to clean up after testing session
- Session data persists between `/session/open`, multiple `/chat` calls, and `/session/close`

### 2. User Adapter (Single File)
**Purpose**: Single `adapter.py` file that users customize for their specific integration

**Main Adapter Interface** (`adapter.py`):
```python
from typing import Tuple, Optional
import time
import requests

class BridgeAdapter:
    def __init__(self, config: dict):
        """Initialize with configuration from config.yml"""
        # TODO: Customize this for your API
        self.api_url = config.get("api_url", "https://api.example.com/v1/chat")
        self.api_key = config.get("api_key")
        # Add your specific configuration here
    
    def send_message(self, message: str, session_id: str, session_data: dict) -> dict:
        """Handle chat message - customize for your API format"""
        # TODO: Implement your API request logic
        try:
            response = requests.post(self.api_url, json={
                "message": message,
                "session_id": session_id
            }, headers={
                "Authorization": f"Bearer {self.api_key}"
            })
            
            result = response.json()
            return {"response": result.get("reply", "No response")}
            
        except Exception as e:
            return {"response": f"Error: {str(e)}"}
    
    def open_session(self, session_id: str, request_data: dict) -> Tuple[dict, Optional[dict]]:
        """Handle session open - customize for your authentication"""
        # TODO: Implement your authentication/login logic
        try:
            # Example: simple validation
            return {"status": "success", "session_id": session_id}, {}
            
        except Exception as e:
            return {"error": str(e), "status": "failed"}, None
    
    def close_session(self, session_id: str, session_data: dict, request_data: dict) -> dict:
        """Handle session close - customize for your cleanup"""
        # TODO: Implement your cleanup logic
        try:
            return {"status": "closed", "session_id": session_id}
            
        except Exception as e:
            return {"status": "error", "error": str(e)}
```

**Example Adapters** (for reference):
- `examples/openai-adapter.py`: OpenAI API integration
- `examples/anthropic-adapter.py`: Anthropic API integration 
- `examples/oauth2-adapter.py`: OAuth2 authentication flow
- `examples/login-adapter.py`: Username/password login
- `examples/generic-rest-adapter.py`: Simple REST API pattern

### 3. Simple Session Management
**Purpose**: Handle session lifecycle with in-memory storage

**Built into main.py**:
```python
# Simple in-memory session storage
sessions = {}

def get_session(session_id: str) -> dict:
    return sessions.get(session_id, {})

def update_session(session_id: str, data: dict):
    sessions[session_id] = data

def delete_session(session_id: str):
    sessions.pop(session_id, None)
```

**Features**:
- **In-memory storage**: Simple and fast for most use cases
- **Automatic cleanup**: Sessions cleaned up on container restart
- **Thread-safe**: Using Python's built-in dict operations
- **No external dependencies**: No Redis, no database needed

### 4. Simple Configuration
**Purpose**: Minimal YAML configuration that users customize

**Configuration Structure** (`config.yml`):
```yaml
# Bridge server settings
bridge:
  host: "0.0.0.0"
  port: 8000
  cors_origins: ["*"]

# Your API configuration - customize for your needs  
api:
  url: "https://api.example.com/v1/chat"
  api_key: "${API_KEY}"
  timeout: 30
  # Add any other settings your adapter needs

# Simple logging
logging:
  level: "INFO"
```

## Project Structure

```
ai-red-teaming-bridge-template/
├── main.py                       # FastAPI app - all bridge logic here
├── adapter.py                    # User customizes this file
├── config.yml                    # Simple YAML configuration
├── .env.example                  # Environment variables template
├── .env                         # User's environment variables (git-ignored)
├── docker-compose.yml           # Docker deployment
├── Dockerfile                   # Container build
├── examples/
│   ├── openai-adapter.py        # OpenAI example
│   ├── azure-openai-adapter.py  # Azure OpenAI example
│   ├── oauth2-adapter.py        # OAuth2 example  
│   └── simple-adapter.py        # Basic REST API example
├── tests/
│   └── test_bridge.py           # Simple tests
├── requirements.txt             # Python dependencies
├── .gitignore
├── .dockerignore
├── README.md
└── DESIGN.md
```

## Request Flow

### Mend AI Session Lifecycle
```
1. Mend AI → POST /session/open {session_id: "abc123"}
2. Mend AI → POST /chat {message: "attack1", session_id: "abc123"}
3. Mend AI → POST /chat {message: "attack2", session_id: "abc123"}
4. Mend AI → POST /chat {message: "attack3", session_id: "abc123"}
5. Mend AI → POST /session/close {session_id: "abc123"}
```

### Session Open Flow
1. **Mend AI calls** → `POST /session/open` with request payload (session_id, etc.)
2. **Adapter execution** → Call `adapter.open_session(session_id, request_data)`
3. **Adapter handles** → Authentication, login, validation, API session creation
4. **Session creation** → Store initial session data returned by adapter  
5. **Custom response** → Return adapter's custom response to Mend AI

### Chat Message Flow
1. **Mend AI calls** → `POST /chat` with `message` and `session_id`
2. **Session retrieval** → Get session data from session manager
3. **Adapter execution** → Call `adapter.send_message(message, session_id, session_data)`
4. **Session update** → Update session data if adapter modifies it
5. **Response** → Return `{"response": "..."}` to Mend AI

### Session Close Flow
1. **Mend AI calls** → `POST /session/close` with request payload (session_id, etc.)
2. **Session retrieval** → Get final session data from session manager
3. **Adapter cleanup** → Call `adapter.close_session(session_id, session_data, request_data)`
4. **Adapter handles** → Logout, cleanup, conversation saving, resource deallocation
5. **Session cleanup** → Remove session from session manager
6. **Custom response** → Return adapter's custom response to Mend AI

## Configuration Examples

### Example 1: Simple API Key (`config.yml`)
```yaml
# Simple API with API key authentication
api:
  url: "https://api.example.com/v1/chat"
  api_key: "${API_KEY}"
  timeout: 30
```

### Example 2: OAuth2 Configuration (`config.yml`)
```yaml
# OAuth2 authentication flow
api:
  url: "https://internal-ai.company.com/api/v2/generate"
  client_id: "${CLIENT_ID}"
  client_secret: "${CLIENT_SECRET}"
  token_url: "https://auth.company.com/oauth/token"
  model: "gpt-4"
  temperature: 0.7
```

### Example 3: Login-based Authentication (`config.yml`)
```yaml
# Username/password login system
api:
  url: "https://internal-system.company.com/api"
  login_endpoint: "/auth/login"
  logout_endpoint: "/auth/logout"
  chat_endpoint: "/chat"
  # Credentials passed via Mend AI session open request
```

### Example 4: Complete Configuration (`config.yml`)
```yaml
bridge:
  host: "0.0.0.0"
  port: 8000
  cors_origins: ["*"]

api:
  url: "https://api.example.com/v1/chat"
  api_key: "${API_KEY}"
  timeout: 30

logging:
  level: "INFO"
```

## Quick Start Guide

### 1. Choose Your Starting Point
```bash
# Copy an example adapter that matches your needs
cp examples/openai-adapter.py adapter.py
cp examples/config-examples/openai-config.yml config.yml
```

### 2. Set Up Environment Variables
```bash
# Copy and customize environment variables
cp .env.example .env
# Edit .env with your API keys and settings
```

### 3. Deploy with Docker Compose
```bash
# Start the bridge (pulls environment from .env automatically)
docker-compose up -d

# Bridge starts on http://localhost:8000
# Logs: docker-compose logs -f
```

### 4. Test Your Setup
```bash
# Test your adapter
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello", "session_id": "test123"}'
```

### 5. Configure Mend AI
**Mend AI REST API Configuration:**
- **URL**: `http://your-bridge-server:8000/chat`
- **POST Request Payload Sample**: `{"message": "{message}", "session_id": "{session_id}"}`
- **Response Path**: `$.response`

**Session Management (if needed):**
- **Open Session**: `http://your-bridge-server:8000/session/open`
- **Open Session Payload**: `{"session_id": "{session_id}"}`  (add auth fields if needed)
- **Close Session**: `http://your-bridge-server:8000/session/close`
- **Close Session Payload**: `{"session_id": "{session_id}"}`

## Docker Deployment

### Docker Compose Configuration
The project includes a ready-to-use Docker Compose setup:

```yaml
# docker-compose.yml
version: '3.8'
services:
  mend-ai-bridge:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - .env  # Automatically loads all variables from .env
    volumes:
      - ./adapter.py:/app/adapter.py
      - ./config.yml:/app/config.yml
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### Environment Variables (.env)
```bash
# .env - automatically passed to container
# Copy from .env.example and customize

# API Configuration (customize for your API)
API_KEY=your_api_key_here
API_URL=https://api.example.com/v1/chat

# OAuth2 Configuration (if using OAuth2 example)
CLIENT_ID=your_oauth_client_id
CLIENT_SECRET=your_oauth_client_secret
TOKEN_URL=https://auth.example.com/oauth/token

# Bridge Settings (optional overrides)
BRIDGE_PORT=8000
BRIDGE_HOST=0.0.0.0
LOG_LEVEL=INFO
```

### .env.example Template
The project includes `.env.example` with all common variables:
```bash
# Copy this file to .env and customize
cp .env.example .env

# .env.example contains:
# - All API configuration options
# - Environment-specific settings  
# - Comments explaining each variable
# - Secure defaults where possible
```

### Deployment Commands
```bash
# Start the bridge
docker-compose up -d

# View logs
docker-compose logs -f mend-ai-bridge

# Restart after changes
docker-compose restart mend-ai-bridge

# Stop everything
docker-compose down
```

## Customizing Your Adapter

### Getting Started
Users customize the single `adapter.py` file for their specific integration. The file comes with a simple template and TODO comments to guide customization:

```python
# adapter.py - customize this file for your integration
import requests
from typing import Tuple, Optional

class BridgeAdapter:
    def __init__(self, config: dict):
        """Customize: Load your API configuration"""
        self.api_url = config["api"]["url"]
        self.api_key = config["api"]["api_key"]
        # Add your specific settings here
        
    def send_message(self, message: str, session_id: str, session_data: dict) -> dict:
        """Customize: Implement your API request logic"""
        
        # TODO: Implement your authentication, request format, and response handling
        try:
            response = requests.post(self.api_url, json={
                "message": message,
                "session_id": session_id,
                # Add your API's required fields
            }, headers={
                "Authorization": f"Bearer {self.api_key}",
                # Add your API's required headers
            })
            
            result = response.json()
            
            # TODO: Extract the response from your API's format
            return {"response": result.get("reply", "No response")}
            
        except Exception as e:
            return {"response": f"Error: {str(e)}"}
    
    def open_session(self, session_id: str, request_data: dict) -> Tuple[dict, Optional[dict]]:
        """Customize: Implement your authentication/login logic"""
        
        # TODO: Add your session initialization logic
        # Examples:
        # - OAuth2 token exchange
        # - User login with credentials from request_data
        # - API session creation
        # - Custom validation
        
        try:
            return {"status": "success", "session_id": session_id}, {}
        except Exception as e:
            return {"error": str(e), "status": "failed"}, None
    
    def close_session(self, session_id: str, session_data: dict, request_data: dict) -> dict:
        """Customize: Implement your cleanup logic"""
        
        # TODO: Add your cleanup logic
        # Examples:
        # - Logout/revoke tokens
        # - Close API sessions
        # - Save conversation history
        # - Resource cleanup
        
        try:
            return {"status": "closed", "session_id": session_id}
        except Exception as e:
            return {"status": "error", "error": str(e)}
```

### Workflow: Using Example Adapters

**Step 1: Choose an example that matches your needs**
```bash
ls examples/
# openai-adapter.py - OpenAI API integration
# azure-openai-adapter.py - Azure OpenAI service integration
# oauth2-adapter.py - OAuth2 authentication flow
# simple-adapter.py - Basic REST API pattern
```

**Step 2: Copy and customize**
```bash
# Copy the closest example
cp examples/oauth2-adapter.py adapter.py

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys
```

**Step 3: Deploy and test**
```bash
# Start with Docker Compose
docker-compose up -d

# Test your adapter
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello", "session_id": "test123"}'
```

### Common Customization Patterns

**OAuth2 Flow in your adapter.py:**
```python
def open_session(self, session_id: str, request_data: dict):
    # Get OAuth2 token
    auth_response = requests.post(self.token_url, data={
        "grant_type": "client_credentials",
        "client_id": self.client_id,
        "client_secret": self.client_secret
    })
    
    token = auth_response.json()["access_token"]
    return {"status": "authenticated"}, {"token": token}
```

**User Login in your adapter.py:**
```python
def open_session(self, session_id: str, request_data: dict):
    username = request_data.get("username")
    password = request_data.get("password")
    
    login_response = requests.post(f"{self.api_url}/login", json={
        "username": username, "password": password
    })
    
    if login_response.status_code == 200:
        user_token = login_response.json()["token"]
        return {"status": "logged_in"}, {"user_token": user_token}
    else:
        return {"error": "Login failed"}, None
```

## Next Steps for Implementation

1. **Single main.py**: FastAPI server with all bridge logic, simple session management
2. **Default adapter.py**: Template with TODO comments for customization
3. **Example Adapters**: 4 key examples (OpenAI, Azure OpenAI, OAuth2, Simple REST)
4. **Docker Setup**: Dockerfile, docker-compose.yml with automatic .env loading
5. **Environment Configuration**: .env.example with common settings
6. **Simple Testing**: Basic test coverage for the bridge
7. **Documentation**: Streamlined README with quick start guide

## Key Features for Mend AI Integration

### ✅ **Full Mend AI Session Support**
- Proper `/session/open` and `/session/close` endpoint implementation
- **Complete control over session open**: Users can implement custom authentication, login flows, validation
- **Custom responses to Mend AI**: Return any JSON response format for session operations
- Session data persistence across multiple `/chat` calls
- User adapters can implement stateful conversations and resource management

### ✅ **Complete User Control**
- Single adapter class handles authentication, formatting, and requests
- Users can implement any complex authentication flow (OAuth2, custom tokens, etc.)
- Full control over request/response transformation

### ✅ **Easy Configuration**
- YAML-based configuration with environment variable support
- Built-in adapters for quick start (OpenAI, Anthropic, etc.)
- Clear examples for custom implementations

## Key Benefits of Single Adapter Approach

### ✅ **Maximum Simplicity**
- **2 files to customize**: Just `adapter.py` and `.env`
- **No complex architecture**: Single `main.py` with all bridge logic
- **No external dependencies**: No Redis, no database, no factory patterns
- **Immediate understanding**: Copy example, add API keys, deploy

### ✅ **Zero-Complexity Deployment**
- **3 commands to deploy**: `cp`, `cp`, `docker-compose up -d`
- **No infrastructure setup**: No Redis, no complex config files
- **Environment-driven**: All secrets in `.env` file, automatically loaded
- **Container-first**: Everything runs in Docker with zero setup

### ✅ **Full Power, Zero Complexity**
- **Complete Mend AI integration**: Full session management support
- **Any authentication**: OAuth2, API keys, custom auth flows
- **Custom responses**: Return any JSON format to Mend AI
- **Production ready**: Health checks, auto-restart, scaling support

### ✅ **Developer Friendly**
- **Single file debugging**: All bridge logic in `main.py`
- **Live code updates**: Docker volumes for instant changes
- **Clear examples**: 3 focused examples covering common patterns
- **No framework learning**: Standard FastAPI, no custom abstractions

This ultra-simplified architecture eliminates all unnecessary complexity while maintaining complete functionality. Users can deploy a production-ready Mend AI bridge in under 5 minutes:

```bash
cp examples/oauth2-adapter.py adapter.py
cp .env.example .env
# Edit .env with API keys
docker-compose up -d
# Bridge running on http://localhost:8000
```

## What We Removed

- ❌ **Redis complexity** - Simple in-memory sessions
- ❌ **Complex module structure** - Single `main.py` file  
- ❌ **Factory patterns** - Direct adapter loading
- ❌ **Multiple config files** - Just `.env` and optional `config.yml`
- ❌ **Excessive examples** - 3 focused examples instead of 5+
- ❌ **Documentation bloat** - Streamlined to essentials

## What We Kept

- ✅ **Full Mend AI session support** - Complete session lifecycle management
- ✅ **Custom authentication** - Any auth flow in adapter.py
- ✅ **Production deployment** - Docker, health checks, scaling
- ✅ **Environment isolation** - All secrets in .env
- ✅ **Live development** - Code changes via Docker volumes

**The design fully supports Mend AI's session management requirements with maximum simplicity and zero external dependencies.**

Would you like me to proceed with implementing this simplified design? 