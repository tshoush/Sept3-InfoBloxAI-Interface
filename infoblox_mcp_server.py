#!/usr/bin/env python3
"""
InfoBlox MCP Server - Dynamic tool generation from WAPI schemas with RAG support.

This MCP server:
1. Connects to InfoBlox WAPI and discovers all available objects and operations
2. Dynamically generates MCP tools for each WAPI endpoint
3. Uses RAG to provide intelligent documentation and examples
4. Auto-updates when WAPI schema changes
"""

import os
import sys
import json
import asyncio
import logging
import hashlib
import pickle
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import requests
from pathlib import Path

# MCP imports
try:
    from mcp import Server, Tool, TextContent
    from mcp.server import StdioServerTransport
    MCP_AVAILABLE = True
except ImportError:
    print("MCP not installed. Install with: pip install mcp")
    MCP_AVAILABLE = False

# RAG and NLP imports
try:
    import chromadb
    from chromadb.utils import embedding_functions
    import numpy as np
    CHROMADB_AVAILABLE = True
except ImportError:
    print("ChromaDB not installed. Install with: pip install chromadb")
    CHROMADB_AVAILABLE = False

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import get_config

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class InfoBloxWAPIDiscovery:
    """Discovers and caches WAPI schemas."""
    
    def __init__(self, config):
        self.config = config
        self.base_url = f"https://{config.get('GRID_MASTER_IP')}/wapi/{config.get('WAPI_VERSION')}"
        self.auth = (config.get('USERNAME'), config.get('PASSWORD'))
        self.cache_dir = Path.home() / '.infoblox_mcp' / 'cache'
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.schema_cache = {}
        self.last_update = None
        
    def get_schema_hash(self, schema):
        """Generate hash of schema for change detection."""
        return hashlib.md5(json.dumps(schema, sort_keys=True).encode()).hexdigest()
    
    def discover_wapi_objects(self):
        """Discover all WAPI objects and their operations."""
        try:
            # Get all supported objects
            response = requests.get(
                f"{self.base_url}?_schema",
                auth=self.auth,
                verify=False,
                timeout=10
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to fetch WAPI schema: {response.status_code}")
                return {}
            
            schema_data = response.json()
            supported_objects = schema_data.get('supported_objects', [])
            
            logger.info(f"Discovered {len(supported_objects)} WAPI objects")
            
            # Fetch detailed schema for each object
            objects = {}
            for obj in supported_objects[:50]:  # Limit for initial implementation
                obj_schema = self.fetch_object_schema(obj)
                if obj_schema:
                    objects[obj] = obj_schema
            
            return objects
            
        except Exception as e:
            logger.error(f"Error discovering WAPI objects: {e}")
            return {}
    
    def fetch_object_schema(self, object_name):
        """Fetch detailed schema for a specific object."""
        cache_file = self.cache_dir / f"{object_name.replace(':', '_')}_schema.json"
        
        # Check cache first (valid for 1 hour)
        if cache_file.exists():
            cache_age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
            if cache_age < timedelta(hours=1):
                with open(cache_file) as f:
                    return json.load(f)
        
        try:
            response = requests.get(
                f"{self.base_url}/{object_name}?_schema&_schema_version=2",
                auth=self.auth,
                verify=False,
                timeout=5
            )
            
            if response.status_code == 200:
                schema = response.json()
                
                # Parse schema to extract operations
                operations = {
                    'object_name': object_name,
                    'fields': [],
                    'searchable_fields': [],
                    'required_fields': [],
                    'functions': [],
                    'restrictions': schema.get('restrictions', []),
                    'supports_crud': {
                        'create': 'create' in schema.get('restrictions', []),
                        'read': 'read' in schema.get('restrictions', []),
                        'update': 'update' in schema.get('restrictions', []),
                        'delete': 'delete' in schema.get('restrictions', [])
                    }
                }
                
                # Extract fields
                for field in schema.get('fields', []):
                    field_info = {
                        'name': field.get('name'),
                        'type': field.get('type'),
                        'is_array': field.get('is_array', False),
                        'searchable': field.get('searchable', False),
                        'required': field.get('required_on_create', False),
                        'supports_search': field.get('supports', {}).get('search', False),
                        'comment': field.get('comment', '')
                    }
                    operations['fields'].append(field_info)
                    
                    if field_info['searchable']:
                        operations['searchable_fields'].append(field_info['name'])
                    if field_info['required']:
                        operations['required_fields'].append(field_info['name'])
                
                # Extract custom functions
                operations['functions'] = schema.get('supported_functions', [])
                
                # Save to cache
                with open(cache_file, 'w') as f:
                    json.dump(operations, f, indent=2)
                
                return operations
                
        except Exception as e:
            logger.error(f"Error fetching schema for {object_name}: {e}")
            return None
    
    def check_for_updates(self):
        """Check if WAPI schema has changed since last check."""
        current_hash = self.get_current_schema_hash()
        cached_hash = self.load_cached_hash()
        
        if current_hash != cached_hash:
            logger.info("WAPI schema has changed, updating tools...")
            self.save_cached_hash(current_hash)
            return True
        return False
    
    def get_current_schema_hash(self):
        """Get hash of current WAPI schema."""
        try:
            response = requests.get(
                f"{self.base_url}?_schema",
                auth=self.auth,
                verify=False,
                timeout=5
            )
            if response.status_code == 200:
                return self.get_schema_hash(response.json())
        except:
            pass
        return None
    
    def load_cached_hash(self):
        """Load cached schema hash."""
        hash_file = self.cache_dir / 'schema_hash.txt'
        if hash_file.exists():
            return hash_file.read_text().strip()
        return None
    
    def save_cached_hash(self, schema_hash):
        """Save schema hash to cache."""
        hash_file = self.cache_dir / 'schema_hash.txt'
        hash_file.write_text(schema_hash)


class InfoBloxRAG:
    """RAG system for InfoBlox documentation and examples."""
    
    def __init__(self):
        self.docs_dir = Path.home() / '.infoblox_mcp' / 'docs'
        self.docs_dir.mkdir(parents=True, exist_ok=True)
        self.collection = None
        
        if CHROMADB_AVAILABLE:
            self.setup_chromadb()
    
    def setup_chromadb(self):
        """Initialize ChromaDB for RAG."""
        try:
            self.client = chromadb.PersistentClient(
                path=str(self.docs_dir / 'chromadb')
            )
            
            # Get or create collection
            try:
                self.collection = self.client.get_collection("infoblox_docs")
                logger.info("Loaded existing InfoBlox documentation collection")
            except:
                self.collection = self.client.create_collection(
                    "infoblox_docs",
                    embedding_function=embedding_functions.DefaultEmbeddingFunction()
                )
                logger.info("Created new InfoBlox documentation collection")
                self.load_default_docs()
                
        except Exception as e:
            logger.error(f"Failed to setup ChromaDB: {e}")
    
    def load_default_docs(self):
        """Load default InfoBlox documentation."""
        default_docs = [
            {
                "id": "network_create",
                "content": "To create a network in InfoBlox, use the network object with the required 'network' field in CIDR format (e.g., 10.0.0.0/24). Optional fields include comment, members, and extensible attributes.",
                "metadata": {"object": "network", "operation": "create"}
            },
            {
                "id": "network_find",
                "content": "To find networks, use GET requests with search parameters like 'network', 'network_view', or 'comment'. You can use wildcards and regex patterns for flexible searching.",
                "metadata": {"object": "network", "operation": "find"}
            },
            {
                "id": "host_record",
                "content": "Host records (record:host) map hostnames to IP addresses. Required fields are 'name' (FQDN) and 'ipv4addrs' (array of IP addresses). Host records can have multiple IPs.",
                "metadata": {"object": "record:host", "operation": "create"}
            },
            {
                "id": "dns_a_record",
                "content": "A records (record:a) map a hostname to a single IPv4 address. Required fields are 'name' (FQDN) and 'ipv4addr' (single IP). TTL can be customized.",
                "metadata": {"object": "record:a", "operation": "create"}
            },
            {
                "id": "ptr_record",
                "content": "PTR records (record:ptr) provide reverse DNS lookup. Required fields are 'ptrdname' (FQDN) and 'ipv4addr' or 'ipv6addr'.",
                "metadata": {"object": "record:ptr", "operation": "create"}
            },
            {
                "id": "dhcp_range",
                "content": "DHCP ranges define IP address pools for dynamic allocation. Required fields are 'start_addr' and 'end_addr'. Must be within a configured network.",
                "metadata": {"object": "range", "operation": "create"}
            },
            {
                "id": "fixed_address",
                "content": "Fixed addresses (fixedaddress) create DHCP reservations. Required fields are 'ipv4addr' and 'mac' (MAC address in format XX:XX:XX:XX:XX:XX).",
                "metadata": {"object": "fixedaddress", "operation": "create"}
            },
            {
                "id": "grid_management",
                "content": "Grid management operations include member management, service restart, and configuration deployment. Use grid:* objects for grid-wide operations.",
                "metadata": {"object": "grid", "operation": "manage"}
            },
            {
                "id": "extensible_attributes",
                "content": "Extensible attributes (EA) are custom fields that can be added to any object. Common EAs include Site, Owner, Department, Environment. Use 'extattrs' field as a dictionary.",
                "metadata": {"concept": "extensible_attributes"}
            },
            {
                "id": "best_practices",
                "content": "Best practices: Always use _return_fields to limit response size, use _max_results for large queries, implement pagination with _paging, use specific search fields instead of generic searches.",
                "metadata": {"concept": "best_practices"}
            }
        ]
        
        if self.collection:
            self.collection.add(
                ids=[doc["id"] for doc in default_docs],
                documents=[doc["content"] for doc in default_docs],
                metadatas=[doc["metadata"] for doc in default_docs]
            )
            logger.info(f"Loaded {len(default_docs)} default documentation entries")
    
    def add_wapi_schema_docs(self, schemas):
        """Add WAPI schema information to RAG."""
        if not self.collection:
            return
        
        docs = []
        for obj_name, schema in schemas.items():
            if schema:
                # Create documentation for each object
                doc_content = f"Object: {obj_name}\n"
                doc_content += f"Supported operations: {', '.join(schema.get('restrictions', []))}\n"
                
                if schema.get('required_fields'):
                    doc_content += f"Required fields: {', '.join(schema['required_fields'])}\n"
                
                if schema.get('searchable_fields'):
                    doc_content += f"Searchable fields: {', '.join(schema['searchable_fields'])}\n"
                
                if schema.get('functions'):
                    doc_content += f"Custom functions: {', '.join(schema['functions'])}\n"
                
                docs.append({
                    "id": f"schema_{obj_name}",
                    "content": doc_content,
                    "metadata": {"object": obj_name, "type": "schema"}
                })
        
        if docs:
            try:
                # Remove old schema docs
                existing_ids = [f"schema_{name}" for name in schemas.keys()]
                self.collection.delete(ids=existing_ids)
                
                # Add new schema docs
                self.collection.add(
                    ids=[doc["id"] for doc in docs],
                    documents=[doc["content"] for doc in docs],
                    metadatas=[doc["metadata"] for doc in docs]
                )
                logger.info(f"Added {len(docs)} schema documentation entries to RAG")
            except Exception as e:
                logger.error(f"Error adding schema docs to RAG: {e}")
    
    def query_docs(self, query, n_results=3):
        """Query documentation using RAG."""
        if not self.collection:
            return []
        
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results
            )
            
            if results and results['documents']:
                return results['documents'][0]
            return []
            
        except Exception as e:
            logger.error(f"Error querying RAG: {e}")
            return []
    
    def generate_example(self, object_name, operation):
        """Generate example for a specific operation."""
        query = f"Example of {operation} operation for {object_name}"
        docs = self.query_docs(query, n_results=1)
        
        if docs:
            return docs[0]
        
        # Fallback to generic examples
        examples = {
            'network': {
                'create': 'Create network 10.0.0.0/24 with comment "Production Network"',
                'find': 'Find all networks containing IP 10.0.0.100',
                'update': 'Update network 10.0.0.0/24 comment to "Updated Network"',
                'delete': 'Delete network 10.0.0.0/24'
            },
            'record:host': {
                'create': 'Create host record server1.example.com with IP 192.168.1.100',
                'find': 'Find all host records in zone example.com',
                'update': 'Update host record server1.example.com to IP 192.168.1.101',
                'delete': 'Delete host record server1.example.com'
            },
            'record:a': {
                'create': 'Create A record www.example.com pointing to 192.168.1.50',
                'find': 'Find A record for www.example.com',
                'update': 'Update A record www.example.com to 192.168.1.51',
                'delete': 'Delete A record www.example.com'
            }
        }
        
        obj_type = object_name.split(':')[0] if ':' in object_name else object_name
        if obj_type in examples and operation in examples[obj_type]:
            return examples[obj_type][operation]
        
        return f"{operation.capitalize()} {object_name}"


