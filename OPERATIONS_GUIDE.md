# InfoBlox NLP System - Operations Guide
## Testing, Restarting, and Port Management

---

## 🧪 Testing the Application

### 1. Quick Health Check
```bash
# Check if app is running
curl http://localhost:5002/health

# Check detailed status
curl http://localhost:5002/api/status | python3 -m json.tool
```

### 2. Full Test Suite
```bash
# Run automated tests
./test_api.sh

# Test specific functionality
curl -X POST http://localhost:5002/api/process \
  -H "Content-Type: application/json" \
  -d '{"query":"List all networks"}' | python3 -m json.tool
```

### 3. Manual Browser Testing
1. Open browser: http://localhost:5002
2. Click "Configure" button
3. Test connection to InfoBlox
4. Try example queries

---

## 🔄 Restarting the Application

### Method 1: Clean Restart Script (Recommended)
```bash
# Create restart script
cat > restart_app.sh << 'EOF'
#!/bin/bash
echo "🛑 Stopping all InfoBlox apps..."
pkill -f app_secure.py 2>/dev/null
pkill -f app_configurable.py 2>/dev/null
pkill -f infoblox_mcp_server.py 2>/dev/null
sleep 2

echo "🧹 Cleaning up ports..."
for port in 5000 5001 5002 5003; do
    lsof -ti :$port | xargs kill -9 2>/dev/null
done

echo "✅ Starting fresh instance..."
source .env
export INFOBLOX_FLASK_PORT=5002
python3 app_configurable.py &
echo "🚀 App started on port 5002"
echo "📊 PID: $!"
EOF

chmod +x restart_app.sh
./restart_app.sh
```

### Method 2: Manual Steps
```bash
# Step 1: Find running processes
ps aux | grep -E "app_secure|app_configurable|infoblox" | grep -v grep

# Step 2: Kill specific process
kill -9 [PID]

# Step 3: Start fresh
export INFOBLOX_FLASK_PORT=5002
python3 app_configurable.py &
```

### Method 3: Using Process Management
```bash
# Save PID when starting
python3 app_configurable.py &
echo $! > app.pid

# Kill using saved PID
kill $(cat app.pid)
rm app.pid
```

---

## 🧹 Cleaning Orphaned Ports

### 1. Find What's Using Ports
```bash
# Check specific port
lsof -i :5002

# Check all Flask ports
for port in 5000 5001 5002 5003; do
    echo "Port $port:"
    lsof -i :$port
done

# Alternative method
netstat -an | grep -E "500[0-3]"
```

### 2. Kill Processes on Specific Port
```bash
# Kill everything on port 5002
lsof -ti :5002 | xargs kill -9

# Kill with confirmation
lsof -i :5002
# Review the output, then:
kill -9 [PID]
```

### 3. Complete Port Cleanup Script
```bash
cat > cleanup_ports.sh << 'EOF'
#!/bin/bash
echo "🧹 Cleaning up InfoBlox ports..."

PORTS=(5000 5001 5002 5003 8080 3000)

for port in "${PORTS[@]}"; do
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null ; then
        echo "Found process on port $port"
        lsof -i :$port
        echo "Killing process on port $port..."
        lsof -ti :$port | xargs kill -9 2>/dev/null
        echo "✅ Port $port cleared"
    else
        echo "✓ Port $port is free"
    fi
done

echo "🎉 All ports cleaned!"
EOF

chmod +x cleanup_ports.sh
./cleanup_ports.sh
```

---

## 🔍 Process Management Commands

### Find All InfoBlox Processes
```bash
# List all related processes
ps aux | grep -E "python.*infoblox|python.*app_|python.*wapi" | grep -v grep

# With details
ps aux | grep python | grep -E "(app_secure|app_configurable|infoblox_mcp)" | awk '{print $2, $11, $12}'
```

### Kill All InfoBlox Processes
```bash
# Kill all at once
pkill -f "app_secure|app_configurable|infoblox_mcp"

# Or more aggressive
killall -9 python3 2>/dev/null  # ⚠️ Kills ALL Python processes
```

### Monitor Resources
```bash
# Watch process in real-time
top -p $(pgrep -f app_configurable)

# Check memory usage
ps aux | grep app_configurable | awk '{print $4 "% memory"}'
```

