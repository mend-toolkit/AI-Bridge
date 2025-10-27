# Mend AI Red Teaming Bridge Template

A flexible bridge template that enables Mend AI red teaming platform to connect to complex AI endpoints that require custom authentication, request formatting, or other specialized integrations.

## 🎯 **What This Solves**

Mend AI provides excellent red teaming capabilities for AI systems, but sometimes customers have complex requirements that can't be easily configured through Mend AI's standard REST API settings:

- **Complex authentication flows** (OAuth, custom tokens, multi-step auth)
- **Non-standard request/response formats** 
- **Custom headers or query parameters**
- **Stateful session management** and conversation tracking
- **Rate limiting or retry logic**
- **Request preprocessing or response post-processing**

## 🏗️ **How It Works**

```
┌─────────┐  /session/open   ┌─────────────┐    Custom Logic    ┌─────────────────┐
│  Mend AI   │  /chat (multi)   │   Bridge    │ ─────────────────► │   Customer's    │
│ Platform│  /session/close  │   Server    │                    │   AI Endpoint   │
└─────────┘ ────────────────► └─────────────┘ ◄───────────────── └─────────────────┘
                                  │
                                  ▼
                            ┌─────────────┐
                            │   Single    │
                            │   Adapter   │
                            │   Class:    │
                            │ • Auth      │
                            │ • Transform │
                            │ • Session   │
                            │ • Requests  │
                            └─────────────┘
```

The bridge acts as a **translator** between Mend AI and your AI endpoint. You customize one file (`adapter.py`) to handle your specific requirements.

## 🚀 **Quick Start (5 Minutes)**

### Step 1: Clone and Setup
```bash
git clone <this-repo>
cd ai-red-teaming-bridge-template
```

### Step 2: Choose Your Integration Type
```bash
# For OpenAI APIs
cp examples/openai-adapter.py adapter.py

# For Azure OpenAI
cp examples/azure-openai-adapter.py adapter.py

# For OAuth2 APIs  
cp examples/oauth2-adapter.py adapter.py

# For simple REST APIs
cp examples/simple-adapter.py adapter.py

# Or start with the echo server (for testing)
# (adapter.py is already set up as an echo server)
```

### Step 3: Configure Your API
Create a `.env` file with your API credentials:

```bash
# For OpenAI
cat > .env << 'EOF'
API_KEY=sk-your-openai-key-here
API_URL=https://api.openai.com/v1/chat/completions
MODEL=gpt-4
TEMPERATURE=0.7
EOF

# For Azure OpenAI
cat > .env << 'EOF'
AZURE_OPENAI_API_KEY=your-azure-api-key
AZURE_OPENAI_ENDPOINT=https://myresource.openai.azure.com
AZURE_OPENAI_DEPLOYMENT=gpt-4
AZURE_OPENAI_API_VERSION=2024-02-15-preview
EOF

# For OAuth2 APIs
cat > .env << 'EOF'
CLIENT_ID=your_oauth_client_id
CLIENT_SECRET=your_oauth_client_secret
TOKEN_URL=https://auth.company.com/oauth/token
API_URL=https://internal-ai.company.com/api/v1/chat
EOF
```

### Step 4: Deploy with Docker
```bash
docker-compose up -d
```

### Step 5: Test Your Bridge
```bash
# Test the health endpoint
curl http://localhost:8000/health

# Test the chat endpoint
curl -X POST http://localhost:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"message": "Hello AI!", "session_id": "test-123"}'

# Test session management
curl -X POST http://localhost:8000/session/open \
  -H 'Content-Type: application/json' \
  -d '{"session_id": "test-123"}'

# If using ngrok, also test the public URL
curl https://your-ngrok-url.ngrok.io/health
curl -X POST https://your-ngrok-url.ngrok.io/chat \
  -H 'Content-Type: application/json' \
  -d '{"message": "Hello AI!", "session_id": "test-123"}'
```

### Step 6: Expose Your Bridge (Optional)
If you need to expose your bridge to the internet for Mend AI to access it, you can use ngrok:

```bash
# Install ngrok (if not already installed)
# Download from https://ngrok.com/download

# Expose your bridge on port 8000
ngrok http 8000

# You'll see output like:
# Forwarding    https://abc123.ngrok.io -> http://localhost:8000
# Use the https URL for Mend AI configuration
```

### Step 7: Configure Mend AI
In your Mend AI platform, configure a new target with these settings:

| Setting | Value |
|---------|-------|
| **Target URL** | `https://your-ngrok-url.ngrok.io/chat` |
| **HTTP Method** | `POST` |
| **Content-Type** | `application/json` |
| **Request Body** | `{"message": "{message}", "session_id": "{session_id}"}` |
| **Response Path** | `$.response` |
| **Session Open URL** | `https://your-ngrok-url.ngrok.io/session/open` |
| **Session Close URL** | `https://your-ngrok-url.ngrok.io/session/close` |

**Note**: Replace `your-ngrok-url.ngrok.io` with the actual URL provided by ngrok.

## 📋 **Configuration Examples**

### OpenAI Integration
```bash
# .env file
API_KEY=sk-your-openai-key-here
API_URL=https://api.openai.com/v1/chat/completions
MODEL=gpt-4
TEMPERATURE=0.7
MAX_TOKENS=1000
```

### Azure OpenAI Integration
```bash
# .env file
AZURE_OPENAI_API_KEY=your-azure-api-key
AZURE_OPENAI_ENDPOINT=https://myresource.openai.azure.com
AZURE_OPENAI_DEPLOYMENT=gpt-4
AZURE_OPENAI_API_VERSION=2024-02-15-preview
TEMPERATURE=0.7
```

### OAuth2 API Integration
```bash
# .env file
CLIENT_ID=your_oauth_client_id
CLIENT_SECRET=your_oauth_client_secret
TOKEN_URL=https://auth.company.com/oauth/token
API_URL=https://internal-ai.company.com/api/v1/chat
SCOPE=chat.read chat.write
```

### Simple REST API Integration
```bash
# .env file
API_KEY=your-api-key-here
API_URL=https://api.example.com/v1/chat
AUTH_HEADER=Authorization
AUTH_PREFIX=Bearer
```

## 🔧 **Customizing Your Adapter**

The bridge works by customizing a single `adapter.py` file. Here's how to create your own:

### Basic Adapter Structure
```python
import requests
from typing import Tuple, Optional, Dict, Any

class BridgeAdapter:
    def __init__(self, config: Dict[str, Any]):
        """Initialize with your API configuration"""
        self.api_url = config.get("api_url")
        self.api_key = config.get("api_key")
        # Add your specific configuration here
    
    def send_message(self, message: str, session_id: str, session_data: Dict[str, Any]) -> Dict[str, str]:
        """Handle chat messages - customize for your API format"""
        # TODO: Implement your API request logic
        response = requests.post(self.api_url, json={
            "message": message,
            "session_id": session_id
        }, headers={
            "Authorization": f"Bearer {self.api_key}"
        })
        
        result = response.json()
        return {"response": result.get("reply", "No response")}
    
    def open_session(self, session_id: str, request_data: Dict[str, Any]) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
        """Handle session opening - customize for your authentication"""
        # TODO: Implement your authentication/login logic
        return {"status": "success", "session_id": session_id}, {}
    
    def close_session(self, session_id: str, session_data: Dict[str, Any], request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle session closing - customize for your cleanup"""
        # TODO: Implement your cleanup logic
        return {"status": "closed", "session_id": session_id}
```

### Advanced OAuth2 Adapter Example
```python
import requests
import time
from typing import Tuple, Optional, Dict, Any

class OAuth2Adapter:
    def __init__(self, config: Dict[str, Any]):
        self.client_id = config.get("client_id")
        self.client_secret = config.get("client_secret")
        self.token_url = config.get("token_url")
        self.api_url = config.get("api_url")
        self._token = None
        self._token_expires_at = 0
    
    def _get_access_token(self) -> str:
        """Get OAuth2 access token with automatic refresh"""
        if not self._token or time.time() > self._token_expires_at:
            response = requests.post(self.token_url, data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret
            })
            
            token_data = response.json()
            self._token = token_data["access_token"]
            self._token_expires_at = time.time() + token_data["expires_in"] - 60
        
        return self._token
    
    def send_message(self, message: str, session_id: str, session_data: Dict[str, Any]) -> Dict[str, str]:
        """Send message with OAuth2 authentication"""
        token = self._get_access_token()
        
        response = requests.post(self.api_url, json={
            "input": message,
            "conversation_id": session_id
        }, headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        })
        
        result = response.json()
        return {"response": result.get("output", "No response")}
```

## 🚀 **Deployment Options**