class InfoBloxMCPServer:
    """MCP Server for InfoBlox WAPI."""
    
    def __init__(self):
        self.config = get_config()
        self.discovery = InfoBloxWAPIDiscovery(self.config)
        self.rag = InfoBloxRAG()
        self.server = Server("infoblox-wapi")
        self.tools = {}
        self.schemas = {}
        
        # Initialize server
        self.setup_server()
    
    def setup_server(self):
        """Setup MCP server with discovered tools."""
        logger.info("Setting up InfoBlox MCP Server...")
        
        # Discover WAPI objects
        self.schemas = self.discovery.discover_wapi_objects()
        
        # Add schemas to RAG
        self.rag.add_wapi_schema_docs(self.schemas)
        
        # Generate tools from schemas
        self.generate_tools_from_schemas()
        
        # Add special tools
        self.add_special_tools()
        
        logger.info(f"MCP Server ready with {len(self.tools)} tools")
    
    def generate_tools_from_schemas(self):
        """Generate MCP tools from WAPI schemas."""
        for obj_name, schema in self.schemas.items():
            if not schema:
                continue
            
            # Generate CRUD tools if supported
            if schema['supports_crud']['create']:
                self.add_create_tool(obj_name, schema)
            
            if schema['supports_crud']['read']:
                self.add_find_tool(obj_name, schema)
            
            if schema['supports_crud']['update']:
                self.add_update_tool(obj_name, schema)
            
            if schema['supports_crud']['delete']:
                self.add_delete_tool(obj_name, schema)
            
            # Add custom function tools
            for func in schema.get('functions', []):
                self.add_function_tool(obj_name, func, schema)
    
    def add_create_tool(self, obj_name, schema):
        """Add create tool for an object."""
        tool_name = f"create_{obj_name.replace(':', '_')}"
        
        # Build parameter schema
        parameters = {
            "type": "object",
            "properties": {},
            "required": schema.get('required_fields', [])
        }
        
        for field in schema['fields']:
            if field['name'] in ['_ref']:  # Skip internal fields
                continue
            
            field_schema = {
                "type": "string",
                "description": field.get('comment', f"{field['name']} field")
            }
            
            if field['type'] == 'bool':
                field_schema['type'] = 'boolean'
            elif field['type'] == 'int':
                field_schema['type'] = 'integer'
            elif field['is_array']:
                field_schema = {
                    "type": "array",
                    "items": {"type": "string"}
                }
            
            parameters['properties'][field['name']] = field_schema
        
        # Generate example
        example = self.rag.generate_example(obj_name, 'create')
        
        @self.server.tool(
            name=tool_name,
            description=f"Create a new {obj_name} object in InfoBlox. {example}",
            parameters=parameters
        )
        async def create_handler(**kwargs):
            return await self.execute_wapi_call('POST', obj_name, None, kwargs)
        
        self.tools[tool_name] = create_handler
        logger.info(f"Added tool: {tool_name}")
    
    def add_find_tool(self, obj_name, schema):
        """Add find/search tool for an object."""
        tool_name = f"find_{obj_name.replace(':', '_')}"
        
        # Build search parameters
        parameters = {
            "type": "object",
            "properties": {
                "_max_results": {
                    "type": "integer",
                    "description": "Maximum results to return",
                    "default": 100
                }
            }
        }
        
        # Add searchable fields
        for field in schema.get('searchable_fields', []):
            parameters['properties'][field] = {
                "type": "string",
                "description": f"Search by {field}"
            }
        
        example = self.rag.generate_example(obj_name, 'find')
        
        @self.server.tool(
            name=tool_name,
            description=f"Search for {obj_name} objects in InfoBlox. {example}",
            parameters=parameters
        )
        async def find_handler(**kwargs):
            return await self.execute_wapi_call('GET', obj_name, None, kwargs)
        
        self.tools[tool_name] = find_handler
        logger.info(f"Added tool: {tool_name}")
    
    def add_update_tool(self, obj_name, schema):
        """Add update tool for an object."""
        tool_name = f"update_{obj_name.replace(':', '_')}"
        
        parameters = {
            "type": "object",
            "properties": {
                "_ref": {
                    "type": "string",
                    "description": "Object reference to update"
                }
            },
            "required": ["_ref"]
        }
        
        # Add updatable fields
        for field in schema['fields']:
            if field['name'] not in ['_ref'] and not field.get('readonly'):
                parameters['properties'][field['name']] = {
                    "type": "string",
                    "description": f"Update {field['name']}"
                }
        
        example = self.rag.generate_example(obj_name, 'update')
        
        @self.server.tool(
            name=tool_name,
            description=f"Update an existing {obj_name} object. {example}",
            parameters=parameters
        )
        async def update_handler(**kwargs):
            ref = kwargs.pop('_ref')
            return await self.execute_wapi_call('PUT', obj_name, ref, kwargs)
        
        self.tools[tool_name] = update_handler
        logger.info(f"Added tool: {tool_name}")
    
    def add_delete_tool(self, obj_name, schema):
        """Add delete tool for an object."""
        tool_name = f"delete_{obj_name.replace(':', '_')}"
        
        parameters = {
            "type": "object",
            "properties": {
                "_ref": {
                    "type": "string",
                    "description": "Object reference to delete"
                }
            },
            "required": ["_ref"]
        }
        
        example = self.rag.generate_example(obj_name, 'delete')
        
        @self.server.tool(
            name=tool_name,
            description=f"Delete a {obj_name} object. {example}",
            parameters=parameters
        )
        async def delete_handler(**kwargs):
            ref = kwargs.get('_ref')
            return await self.execute_wapi_call('DELETE', obj_name, ref, {})
        
        self.tools[tool_name] = delete_handler
        logger.info(f"Added tool: {tool_name}")
    
    def add_function_tool(self, obj_name, func_name, schema):
        """Add custom function tool."""
        tool_name = f"{func_name}_{obj_name.replace(':', '_')}"
        
        @self.server.tool(
            name=tool_name,
            description=f"Execute {func_name} function on {obj_name}"
        )
        async def function_handler(**kwargs):
            ref = kwargs.get('_ref')
            return await self.execute_wapi_call('POST', obj_name, ref, kwargs, function=func_name)
        
        self.tools[tool_name] = function_handler
        logger.info(f"Added function tool: {tool_name}")
    
    def add_special_tools(self):
        """Add special high-level tools."""
        
        @self.server.tool(
            name="infoblox_natural_query",
            description="Process a natural language query for InfoBlox operations",
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language query"
                    }
                },
                "required": ["query"]
            }
        )
        async def natural_query_handler(query: str):
            # Use RAG to understand query
            docs = self.rag.query_docs(query)
            
            # Process with NLP (simplified)
            return TextContent(
                text=f"Processed query: {query}\nRelevant docs: {docs}"
            )
        
        @self.server.tool(
            name="infoblox_get_schemas",
            description="Get all available WAPI object schemas",
            parameters={"type": "object", "properties": {}}
        )
        async def get_schemas_handler():
            return TextContent(
                text=json.dumps(list(self.schemas.keys()), indent=2)
            )
        
        @self.server.tool(
            name="infoblox_refresh_tools",
            description="Refresh tools from latest WAPI schema",
            parameters={"type": "object", "properties": {}}
        )
        async def refresh_tools_handler():
            if self.discovery.check_for_updates():
                self.schemas = self.discovery.discover_wapi_objects()
                self.generate_tools_from_schemas()
                return TextContent(text="Tools refreshed successfully")
            return TextContent(text="No schema changes detected")
        
        self.tools['infoblox_natural_query'] = natural_query_handler
        self.tools['infoblox_get_schemas'] = get_schemas_handler
        self.tools['infoblox_refresh_tools'] = refresh_tools_handler
    
    async def execute_wapi_call(self, method, object_name, ref=None, data=None, function=None):
        """Execute actual WAPI call."""
        try:
            base_url = self.discovery.base_url
            auth = self.discovery.auth
            
            if ref:
                url = f"{base_url}/{ref}"
            else:
                url = f"{base_url}/{object_name}"
            
            if function:
                url += f"?_function={function}"
            
            # Make the request
            if method == 'GET':
                response = requests.get(url, params=data, auth=auth, verify=False)
            elif method == 'POST':
                response = requests.post(url, json=data, auth=auth, verify=False)
            elif method == 'PUT':
                response = requests.put(url, json=data, auth=auth, verify=False)
            elif method == 'DELETE':
                response = requests.delete(url, auth=auth, verify=False)
            else:
                return TextContent(text=f"Unsupported method: {method}")
            
            if response.status_code >= 400:
                return TextContent(
                    text=f"Error: {response.status_code} - {response.text}"
                )
            
            return TextContent(
                text=json.dumps(response.json(), indent=2)
            )
            
        except Exception as e:
            return TextContent(text=f"Error executing WAPI call: {str(e)}")
    
    async def run(self):
        """Run the MCP server."""
        if not MCP_AVAILABLE:
            logger.error("MCP is not installed")
            return
        
        logger.info("Starting InfoBlox MCP Server...")
        
        # Check for updates periodically
        async def update_checker():
            while True:
                await asyncio.sleep(3600)  # Check every hour
                if self.discovery.check_for_updates():
                    logger.info("Schema updates detected, refreshing tools...")
                    self.schemas = self.discovery.discover_wapi_objects()
                    self.generate_tools_from_schemas()
        
        # Start update checker
        asyncio.create_task(update_checker())
        
        # Run server
        transport = StdioServerTransport()
        await self.server.run(transport)


async def main():
    """Main entry point."""
    try:
        server = InfoBloxMCPServer()
        await server.run()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")


if __name__ == "__main__":
    asyncio.run(main())