---

## 🚀 Complete Start/Stop/Restart Script

Create this master control script:

```bash
cat > infoblox_control.sh << 'EOF'
#!/bin/bash

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
APP_SCRIPT="app_configurable.py"
MCP_SCRIPT="infoblox_mcp_server.py"
DEFAULT_PORT=5002
PID_FILE=".infoblox_app.pid"

# Functions
status() {
    echo -e "${YELLOW}📊 Status Check${NC}"
    echo "------------------------"
    
    # Check Flask app
    if pgrep -f "$APP_SCRIPT" > /dev/null; then
        PID=$(pgrep -f "$APP_SCRIPT")
        echo -e "${GREEN}✅ Flask app running (PID: $PID)${NC}"
        echo "   URL: http://localhost:$DEFAULT_PORT"
    else
        echo -e "${RED}❌ Flask app not running${NC}"
    fi
    
    # Check MCP server
    if pgrep -f "$MCP_SCRIPT" > /dev/null; then
        PID=$(pgrep -f "$MCP_SCRIPT")
        echo -e "${GREEN}✅ MCP server running (PID: $PID)${NC}"
    else
        echo -e "${YELLOW}⚠️  MCP server not running${NC}"
    fi
    
    # Check ports
    echo -e "\n${YELLOW}🔌 Port Status:${NC}"
    for port in 5000 5001 5002 5003; do
        if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null ; then
            echo "   Port $port: IN USE"
        else
            echo "   Port $port: FREE"
        fi
    done
}

start() {
    echo -e "${GREEN}🚀 Starting InfoBlox services...${NC}"
    
    # Clean any existing
    stop > /dev/null 2>&1
    
    # Load environment
    if [ -f .env ]; then
        export $(cat .env | grep -v '^#' | xargs)
    fi
    
    # Start Flask app
    export INFOBLOX_FLASK_PORT=$DEFAULT_PORT
    nohup python3 $APP_SCRIPT > flask_app.log 2>&1 &
    echo $! > $PID_FILE
    
    sleep 2
    
    # Verify startup
    if curl -s http://localhost:$DEFAULT_PORT/health > /dev/null; then
        echo -e "${GREEN}✅ Flask app started successfully${NC}"
        echo "   URL: http://localhost:$DEFAULT_PORT"
        echo "   Config: http://localhost:$DEFAULT_PORT/config"
        echo "   PID: $(cat $PID_FILE)"
    else
        echo -e "${RED}❌ Failed to start Flask app${NC}"
        return 1
    fi
    
    # Optional: Start MCP server
    read -p "Start MCP server too? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        nohup python3 $MCP_SCRIPT > mcp_server.log 2>&1 &
        echo -e "${GREEN}✅ MCP server started${NC}"
    fi
}

stop() {
    echo -e "${RED}🛑 Stopping InfoBlox services...${NC}"
    
    # Stop Flask app
    if [ -f $PID_FILE ]; then
        kill $(cat $PID_FILE) 2>/dev/null
        rm $PID_FILE
    fi
    pkill -f "$APP_SCRIPT" 2>/dev/null
    
    # Stop MCP server
    pkill -f "$MCP_SCRIPT" 2>/dev/null
    
    # Clean ports
    for port in 5000 5001 5002 5003; do
        lsof -ti :$port | xargs kill -9 2>/dev/null
    done
    
    echo -e "${GREEN}✅ All services stopped${NC}"
}

restart() {
    echo -e "${YELLOW}🔄 Restarting InfoBlox services...${NC}"
    stop
    sleep 2
    start
}

cleanup() {
    echo -e "${YELLOW}🧹 Deep cleanup...${NC}"
    
    # Kill all Python processes (careful!)
    read -p "Kill ALL Python processes? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        killall -9 python3 2>/dev/null
        echo -e "${GREEN}✅ All Python processes killed${NC}"
    fi
    
    # Clean all ports
    for port in {5000..5010}; do
        lsof -ti :$port | xargs kill -9 2>/dev/null
    done
    
    # Remove temp files
    rm -f *.pid *.log nohup.out
    
    echo -e "${GREEN}✅ Cleanup complete${NC}"
}

logs() {
    echo -e "${YELLOW}📄 Recent logs:${NC}"
    echo "------------------------"
    
    if [ -f flask_app.log ]; then
        echo "Flask App (last 20 lines):"
        tail -n 20 flask_app.log
    fi
    
    echo ""
    if [ -f mcp_server.log ]; then
        echo "MCP Server (last 20 lines):"
        tail -n 20 mcp_server.log
    fi
}

# Main menu
case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    status)
        status
        ;;
    cleanup)
        cleanup
        ;;
    logs)
        logs
        ;;
    *)
        echo "InfoBlox Control Script"
        echo "Usage: $0 {start|stop|restart|status|cleanup|logs}"
        echo ""
        echo "  start   - Start all services"
        echo "  stop    - Stop all services"
        echo "  restart - Restart all services"
        echo "  status  - Show current status"
        echo "  cleanup - Deep cleanup (kills all Python)"
        echo "  logs    - Show recent logs"
        ;;
esac
EOF

chmod +x infoblox_control.sh
```

