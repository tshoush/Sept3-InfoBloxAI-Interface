#!/usr/bin/env python3
"""
Enhanced Flask application with MCP configuration and tool browsing.
"""

from flask import Flask, request, jsonify, render_template_string, redirect, url_for
import sys
import os
import json
import logging
import subprocess
import asyncio
from datetime import datetime
import requests
from pathlib import Path

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import get_config, ConfigurationError
from wapi_nlp_secure import extract_entities_basic, classify_intent_basic

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Runtime configuration storage
RUNTIME_CONFIG = {
    'llm_provider': 'basic',
    'llm_api_key': '',
    'llm_model': '',
    'llm_endpoint': '',
    'confidence_threshold': 0.7,
    'infoblox_ip': '',
    'infoblox_username': '',
    'infoblox_password': '',
    'infoblox_wapi_version': 'v2.13.1',
    'infoblox_ssl_verify': False,
    'enable_autocomplete': True,
    'enable_logging': True,
    'max_results': 100,
    'mcp_enabled': False,
    'mcp_auto_discovery': True,
    'mcp_refresh_interval': 3600,
    'mcp_cache_enabled': True,
    'mcp_rag_enabled': True
}

# MCP tools cache
MCP_TOOLS_CACHE = {}
MCP_LAST_REFRESH = None
MCP_SERVER_PID = None

# Load initial configuration
try:
    config = get_config()
    RUNTIME_CONFIG.update({
        'infoblox_ip': config.get('GRID_MASTER_IP', ''),
        'infoblox_username': config.get('USERNAME', ''),
        'infoblox_password': config.get('PASSWORD', ''),
        'infoblox_wapi_version': config.get('WAPI_VERSION', 'v2.13.1'),
    })
except:
    pass

# Load saved configuration if exists
CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'app_config.json')
if os.path.exists(CONFIG_FILE):
    try:
        with open(CONFIG_FILE, 'r') as f:
            saved_config = json.load(f)
            RUNTIME_CONFIG.update(saved_config)
    except:
        pass

