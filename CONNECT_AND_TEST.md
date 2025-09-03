# 🚀 InfoBlox WAPI NLP System - Connection & Testing Guide

## Quick Start (2 Minutes)

### 1️⃣ Start the Application

```bash
# Option A: Quick start script (Recommended)
./quickstart.sh

# Option B: Manual start
export $(cat .env | grep -v '^#' | xargs)
python3 app_secure.py
```

### 2️⃣ Access the Web Interface

Open your browser and go to:
**http://localhost:5000**

You'll see a beautiful web interface with:
- Natural language query input
- Real-time connection status
- Autocomplete suggestions
- Example queries to try

### 3️⃣ Test the System

Click on any example query or type your own:
- "Create a network with CIDR 10.0.0.0/24"
- "List all networks"
- "Find network 192.168.1.0/24"

---

## 📋 Complete Setup Instructions

### Prerequisites

1. **Check Python and pip**:
   ```bash
   python3 --version  # Should be 3.7+
   pip3 --version
   ```

2. **Install basic dependencies**:
   ```bash
   pip3 install flask requests python-dotenv
   ```

3. **Configure credentials**:
   ```bash
   # Copy template
   cp .env.example .env
   
   # Edit with your Infoblox credentials
   nano .env
   ```

### Starting the Application

#### Method 1: Quick Start (Easiest)
```bash
./quickstart.sh
```

This script will:
- ✅ Load environment configuration
- ✅ Validate settings
- ✅ Check dependencies
- ✅ Test WAPI connectivity
- ✅ Start Flask server

#### Method 2: Manual Start
```bash
# Load environment
source .env

# Test configuration
python3 config.py

# Start Flask app
python3 app_secure.py
```

#### Method 3: Background Mode
```bash
# Start in background
nohup python3 app_secure.py > app.log 2>&1 &

# Check if running
ps aux | grep app_secure

# View logs
tail -f app.log

# Stop the app
pkill -f app_secure.py
```

---

## 🌐 Accessing the Application

### Web Interface

1. **Main Interface**: http://localhost:5000
   - Modern, responsive design
   - Real-time connection status
   - Query autocomplete
   - Example queries

2. **Features**:
   - Natural language input
   - JSON response viewer
   - Connection status indicator
   - Configuration display

### API Endpoints

| Endpoint | Method | Description | Example |
|----------|--------|-------------|---------|
| `/` | GET | Web interface | `curl http://localhost:5000` |
| `/api/status` | GET | Connection status | `curl http://localhost:5000/api/status` |
| `/api/process` | POST | Process query | See examples below |
| `/api/suggestions` | GET | Autocomplete | `curl "http://localhost:5000/api/suggestions?query=create"` |
| `/api/config` | GET | View config (masked) | `curl http://localhost:5000/api/config` |
| `/health` | GET | Health check | `curl http://localhost:5000/health` |

---

## 🧪 Testing the System

### Automated Testing

Run the comprehensive test suite:
```bash
./test_api.sh
```

This will test:
- Health checks
- API endpoints
- Query processing
- Error handling
- Autocomplete

### Manual Testing

#### Test 1: Check Status
```bash
curl http://localhost:5000/api/status | python3 -m json.tool
```

Expected response:
```json
{
    "connected": true,
    "message": "Connected successfully",
    "grid_master": "192.168.1.222",
    "wapi_version": "v2.13.1"
}
```

#### Test 2: Process a Query
```bash
curl -X POST http://localhost:5000/api/process \
  -H "Content-Type: application/json" \
  -d '{"query":"Create a network with CIDR 10.0.0.0/24"}' \
  | python3 -m json.tool
```

Expected response:
```json
{
    "query": "Create a network with CIDR 10.0.0.0/24",
    "intent": "create_network",
    "confidence": 0.85,
    "entities": {
        "network": "10.0.0.0/24"
    },
    "wapi_result": {
        "message": "Network created" 
    }
}
```

#### Test 3: Get Suggestions
```bash
curl "http://localhost:5000/api/suggestions?query=create" | python3 -m json.tool
```

#### Test 4: Health Check
```bash
curl http://localhost:5000/health
```

### Browser Testing

1. **Open Web Interface**: http://localhost:5000

2. **Try Example Queries**:
   - Click on any blue example query
   - It will auto-fill and submit

3. **Test Autocomplete**:
   - Type "create" in the input
   - See suggestions appear

4. **Check Connection**:
   - Look for green/red indicator
   - Top-right corner shows status