---

## 📊 Testing Procedures

### 1. Basic Connectivity Test
```bash
cat > test_connection.sh << 'EOF'
#!/bin/bash
echo "🧪 Testing InfoBlox Connection..."

# Test Flask app
if curl -s http://localhost:5002/health > /dev/null; then
    echo "✅ Flask app responding"
else
    echo "❌ Flask app not responding"
fi

# Test InfoBlox connection
RESULT=$(curl -s http://localhost:5002/api/status | python3 -c "import sys, json; print(json.load(sys.stdin)['infoblox_connected'])")
if [ "$RESULT" = "True" ]; then
    echo "✅ InfoBlox connected"
else
    echo "❌ InfoBlox not connected"
fi

# Test query processing
RESPONSE=$(curl -s -X POST http://localhost:5002/api/process \
  -H "Content-Type: application/json" \
  -d '{"query":"test"}')
  
if [ $? -eq 0 ]; then
    echo "✅ Query processing working"
else
    echo "❌ Query processing failed"
fi
EOF

chmod +x test_connection.sh
./test_connection.sh
```

### 2. Load Testing
```bash
# Simple load test
for i in {1..10}; do
    curl -s http://localhost:5002/api/status &
done
wait
echo "Load test complete"
```

### 3. Memory Leak Detection
```bash
# Monitor memory over time
while true; do
    ps aux | grep app_configurable | awk '{print strftime("%Y-%m-%d %H:%M:%S"), $4 "% memory"}'
    sleep 60
done
```

---

## 🐛 Troubleshooting

### Problem: Port Already in Use
```bash
# Solution 1: Find and kill
lsof -i :5002
kill -9 [PID]

# Solution 2: Use different port
export INFOBLOX_FLASK_PORT=5003
python3 app_configurable.py
```

### Problem: Can't Stop Application
```bash
# Force kill all Python
pkill -9 -f python

# Nuclear option (kills everything)
killall -9 python python3
```

### Problem: Application Won't Start
```bash
# Check for errors
python3 app_configurable.py  # Run in foreground to see errors

# Check dependencies
pip3 list | grep -E "flask|requests"

# Check environment
env | grep INFOBLOX
```

---

## 🎯 Quick Commands Reference

```bash
# Start
./infoblox_control.sh start

# Stop
./infoblox_control.sh stop

# Restart
./infoblox_control.sh restart

# Status
./infoblox_control.sh status

# Clean everything
./infoblox_control.sh cleanup

# View logs
./infoblox_control.sh logs

# Quick test
curl http://localhost:5002/health

# Full test
./test_api.sh
```

---

## 💡 Best Practices

1. **Always check status before starting**
   ```bash
   ./infoblox_control.sh status
   ```

2. **Use the control script for clean restarts**
   ```bash
   ./infoblox_control.sh restart
   ```

3. **Monitor logs during troubleshooting**
   ```bash
   tail -f flask_app.log
   ```

4. **Clean up weekly**
   ```bash
   ./infoblox_control.sh cleanup
   ```

5. **Keep PID files**
   ```bash
   echo $! > app.pid  # When starting manually
   ```

This guide ensures you can properly manage, test, and troubleshoot your InfoBlox system without leaving orphaned processes or blocked ports!