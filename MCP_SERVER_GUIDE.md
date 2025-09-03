# InfoBlox MCP Server - Complete Guide

## 🚀 Overview

The InfoBlox MCP (Model Context Protocol) Server is an intelligent integration layer that:
- **Auto-discovers** all WAPI objects and operations from your InfoBlox Grid Master
- **Dynamically generates** MCP tools for every WAPI endpoint
- **Uses RAG** (Retrieval-Augmented Generation) to provide intelligent documentation
- **Auto-updates** when WAPI schema changes
- **Caches** schemas for optimal performance

## 🎯 Key Features

### 1. Dynamic Tool Generation
Instead of hardcoding tools, the MCP server:
- Connects to InfoBlox WAPI at startup
- Discovers all available objects (network, record:host, record:a, etc.)
- Analyzes each object's schema to understand:
  - Required fields
  - Optional fields
  - Searchable fields
  - Supported operations (CRUD)
  - Custom functions
- Generates appropriate MCP tools for each operation

### 2. RAG-Powered Documentation
- Loads InfoBlox admin guides and documentation into a vector database
- Provides context-aware help and examples
- Learns from successful operations to improve suggestions

### 3. Auto-Discovery & Updates
- Checks WAPI schema every hour
- Automatically generates new tools when new objects are added
- Updates existing tools when schemas change
- No manual intervention required

## 📦 Installation

### Quick Setup
```bash
./setup_mcp.sh
```

### Manual Installation
```bash
# Install dependencies
pip3 install mcp requests chromadb sentence-transformers

# Test connection
python3 infoblox_mcp_server.py
```

## 🔧 Configuration

### Environment Variables
```bash
export INFOBLOX_GRID_MASTER_IP="192.168.1.224"
export INFOBLOX_USERNAME="admin"
export INFOBLOX_PASSWORD="infoblox"
export INFOBLOX_WAPI_VERSION="v2.13.1"
```

### MCP Configuration
The `mcp_config.json` file defines how MCP clients connect to the server:
```json
{
  "mcpServers": {
    "infoblox-wapi": {
      "command": "python3",
      "args": ["infoblox_mcp_server.py"]
    }
  }
}
```

## 🛠️ Generated Tools

### Object-Specific Tools
For each WAPI object (e.g., `network`), the server generates:

#### CRUD Operations
- `create_network` - Create a new network
- `find_network` - Search for networks
- `update_network` - Update existing network
- `delete_network` - Delete a network

#### Custom Functions
- `next_available_ip_network` - Get next available IP
- `resize_network` - Resize network
- `split_network` - Split network into subnets

### Example Generated Tools

#### Network Object
```
Tool: create_network
Description: Create a new network object in InfoBlox
Parameters:
  - network (required): CIDR notation (e.g., 10.0.0.0/24)
  - comment: Description of the network
  - members: Grid members to assign
  - extattrs: Extensible attributes

Tool: find_network
Description: Search for network objects
Parameters:
  - network: Network to search (supports wildcards)
  - comment: Search by comment
  - _max_results: Maximum results to return
```

#### DNS Records
```
Tool: create_record_host
Description: Create host record
Parameters:
  - name (required): FQDN
  - ipv4addrs (required): IPv4 addresses
  - comment: Description

Tool: create_record_a
Description: Create A record
Parameters:
  - name (required): Hostname
  - ipv4addr (required): IPv4 address
  - ttl: Time to live
```

#### DHCP Objects
```
Tool: create_range
Description: Create DHCP range
Parameters:
  - start_addr (required): Start IP
  - end_addr (required): End IP
  - network_view: Network view
  - member: DHCP member

Tool: create_fixedaddress
Description: Create DHCP reservation
Parameters:
  - ipv4addr (required): IP address
  - mac (required): MAC address
```

### Special Tools

#### Natural Language Processing
```
Tool: infoblox_natural_query
Description: Process natural language queries
Example: "Create a network 10.0.0.0/24 with comment Production"
```

#### Schema Management
```
Tool: infoblox_get_schemas
Description: List all available WAPI objects

Tool: infoblox_refresh_tools
Description: Refresh tools from latest WAPI schema
```

## 📚 RAG System

### How It Works
1. **Documentation Loading**: Loads InfoBlox documentation into ChromaDB
2. **Embedding Generation**: Creates vector embeddings for semantic search
3. **Context Retrieval**: Finds relevant documentation for queries
4. **Example Generation**: Provides context-aware examples

