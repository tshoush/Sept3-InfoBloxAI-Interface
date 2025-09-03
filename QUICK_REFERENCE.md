# 🚀 InfoBlox NLP System - Quick Reference

## 📍 Current Setup
- **Web Interface**: http://localhost:5002
- **Configuration**: http://localhost:5002/config
- **Grid Master**: 192.168.1.224
- **Credentials**: admin / infoblox

---

## ⚡ Quick Commands

### 🎯 Most Used Commands
```bash
# Check status
./infoblox_control.sh status

# Restart application
./infoblox_control.sh restart

# View logs
./infoblox_control.sh logs

# Run tests
./infoblox_control.sh test
```

### 🚀 Starting Services
```bash
# Start with control script (RECOMMENDED)
./infoblox_control.sh start

# Start manually
export INFOBLOX_FLASK_PORT=5002
python3 app_configurable.py &

# Quick start script
./quickstart.sh
```

### 🛑 Stopping Services
```bash
# Stop with control script (RECOMMENDED)
./infoblox_control.sh stop

# Kill specific app
pkill -f app_configurable.py

# Emergency stop (kills ALL Python)
./infoblox_control.sh cleanup
```

### 🔄 Restarting
```bash
# Clean restart (RECOMMENDED)
./infoblox_control.sh restart

# Manual restart
pkill -f app_configurable.py
sleep 2
python3 app_configurable.py &
```

---

## 🧪 Testing

### Quick Test
```bash
# Test if running
curl http://localhost:5002/health

# Test connection status
curl http://localhost:5002/api/status | jq

# Test query processing
curl -X POST http://localhost:5002/api/process \
  -H "Content-Type: application/json" \
  -d '{"query":"List all networks"}' | jq
```

### Full Test Suite
```bash
# Run all tests
./test_api.sh

# Run control script tests
./infoblox_control.sh test

# Live monitoring
./infoblox_control.sh monitor
```

---

## 🧹 Port Management

### Check Ports
```bash
# See what's using port 5002
lsof -i :5002

# Check all Flask ports
for port in 5000 5001 5002 5003; do
    echo "Port $port:"
    lsof -i :$port
done
```

### Clear Ports
```bash
# Clear specific port
lsof -ti :5002 | xargs kill -9

# Clear all Flask ports
for port in 5000 5001 5002 5003; do
    lsof -ti :$port | xargs kill -9 2>/dev/null
done
```

---

## 🔍 Process Management

### Find Processes
```bash
# Find InfoBlox processes
ps aux | grep -E "app_configurable|infoblox_mcp" | grep -v grep

# Get PIDs
pgrep -f app_configurable
```

### Kill Processes
```bash
# Kill by name
pkill -f app_configurable.py

# Kill by PID
kill -9 [PID]

# Kill all Python (CAREFUL!)
killall -9 python3
```

---

## 📊 Monitoring

### Check Status
```bash
# System status
./infoblox_control.sh status

# API status
curl http://localhost:5002/api/status | jq

# Live monitoring
./infoblox_control.sh monitor
```

### View Logs
```bash
# Recent logs
./infoblox_control.sh logs

# Live logs
tail -f flask_app.log

# All logs
ls -la *.log
```

### Check Resources
```bash
# Memory usage
ps aux | grep app_configurable | awk '{print $4 "% memory"}'

# Monitor in real-time
top -p $(pgrep -f app_configurable)
```

---

## 🛠️ Configuration

### Update Settings
1. Open browser: http://localhost:5002/config
2. Or edit `.env` file:
   ```bash
   nano .env
   source .env
   ./infoblox_control.sh restart
   ```

### Test Connection
```bash
# Via API
curl -X POST http://localhost:5002/api/test-connection \
  -H "Content-Type: application/json" \
  -d '{"ip":"192.168.1.224","username":"admin","password":"infoblox"}'

# Via Python
python3 wapi_nlp_secure.py
```

---

## 🚨 Troubleshooting

### App Won't Start
```bash
# Check for errors
python3 app_configurable.py  # Run in foreground

# Check port availability
lsof -i :5002

# Use different port
export INFOBLOX_FLASK_PORT=5003
python3 app_configurable.py
```

### Can't Connect to InfoBlox
```bash
# Test credentials
curl -k -u admin:infoblox https://192.168.1.224/wapi/v2.13.1?_schema

# Check environment
env | grep INFOBLOX
```

### Orphaned Processes
```bash
# Find all Python
ps aux | grep python

# Clean everything
./infoblox_control.sh cleanup
```

---

## 📝 File Locations

| File | Purpose |
|------|---------|
| `app_configurable.py` | Main Flask application |
| `infoblox_mcp_server.py` | MCP server |
| `infoblox_control.sh` | Master control script |
| `.env` | Configuration |
| `flask_app.log` | Application logs |
| `app_config.json` | Saved UI configuration |

---

## 🎯 One-Line Commands

```bash
# Restart everything
./infoblox_control.sh restart

# Check if working
curl -s http://localhost:5002/health && echo "✅ Working" || echo "❌ Not working"

# Quick status
./infoblox_control.sh status | grep "Flask App"

# Emergency cleanup
pkill -9 -f python && lsof -ti :5002 | xargs kill -9

# View errors
tail -n 50 flask_app.log | grep -i error
```

---

## 💡 Pro Tips

1. **Always use the control script** for clean starts/stops
2. **Check status first** before starting: `./infoblox_control.sh status`
3. **Monitor logs** when debugging: `tail -f flask_app.log`
4. **Use different ports** if conflicts: `export INFOBLOX_FLASK_PORT=5003`
5. **Clean weekly**: `./infoblox_control.sh cleanup`

---

**Remember**: The control script (`./infoblox_control.sh`) is your best friend!