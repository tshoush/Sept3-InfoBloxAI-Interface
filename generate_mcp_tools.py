#!/usr/bin/env python3
"""Generate MCP tools from InfoBlox WAPI discovery."""

import os
import json
import requests
from pathlib import Path
from datetime import datetime

# Configuration
GRID_MASTER = os.environ.get('INFOBLOX_GRID_MASTER_IP', '192.168.1.222')
USERNAME = os.environ.get('INFOBLOX_USERNAME', 'admin')
PASSWORD = os.environ.get('INFOBLOX_PASSWORD', 'InfoBlox')
WAPI_VERSION = 'v2.13.1'

# Disable SSL warnings
requests.packages.urllib3.disable_warnings()

def discover_wapi_objects():
    """Discover available WAPI objects."""
    objects = []
    
    # Common InfoBlox objects
    common_objects = [
        'network', 'record:a', 'record:aaaa', 'record:cname', 'record:ptr',
        'record:host', 'range', 'lease', 'fixedaddress', 'grid', 'member',
        'zone_auth', 'zone_forward', 'nsgroup'
    ]
    
    for obj in common_objects:
        objects.append({
            'name': obj,
            'category': get_category(obj),
            'operations': ['GET', 'POST', 'PUT', 'DELETE']
        })
    
    return objects

def get_category(obj_name):
    """Categorize object."""
    if 'network' in obj_name or 'fixedaddress' in obj_name:
        return 'ipam'
    elif 'record' in obj_name or 'zone' in obj_name or 'nsgroup' in obj_name:
        return 'dns'
    elif 'range' in obj_name or 'lease' in obj_name:
        return 'dhcp'
    elif 'grid' in obj_name or 'member' in obj_name:
        return 'grid'
    else:
        return 'other'

def generate_tools(objects):
    """Generate MCP tools from objects."""
    tools = []
    
    for obj in objects:
        obj_name = obj['name']
        category = obj['category']
        
        # Generate tools for each operation
        if 'GET' in obj['operations']:
            tools.append({
                'name': f"get_{obj_name.replace(':', '_')}",
                'displayName': f"Get {obj_name.replace(':', ' ').title()}",
                'description': f"Retrieve {obj_name} objects from InfoBlox",
                'category': category,
                'method': 'GET',
                'path': f"/wapi/{WAPI_VERSION}/{obj_name}",
                'parameters': get_search_params(obj_name)
            })
        
        if 'POST' in obj['operations']:
            tools.append({
                'name': f"create_{obj_name.replace(':', '_')}",
                'displayName': f"Create {obj_name.replace(':', ' ').title()}",
                'description': f"Create a new {obj_name} object",
                'category': category,
                'method': 'POST',
                'path': f"/wapi/{WAPI_VERSION}/{obj_name}",
                'parameters': get_create_params(obj_name)
            })
        
        if 'DELETE' in obj['operations']:
            tools.append({
                'name': f"delete_{obj_name.replace(':', '_')}",
                'displayName': f"Delete {obj_name.replace(':', ' ').title()}",
                'description': f"Delete a {obj_name} object",
                'category': category,
                'method': 'DELETE',
                'path': f"/wapi/{WAPI_VERSION}/{obj_name}",
                'parameters': [
                    {
                        'name': 'ref',
                        'type': 'string',
                        'required': True,
                        'description': 'Object reference (_ref) to delete'
                    }
                ]
            })
    
    return tools

def get_search_params(obj_name):
    """Get search parameters for an object."""
    params = []
    
    # Common search parameters
    if 'network' in obj_name:
        params.append({
            'name': 'network',
            'type': 'string',
            'required': False,
            'description': 'Network in CIDR notation (e.g., 10.0.0.0/24)'
        })
    
    if 'record' in obj_name:
        params.append({
            'name': 'name',
            'type': 'string',
            'required': False,
            'description': 'Record name or FQDN'
        })
        params.append({
            'name': 'zone',
            'type': 'string',
            'required': False,
            'description': 'DNS zone'
        })
    
    if 'range' in obj_name:
        params.append({
            'name': 'network',
            'type': 'string',
            'required': False,
            'description': 'Network containing the range'
        })
    
    # Always add max_results
    params.append({
        'name': 'max_results',
        'type': 'number',
        'required': False,
        'description': 'Maximum number of results (default: 100)'
    })
    
    return params

def get_create_params(obj_name):
    """Get create parameters for an object."""
    params = []
    
    if obj_name == 'network':
        params = [
            {'name': 'network', 'type': 'string', 'required': True, 'description': 'Network in CIDR notation'},
            {'name': 'comment', 'type': 'string', 'required': False, 'description': 'Network description'}
        ]
    elif obj_name == 'record:a':
        params = [
            {'name': 'name', 'type': 'string', 'required': True, 'description': 'Hostname (FQDN)'},
            {'name': 'ipv4addr', 'type': 'string', 'required': True, 'description': 'IPv4 address'},
            {'name': 'ttl', 'type': 'number', 'required': False, 'description': 'TTL in seconds'},
            {'name': 'comment', 'type': 'string', 'required': False, 'description': 'Record comment'}
        ]
    elif obj_name == 'record:host':
        params = [
            {'name': 'name', 'type': 'string', 'required': True, 'description': 'Hostname (FQDN)'},
            {'name': 'ipv4addrs', 'type': 'array', 'required': True, 'description': 'IPv4 addresses'},
            {'name': 'comment', 'type': 'string', 'required': False, 'description': 'Host comment'}
        ]
    elif obj_name == 'range':
        params = [
            {'name': 'start_addr', 'type': 'string', 'required': True, 'description': 'Start IP address'},
            {'name': 'end_addr', 'type': 'string', 'required': True, 'description': 'End IP address'},
            {'name': 'network', 'type': 'string', 'required': True, 'description': 'Parent network'},
            {'name': 'comment', 'type': 'string', 'required': False, 'description': 'Range comment'}
        ]
    else:
        # Generic parameters
        params = [
            {'name': 'name', 'type': 'string', 'required': True, 'description': 'Object name'},
            {'name': 'comment', 'type': 'string', 'required': False, 'description': 'Object comment'}
        ]
    
    return params

def save_tools(tools):
    """Save tools to cache."""
    cache_dir = Path.home() / '.infoblox_mcp' / 'tools'
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    # Save tools
    tools_file = cache_dir / 'discovered_tools.json'
    with open(tools_file, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'total': len(tools),
            'tools': tools
        }, f, indent=2)
    
    print(f"✓ Saved {len(tools)} tools to {tools_file}")
    
    # Save by category
    by_category = {}
    for tool in tools:
        cat = tool['category']
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(tool)
    
    for category, cat_tools in by_category.items():
        print(f"  - {category}: {len(cat_tools)} tools")
    
    return tools_file

def main():
    """Generate MCP tools."""
    print("InfoBlox MCP Tools Generator")
    print("=" * 50)
    
    # Discover objects
    print("\nDiscovering WAPI objects...")
    objects = discover_wapi_objects()
    print(f"✓ Found {len(objects)} objects")
    
    # Generate tools
    print("\nGenerating MCP tools...")
    tools = generate_tools(objects)
    print(f"✓ Generated {len(tools)} tools")
    
    # Save tools
    print("\nSaving tools...")
    tools_file = save_tools(tools)
    
    print("\n" + "=" * 50)
    print("Tool generation complete!")
    print(f"Tools saved to: {tools_file}")

if __name__ == "__main__":
    main()