### Adding Documentation
Place documentation files in `~/.infoblox_mcp/docs/`:
```bash
# Add InfoBlox admin guide
cp infoblox_admin_guide.pdf ~/.infoblox_mcp/docs/

# Add WAPI reference
cp wapi_reference.html ~/.infoblox_mcp/docs/
```

The RAG system will automatically index new documents.

## 🚀 Usage Examples

### Starting the Server
```bash
# Run directly
python3 infoblox_mcp_server.py

# Run as service
sudo systemctl start infoblox-mcp

# Run in background
nohup python3 infoblox_mcp_server.py > mcp.log 2>&1 &
```

### Using with Claude Desktop
Add to Claude Desktop's configuration:
```json
{
  "mcpServers": {
    "infoblox": {
      "command": "python3",
      "args": ["/path/to/infoblox_mcp_server.py"]
    }
  }
}
```

### Using with Other MCP Clients
Any MCP-compatible client can connect:
```python
from mcp.client import MCPClient

client = MCPClient()
await client.connect("infoblox-wapi")

# List available tools
tools = await client.list_tools()

# Use a tool
result = await client.call_tool(
    "create_network",
    network="10.0.0.0/24",
    comment="Test Network"
)
```

## 📊 Monitoring

### Logs
```bash
# View logs
tail -f ~/.infoblox_mcp/logs/mcp_server.log

# Check cache
ls -la ~/.infoblox_mcp/cache/
```

### Health Check
```bash
# Check if server is running
ps aux | grep infoblox_mcp_server

# Test WAPI connection
curl -k -u admin:infoblox https://192.168.1.224/wapi/v2.13.1?_schema
```

## 🔍 Troubleshooting

### Common Issues

#### 1. MCP Package Not Found
```bash
# Install from source
git clone https://github.com/modelcontextprotocol/mcp.git
cd mcp && pip3 install .
```

#### 2. ChromaDB Issues
```bash
# Clear cache and reinitialize
rm -rf ~/.infoblox_mcp/docs/chromadb
python3 -c "from infoblox_mcp_server import InfoBloxRAG; InfoBloxRAG()"
```

#### 3. Schema Discovery Fails
```bash
# Test connection manually
python3 -c "
from infoblox_mcp_server import InfoBloxWAPIDiscovery
from config import get_config
d = InfoBloxWAPIDiscovery(get_config())
print(d.discover_wapi_objects())
"
```

## 🎯 Advanced Features

### Custom Tool Templates
Add custom tool templates in `~/.infoblox_mcp/templates/`:
```python
# custom_tool.py
def generate_custom_tool(obj_name, schema):
    @tool(name=f"custom_{obj_name}")
    async def handler(**kwargs):
        # Custom logic here
        pass
    return handler
```

### Schema Filters
Configure which objects to expose:
```python
# In infoblox_mcp_server.py
INCLUDE_OBJECTS = ['network', 'record:host', 'record:a']
EXCLUDE_OBJECTS = ['grid:*', 'discovery:*']
```

### Performance Tuning
```python
# Adjust cache TTL
CACHE_TTL = timedelta(hours=24)  # Default: 1 hour

# Limit discovered objects
MAX_OBJECTS = 100  # Default: 50

# Parallel schema fetching
PARALLEL_FETCH = True
```

## 📈 Benefits

### For Developers
- No need to manually code WAPI integrations
- Automatic tool discovery and generation
- Built-in documentation and examples

### For Operations
- Natural language interface to InfoBlox
- No need to remember WAPI syntax
- Automated common tasks

### For AI Assistants
- Rich context from RAG system
- Automatic capability discovery
- Error handling and validation

## 🔮 Future Enhancements

### Planned Features
- [ ] GraphQL interface
- [ ] WebSocket support for real-time updates
- [ ] Multi-grid support
- [ ] Automated backup/restore tools
- [ ] Compliance reporting tools
- [ ] Integration with Terraform/Ansible

### Community Contributions
We welcome contributions! Areas for improvement:
- Additional RAG documentation sources
- Better error handling
- Performance optimizations
- Additional custom functions
- Integration examples

## 📝 Summary

The InfoBlox MCP Server transforms your InfoBlox Grid Master into an intelligent, self-documenting API that:
- **Discovers** all capabilities automatically
- **Generates** tools dynamically
- **Documents** itself using RAG
- **Updates** automatically
- **Integrates** with any MCP client

This creates a powerful, maintainable, and intelligent interface to your InfoBlox infrastructure that evolves with your WAPI schema automatically.