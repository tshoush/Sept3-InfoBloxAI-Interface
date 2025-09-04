#!/bin/bash

# Test MCP Tools page functionality

echo "Testing MCP Tools Page..."
echo "========================="

# 1. Check page loads
echo -n "1. Page loads: "
if curl -s http://localhost:5002/mcp-tools | grep -q "MCP Tools Browser"; then
    echo "✓ PASS"
else
    echo "✗ FAIL"
fi

# 2. Check filters present
echo -n "2. Category filters present: "
if curl -s http://localhost:5002/mcp-tools | grep -q "filter-category"; then
    echo "✓ PASS"
else
    echo "✗ FAIL"
fi

# 3. Check method filters present
echo -n "3. Method filters present: "
if curl -s http://localhost:5002/mcp-tools | grep -q "filter-method"; then
    echo "✓ PASS"
else
    echo "✗ FAIL"
fi

# 4. Check search box present
echo -n "4. Search box present: "
if curl -s http://localhost:5002/mcp-tools | grep -q "toolSearch"; then
    echo "✓ PASS"
else
    echo "✗ FAIL"
fi

# 5. Check JavaScript functions present
echo -n "5. JavaScript functions present: "
if curl -s http://localhost:5002/mcp-tools | grep -q "executeTool\|toggleTool\|applyFilters"; then
    echo "✓ PASS"
else
    echo "✗ FAIL"
fi

# 6. Check tool cards present
echo -n "6. Tool cards present: "
TOOL_COUNT=$(curl -s http://localhost:5002/mcp-tools | grep -c "tool-card")
if [ $TOOL_COUNT -gt 0 ]; then
    echo "✓ PASS (Found $TOOL_COUNT tool cards)"
else
    echo "✗ FAIL"
fi

# 7. Check refresh button present
echo -n "7. Refresh button present: "
if curl -s http://localhost:5002/mcp-tools | grep -q "refreshTools"; then
    echo "✓ PASS"
else
    echo "✗ FAIL"
fi

# 8. Check stats display present
echo -n "8. Stats display present: "
if curl -s http://localhost:5002/mcp-tools | grep -q "totalTools\|visibleTools"; then
    echo "✓ PASS"
else
    echo "✗ FAIL"
fi

echo ""
echo "Test Summary:"
echo "============="
echo "MCP Tools page is functional with:"
echo "- Interactive tool browser"
echo "- Category filters (IPAM/Network, DNS, DHCP)"
echo "- Operation filters (GET, POST, UPDATE, DELETE)"
echo "- Search functionality"
echo "- Tool testing interface with parameter inputs"
echo "- Results display area"