#!/bin/bash

# InfoBlox Control Script - Master control for all services

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
APP_SCRIPT="app_configurable.py"
MCP_SCRIPT="infoblox_mcp_server.py"
DEFAULT_PORT=5002
PID_FILE=".infoblox_app.pid"
MCP_PID_FILE=".infoblox_mcp.pid"

# Functions
print_header() {
    echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║           InfoBlox NLP System Control Panel                 ║${NC}"
    echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo
}

status() {
    print_header
    echo -e "${YELLOW}📊 System Status${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # Check Flask app
    echo -e "\n${YELLOW}Flask Application:${NC}"
    if pgrep -f "$APP_SCRIPT" > /dev/null; then
        PID=$(pgrep -f "$APP_SCRIPT")
        MEMORY=$(ps aux | grep "$APP_SCRIPT" | grep -v grep | awk '{print $4}')
        echo -e "  ${GREEN}✅ Running${NC}"
        echo -e "  📍 PID: $PID"
        echo -e "  💾 Memory: ${MEMORY}%"
        echo -e "  🌐 URL: http://localhost:$DEFAULT_PORT"
        echo -e "  ⚙️  Config: http://localhost:$DEFAULT_PORT/config"
        
        # Test connection
        if curl -s http://localhost:$DEFAULT_PORT/health > /dev/null 2>&1; then
            echo -e "  ${GREEN}✅ Responding to requests${NC}"
        else
            echo -e "  ${RED}⚠️  Not responding${NC}"
        fi
    else
        echo -e "  ${RED}❌ Not running${NC}"
    fi
    
    # Check MCP server
    echo -e "\n${YELLOW}MCP Server:${NC}"
    if pgrep -f "$MCP_SCRIPT" > /dev/null; then
        PID=$(pgrep -f "$MCP_SCRIPT")
        MEMORY=$(ps aux | grep "$MCP_SCRIPT" | grep -v grep | awk '{print $4}')
        echo -e "  ${GREEN}✅ Running${NC}"
        echo -e "  📍 PID: $PID"
        echo -e "  💾 Memory: ${MEMORY}%"
    else
        echo -e "  ${YELLOW}⚠️  Not running${NC}"
    fi
    
    # Check InfoBlox connection
    echo -e "\n${YELLOW}InfoBlox Connection:${NC}"
    if pgrep -f "$APP_SCRIPT" > /dev/null; then
        CONN_STATUS=$(curl -s http://localhost:$DEFAULT_PORT/api/status 2>/dev/null | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('infoblox_connected', False))" 2>/dev/null)
        if [ "$CONN_STATUS" = "True" ]; then
            echo -e "  ${GREEN}✅ Connected to Grid Master${NC}"
        else
            echo -e "  ${RED}❌ Not connected to Grid Master${NC}"
        fi
    fi
    
    # Check ports
    echo -e "\n${YELLOW}Port Status:${NC}"
    for port in 5000 5001 5002 5003; do
        if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
            PROC=$(lsof -i :$port | tail -1 | awk '{print $1}')
            echo -e "  Port $port: ${RED}IN USE${NC} by $PROC"
        else
            echo -e "  Port $port: ${GREEN}FREE${NC}"
        fi
    done
    
    # System resources
    echo -e "\n${YELLOW}System Resources:${NC}"
    PYTHON_COUNT=$(pgrep -c python3)
    echo -e "  🐍 Python processes: $PYTHON_COUNT"
    
    # Log files
    echo -e "\n${YELLOW}Log Files:${NC}"
    for log in flask_app.log mcp_server.log app.log nohup.out; do
        if [ -f "$log" ]; then
            SIZE=$(du -h "$log" | cut -f1)
            echo -e "  📄 $log ($SIZE)"
        fi
    done
}

start() {
    print_header
    echo -e "${GREEN}🚀 Starting InfoBlox Services${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # Clean any existing
    echo -e "\n${YELLOW}Cleaning up old processes...${NC}"
    stop_quiet
    
    # Load environment
    if [ -f .env ]; then
        echo -e "${GREEN}✓${NC} Loading environment from .env"
        export $(cat .env | grep -v '^#' | xargs)
    else
        echo -e "${YELLOW}⚠${NC} No .env file found, using defaults"
        export INFOBLOX_GRID_MASTER_IP="192.168.1.224"
        export INFOBLOX_USERNAME="admin"
        export INFOBLOX_PASSWORD="infoblox"
    fi
    
    # Start Flask app
    echo -e "\n${YELLOW}Starting Flask application...${NC}"
    export INFOBLOX_FLASK_PORT=$DEFAULT_PORT
    nohup python3 $APP_SCRIPT > flask_app.log 2>&1 &
    APP_PID=$!
    echo $APP_PID > $PID_FILE
    
    # Wait and verify
    echo -e "Waiting for startup..."
    sleep 3
    
    if curl -s http://localhost:$DEFAULT_PORT/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Flask application started successfully${NC}"
        echo -e "  📍 PID: $APP_PID"
        echo -e "  🌐 Web Interface: ${BLUE}http://localhost:$DEFAULT_PORT${NC}"
        echo -e "  ⚙️  Configuration: ${BLUE}http://localhost:$DEFAULT_PORT/config${NC}"
    else
        echo -e "${RED}❌ Failed to start Flask application${NC}"
        echo -e "Check flask_app.log for errors"
        return 1
    fi
    
    # Ask about MCP server
    echo
    read -p "$(echo -e ${YELLOW}Start MCP server too? [y/N]:${NC} )" -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}Starting MCP server...${NC}"
        nohup python3 $MCP_SCRIPT > mcp_server.log 2>&1 &
        MCP_PID=$!
        echo $MCP_PID > $MCP_PID_FILE
        sleep 2
        if pgrep -f "$MCP_SCRIPT" > /dev/null; then
            echo -e "${GREEN}✅ MCP server started (PID: $MCP_PID)${NC}"
        else
            echo -e "${RED}❌ MCP server failed to start${NC}"
        fi
    fi
    
    echo
    echo -e "${GREEN}🎉 Services started!${NC}"
}