# Enhanced main template with MCP tabs
ENHANCED_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>InfoBlox WAPI NLP Interface - Enhanced</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/themes/prism-tomorrow.min.css" rel="stylesheet">
    <style>
        :root {
            --primary-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            --success-color: #28a745;
            --danger-color: #dc3545;
            --warning-color: #ffc107;
        }
        
        body { 
            background: var(--primary-gradient); 
            min-height: 100vh; 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        
        .main-nav {
            background: rgba(255,255,255,0.98);
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            padding: 15px 0;
            margin-bottom: 30px;
        }
        
        .nav-link {
            color: #495057;
            font-weight: 500;
            padding: 10px 20px;
            margin: 0 5px;
            border-radius: 25px;
            transition: all 0.3s;
        }
        
        .nav-link:hover {
            background: rgba(118, 75, 162, 0.1);
            color: #764ba2;
        }
        
        .nav-link.active {
            background: var(--primary-gradient);
            color: white;
        }
        
        .container { max-width: 1200px; }
        
        .main-card { 
            background: rgba(255,255,255,0.98); 
            backdrop-filter: blur(10px); 
            border: none; 
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            border-radius: 15px;
        }
        
        .status-badge {
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 600;
        }
        
        .status-active {
            background: #d4edda;
            color: #155724;
        }
        
        .status-inactive {
            background: #f8d7da;
            color: #721c24;
        }
        
        .tool-card {
            border: 1px solid #e0e0e0;
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 15px;
            transition: all 0.3s;
            cursor: pointer;
        }
        
        .tool-card:hover {
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            transform: translateY(-2px);
        }
        
        .tool-category {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 10px 20px;
            border-radius: 10px;
            margin: 20px 0 10px 0;
        }
        
        .parameter-input {
            margin-bottom: 10px;
        }
        
        .code-block {
            background: #2d2d2d;
            color: #f8f8f2;
            padding: 15px;
            border-radius: 8px;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
            overflow-x: auto;
        }
        
        .mcp-status-card {
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
        }
    </style>
</head>
<body>
    <!-- Navigation -->
    <nav class="main-nav">
        <div class="container">
            <div class="d-flex justify-content-between align-items-center">
                <h3 class="mb-0">
                    <i class="fas fa-network-wired text-primary"></i> InfoBlox NLP System
                </h3>
                <div>
                    <a href="/" class="nav-link {{ 'active' if page == 'home' else '' }}">
                        <i class="fas fa-home"></i> Query
                    </a>
                    <a href="/config" class="nav-link {{ 'active' if page == 'config' else '' }}">
                        <i class="fas fa-cog"></i> Config
                    </a>
                    <a href="/mcp-config" class="nav-link {{ 'active' if page == 'mcp-config' else '' }}">
                        <i class="fas fa-server"></i> MCP Config
                    </a>
                    <a href="/mcp-tools" class="nav-link {{ 'active' if page == 'mcp-tools' else '' }}">
                        <i class="fas fa-tools"></i> MCP Tools
                    </a>
                </div>
            </div>
        </div>
    </nav>
    
    <div class="container">
        {% block content %}{% endblock %}
    </div>
    
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/prism.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-json.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-python.min.js"></script>
</body>
</html>
"""

# MCP Configuration Page
MCP_CONFIG_TEMPLATE = """
<div class="main-card">
    <div class="card-header bg-gradient text-white">
        <h4><i class="fas fa-server"></i> MCP Server Configuration</h4>
    </div>
    <div class="card-body">
        <!-- MCP Status -->
        <div class="mcp-status-card">
            <div class="row">
                <div class="col-md-6">
                    <h5>MCP Server Status</h5>
                    <div class="mt-3">
                        <span class="status-badge {{ 'status-active' if mcp_status.running else 'status-inactive' }}">
                            {{ 'Running' if mcp_status.running else 'Stopped' }}
                        </span>
                        {% if mcp_status.pid %}
                        <small class="ms-2">PID: {{ mcp_status.pid }}</small>
                        {% endif %}
                    </div>
                </div>
                <div class="col-md-6 text-end">
                    <button class="btn btn-success" id="startMCP" {{ 'disabled' if mcp_status.running }}>
                        <i class="fas fa-play"></i> Start Server
                    </button>
                    <button class="btn btn-danger" id="stopMCP" {{ 'disabled' if not mcp_status.running }}>
                        <i class="fas fa-stop"></i> Stop Server
                    </button>
                    <button class="btn btn-warning" id="restartMCP">
                        <i class="fas fa-sync"></i> Restart
                    </button>
                </div>
            </div>
            {% if mcp_status.last_refresh %}
            <div class="mt-3">
                <small>Last Schema Refresh: {{ mcp_status.last_refresh }}</small>
            </div>
            {% endif %}
        </div>
        
        <!-- MCP Settings -->
        <form id="mcpConfigForm">
            <h5 class="mt-4">Server Settings</h5>
            <div class="row">
                <div class="col-md-6">
                    <div class="form-check form-switch mb-3">
                        <input class="form-check-input" type="checkbox" id="mcp_enabled" 
                            {{ 'checked' if config.mcp_enabled }}>
                        <label class="form-check-label" for="mcp_enabled">
                            Enable MCP Server
                        </label>
                    </div>
                    
                    <div class="form-check form-switch mb-3">
                        <input class="form-check-input" type="checkbox" id="mcp_auto_discovery" 
                            {{ 'checked' if config.mcp_auto_discovery }}>
                        <label class="form-check-label" for="mcp_auto_discovery">
                            Auto-Discovery Mode
                        </label>
                        <small class="text-muted d-block">
                            Automatically discover and generate tools from WAPI schemas
                        </small>
                    </div>
                    
                    <div class="form-check form-switch mb-3">
                        <input class="form-check-input" type="checkbox" id="mcp_cache_enabled" 
                            {{ 'checked' if config.mcp_cache_enabled }}>
                        <label class="form-check-label" for="mcp_cache_enabled">
                            Enable Schema Caching
                        </label>
                        <small class="text-muted d-block">
                            Cache schemas for better performance
                        </small>
                    </div>
                    
                    <div class="form-check form-switch mb-3">
                        <input class="form-check-input" type="checkbox" id="mcp_rag_enabled" 
                            {{ 'checked' if config.mcp_rag_enabled }}>
                        <label class="form-check-label" for="mcp_rag_enabled">
                            Enable RAG Documentation
                        </label>
                        <small class="text-muted d-block">
                            Use AI-powered documentation assistance
                        </small>
                    </div>
                </div>
                
                <div class="col-md-6">
                    <div class="mb-3">
                        <label class="form-label">Schema Refresh Interval (seconds)</label>
                        <input type="number" class="form-control" id="mcp_refresh_interval" 
                            value="{{ config.mcp_refresh_interval }}" min="60" max="86400">
                        <small class="text-muted">How often to check for WAPI schema updates</small>
                    </div>
                    
                    <div class="mb-3">
                        <label class="form-label">Max Discovered Objects</label>
                        <input type="number" class="form-control" id="mcp_max_objects" 
                            value="{{ config.get('mcp_max_objects', 50) }}" min="10" max="500">
                        <small class="text-muted">Limit number of objects to discover</small>
                    </div>
                    
                    <div class="mb-3">
                        <label class="form-label">MCP Server Port</label>
                        <input type="number" class="form-control" id="mcp_port" 
                            value="{{ config.get('mcp_port', 5555) }}" min="1024" max="65535">
                    </div>
                </div>
            </div>
            
            <h5 class="mt-4">Discovery Filters</h5>
            <div class="row">
                <div class="col-md-6">
                    <div class="mb-3">
                        <label class="form-label">Include Objects (comma-separated)</label>
                        <textarea class="form-control" id="mcp_include_objects" rows="3" 
                            placeholder="network, record:host, record:a">{{ config.get('mcp_include_objects', '') }}</textarea>
                        <small class="text-muted">Leave empty to include all</small>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="mb-3">
                        <label class="form-label">Exclude Objects (comma-separated)</label>
                        <textarea class="form-control" id="mcp_exclude_objects" rows="3" 
                            placeholder="discovery:*, admingroup">{{ config.get('mcp_exclude_objects', '') }}</textarea>
                        <small class="text-muted">Objects to exclude from discovery</small>
                    </div>
                </div>
            </div>
            
            <div class="mt-4">
                <button type="submit" class="btn btn-primary">
                    <i class="fas fa-save"></i> Save Configuration
                </button>
                <button type="button" class="btn btn-info ms-2" id="refreshSchemas">
                    <i class="fas fa-sync"></i> Refresh Schemas Now
                </button>
                <button type="button" class="btn btn-warning ms-2" id="clearCache">
                    <i class="fas fa-trash"></i> Clear Cache
                </button>
            </div>
        </form>
        
        <!-- MCP Statistics -->
        <div class="mt-5">
            <h5>Discovery Statistics</h5>
            <div class="row mt-3">
                <div class="col-md-3">
                    <div class="text-center">
                        <h2 class="text-primary">{{ mcp_stats.total_objects }}</h2>
                        <small>Total Objects</small>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="text-center">
                        <h2 class="text-success">{{ mcp_stats.total_tools }}</h2>
                        <small>Generated Tools</small>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="text-center">
                        <h2 class="text-info">{{ mcp_stats.cached_schemas }}</h2>
                        <small>Cached Schemas</small>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="text-center">
                        <h2 class="text-warning">{{ mcp_stats.rag_documents }}</h2>
                        <small>RAG Documents</small>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>

<script>
$(document).ready(function() {
    // Start MCP Server
    $('#startMCP').click(function() {
        $.post('/api/mcp/start', function(result) {
            if (result.success) {
                location.reload();
            } else {
                alert('Failed to start MCP server: ' + result.error);
            }
        });
    });
    
    // Stop MCP Server
    $('#stopMCP').click(function() {
        $.post('/api/mcp/stop', function(result) {
            if (result.success) {
                location.reload();
            } else {
                alert('Failed to stop MCP server: ' + result.error);
            }
        });
    });
    
    // Restart MCP Server
    $('#restartMCP').click(function() {
        $.post('/api/mcp/restart', function(result) {
            if (result.success) {
                location.reload();
            } else {
                alert('Failed to restart MCP server: ' + result.error);
            }
        });
    });
    
    // Refresh Schemas
    $('#refreshSchemas').click(function() {
        $(this).prop('disabled', true);
        $.post('/api/mcp/refresh-schemas', function(result) {
            alert('Schema refresh ' + (result.success ? 'completed' : 'failed'));
            location.reload();
        });
    });
    
    // Clear Cache
    $('#clearCache').click(function() {
        if (confirm('Clear all cached schemas?')) {
            $.post('/api/mcp/clear-cache', function(result) {
                alert('Cache cleared');
                location.reload();
            });
        }
    });
    
    // Save Configuration
    $('#mcpConfigForm').submit(function(e) {
        e.preventDefault();
        
        const config = {
            mcp_enabled: $('#mcp_enabled').is(':checked'),
            mcp_auto_discovery: $('#mcp_auto_discovery').is(':checked'),
            mcp_cache_enabled: $('#mcp_cache_enabled').is(':checked'),
            mcp_rag_enabled: $('#mcp_rag_enabled').is(':checked'),
            mcp_refresh_interval: parseInt($('#mcp_refresh_interval').val()),
            mcp_max_objects: parseInt($('#mcp_max_objects').val()),
            mcp_port: parseInt($('#mcp_port').val()),
            mcp_include_objects: $('#mcp_include_objects').val(),
            mcp_exclude_objects: $('#mcp_exclude_objects').val()
        };
        
        $.ajax({
            url: '/api/mcp/config',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(config),
            success: function(result) {
                alert('Configuration saved successfully');
            }
        });
    });
});
</script>
"""

# MCP Tools Browser Page
MCP_TOOLS_TEMPLATE = """
<div class="main-card">
    <div class="card-header bg-gradient text-white">
        <h4><i class="fas fa-tools"></i> MCP Tools Browser</h4>
    </div>
    <div class="card-body">
        <!-- Search and Filters -->
        <div class="row mb-4">
            <div class="col-md-6">
                <input type="text" class="form-control" id="toolSearch" 
                    placeholder="Search tools...">
            </div>
            <div class="col-md-3">
                <select class="form-control" id="categoryFilter">
                    <option value="">All Categories</option>
                    <option value="network">Network</option>
                    <option value="dns">DNS Records</option>
                    <option value="dhcp">DHCP</option>
                    <option value="grid">Grid Management</option>
                    <option value="custom">Custom Functions</option>
                </select>
            </div>
            <div class="col-md-3">
                <button class="btn btn-primary" id="refreshTools">
                    <i class="fas fa-sync"></i> Refresh Tools
                </button>
            </div>
        </div>
        
        <!-- Tools Count -->
        <div class="alert alert-info">
            <i class="fas fa-info-circle"></i> 
            Discovered <strong>{{ tools|length }}</strong> tools from WAPI schemas
            {% if last_update %}
            <small class="float-end">Last updated: {{ last_update }}</small>
            {% endif %}
        </div>
        
        <!-- Tools List -->
        <div id="toolsList">
            {% for category, category_tools in tools_by_category.items() %}
            <div class="tool-category">
                <h5 class="mb-0">
                    <i class="fas fa-folder"></i> {{ category|title }} 
                    <span class="badge bg-light text-dark">{{ category_tools|length }}</span>
                </h5>
            </div>
            
            {% for tool in category_tools %}
            <div class="tool-card" data-tool="{{ tool.name }}" data-category="{{ category }}">
                <div class="row">
                    <div class="col-md-8">
                        <h6 class="text-primary">
                            <i class="fas fa-wrench"></i> {{ tool.name }}
                        </h6>
                        <p class="mb-2">{{ tool.description }}</p>
                        {% if tool.example %}
                        <small class="text-muted">
                            <i class="fas fa-lightbulb"></i> Example: {{ tool.example }}
                        </small>
                        {% endif %}
                    </div>
                    <div class="col-md-4 text-end">
                        <button class="btn btn-sm btn-outline-primary test-tool" 
                            data-tool="{{ tool.name }}">
                            <i class="fas fa-play"></i> Test
                        </button>
                        <button class="btn btn-sm btn-outline-secondary view-schema" 
                            data-tool="{{ tool.name }}">
                            <i class="fas fa-code"></i> Schema
                        </button>
                    </div>
                </div>
                
                <!-- Parameters (hidden by default) -->
                <div class="tool-params mt-3" id="params-{{ tool.name }}" style="display: none;">
                    <h6>Parameters:</h6>
                    {% for param in tool.parameters %}
                    <div class="parameter-input">
                        <label class="form-label">
                            {{ param.name }}
                            {% if param.required %}<span class="text-danger">*</span>{% endif %}
                            <small class="text-muted">{{ param.type }}</small>
                        </label>
                        {% if param.type == 'boolean' %}
                        <div class="form-check">
                            <input class="form-check-input" type="checkbox" 
                                id="param-{{ tool.name }}-{{ param.name }}">
                        </div>
                        {% elif param.type == 'select' %}
                        <select class="form-control" id="param-{{ tool.name }}-{{ param.name }}">
                            {% for option in param.options %}
                            <option value="{{ option }}">{{ option }}</option>
                            {% endfor %}
                        </select>
                        {% else %}
                        <input type="text" class="form-control" 
                            id="param-{{ tool.name }}-{{ param.name }}"
                            placeholder="{{ param.description }}">
                        {% endif %}
                    </div>
                    {% endfor %}
                    
                    <div class="mt-3">
                        <button class="btn btn-success execute-tool" data-tool="{{ tool.name }}">
                            <i class="fas fa-rocket"></i> Execute
                        </button>
                        <button class="btn btn-secondary cancel-test" data-tool="{{ tool.name }}">
                            Cancel
                        </button>
                    </div>
                </div>
                
                <!-- Results (hidden by default) -->
                <div class="tool-results mt-3" id="results-{{ tool.name }}" style="display: none;">
                    <h6>Results:</h6>
                    <pre class="code-block"><code class="language-json"></code></pre>
                </div>
            </div>
            {% endfor %}
            {% endfor %}
        </div>
        
        <!-- Tool Schema Modal -->
        <div class="modal fade" id="schemaModal" tabindex="-1">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Tool Schema</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <pre class="code-block"><code class="language-json" id="schemaContent"></code></pre>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>

<script>
$(document).ready(function() {
    // Search functionality
    $('#toolSearch').on('input', function() {
        const search = $(this).val().toLowerCase();
        $('.tool-card').each(function() {
            const name = $(this).data('tool').toLowerCase();
            const visible = name.includes(search);
            $(this).toggle(visible);
        });
    });
    
    // Category filter
    $('#categoryFilter').change(function() {
        const category = $(this).val();
        $('.tool-card').each(function() {
            if (category === '' || $(this).data('category') === category) {
                $(this).show();
            } else {
                $(this).hide();
            }
        });
    });
    
    // Test tool
    $('.test-tool').click(function() {
        const toolName = $(this).data('tool');
        $('#params-' + toolName).slideToggle();
        $('#results-' + toolName).hide();
    });
    
    // View schema
    $('.view-schema').click(function() {
        const toolName = $(this).data('tool');
        $.get('/api/mcp/tool-schema/' + toolName, function(schema) {
            $('#schemaContent').text(JSON.stringify(schema, null, 2));
            Prism.highlightElement($('#schemaContent')[0]);
            $('#schemaModal').modal('show');
        });
    });
    
    // Execute tool
    $('.execute-tool').click(function() {
        const toolName = $(this).data('tool');
        const params = {};
        
        // Collect parameters
        $('[id^="param-' + toolName + '-"]').each(function() {
            const paramName = $(this).attr('id').replace('param-' + toolName + '-', '');
            if ($(this).is(':checkbox')) {
                params[paramName] = $(this).is(':checked');
            } else {
                params[paramName] = $(this).val();
            }
        });
        
        // Execute
        $.ajax({
            url: '/api/mcp/execute-tool',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                tool: toolName,
                parameters: params
            }),
            success: function(result) {
                $('#results-' + toolName + ' code').text(JSON.stringify(result, null, 2));
                Prism.highlightElement($('#results-' + toolName + ' code')[0]);
                $('#results-' + toolName).show();
            },
            error: function(xhr) {
                $('#results-' + toolName + ' code').text('Error: ' + xhr.responseText);
                $('#results-' + toolName).show();
            }
        });
    });
    
    // Cancel test
    $('.cancel-test').click(function() {
        const toolName = $(this).data('tool');
        $('#params-' + toolName).hide();
        $('#results-' + toolName).hide();
    });
    
    // Refresh tools
    $('#refreshTools').click(function() {
        $(this).prop('disabled', true);
        $.post('/api/mcp/refresh-tools', function(result) {
            location.reload();
        });
    });
});
</script>
"""

def get_mcp_status():
    """Get MCP server status."""
    global MCP_SERVER_PID
    
    # Check if MCP server is running
    try:
        result = subprocess.run(['pgrep', '-f', 'infoblox_mcp_server.py'], 
                               capture_output=True, text=True)
        if result.stdout:
            MCP_SERVER_PID = int(result.stdout.strip().split()[0])
            return {
                'running': True,
                'pid': MCP_SERVER_PID,
                'last_refresh': MCP_LAST_REFRESH
            }
    except:
        pass
    
    return {
        'running': False,
        'pid': None,
        'last_refresh': None
    }

def get_mcp_statistics():
    """Get MCP discovery statistics."""
    cache_dir = Path.home() / '.infoblox_mcp' / 'cache'
    
    stats = {
        'total_objects': 0,
        'total_tools': len(MCP_TOOLS_CACHE),
        'cached_schemas': 0,
        'rag_documents': 0
    }
    
    # Count cached schemas
    if cache_dir.exists():
        stats['cached_schemas'] = len(list(cache_dir.glob('*_schema.json')))
    
    # Count total objects from cache
    for tool in MCP_TOOLS_CACHE.values():
        if 'object' in tool:
            stats['total_objects'] += 1
    
    return stats

def discover_mcp_tools():
    """Discover available MCP tools."""
    global MCP_TOOLS_CACHE, MCP_LAST_REFRESH
    
    tools = []
    
    # Try to get tools from MCP server
    try:
        # This would normally connect to the MCP server
        # For now, we'll simulate with cached data
        cache_dir = Path.home() / '.infoblox_mcp' / 'cache'
        
        if cache_dir.exists():
            for schema_file in cache_dir.glob('*_schema.json'):
                with open(schema_file) as f:
                    schema = json.load(f)
                    obj_name = schema.get('object_name', schema_file.stem.replace('_schema', ''))
                    
                    # Generate tools based on operations
                    if schema.get('supports_crud', {}).get('create'):
                        tools.append({
                            'name': f"create_{obj_name.replace(':', '_')}",
                            'description': f"Create a new {obj_name} object",
                            'category': get_tool_category(obj_name),
                            'example': f"Create {obj_name}",
                            'parameters': get_tool_parameters(schema, 'create')
                        })
                    
                    if schema.get('supports_crud', {}).get('read'):
                        tools.append({
                            'name': f"find_{obj_name.replace(':', '_')}",
                            'description': f"Search for {obj_name} objects",
                            'category': get_tool_category(obj_name),
                            'example': f"Find all {obj_name}",
                            'parameters': get_tool_parameters(schema, 'find')
                        })
    except Exception as e:
        logger.error(f"Error discovering MCP tools: {e}")
    
    # Add default tools if no discovery
    if not tools:
        tools = get_default_tools()
    
    MCP_TOOLS_CACHE = {tool['name']: tool for tool in tools}
    MCP_LAST_REFRESH = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    return tools

def get_tool_category(obj_name):
    """Get category for a tool based on object name."""
    if 'network' in obj_name:
        return 'network'
    elif 'record' in obj_name:
        return 'dns'
    elif 'range' in obj_name or 'lease' in obj_name or 'fixed' in obj_name:
        return 'dhcp'
    elif 'grid' in obj_name or 'member' in obj_name:
        return 'grid'
    else:
        return 'other'

def get_tool_parameters(schema, operation):
    """Get parameters for a tool."""
    params = []
    
    if operation == 'create':
        for field in schema.get('required_fields', []):
            params.append({
                'name': field,
                'type': 'string',
                'required': True,
                'description': f"Required: {field}"
            })
    elif operation == 'find':
        for field in schema.get('searchable_fields', [])[:3]:  # Limit to 3 for UI
            params.append({
                'name': field,
                'type': 'string',
                'required': False,
                'description': f"Search by {field}"
            })
    
    return params

def get_default_tools():
    """Get default tools when discovery is not available."""
    return [
        {
            'name': 'create_network',
            'description': 'Create a new network',
            'category': 'network',
            'example': 'Create network 10.0.0.0/24',
            'parameters': [
                {'name': 'network', 'type': 'string', 'required': True, 'description': 'CIDR notation'},
                {'name': 'comment', 'type': 'string', 'required': False, 'description': 'Description'}
            ]
        },
        {
            'name': 'find_network',
            'description': 'Search for networks',
            'category': 'network',
            'example': 'Find all networks',
            'parameters': [
                {'name': 'network', 'type': 'string', 'required': False, 'description': 'Network to search'},
            ]
        },
        {
            'name': 'create_record_host',
            'description': 'Create host record',
            'category': 'dns',
            'example': 'Create host server.example.com',
            'parameters': [
                {'name': 'name', 'type': 'string', 'required': True, 'description': 'FQDN'},
                {'name': 'ipv4addrs', 'type': 'string', 'required': True, 'description': 'IP address'}
            ]
        }
    ]

def organize_tools_by_category(tools):
    """Organize tools by category."""
    by_category = {}
    for tool in tools:
        category = tool.get('category', 'other')
        if category not in by_category:
            by_category[category] = []
        by_category[category].append(tool)
    return by_category

# Routes

@app.route('/')
def home():
    """Home page - shows query interface."""
    query_content = """
    <style>
        .query-page { padding: 20px 0; }
        .query-card {
            background: white;
            border-radius: 20px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        .query-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        .query-body {
            padding: 40px;
        }
        .query-input-group {
            background: #f8f9fa;
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 30px;
        }
        .query-input {
            border: 2px solid #e9ecef;
            border-radius: 10px;
            padding: 15px 20px;
            font-size: 16px;
            transition: all 0.3s;
        }
        .query-input:focus {
            border-color: #667eea;
            box-shadow: 0 0 0 0.2rem rgba(102, 126, 234, 0.25);
        }
        .query-button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border: none;
            border-radius: 10px;
            padding: 15px 40px;
            font-size: 16px;
            font-weight: 600;
            color: white;
            transition: all 0.3s;
            margin-top: 15px;
        }
        .query-button:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(102, 126, 234, 0.3);
        }
        .example-section {
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            border-radius: 15px;
            padding: 25px;
            margin: 30px 0;
        }
        .example-query {
            display: inline-block;
            background: white;
            padding: 8px 16px;
            border-radius: 20px;
            margin: 5px;
            color: #667eea;
            text-decoration: none;
            transition: all 0.3s;
            font-size: 14px;
        }
        .example-query:hover {
            background: #667eea;
            color: white;
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.3);
        }
        .status-section {
            display: flex;
            gap: 30px;
            margin-top: 30px;
        }
        .status-card {
            flex: 1;
            background: white;
            border-radius: 15px;
            padding: 20px;
            border: 2px solid #e9ecef;
            text-align: center;
            transition: all 0.3s;
        }
        .status-card:hover {
            border-color: #667eea;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }
        .status-icon {
            font-size: 32px;
            margin-bottom: 10px;
        }
        .status-badge {
            display: inline-block;
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 13px;
            font-weight: 600;
            margin-top: 8px;
        }
        .status-connected {
            background: #d4edda;
            color: #155724;
        }
        .status-disconnected {
            background: #f8d7da;
            color: #721c24;
        }
        .status-checking {
            background: #fff3cd;
            color: #856404;
        }
        .response-area {
            margin-top: 30px;
            animation: slideIn 0.3s ease-out;
        }
        @keyframes slideIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .response-box {
            background: #2d2d2d;
            color: #f8f8f2;
            border-radius: 15px;
            padding: 20px;
            font-family: 'Courier New', monospace;
            font-size: 14px;
            max-height: 400px;
            overflow-y: auto;
            white-space: pre-wrap;
            word-break: break-all;
        }
    </style>
    
    <div class="query-page">
        <div class="query-card">
            <div class="query-header">
                <h2 class="mb-0"><i class="fas fa-robot"></i> InfoBlox Natural Language Interface</h2>
                <p class="mb-0 mt-2">Ask questions in plain English about your network infrastructure</p>
            </div>
            
            <div class="query-body">
                <!-- Query Input Section -->
                <div class="query-input-group">
                    <form id="queryForm">
                        <label for="queryInput" class="form-label mb-3">
                            <strong><i class="fas fa-terminal"></i> What would you like to know?</strong>
                        </label>
                        <input type="text" class="form-control query-input" id="queryInput" 
                            placeholder="Try: 'List all networks' or 'Show DNS zones' or 'Create a host record'"
                            autocomplete="off">
                        <div class="text-center">
                            <button type="submit" class="btn query-button">
                                <i class="fas fa-magic"></i> Process Query
                            </button>
                        </div>
                    </form>
                </div>
                
                <!-- Example Queries -->
                <div class="example-section">
                    <h5 class="mb-3"><i class="fas fa-lightbulb"></i> Quick Examples</h5>
                    <div class="d-flex flex-wrap">
                        <a href="#" class="example-query" data-query="List all networks">
                            <i class="fas fa-network-wired"></i> List all networks
                        </a>
                        <a href="#" class="example-query" data-query="Show all DNS zones">
                            <i class="fas fa-globe"></i> Show DNS zones
                        </a>
                        <a href="#" class="example-query" data-query="Create host record server1.example.com with IP 10.0.0.100">
                            <i class="fas fa-server"></i> Create host record
                        </a>
                        <a href="#" class="example-query" data-query="Find all A records in zone example.com">
                            <i class="fas fa-search"></i> Find A records
                        </a>
                        <a href="#" class="example-query" data-query="Get next available IP in network 10.0.0.0/24">
                            <i class="fas fa-plus-circle"></i> Next available IP
                        </a>
                        <a href="#" class="example-query" data-query="Show all DHCP ranges">
                            <i class="fas fa-list"></i> DHCP ranges
                        </a>
                    </div>
                </div>
                
                <!-- Status Section -->
                <div class="status-section">
                    <div class="status-card">
                        <div class="status-icon">
                            <i class="fas fa-server text-primary"></i>
                        </div>
                        <h6>InfoBlox Grid</h6>
                        <div id="infobloxStatus" class="status-badge status-checking">
                            <i class="fas fa-spinner fa-spin"></i> Checking...
                        </div>
                    </div>
                    
                    <div class="status-card">
                        <div class="status-icon">
                            <i class="fas fa-brain text-info"></i>
                        </div>
                        <h6>MCP Server</h6>
                        <div id="mcpStatus" class="status-badge status-checking">
                            <i class="fas fa-spinner fa-spin"></i> Checking...
                        </div>
                    </div>
                    
                    <div class="status-card">
                        <div class="status-icon">
                            <i class="fas fa-microchip text-warning"></i>
                        </div>
                        <h6>NLP Engine</h6>
                        <div id="nlpStatus" class="status-badge status-connected">
                            <i class="fas fa-check-circle"></i> Ready
                        </div>
                    </div>
                </div>
                
                <!-- Response Area -->
                <div id="responseArea" class="response-area" style="display:none;">
                    <h5 class="mb-3"><i class="fas fa-reply"></i> Response</h5>
                    <div id="response" class="response-box"></div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
    $(document).ready(function() {
        // Check status on load
        function checkStatus() {
            $.ajax({
                url: '/api/status',
                method: 'GET',
                success: function(data) {
                    // Update InfoBlox status
                    $('#infobloxStatus')
                        .removeClass('status-checking status-connected status-disconnected')
                        .addClass(data.infoblox_connected ? 'status-connected' : 'status-disconnected')
                        .html(data.infoblox_connected ? 
                            '<i class="fas fa-check-circle"></i> Connected' : 
                            '<i class="fas fa-times-circle"></i> Disconnected');
                    
                    // Update MCP status
                    $('#mcpStatus')
                        .removeClass('status-checking status-connected status-disconnected')
                        .addClass(data.mcp_server_running ? 'status-connected' : 'status-disconnected')
                        .html(data.mcp_server_running ? 
                            '<i class="fas fa-check-circle"></i> Running' : 
                            '<i class="fas fa-times-circle"></i> Not Running');
                },
                error: function() {
                    $('#infobloxStatus, #mcpStatus')
                        .removeClass('status-checking status-connected')
                        .addClass('status-disconnected')
                        .html('<i class="fas fa-exclamation-triangle"></i> Error');
                }
            });
        }
        
        // Check status immediately and then every 5 seconds
        checkStatus();
        setInterval(checkStatus, 5000);
        
        // Handle form submission
        $('#queryForm').submit(function(e) {
            e.preventDefault();
            const query = $('#queryInput').val();
            if (!query) {
                $('#queryInput').focus();
                return;
            }
            
            $('#response').text('Processing your query...');
            $('#responseArea').show();
            
            $.ajax({
                url: '/api/process',
                method: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({query: query}),
                success: function(result) {
                    $('#response').text(JSON.stringify(result, null, 2));
                },
                error: function(xhr) {
                    $('#response').text('Error: ' + (xhr.responseJSON?.error || xhr.responseText || 'Unknown error'));
                }
            });
        });
        
        // Handle example queries
        $('.example-query').click(function(e) {
            e.preventDefault();
            const query = $(this).data('query') || $(this).text().trim();
            $('#queryInput').val(query).focus();
        });
        
        // Auto-focus on input
        $('#queryInput').focus();
    });
    </script>
    """
    template = ENHANCED_TEMPLATE.replace('{% block content %}{% endblock %}', 
                                         '{% block content %}' + query_content + '{% endblock %}')
    return render_template_string(template, page='home')

@app.route('/config')
def config_page():
    """Configuration page."""
    config_content = """
    <div class="main-card">
        <div class="card-header bg-gradient text-white">
            <h4><i class="fas fa-cog"></i> System Configuration</h4>
        </div>
        <div class="card-body">
            <!-- InfoBlox Settings -->
            <div class="mb-4">
                <h5><i class="fas fa-server"></i> InfoBlox Connection</h5>
                <form id="infobloxForm">
                    <div class="row">
                        <div class="col-md-4">
                            <label>Grid Master IP</label>
                            <input type="text" class="form-control" id="gridMaster" 
                                value="{{ config.get('INFOBLOX_GRID_MASTER_IP', '') }}" 
                                placeholder="192.168.1.224">
                        </div>
                        <div class="col-md-4">
                            <label>Username</label>
                            <input type="text" class="form-control" id="username" 
                                value="{{ config.get('INFOBLOX_USERNAME', '') }}"
                                placeholder="admin">
                        </div>
                        <div class="col-md-4">
                            <label>Password</label>
                            <input type="password" class="form-control" id="password" 
                                value="{{ config.get('INFOBLOX_PASSWORD', '') }}"
                                placeholder="••••••••">
                        </div>
                    </div>
                    <button type="submit" class="btn btn-primary mt-3">
                        <i class="fas fa-save"></i> Save & Test Connection
                    </button>
                </form>
            </div>
            
            <!-- LLM Settings -->
            <div class="mb-4">
                <h5><i class="fas fa-brain"></i> LLM Provider Settings</h5>
                <form id="llmForm">
                    <div class="row mb-3">
                        <div class="col-md-6">
                            <label>Active Provider</label>
                            <select class="form-control" id="llmProvider">
                                <option value="none">Basic NLP (No LLM)</option>
                                <option value="openai">OpenAI GPT</option>
                                <option value="anthropic">Anthropic Claude</option>
                                <option value="grok">Grok</option>
                                <option value="ollama">Ollama (Local)</option>
                            </select>
                        </div>
                        <div class="col-md-6">
                            <label>API Key</label>
                            <input type="password" class="form-control" id="apiKey" 
                                placeholder="Enter API key for selected provider">
                        </div>
                    </div>
                    <button type="submit" class="btn btn-primary">
                        <i class="fas fa-save"></i> Save LLM Settings
                    </button>
                </form>
            </div>
            
            <!-- Advanced Settings -->
            <div class="mb-4">
                <h5><i class="fas fa-sliders-h"></i> Advanced Settings</h5>
                <div class="row">
                    <div class="col-md-4">
                        <label>Confidence Threshold</label>
                        <input type="range" class="form-range" min="0" max="100" value="70" id="confidenceThreshold">
                        <small class="text-muted">Current: <span id="confidenceValue">70</span>%</small>
                    </div>
                    <div class="col-md-4">
                        <label>Max Results</label>
                        <input type="number" class="form-control" value="50" min="1" max="1000">
                    </div>
                    <div class="col-md-4">
                        <label>Timeout (seconds)</label>
                        <input type="number" class="form-control" value="30" min="5" max="300">
                    </div>
                </div>
            </div>
            
            <!-- Actions -->
            <div class="mt-4">
                <button class="btn btn-success" id="exportConfig">
                    <i class="fas fa-download"></i> Export Config
                </button>
                <button class="btn btn-info" id="importConfig">
                    <i class="fas fa-upload"></i> Import Config
                </button>
                <button class="btn btn-warning" id="resetConfig">
                    <i class="fas fa-undo"></i> Reset to Defaults
                </button>
            </div>
        </div>
    </div>
    
    <script>
    $(document).ready(function() {
        // Update confidence value display
        $('#confidenceThreshold').on('input', function() {
            $('#confidenceValue').text($(this).val());
        });
        
        // Save InfoBlox settings
        $('#infobloxForm').submit(function(e) {
            e.preventDefault();
            const config = {
                INFOBLOX_GRID_MASTER_IP: $('#gridMaster').val(),
                INFOBLOX_USERNAME: $('#username').val(),
                INFOBLOX_PASSWORD: $('#password').val()
            };
            
            $.ajax({
                url: '/api/config',
                method: 'POST',
                contentType: 'application/json',
                data: JSON.stringify(config),
                success: function(result) {
                    alert(result.message || 'Configuration saved successfully');
                    if (result.infoblox_connected) {
                        alert('InfoBlox connection successful!');
                    }
                }
            });
        });
        
        // Save LLM settings
        $('#llmForm').submit(function(e) {
            e.preventDefault();
            const provider = $('#llmProvider').val();
            const apiKey = $('#apiKey').val();
            
            $.ajax({
                url: '/api/llm/config',
                method: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({
                    provider: provider,
                    api_key: apiKey
                }),
                success: function(result) {
                    alert('LLM configuration saved');
                }
            });
        });
    });
    </script>
    """
    template = ENHANCED_TEMPLATE.replace('{% block content %}{% endblock %}', 
                                         '{% block content %}' + config_content + '{% endblock %}')
    return render_template_string(template, page='config', config=RUNTIME_CONFIG)

@app.route('/mcp-config')
def mcp_config_page():
    """MCP Configuration page."""
    # Use a modified template with the MCP content embedded
    template = ENHANCED_TEMPLATE.replace('{% block content %}{% endblock %}', 
                                         '{% block content %}' + MCP_CONFIG_TEMPLATE + '{% endblock %}')
    return render_template_string(
        template,
        page='mcp-config',
        config=RUNTIME_CONFIG,
        mcp_status=get_mcp_status(),
        mcp_stats=get_mcp_statistics()
    )

@app.route('/mcp-tools')
def mcp_tools_page():
    """MCP Tools browser page."""
    tools = discover_mcp_tools()
    tools_by_category = organize_tools_by_category(tools)
    
    # Use a modified template with the MCP content embedded
    template = ENHANCED_TEMPLATE.replace('{% block content %}{% endblock %}', 
                                         '{% block content %}' + MCP_TOOLS_TEMPLATE + '{% endblock %}')
    return render_template_string(
        template,
        page='mcp-tools',
        tools=tools,
        tools_by_category=tools_by_category,
        last_update=MCP_LAST_REFRESH
    )

# API Endpoints

@app.route('/api/mcp/start', methods=['POST'])
def start_mcp_server():
    """Start MCP server."""
    try:
        subprocess.Popen(['python3', 'infoblox_mcp_server.py'], 
                        stdout=subprocess.PIPE, 
                        stderr=subprocess.PIPE)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/mcp/stop', methods=['POST'])
def stop_mcp_server():
    """Stop MCP server."""
    try:
        subprocess.run(['pkill', '-f', 'infoblox_mcp_server.py'])
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/mcp/status')
def mcp_status_api():
    """Get MCP server status via API."""
    return jsonify(get_mcp_status())

@app.route('/api/mcp/statistics')
def mcp_statistics_api():
    """Get MCP statistics via API."""
    return jsonify(get_mcp_statistics())

@app.route('/api/mcp/restart', methods=['POST'])
def restart_mcp_server():
    """Restart MCP server."""
    stop_mcp_server()
    import time
    time.sleep(2)
    return start_mcp_server()

@app.route('/api/mcp/refresh-schemas', methods=['POST'])
def refresh_schemas():
    """Refresh WAPI schemas."""
    try:
        # Trigger schema refresh in MCP server
        discover_mcp_tools()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/mcp/clear-cache', methods=['POST'])
def clear_cache():
    """Clear schema cache."""
    try:
        cache_dir = Path.home() / '.infoblox_mcp' / 'cache'
        if cache_dir.exists():
            import shutil
            shutil.rmtree(cache_dir)
            cache_dir.mkdir(parents=True, exist_ok=True)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/mcp/config', methods=['GET', 'POST'])
def mcp_config_api():
    """Get or update MCP configuration."""
    if request.method == 'POST':
        data = request.get_json()
        RUNTIME_CONFIG.update(data)
        # Save configuration
        with open(CONFIG_FILE, 'w') as f:
            json.dump(RUNTIME_CONFIG, f, indent=2)
        return jsonify({'success': True})
    else:
        return jsonify(RUNTIME_CONFIG)

@app.route('/api/mcp/tool-schema/<tool_name>')
def get_tool_schema(tool_name):
    """Get schema for a specific tool."""
    tool = MCP_TOOLS_CACHE.get(tool_name, {})
    return jsonify(tool)

@app.route('/api/mcp/execute-tool', methods=['POST'])
def execute_tool():
    """Execute an MCP tool."""
    data = request.get_json()
    tool_name = data.get('tool')
    parameters = data.get('parameters', {})
    
    # This would normally execute via MCP
    # For now, simulate execution
    result = {
        'tool': tool_name,
        'parameters': parameters,
        'result': 'Simulated execution result',
        'timestamp': datetime.now().isoformat()
    }
    
    return jsonify(result)

@app.route('/api/mcp/refresh-tools', methods=['POST'])
def refresh_tools():
    """Refresh tool list."""
    discover_mcp_tools()
    return jsonify({'success': True, 'tools_count': len(MCP_TOOLS_CACHE)})

# Existing API endpoints (simplified)
@app.route('/api/status')
def api_status():
    """System status."""
    # Check InfoBlox connection
    infoblox_connected = False
    try:
        import requests
        grid_master = os.environ.get('INFOBLOX_GRID_MASTER_IP', RUNTIME_CONFIG.get('INFOBLOX_GRID_MASTER_IP', ''))
        username = os.environ.get('INFOBLOX_USERNAME', RUNTIME_CONFIG.get('INFOBLOX_USERNAME', ''))
        password = os.environ.get('INFOBLOX_PASSWORD', RUNTIME_CONFIG.get('INFOBLOX_PASSWORD', ''))
        
        if grid_master and username and password:
            response = requests.get(
                f"https://{grid_master}/wapi/v2.13.1/?_schema",
                auth=(username, password),
                verify=False,
                timeout=5
            )
            infoblox_connected = response.status_code == 200
    except:
        infoblox_connected = False
    
    return jsonify({
        'infoblox_connected': infoblox_connected,
        'mcp_enabled': RUNTIME_CONFIG.get('mcp_enabled', False),
        'mcp_server_running': get_mcp_status()['running']
    })

@app.route('/health')
def health():
    """Health check."""
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    port = int(os.environ.get('INFOBLOX_FLASK_PORT', 5002))
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║     InfoBlox NLP System - MCP Enhanced Version              ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  Web Interface: http://localhost:{port:<5}                     ║
║  MCP Config:    http://localhost:{port:<5}/mcp-config          ║
║  MCP Tools:     http://localhost:{port:<5}/mcp-tools           ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    app.run(host='0.0.0.0', port=port, debug=False)