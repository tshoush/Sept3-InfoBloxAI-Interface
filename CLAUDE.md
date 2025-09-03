# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an Infoblox WAPI integration project that creates a natural language processing (NLP) system for interacting with Infoblox Web API (WAPI) through multiple interfaces. The system uses AI models including Grok API for intent classification and entity extraction.

## Key Components

### setup.sh
The main setup script that orchestrates the entire system installation and configuration. It:
- Sets up Docker containers for Infoblox Swagger UI and Open WebUI
- Fetches WAPI schemas from the Grid Master
- Creates a Python environment with NLP dependencies
- Generates all necessary Python scripts and web interfaces
- Creates training data storage for continuous improvement

## Architecture

### Core Services
1. **Infoblox WAPI**: Target API at `192.168.1.222` (Grid Master)
2. **Docker Services**:
   - Infoblox Swagger UI (port 8080)
   - Open WebUI (port 3000)
3. **Flask Web Interface** (port 5000): Custom web UI with autocomplete
4. **NLP Processing Pipeline**: 
   - spaCy for entity extraction
   - BART model for intent classification
   - Grok API for enhanced processing when confidence is low

### Data Flow
1. User enters natural language query
2. System extracts entities (IP, CIDR, MAC, FQDN, TTL, etc.)
3. Classifies intent based on WAPI operations
4. Executes appropriate WAPI call
5. Returns formatted results
6. Stores successful queries for training

## Development Commands

### Initial Setup
```bash
chmod +x setup.sh
./setup.sh
```

### Docker Management
```bash
# Start services
docker-compose -f ~/infoblox-wapi-nlp/docker-compose.yml up -d

# Stop services
docker-compose -f ~/infoblox-wapi-nlp/docker-compose.yml down

# View logs
docker logs infoblox-swagger
docker logs open-webui
```

### Python Environment
```bash
# Activate environment
source ~/infoblox-wapi-nlp/venv/bin/activate

# Run Flask server
python ~/infoblox-wapi-nlp/app.py

# Test NLP processing directly
python ~/infoblox-wapi-nlp/wapi_nlp.py
```

### Testing API Endpoints
```bash
# Test WAPI connectivity
curl -k -u admin:InfoBlox "https://192.168.1.222/wapi/v2.13.1?_schema"

# Test Flask API
curl -X POST -H "Content-Type: application/json" \
  -d '{"query": "Create a network with CIDR 10.0.0.0/24"}' \
  "http://localhost:5000/api/process_query"

# Test autocomplete suggestions
curl "http://localhost:5000/api/suggestions?query=create"
```

## Key Files and Locations

- **Working Directory**: `~/infoblox-wapi-nlp/`
- **WAPI Schemas**: `~/infoblox-wapi-nlp/schemas/`
- **Python Scripts**: 
  - `wapi_nlp.py`: Core NLP and WAPI integration
  - `app.py`: Flask API server
- **Web Interface**: `~/infoblox-wapi-nlp/templates/index.html`
- **Configuration**: 
  - `grok_config.json`: Grok API key storage
  - `docker-compose.yml`: Container configuration
- **Data Storage**:
  - `training_data.csv`: Successful query storage
  - `wapi_nlp.log`: System logs

## WAPI Operations Support

The system dynamically generates intents for all WAPI objects based on their schemas, supporting:
- **CRUD Operations**: Create, Read (Find/List), Update, Delete
- **Custom Functions**: Object-specific operations
- **Special Operations**: 
  - Get next available IP from network
  - Set extensible attributes
  - Find network utilization
  - Release leases
  - DNS zone management

## Example Natural Language Queries

- "Create a network with CIDR 10.0.0.0/24 and comment TestNetwork"
- "List all networks"
- "Find all host records matching name infoblox.localdomain"
- "Get next available IP from network 10.0.0.0/24"
- "Create a host record for server1.example.com with IP 192.168.0.10"
- "Update A record for test.example.com to IP 192.168.0.20 with TTL 3600"
- "Delete host record for server1.example.com"
- "Show network 192.168.1.0/24 utilization"

## Important Configuration

### Grid Master Settings (in setup.sh)
- `GRID_MASTER_IP`: 192.168.1.222
- `USERNAME`: admin
- `PASSWORD`: InfoBlox
- `WAPI_VERSION`: v2.13.1

### Service Ports
- Swagger UI: 8080
- Open WebUI: 3000
- Flask API: 5000

## Troubleshooting

### Check Service Status
```bash
# Docker services
docker ps

# Python environment
which python
pip list | grep -E "spacy|transformers|flask|openai"
```

### View Logs
```bash
# Application logs
tail -f ~/infoblox-wapi-nlp/wapi_nlp.log

# Docker logs
docker logs -f open-webui
```

### Common Issues
1. **SSL Certificate Warnings**: The script uses `verify=False` for WAPI calls. For production, implement proper SSL verification.
2. **Grok API Key**: Update `~/infoblox-wapi-nlp/grok_config.json` with valid API key
3. **WAPI Access**: Ensure Grid Master IP and credentials are correct
4. **Port Conflicts**: Check if ports 3000, 5000, 8080 are available

## Security Considerations

- Credentials are currently hardcoded in setup.sh - consider using environment variables or secure vaults
- SSL verification is disabled (`verify=False`) - enable for production use
- Grok API key is stored in plain text - consider encrypted storage
- No authentication on Flask web interface - add authentication for production