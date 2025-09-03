# InfoBlox AI Interface - Claude Development Guide

This document provides context and guidance for future Claude instances working on this codebase.

**Last Updated:** September 3, 2025
**Version:** 2.0.0

## 📋 Project Overview

An advanced InfoBlox WAPI integration system featuring:
- Natural language query processing
- MCP (Model Context Protocol) integration
- Dynamic tool discovery from WAPI schemas
- RAG-powered documentation
- Modern, responsive web interface

## 🏗️ Architecture

### Core Components

1. **app_mcp_enhanced.py** - Main Flask application
   - Modern UI with gradient design
   - Real-time status monitoring
   - Configuration management
   - MCP integration pages

2. **infoblox_mcp_server.py** - MCP server
   - Auto-discovers WAPI objects
   - Generates tools dynamically
   - RAG documentation system
   - Schema caching

3. **wapi_nlp_secure.py** - NLP engine
   - Query parsing
   - Intent recognition
   - Entity extraction
   - WAPI call execution

4. **config.py** - Configuration management
   - Secure credential handling
   - Environment variables
   - Runtime configuration

### Service Ports
- Flask Web UI: 5002
- MCP Server: Runs as subprocess
- InfoBlox Grid: 192.168.1.224

## 🚀 Quick Start

```bash
# Start everything
./infoblox_control.sh start

# Access web interface
open http://localhost:5002
```

## 🔧 Key Files

### Control & Management
- `infoblox_control.sh` - Master control script
- `test_mcp_pages.sh` - Test MCP features
- `test_api.sh` - API testing

### Configuration
- `.env` - Environment variables
- `app_config.json` - Runtime configuration
- `requirements.txt` - Python dependencies

### Documentation
- `README.md` - User documentation
- `QUICK_REFERENCE.md` - Command reference
- `OPERATIONS_GUIDE.md` - Operations procedures
- `MCP_SERVER_GUIDE.md` - MCP details

## 💻 Development Workflow

### Making Changes
1. Always check status first: `./infoblox_control.sh status`
2. Make changes to relevant files
3. Restart with: `./infoblox_control.sh restart`
4. Test with: `./test_mcp_pages.sh`

### Adding Features
1. For UI changes: Edit `app_mcp_enhanced.py`
2. For MCP tools: Update `infoblox_mcp_server.py`
3. For NLP: Modify `wapi_nlp_secure.py`

### Common Tasks

#### Fix Port Issues
```bash
lsof -ti :5002 | xargs kill -9
./infoblox_control.sh start
```

#### Update Configuration
```bash
# Edit .env file
nano .env
source .env
./infoblox_control.sh restart
```

#### Check Logs
```bash
tail -f flask_app.log
./infoblox_control.sh logs
```

## 🎯 Current Configuration

- **Grid Master IP:** 192.168.1.224
- **Username:** admin
- **Password:** infoblox
- **Port:** 5002
- **WAPI Version:** v2.13.1

## 🐛 Troubleshooting

### App Won't Start
```bash
# Check for port conflicts
lsof -i :5002
# Clean and restart
./infoblox_control.sh cleanup
./infoblox_control.sh start
```

### Status Shows "Checking..."
- Verify InfoBlox credentials in .env
- Test connection: `curl -k -u admin:infoblox https://192.168.1.224/wapi/v2.13.1/?_schema`

### MCP Tools Not Loading
- Start MCP server from MCP Config page
- Check MCP logs: `tail -f mcp_server.log`

## 📝 Recent Changes (v2.0.0)

1. **UI Enhancement**
   - Modern gradient design
   - Spacious layout
   - Real-time status updates
   - Quick example buttons

2. **MCP Integration**
   - Dynamic tool discovery
   - RAG documentation
   - Tool browser page
   - Configuration page

3. **Bug Fixes**
   - Fixed navigation links
   - Fixed status checking
   - Improved error handling

## 🔮 Future Enhancements

- [ ] GraphQL API interface
- [ ] WebSocket for real-time updates
- [ ] Multi-grid support
- [ ] Terraform/Ansible integration
- [ ] Advanced query builder UI

## ⚠️ Important Notes

1. **Security**: Never commit credentials to git
2. **Ports**: Always use port 5002 to avoid conflicts
3. **Testing**: Run tests before committing
4. **Documentation**: Update docs when adding features

## 🤝 For New Contributors

1. Read all documentation first
2. Use the control script for management
3. Test thoroughly before committing
4. Follow existing code patterns
5. Update documentation with changes

---

**Remember**: The control script (`./infoblox_control.sh`) is your best friend!