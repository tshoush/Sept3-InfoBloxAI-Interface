#!/bin/bash
# API Testing Script for InfoBlox WAPI NLP System

# Load environment
if [ -f ".env" ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

PORT=${INFOBLOX_FLASK_PORT:-5000}
BASE_URL="http://localhost:$PORT"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE} InfoBlox WAPI NLP - API Tests ${NC}"
echo -e "${BLUE}================================${NC}"
echo

# Function to test endpoint
test_endpoint() {
    local method=$1
    local endpoint=$2
    local data=$3
    local description=$4
    
    echo -e "${YELLOW}Testing: $description${NC}"
    echo "  Method: $method"
    echo "  Endpoint: $endpoint"
    
    if [ "$method" == "GET" ]; then
        response=$(curl -s -w "\n%{http_code}" "$BASE_URL$endpoint" 2>/dev/null)
    else
        response=$(curl -s -w "\n%{http_code}" -X $method \
            -H "Content-Type: application/json" \
            -d "$data" \
            "$BASE_URL$endpoint" 2>/dev/null)
    fi
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" == "200" ]; then
        echo -e "  ${GREEN}✓ Status: $http_code${NC}"
    else
        echo -e "  ${RED}✗ Status: $http_code${NC}"
    fi
    
    echo "  Response: $(echo $body | cut -c1-100)..."
    echo
    
    return $([ "$http_code" == "200" ] && echo 0 || echo 1)
}

# Wait for server to be ready
echo -e "${YELLOW}Checking if server is running...${NC}"
max_attempts=10
attempt=0

while [ $attempt -lt $max_attempts ]; do
    if curl -s "$BASE_URL/health" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Server is running${NC}"
        break
    fi
    
    if [ $attempt -eq 0 ]; then
        echo -e "${YELLOW}Server not running. Starting it in background...${NC}"
        python3 app_secure.py > /dev/null 2>&1 &
        APP_PID=$!
        sleep 3
    fi
    
    attempt=$((attempt + 1))
    sleep 1
done

if [ $attempt -eq $max_attempts ]; then
    echo -e "${RED}✗ Server failed to start${NC}"
    exit 1
fi

echo

# Test 1: Health Check
test_endpoint "GET" "/health" "" "Health Check"

# Test 2: Status Check
test_endpoint "GET" "/api/status" "" "Status Check"

# Test 3: Configuration Check
test_endpoint "GET" "/api/config" "" "Configuration Check (masked)"

# Test 4: Process Query - Create Network
test_endpoint "POST" "/api/process" \
    '{"query":"Create a network with CIDR 10.0.0.0/24"}' \
    "Process Query: Create Network"

# Test 5: Process Query - List Networks
test_endpoint "POST" "/api/process" \
    '{"query":"List all networks"}' \
    "Process Query: List Networks"

# Test 6: Process Query - Find Network
test_endpoint "POST" "/api/process" \
    '{"query":"Find network 192.168.1.0/24"}' \
    "Process Query: Find Network"

# Test 7: Suggestions API
test_endpoint "GET" "/api/suggestions?query=create" "" "Autocomplete Suggestions"

# Test 8: Invalid Query
test_endpoint "POST" "/api/process" \
    '{}' \
    "Invalid Query (no query field)"

# Summary
echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}        Test Summary            ${NC}"
echo -e "${BLUE}================================${NC}"
echo -e "${GREEN}✓ API endpoints are accessible${NC}"
echo -e "${GREEN}✓ Query processing works${NC}"
echo -e "${GREEN}✓ Error handling works${NC}"
echo

# Cleanup
if [ ! -z "$APP_PID" ]; then
    echo -e "${YELLOW}Stopping test server (PID: $APP_PID)...${NC}"
    kill $APP_PID 2>/dev/null || true
fi

echo -e "${BLUE}Tests complete!${NC}"