### Docker Compose (Recommended)
```bash
# Start the bridge
docker-compose up -d

# View logs
docker-compose logs -f mend-ai-bridge

# Restart after changes
docker-compose restart mend-ai-bridge

# Stop the bridge
docker-compose down
```

### Production Deployment
```bash
# Scale multiple instances
docker-compose up -d --scale mend-ai-bridge=3

# Use with reverse proxy (nginx/traefik) for HTTPS
# Configure load balancing and SSL termination
```

### Exposing with ngrok (Development/Testing)
For development or testing when you need to expose your local bridge to the internet:

```bash
# Start your bridge
docker-compose up -d

# In a new terminal, expose with ngrok
ngrok http 8000

# You'll see output like:
# Forwarding    https://abc123.ngrok.io -> http://localhost:8000
# Forwarding    https://def456.ngrok.io -> http://localhost:8000

# Use the https URL in Mend AI configuration
```

**ngrok Tips:**
- **Free tier**: URLs change each time you restart ngrok
- **Paid tier**: Get persistent URLs
- **Custom domains**: Available with paid plans
- **Authentication**: Add `--basic-auth username:password` for security
- **Region**: Use `ngrok http 8000 --region us` for specific regions

**Security Considerations:**
- ngrok exposes your bridge to the internet
- Consider adding authentication to your bridge
- Use ngrok's built-in authentication for additional security
- Monitor ngrok logs for suspicious activity

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
python main.py

# Or with specific config
python main.py --config config.yml
```

## 🔍 **Troubleshooting**

### Common Issues

**1. Bridge won't start**
```bash
# Check logs
docker-compose logs mend-ai-bridge

# Common causes:
# - Missing .env file
# - Invalid API credentials
# - Network connectivity issues
```

**2. Mend AI can't connect**
```bash
# Test bridge health
curl http://localhost:8000/health

# Test chat endpoint
curl -X POST http://localhost:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"message": "test", "session_id": "test"}'
```

**3. API authentication errors**
```bash
# Check your .env file
cat .env

# Verify API credentials work
curl -H "Authorization: Bearer YOUR_API_KEY" \
  https://api.openai.com/v1/models
```

**4. Session management issues**
```bash
# Test session endpoints
curl -X POST http://localhost:8000/session/open \
  -H 'Content-Type: application/json' \
  -d '{"session_id": "test"}'

curl -X POST http://localhost:8000/session/close \
  -H 'Content-Type: application/json' \
  -d '{"session_id": "test"}'
```

**5. ngrok connection issues**
```bash
# Test ngrok tunnel
curl https://your-ngrok-url.ngrok.io/health

# Check ngrok status
ngrok status

# Restart ngrok if needed
pkill ngrok
ngrok http 8000

# Verify bridge is running
docker-compose ps
curl http://localhost:8000/health
```

### Debug Mode
```bash
# Run with debug logging
LOG_LEVEL=DEBUG docker-compose up

# Or edit config.yml
logging:
  level: "DEBUG"
```

## 📚 **Available Examples**

The `examples/` folder contains working adapters for common scenarios:

- **`openai-adapter.py`** - OpenAI ChatGPT integration
- **`azure-openai-adapter.py`** - Azure OpenAI service integration  
- **`oauth2-adapter.py`** - OAuth2 authentication flow
- **`simple-adapter.py`** - Basic REST API with API key auth

## 🔧 **Environment Variables**

All configuration is controlled via `.env` file:

```bash
# API Configuration (required)
API_KEY=your_secret_key
API_URL=https://api.example.com/v1/chat

# OAuth2 Configuration (if using OAuth2)
CLIENT_ID=oauth_client_id
CLIENT_SECRET=oauth_secret
TOKEN_URL=https://auth.company.com/oauth/token

# Bridge Settings (optional)
BRIDGE_PORT=8000
BRIDGE_HOST=0.0.0.0
LOG_LEVEL=INFO
```

## 📖 **API Reference**

### Bridge Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/chat` | POST | Main chat endpoint for Mend AI |
| `/session/open` | POST | Initialize new testing session |
| `/session/close` | POST | Clean up testing session |
| `/health` | GET | Health check endpoint |

### Request/Response Formats

**Chat Request:**
```json
{
  "message": "Your AI prompt here",
  "session_id": "unique-session-id"
}
```

**Chat Response:**
```json
{
  "response": "AI response text"
}
```

**Session Open/Close:**
```json
{
  "session_id": "unique-session-id"
}
```

## 🤝 **Contributing**

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## 📄 **License**

MIT License - see LICENSE file for details. 