#!/bin/bash
# Quick start script for InfoBlox WAPI NLP System

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     InfoBlox WAPI NLP System - Quick Start                  ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo

# Step 1: Load environment
echo -e "${YELLOW}Step 1: Loading environment configuration...${NC}"
if [ -f ".env" ]; then
    export $(cat .env | grep -v '^#' | xargs)
    echo -e "${GREEN}✓ Environment loaded from .env${NC}"
else
    echo -e "${RED}✗ No .env file found${NC}"
    echo -e "${YELLOW}Please create one from template:${NC}"
    echo "  cp .env.example .env"
    echo "  nano .env  # Add your credentials"
    exit 1
fi

# Step 2: Test configuration
echo -e "\n${YELLOW}Step 2: Testing configuration...${NC}"
if python3 config.py > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Configuration valid${NC}"
    python3 -c "
from config import get_config
c = get_config()
print(f'  Grid Master: {c.get(\"GRID_MASTER_IP\")}')
print(f'  Username: {c.get(\"USERNAME\")}')
print(f'  WAPI URL: {c.get_wapi_url()}')
"
else
    echo -e "${RED}✗ Configuration error${NC}"
    python3 config.py
    exit 1
fi

# Step 3: Check Python dependencies
echo -e "\n${YELLOW}Step 3: Checking Python dependencies...${NC}"
missing_deps=()

for dep in flask requests; do
    if python3 -c "import $dep" 2>/dev/null; then
        echo -e "${GREEN}✓ $dep installed${NC}"
    else
        echo -e "${YELLOW}⚠ $dep not installed${NC}"
        missing_deps+=($dep)
    fi
done

if [ ${#missing_deps[@]} -gt 0 ]; then
    echo -e "${YELLOW}Installing missing dependencies...${NC}"
    pip3 install ${missing_deps[@]}
fi

# Step 4: Test WAPI connectivity
echo -e "\n${YELLOW}Step 4: Testing WAPI connectivity...${NC}"
python3 -c "
import sys
sys.path.insert(0, '.')
from wapi_nlp_secure import test_connection
connected, message = test_connection()
if connected:
    print('${GREEN}✓ ' + message + '${NC}')
    sys.exit(0)
else:
    print('${RED}✗ ' + message + '${NC}')
    print('${YELLOW}Note: Grid Master may not be accessible in demo mode${NC}')
    sys.exit(0)  # Continue anyway for demo
" || true

# Step 5: Start Flask application
echo -e "\n${YELLOW}Step 5: Starting Flask application...${NC}"
echo -e "${GREEN}✓ Starting on port ${INFOBLOX_FLASK_PORT:-5000}${NC}"
echo
echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                    ACCESS INFORMATION                        ║${NC}"
echo -e "${BLUE}╠══════════════════════════════════════════════════════════════╣${NC}"
echo -e "${BLUE}║  Web Interface:                                              ║${NC}"
echo -e "${BLUE}║    ${GREEN}http://localhost:${INFOBLOX_FLASK_PORT:-5000}${NC}                                   ${BLUE}║${NC}"
echo -e "${BLUE}║                                                              ║${NC}"
echo -e "${BLUE}║  API Endpoints:                                              ║${NC}"
echo -e "${BLUE}║    Process Query: POST /api/process                         ║${NC}"
echo -e "${BLUE}║    Status Check:  GET  /api/status                          ║${NC}"
echo -e "${BLUE}║    Suggestions:   GET  /api/suggestions                     ║${NC}"
echo -e "${BLUE}║    Health Check:  GET  /health                              ║${NC}"
echo -e "${BLUE}║                                                              ║${NC}"
echo -e "${BLUE}║  Press Ctrl+C to stop the server                            ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo

# Run the Flask app
python3 app_secure.py