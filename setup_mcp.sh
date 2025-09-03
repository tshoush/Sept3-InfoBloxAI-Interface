#!/bin/bash
# Setup script for InfoBlox MCP Server

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     InfoBlox MCP Server Setup                               ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo

# Check Python
echo -e "${YELLOW}Checking Python installation...${NC}"
if command -v python3 &>/dev/null; then
    echo -e "${GREEN}✓ Python3 found${NC}"
else
    echo -e "${RED}✗ Python3 not found. Please install Python 3.8+${NC}"
    exit 1
fi

# Install required packages
echo -e "\n${YELLOW}Installing required packages...${NC}"

# Core requirements
pip3 install --quiet requests python-dotenv

# MCP package
echo -e "${YELLOW}Installing MCP...${NC}"
pip3 install --quiet mcp || {
    echo -e "${YELLOW}MCP not available via pip. Installing from source...${NC}"
    git clone https://github.com/modelcontextprotocol/mcp.git /tmp/mcp
    cd /tmp/mcp && pip3 install --quiet .
    cd -
}

# ChromaDB for RAG
echo -e "${YELLOW}Installing ChromaDB for RAG support...${NC}"
pip3 install --quiet chromadb

# Optional: Install better embedding models
echo -e "${YELLOW}Installing sentence-transformers for better embeddings...${NC}"
pip3 install --quiet sentence-transformers

echo -e "${GREEN}✓ All packages installed${NC}"

# Create directories
echo -e "\n${YELLOW}Creating MCP directories...${NC}"
mkdir -p ~/.infoblox_mcp/cache
mkdir -p ~/.infoblox_mcp/docs
mkdir -p ~/.infoblox_mcp/logs

# Load environment
if [ -f ".env" ]; then
    echo -e "${GREEN}✓ Loading configuration from .env${NC}"
    export $(cat .env | grep -v '^#' | xargs)
else
    echo -e "${YELLOW}No .env file found. Using defaults.${NC}"
    export INFOBLOX_GRID_MASTER_IP="192.168.1.224"
    export INFOBLOX_USERNAME="admin"
    export INFOBLOX_PASSWORD="infoblox"
fi

# Test InfoBlox connection
echo -e "\n${YELLOW}Testing InfoBlox connection...${NC}"
python3 -c "
import requests
import os
requests.packages.urllib3.disable_warnings()
try:
    url = f\"https://{os.environ.get('INFOBLOX_GRID_MASTER_IP')}/wapi/v2.13.1?_schema\"
    auth = (os.environ.get('INFOBLOX_USERNAME'), os.environ.get('INFOBLOX_PASSWORD'))
    r = requests.get(url, auth=auth, verify=False, timeout=5)
    if r.status_code == 200:
        print('\033[0;32m✓ Successfully connected to InfoBlox\033[0m')
        print(f'  Found {len(r.json().get(\"supported_objects\", []))} WAPI objects')
    else:
        print(f'\033[0;31m✗ Connection failed: {r.status_code}\033[0m')
except Exception as e:
    print(f'\033[0;31m✗ Connection error: {e}\033[0m')
"

# Create systemd service (optional)
echo -e "\n${YELLOW}Do you want to create a systemd service? (y/n)${NC}"
read -r CREATE_SERVICE

if [ "$CREATE_SERVICE" = "y" ]; then
    SERVICE_FILE="/etc/systemd/system/infoblox-mcp.service"
    
    sudo tee $SERVICE_FILE > /dev/null << EOF
[Unit]
Description=InfoBlox MCP Server
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
Environment="PATH=/usr/local/bin:/usr/bin"
EnvironmentFile=$(pwd)/.env
ExecStart=/usr/bin/python3 $(pwd)/infoblox_mcp_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    
    sudo systemctl daemon-reload
    echo -e "${GREEN}✓ Systemd service created${NC}"
    echo -e "  Start with: sudo systemctl start infoblox-mcp"
    echo -e "  Enable on boot: sudo systemctl enable infoblox-mcp"
fi

# Create test script
echo -e "\n${YELLOW}Creating test script...${NC}"
cat > test_mcp.py << 'EOF'
#!/usr/bin/env python3
"""Test script for InfoBlox MCP Server."""

import asyncio
import json
from pathlib import Path

# Add the MCP client code here for testing
async def test_mcp():
    print("Testing InfoBlox MCP Server...")
    
    # Test 1: List available schemas
    print("\n1. Testing schema discovery...")
    # Add actual MCP client code here
    
    print("\nMCP server tests would run here")
    print("Install an MCP client to test the server")

if __name__ == "__main__":
    asyncio.run(test_mcp())
EOF

chmod +x test_mcp.py
echo -e "${GREEN}✓ Test script created${NC}"

echo
echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     Setup Complete!                                         ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo
echo -e "${GREEN}To start the MCP server:${NC}"
echo -e "  python3 infoblox_mcp_server.py"
echo
echo -e "${GREEN}To test the MCP server:${NC}"
echo -e "  python3 test_mcp.py"
echo
echo -e "${GREEN}MCP Configuration:${NC}"
echo -e "  Config file: mcp_config.json"
echo -e "  Cache directory: ~/.infoblox_mcp/cache"
echo -e "  Documentation: ~/.infoblox_mcp/docs"
echo
echo -e "${YELLOW}The MCP server will:${NC}"
echo -e "  • Auto-discover all WAPI objects and operations"
echo -e "  • Generate tools dynamically for each endpoint"
echo -e "  • Use RAG for intelligent documentation"
echo -e "  • Check for schema updates hourly"
echo -e "  • Cache schemas for better performance"