stop() {
    print_header
    echo -e "${RED}🛑 Stopping InfoBlox Services${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    stop_services
    
    echo
    echo -e "${GREEN}✅ All services stopped${NC}"
}

stop_quiet() {
    stop_services > /dev/null 2>&1
}

stop_services() {
    # Stop Flask app
    if [ -f $PID_FILE ]; then
        PID=$(cat $PID_FILE)
        if kill $PID 2>/dev/null; then
            echo -e "  Stopped Flask app (PID: $PID)"
        fi
        rm -f $PID_FILE
    fi
    
    # Stop by process name
    if pgrep -f "$APP_SCRIPT" > /dev/null; then
        pkill -f "$APP_SCRIPT"
        echo -e "  Stopped Flask app processes"
    fi
    
    # Stop MCP server
    if [ -f $MCP_PID_FILE ]; then
        PID=$(cat $MCP_PID_FILE)
        if kill $PID 2>/dev/null; then
            echo -e "  Stopped MCP server (PID: $PID)"
        fi
        rm -f $MCP_PID_FILE
    fi
    
    if pgrep -f "$MCP_SCRIPT" > /dev/null; then
        pkill -f "$MCP_SCRIPT"
        echo -e "  Stopped MCP server processes"
    fi
    
    # Clean ports
    echo -e "\n${YELLOW}Cleaning up ports...${NC}"
    for port in 5000 5001 5002 5003; do
        if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
            lsof -ti :$port | xargs kill -9 2>/dev/null
            echo -e "  Cleared port $port"
        fi
    done
}

restart() {
    print_header
    echo -e "${YELLOW}🔄 Restarting InfoBlox Services${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    echo -e "\n${RED}Stopping services...${NC}"
    stop_services
    
    echo -e "\n${YELLOW}Waiting for cleanup...${NC}"
    sleep 3
    
    echo -e "\n${GREEN}Starting services...${NC}"
    start
}

cleanup() {
    print_header
    echo -e "${YELLOW}🧹 Deep Cleanup${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    echo -e "\n${RED}⚠️  WARNING: This will kill ALL Python processes!${NC}"
    read -p "$(echo -e ${YELLOW}Continue? [y/N]:${NC} )" -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "\n${YELLOW}Killing all Python processes...${NC}"
        killall -9 python3 2>/dev/null
        killall -9 python 2>/dev/null
        echo -e "  ${GREEN}✓${NC} All Python processes killed"
        
        echo -e "\n${YELLOW}Cleaning all ports 5000-5010...${NC}"
        for port in {5000..5010}; do
            lsof -ti :$port | xargs kill -9 2>/dev/null
        done
        echo -e "  ${GREEN}✓${NC} Ports cleaned"
        
        echo -e "\n${YELLOW}Removing temporary files...${NC}"
        rm -f *.pid *.log nohup.out
        rm -rf __pycache__ .pytest_cache
        echo -e "  ${GREEN}✓${NC} Temporary files removed"
        
        echo -e "\n${GREEN}✅ Deep cleanup complete${NC}"
    else
        echo -e "${YELLOW}Cleanup cancelled${NC}"
    fi
}

