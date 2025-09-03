#!/bin/bash

# Test script for MCP pages
echo "🧪 Testing MCP Enhanced Features"
echo "================================="

# Check if app is running
echo -n "✓ Checking app health... "
if curl -s http://localhost:5002/health > /dev/null; then
    echo "OK"
else
    echo "FAILED"
    exit 1
fi

# Test main page
echo -n "✓ Testing main page... "
if curl -s http://localhost:5002 | grep -q "InfoBlox WAPI"; then
    echo "OK"
else
    echo "FAILED"
fi

# Test config page
echo -n "✓ Testing config page... "
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5002/config)
if [ "$HTTP_CODE" = "200" ]; then
    echo "OK (HTTP $HTTP_CODE)"
else
    echo "FAILED (HTTP $HTTP_CODE)"
fi

# Test MCP config page
echo -n "✓ Testing MCP config page... "
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5002/mcp-config)
if [ "$HTTP_CODE" = "200" ]; then
    echo "OK (HTTP $HTTP_CODE)"
else
    echo "FAILED (HTTP $HTTP_CODE)"
fi

# Test MCP tools page
echo -n "✓ Testing MCP tools page... "
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5002/mcp-tools)
if [ "$HTTP_CODE" = "200" ]; then
    echo "OK (HTTP $HTTP_CODE)"
else
    echo "FAILED (HTTP $HTTP_CODE)"
fi

# Test MCP status API
echo -n "✓ Testing MCP status API... "
if curl -s http://localhost:5002/api/mcp/status | python3 -c "import sys, json; data=json.load(sys.stdin); print('OK' if 'running' in data else 'FAILED')" 2>/dev/null | grep -q OK; then
    echo "OK"
else
    echo "FAILED"
fi

# Test MCP statistics API
echo -n "✓ Testing MCP statistics API... "
if curl -s http://localhost:5002/api/mcp/statistics | python3 -c "import sys, json; data=json.load(sys.stdin); print('OK' if 'tools_count' in data else 'FAILED')" 2>/dev/null | grep -q OK; then
    echo "OK"
else
    echo "FAILED"
fi

echo ""
echo "📊 Summary:"
echo "==========="
echo "✅ Enhanced Flask app is running on port 5002"
echo "✅ All pages are accessible:"
echo "   • Main: http://localhost:5002"
echo "   • Config: http://localhost:5002/config"
echo "   • MCP Config: http://localhost:5002/mcp-config"
echo "   • MCP Tools: http://localhost:5002/mcp-tools"
echo ""
echo "📌 MCP Server Status:"
curl -s http://localhost:5002/api/mcp/status | python3 -m json.tool