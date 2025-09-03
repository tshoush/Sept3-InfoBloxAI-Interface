# InfoBlox AI Interface 🤖

A modern, AI-powered natural language interface for InfoBlox WAPI with MCP (Model Context Protocol) integration.

![Version](https://img.shields.io/badge/version-2.0.0-blue)
![Python](https://img.shields.io/badge/python-3.8+-green)
![License](https://img.shields.io/badge/license-MIT-purple)

## 🌟 Features

### Natural Language Processing
- Query InfoBlox using plain English
- Automatic intent recognition and parameter extraction
- Support for multiple LLM providers (OpenAI, Anthropic, Grok, Ollama)

### MCP Integration
- Dynamic discovery of WAPI endpoints
- Auto-generated tools for every WAPI object
- RAG-powered documentation and examples
- Real-time schema updates

### Modern Web Interface
- Beautiful, responsive UI with gradient design
- Real-time status monitoring
- Configuration management without restarts
- Interactive tool testing and exploration

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- InfoBlox Grid Master (WAPI v2.13.1+)
- Network access to Grid Master

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/Sept3-InfoBloxAI-Interface.git
cd Sept3-InfoBloxAI-Interface
```

2. Install dependencies:
```bash
pip3 install -r requirements.txt
```

3. Configure environment:
```bash
cp .env.example .env
# Edit .env with your InfoBlox credentials
```

4. Start the application:
```bash
./infoblox_control.sh start
```

5. Open your browser:
```
http://localhost:5002
```

## 📱 Interface Overview

### Main Query Page
- Natural language query input
- Quick example buttons
- Real-time status indicators
- Response viewer with syntax highlighting

### Configuration Page
- InfoBlox connection settings
- LLM provider selection
- Advanced parameters tuning
- Import/Export configuration

### MCP Config Page
- MCP server management
- Statistics dashboard
- Cache management
- Schema refresh controls

### MCP Tools Browser
- Browse discovered WAPI tools
- Search and filter capabilities
- Interactive tool testing
- Category organization

## 🔧 Configuration

### Environment Variables
```bash
# InfoBlox Settings
INFOBLOX_GRID_MASTER_IP=192.168.1.224
INFOBLOX_USERNAME=admin
INFOBLOX_PASSWORD=infoblox
INFOBLOX_WAPI_VERSION=v2.13.1

# Application Settings
INFOBLOX_FLASK_PORT=5002

# LLM Settings (Optional)
OPENAI_API_KEY=your-key-here
ANTHROPIC_API_KEY=your-key-here
GROK_API_KEY=your-key-here
```

## 📝 Example Queries

- "List all networks"
- "Show DNS zones"
- "Create host record server1.example.com with IP 10.0.0.100"
- "Find all A records in zone example.com"
- "Get next available IP in network 10.0.0.0/24"
- "Show DHCP ranges"
- "Delete host record old-server.example.com"

## 🛠️ Management

### Control Script
```bash
# Start services
./infoblox_control.sh start

# Stop services
./infoblox_control.sh stop

# Restart services
./infoblox_control.sh restart

# Check status
./infoblox_control.sh status

# View logs
./infoblox_control.sh logs

# Run tests
./infoblox_control.sh test
```

### Testing
```bash
# Test all pages
./test_mcp_pages.sh

# Test API endpoints
./test_api.sh
```

## 🏗️ Architecture

### Components
1. **Flask Web Application** (`app_mcp_enhanced.py`)
   - Main web interface
   - API endpoints
   - Configuration management

2. **MCP Server** (`infoblox_mcp_server.py`)
   - WAPI discovery
   - Tool generation
   - RAG documentation

3. **NLP Engine** (`wapi_nlp_secure.py`)
   - Query parsing
   - Intent recognition
   - Parameter extraction

4. **Configuration** (`config.py`)
   - Secure credential management
   - Runtime configuration
   - Environment handling

## 📊 API Endpoints

### Status & Health
- `GET /api/status` - System status
- `GET /health` - Health check

### Query Processing
- `POST /api/process` - Process natural language query
- `POST /api/test-connection` - Test InfoBlox connection

### Configuration
- `POST /api/config` - Update configuration
- `POST /api/llm/config` - Configure LLM provider

### MCP Management
- `GET /api/mcp/status` - MCP server status
- `POST /api/mcp/start` - Start MCP server
- `POST /api/mcp/stop` - Stop MCP server
- `POST /api/mcp/refresh-tools` - Refresh tool list

## 🐛 Troubleshooting

### Port Already in Use
```bash
lsof -ti :5002 | xargs kill -9
./infoblox_control.sh start
```

### Connection Issues
```bash
# Test InfoBlox connection
curl -k -u admin:infoblox https://192.168.1.224/wapi/v2.13.1/?_schema

# Check logs
tail -f flask_app.log
```

### Clear Everything
```bash
./infoblox_control.sh cleanup
```

## 📚 Documentation

- [Quick Reference](QUICK_REFERENCE.md) - Common commands and operations
- [Operations Guide](OPERATIONS_GUIDE.md) - Testing and management procedures
- [MCP Server Guide](MCP_SERVER_GUIDE.md) - MCP integration details
- [Development Guide](CLAUDE.md) - Architecture and development notes

## 🤝 Contributing

Contributions are welcome! Please feel free to submit pull requests.

## 📄 License

MIT License - See [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- InfoBlox for WAPI
- Anthropic for Claude and MCP
- OpenAI, Grok, and Ollama for LLM support

---

**Built with ❤️ using Flask, MCP, and AI**