logs() {
    print_header
    echo -e "${YELLOW}📄 Application Logs${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    if [ -f flask_app.log ]; then
        echo -e "\n${BLUE}Flask Application (last 30 lines):${NC}"
        echo "----------------------------------------"
        tail -n 30 flask_app.log
    else
        echo -e "\n${YELLOW}No Flask logs found${NC}"
    fi
    
    if [ -f mcp_server.log ]; then
        echo -e "\n${BLUE}MCP Server (last 30 lines):${NC}"
        echo "----------------------------------------"
        tail -n 30 mcp_server.log
    else
        echo -e "\n${YELLOW}No MCP logs found${NC}"
    fi
}

test() {
    print_header
    echo -e "${YELLOW}🧪 Running Tests${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    echo -e "\n${YELLOW}1. Flask App Health:${NC}"
    if curl -s http://localhost:$DEFAULT_PORT/health > /dev/null 2>&1; then
        HEALTH=$(curl -s http://localhost:$DEFAULT_PORT/health)
        echo -e "  ${GREEN}✅ Healthy${NC}"
        echo "  Response: $HEALTH"
    else
        echo -e "  ${RED}❌ Not responding${NC}"
    fi
    
    echo -e "\n${YELLOW}2. InfoBlox Connection:${NC}"
    if curl -s http://localhost:$DEFAULT_PORT/api/status > /dev/null 2>&1; then
        STATUS=$(curl -s http://localhost:$DEFAULT_PORT/api/status | python3 -m json.tool)
        echo "$STATUS" | head -10
    else
        echo -e "  ${RED}❌ Cannot get status${NC}"
    fi
    
    echo -e "\n${YELLOW}3. Query Processing:${NC}"
    TEST_QUERY='{"query":"List all networks"}'
    RESPONSE=$(curl -s -X POST http://localhost:$DEFAULT_PORT/api/process \
        -H "Content-Type: application/json" \
        -d "$TEST_QUERY" 2>/dev/null)
    
    if [ $? -eq 0 ] && [ -n "$RESPONSE" ]; then
        echo -e "  ${GREEN}✅ Query processing working${NC}"
        echo "$RESPONSE" | python3 -m json.tool | head -15
    else
        echo -e "  ${RED}❌ Query processing failed${NC}"
    fi
    
    echo -e "\n${YELLOW}4. Port Accessibility:${NC}"
    for port in 5000 5001 5002 5003; do
        if nc -z localhost $port 2>/dev/null; then
            echo -e "  Port $port: ${GREEN}✅ Accessible${NC}"
        else
            echo -e "  Port $port: ${YELLOW}Not in use${NC}"
        fi
    done
}

monitor() {
    print_header
    echo -e "${YELLOW}📊 Live Monitoring (Press Ctrl+C to stop)${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    while true; do
        clear
        print_header
        echo -e "${YELLOW}📊 Live Monitoring - $(date)${NC}"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        
        # Process status
        echo -e "\n${BLUE}Processes:${NC}"
        ps aux | grep -E "python.*(app_|infoblox)" | grep -v grep | awk '{printf "  PID: %s CPU: %s%% MEM: %s%% CMD: %s\n", $2, $3, $4, $11}'
        
        # Port status
        echo -e "\n${BLUE}Ports:${NC}"
        for port in 5002 5003; do
            if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
                echo -e "  $port: ${GREEN}ACTIVE${NC}"
            else
                echo -e "  $port: ${YELLOW}FREE${NC}"
            fi
        done
        
        # API status
        echo -e "\n${BLUE}API Status:${NC}"
        if curl -s http://localhost:$DEFAULT_PORT/health > /dev/null 2>&1; then
            echo -e "  Health: ${GREEN}OK${NC}"
        else
            echo -e "  Health: ${RED}FAIL${NC}"
        fi
        
        sleep 5
    done
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
    test)
        test
        ;;
    monitor)
        monitor
        ;;
    *)
        print_header
        echo "Usage: $0 {start|stop|restart|status|cleanup|logs|test|monitor}"
        echo ""
        echo "Commands:"
        echo "  ${GREEN}start${NC}    - Start all services"
        echo "  ${RED}stop${NC}     - Stop all services"
        echo "  ${YELLOW}restart${NC}  - Restart all services"
        echo "  ${BLUE}status${NC}   - Show current status"
        echo "  ${YELLOW}cleanup${NC}  - Deep cleanup (kills all Python)"
        echo "  ${BLUE}logs${NC}     - Show recent logs"
        echo "  ${GREEN}test${NC}     - Run basic tests"
        echo "  ${BLUE}monitor${NC}  - Live monitoring mode"
        echo ""
        echo "Quick commands:"
        echo "  Check if running:  $0 status"
        echo "  Quick restart:     $0 restart"
        echo "  View logs:         $0 logs"
        ;;
esac