---

## 🔍 Troubleshooting

### Common Issues

#### 1. Port Already in Use
```bash
# Check what's using port 5000
lsof -i :5000

# Use different port
export INFOBLOX_FLASK_PORT=5001
python3 app_secure.py
```

#### 2. Connection Failed
```bash
# Test configuration
python3 -c "
from config import get_config
config = get_config()
print(f'Grid Master: {config.get(\"GRID_MASTER_IP\")}')
print(f'Credentials: {config.get(\"USERNAME\")}')
"

# Test connectivity
python3 wapi_nlp_secure.py
```

#### 3. Missing Dependencies
```bash
# Install all dependencies
pip3 install flask requests python-dotenv

# Optional: Install NLP libraries
pip3 install spacy transformers torch pandas openai
python3 -m spacy download en_core_web_sm
```

#### 4. Configuration Not Loading
```bash
# Check .env file exists
ls -la .env

# Check permissions
chmod 600 .env

# Manually export
export INFOBLOX_GRID_MASTER_IP="192.168.1.222"
export INFOBLOX_USERNAME="admin"
export INFOBLOX_PASSWORD="InfoBlox"
```

---

## 📊 Monitoring

### View Logs
```bash
# Application logs
tail -f ~/infoblox-wapi-nlp/wapi_nlp.log

# Flask debug output
INFOBLOX_DEBUG=true python3 app_secure.py

# System logs
journalctl -f | grep python
```

### Check Performance
```bash
# Monitor resource usage
top -p $(pgrep -f app_secure.py)

# Check response time
time curl http://localhost:5000/api/status
```

---

## 🎯 Usage Examples

### From Web Interface

1. **Create Network**:
   - Type: "Create a network with CIDR 10.0.0.0/24 and comment Production"
   - Click Process

2. **Find Resources**:
   - Type: "Find all host records for example.com"
   - Click Process

3. **Update Records**:
   - Type: "Update A record for www.example.com to 192.168.1.100"
   - Click Process

### From Command Line

```bash
# Create network
./api_query.sh "Create network 10.0.0.0/24"

# List networks
./api_query.sh "Show all networks"

# Find specific network
./api_query.sh "Find network containing IP 10.0.0.100"
```

### From Python

```python
import requests

# Process a query
response = requests.post(
    'http://localhost:5000/api/process',
    json={'query': 'Create a network with CIDR 10.0.0.0/24'}
)

result = response.json()
print(f"Intent: {result['intent']}")
print(f"Confidence: {result['confidence']}")
print(f"Result: {result['wapi_result']}")
```

---

## 🚦 Production Deployment

### Using systemd (Linux)

Create `/etc/systemd/system/infoblox-nlp.service`:

```ini
[Unit]
Description=InfoBlox WAPI NLP Service
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/InfoBlox-UI
Environment="PATH=/usr/local/bin:/usr/bin"
EnvironmentFile=/path/to/.env
ExecStart=/usr/bin/python3 /path/to/app_secure.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl enable infoblox-nlp
sudo systemctl start infoblox-nlp
sudo systemctl status infoblox-nlp
```

### Using Docker

```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
ENV INFOBLOX_FLASK_PORT=5000
EXPOSE 5000
CMD ["python", "app_secure.py"]
```

Build and run:
```bash
docker build -t infoblox-nlp .
docker run -d -p 5000:5000 --env-file .env infoblox-nlp
```

---

## 📝 Quick Reference Card

```bash
# Start application
./quickstart.sh

# Access web interface
open http://localhost:5000

# Test API
curl http://localhost:5000/api/status

# Process query
curl -X POST http://localhost:5000/api/process \
  -H "Content-Type: application/json" \
  -d '{"query":"List all networks"}'

# Stop application
pkill -f app_secure.py

# View logs
tail -f ~/infoblox-wapi-nlp/wapi_nlp.log

# Run tests
./test_api.sh
```

---

## 🆘 Support

If you encounter issues:

1. Check the [Troubleshooting](#-troubleshooting) section
2. Review logs: `tail -f ~/infoblox-wapi-nlp/wapi_nlp.log`
3. Verify configuration: `python3 config.py`
4. Test connectivity: `python3 wapi_nlp_secure.py`

For additional help, ensure you have:
- ✅ Valid Infoblox credentials
- ✅ Network access to Grid Master
- ✅ Python 3.7+ installed
- ✅ Required Python packages installed

---

**Happy Testing! 🎉**