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
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
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
            margin: 0;
            padding-top: 60px; /* Space for fixed header */
        }
        
        /* Compact Fixed Header */
        .main-header {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            height: 60px;
            background: rgba(255,255,255,0.98);
            backdrop-filter: blur(10px);
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            z-index: 1000;
            border-bottom: 2px solid rgba(102, 126, 234, 0.2);
        }
        
        .header-content {
            max-width: 1400px;
            margin: 0 auto;
            height: 100%;
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 20px;
        }
        
        .logo-section {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        
        .logo-icon {
            background: var(--primary-gradient);
            color: white;
            width: 35px;
            height: 35px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 18px;
        }
        
        .logo-text {
            font-size: 16px;
            font-weight: 600;
            color: #333;
        }
        
        .nav-pills {
            display: flex;
            gap: 5px;
            margin: 0;
            padding: 4px;
            background: rgba(0,0,0,0.05);
            border-radius: 25px;
        }
        
        .nav-link {
            color: #666;
            font-weight: 500;
            font-size: 13px;
            padding: 6px 16px;
            border-radius: 20px;
            transition: all 0.3s;
            display: flex;
            align-items: center;
            gap: 6px;
            text-decoration: none;
            white-space: nowrap;
        }
        
        .nav-link i {
            font-size: 12px;
        }
        
        .nav-link:hover {
            background: rgba(102, 126, 234, 0.1);
            color: #667eea;
        }
        
        .nav-link.active {
            background: var(--primary-gradient);
            color: white;
        }
        
        .container { 
            max-width: 1400px;
            padding: 40px 20px;
            margin: 0 auto;
        }
        
        .main-card { 
            background: rgba(255,255,255,0.98); 
            backdrop-filter: blur(10px); 
            border: none; 
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            border-radius: 15px;
            margin-bottom: 30px;
            overflow: hidden;
        }
        
        .card-header {
            background: var(--primary-gradient);
            color: white;
            padding: 20px 30px;
            border-radius: 15px 15px 0 0 !important;
        }
        
        .card-body {
            padding: 30px;
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
    <!-- Compact Fixed Header -->
    <header class="main-header">
        <div class="header-content">
            <div class="logo-section">
                <div class="logo-icon">
                    <i class="fas fa-network-wired"></i>
                </div>
                <div class="logo-text">InfoBlox NLP System</div>
            </div>
            
            <nav class="nav-pills">
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
            </nav>
        </div>
    </header>
    
    <div class="container">
        {% block content %}{% endblock %}
    </div>
    
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
<style>
    /* MCP Tools Page Styles */
    .tools-container {
        display: flex;
        gap: 25px;
        margin-top: 20px;
    }
    
    .filters-sidebar {
        width: 280px;
        flex-shrink: 0;
    }
    
    .tools-main {
        flex: 1;
        min-width: 0;
    }
    
    .filter-card {
        background: white;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    }
    
    .filter-card h6 {
        color: #495057;
        font-weight: 600;
        margin-bottom: 15px;
        font-size: 14px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .filter-checkbox {
        display: flex;
        align-items: center;
        padding: 8px 12px;
        margin: 5px 0;
        border-radius: 8px;
        cursor: pointer;
        transition: all 0.2s;
    }
    
    .filter-checkbox:hover {
        background: #f8f9fa;
    }
    
    .filter-checkbox input[type="checkbox"] {
        margin-right: 10px;
        cursor: pointer;
    }
    
    .filter-checkbox label {
        cursor: pointer;
        margin: 0;
        font-size: 14px;
        color: #495057;
        user-select: none;
    }
    
    .filter-badge {
        margin-left: auto;
        background: #e9ecef;
        color: #495057;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 11px;
        font-weight: 600;
    }
    
    .search-box {
        position: relative;
        margin-bottom: 25px;
    }
    
    .search-box input {
        width: 100%;
        padding: 12px 45px 12px 20px;
        border: 2px solid #e9ecef;
        border-radius: 10px;
        font-size: 15px;
        transition: all 0.3s;
    }
    
    .search-box input:focus {
        border-color: #667eea;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
    }
    
    .search-box i {
        position: absolute;
        right: 20px;
        top: 50%;
        transform: translateY(-50%);
        color: #adb5bd;
    }
    
    .stats-bar {
        display: flex;
        gap: 20px;
        margin-bottom: 20px;
        padding: 15px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 10px;
        color: white;
    }
    
    .stat-item {
        display: flex;
        align-items: center;
        gap: 10px;
    }
    
    .stat-item i {
        font-size: 20px;
        opacity: 0.8;
    }
    
    .stat-value {
        font-size: 24px;
        font-weight: 600;
    }
    
    .stat-label {
        font-size: 12px;
        opacity: 0.9;
    }
    
    .tool-card {
        background: white;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 15px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        transition: all 0.3s;
        cursor: pointer;
        position: relative;
        overflow: hidden;
    }
    
    .tool-card:hover {
        box-shadow: 0 5px 20px rgba(0,0,0,0.1);
        transform: translateY(-2px);
    }
    
    .tool-card.expanded {
        box-shadow: 0 8px 25px rgba(0,0,0,0.15);
    }
    
    .tool-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 10px;
    }
    
    .tool-name {
        font-size: 18px;
        font-weight: 600;
        color: #2c3e50;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    
    .tool-method {
        padding: 4px 12px;
        border-radius: 6px;
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
    }
    
    .method-get {
        background: #d1f2eb;
        color: #0f5132;
    }
    
    .method-post {
        background: #cff4fc;
        color: #055160;
    }
    
    .method-put, .method-update {
        background: #fff3cd;
        color: #664d03;
    }
    
    .method-delete {
        background: #f8d7da;
        color: #842029;
    }
    
    .tool-category {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 11px;
        font-weight: 600;
        margin-right: 8px;
    }
    
    .category-ipam {
        background: #e7f5ff;
        color: #1864ab;
    }
    
    .category-dns {
        background: #f3f0ff;
        color: #5f3dc4;
    }
    
    .category-dhcp {
        background: #fff0f6;
        color: #a61e4d;
    }
    
    .tool-description {
        color: #6c757d;
        font-size: 14px;
        margin: 10px 0;
        line-height: 1.5;
    }
    
    .tool-path {
        font-family: 'Courier New', monospace;
        font-size: 12px;
        color: #868e96;
        background: #f8f9fa;
        padding: 8px 12px;
        border-radius: 6px;
        margin: 10px 0;
    }
    
    .tool-actions {
        display: flex;
        gap: 10px;
        margin-top: 15px;
    }
    
    .tool-expand {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 8px 16px;
        border-radius: 8px;
        font-size: 13px;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.3s;
    }
    
    .tool-expand:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
    }
    
    .tool-testing {
        display: none;
        margin-top: 20px;
        padding-top: 20px;
        border-top: 2px solid #e9ecef;
    }
    
    .tool-testing.show {
        display: block;
    }
    
    .parameter-group {
        margin-bottom: 20px;
    }
    
    .parameter-label {
        display: block;
        color: #495057;
        font-weight: 500;
        margin-bottom: 8px;
        font-size: 14px;
    }
    
    .parameter-required {
        color: #dc3545;
        font-weight: 600;
    }
    
    .parameter-input {
        width: 100%;
        padding: 10px 15px;
        border: 2px solid #e9ecef;
        border-radius: 8px;
        font-size: 14px;
        transition: all 0.3s;
    }
    
    .parameter-input:focus {
        border-color: #667eea;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
    }
    
    .parameter-hint {
        color: #6c757d;
        font-size: 12px;
        margin-top: 5px;
        font-style: italic;
    }
    
    .execute-button {
        background: linear-gradient(135deg, #51cf66 0%, #37b24d 100%);
        color: white;
        border: none;
        padding: 10px 24px;
        border-radius: 8px;
        font-size: 14px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.3s;
    }
    
    .execute-button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(55, 178, 77, 0.3);
    }
    
    .execute-button:disabled {
        background: #adb5bd;
        cursor: not-allowed;
        transform: none;
    }
    
    .result-container {
        margin-top: 20px;
        padding: 20px;
        background: #f8f9fa;
        border-radius: 10px;
        display: none;
    }
    
    .result-container.show {
        display: block;
    }
    
    .result-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 15px;
    }
    
    .result-status {
        padding: 6px 12px;
        border-radius: 6px;
        font-size: 12px;
        font-weight: 600;
    }
    
    .status-success {
        background: #d1f2eb;
        color: #0f5132;
    }
    
    .status-error {
        background: #f8d7da;
        color: #842029;
    }
    
    .result-content {
        background: #2d2d2d;
        color: #f8f8f2;
        padding: 15px;
        border-radius: 8px;
        font-family: 'Courier New', monospace;
        font-size: 13px;
        white-space: pre-wrap;
        word-break: break-all;
        max-height: 400px;
        overflow-y: auto;
    }
    
    .loading {
        text-align: center;
        color: #667eea;
        padding: 20px;
        font-size: 14px;
    }
    
    .loading i {
        margin-right: 8px;
    }
    
    .result-success {
        background: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 8px;
        padding: 15px;
        margin-top: 15px;
    }
    
    .result-success i {
        color: #155724;
        margin-right: 8px;
    }
    
    .result-success pre {
        background: white;
        border: 1px solid #dee2e6;
        border-radius: 4px;
        padding: 12px;
        margin-top: 10px;
        font-size: 12px;
        overflow-x: auto;
    }
    
    .result-error {
        background: #f8d7da;
        border: 1px solid #f5c6cb;
        border-radius: 8px;
        padding: 15px;
        margin-top: 15px;
    }
    
    .result-error i {
        color: #721c24;
        margin-right: 8px;
    }
    
    .result-error pre {
        background: white;
        border: 1px solid #dee2e6;
        border-radius: 4px;
        padding: 12px;
        margin-top: 10px;
        font-size: 12px;
        overflow-x: auto;
    }
    
    .no-tools {
        text-align: center;
        padding: 60px 20px;
        color: #6c757d;
    }
    
    .no-tools i {
        font-size: 48px;
        color: #dee2e6;
        margin-bottom: 20px;
    }
    
    .clear-filters {
        color: #667eea;
        cursor: pointer;
        font-size: 13px;
        text-decoration: underline;
    }
    
    .clear-filters:hover {
        color: #764ba2;
    }
</style>

<div class="tools-container">
    <!-- Filters Sidebar -->
    <div class="filters-sidebar">
        <!-- Search -->
        <div class="filter-card">
            <div class="search-box">
                <input type="text" id="toolSearch" placeholder="Search tools...">
                <i class="fas fa-search"></i>
            </div>
        </div>
        
        <!-- Category Filter -->
        <div class="filter-card">
            <h6><i class="fas fa-layer-group"></i> Categories</h6>
            <div class="filter-checkbox">
                <input type="checkbox" id="cat-ipam" value="ipam" checked>
                <label for="cat-ipam">IPAM</label>
                <span class="filter-badge" id="count-ipam">0</span>
            </div>
            <div class="filter-checkbox">
                <input type="checkbox" id="cat-dns" value="dns" checked>
                <label for="cat-dns">DNS</label>
                <span class="filter-badge" id="count-dns">0</span>
            </div>
            <div class="filter-checkbox">
                <input type="checkbox" id="cat-dhcp" value="dhcp" checked>
                <label for="cat-dhcp">DHCP</label>
                <span class="filter-badge" id="count-dhcp">0</span>
            </div>
            <div class="filter-checkbox">
                <input type="checkbox" id="cat-grid" value="grid" checked>
                <label for="cat-grid">Grid</label>
                <span class="filter-badge" id="count-grid">0</span>
            </div>
            <div class="filter-checkbox">
                <input type="checkbox" id="cat-other" value="other" checked>
                <label for="cat-other">Other</label>
                <span class="filter-badge" id="count-other">0</span>
            </div>
        </div>
        
        <!-- Operation Filter -->
        <div class="filter-card">
            <h6><i class="fas fa-code"></i> Operations</h6>
            <div class="filter-checkbox">
                <input type="checkbox" id="op-get" value="GET" checked>
                <label for="op-get">GET</label>
                <span class="filter-badge" id="count-get">0</span>
            </div>
            <div class="filter-checkbox">
                <input type="checkbox" id="op-post" value="POST" checked>
                <label for="op-post">POST</label>
                <span class="filter-badge" id="count-post">0</span>
            </div>
            <div class="filter-checkbox">
                <input type="checkbox" id="op-put" value="PUT" checked>
                <label for="op-put">PUT/UPDATE</label>
                <span class="filter-badge" id="count-put">0</span>
            </div>
            <div class="filter-checkbox">
                <input type="checkbox" id="op-delete" value="DELETE" checked>
                <label for="op-delete">DELETE</label>
                <span class="filter-badge" id="count-delete">0</span>
            </div>
            <div class="mt-3">
                <span class="clear-filters" onclick="clearAllFilters()">Clear all filters</span>
            </div>
        </div>
        
        <!-- Actions -->
        <div class="filter-card">
            <button class="btn btn-primary w-100 mb-2" onclick="refreshTools()">
                <i class="fas fa-sync"></i> Refresh Tools
            </button>
            <button class="btn btn-secondary w-100" onclick="startMCPServer()">
                <i class="fas fa-server"></i> Start MCP Server
            </button>
        </div>
    </div>
    
    <!-- Main Content -->
    <div class="tools-main">
        <!-- Statistics Bar -->
        <div class="stats-bar">
            <div class="stat-item">
                <i class="fas fa-tools"></i>
                <div>
                    <div class="stat-value" id="totalTools">0</div>
                    <div class="stat-label">Total Tools</div>
                </div>
            </div>
            <div class="stat-item">
                <i class="fas fa-filter"></i>
                <div>
                    <div class="stat-value" id="visibleTools">0</div>
                    <div class="stat-label">Filtered</div>
                </div>
            </div>
            <div class="stat-item">
                <i class="fas fa-clock"></i>
                <div>
                    <div class="stat-value" id="lastUpdate">Never</div>
                    <div class="stat-label">Last Update</div>
                </div>
            </div>
        </div>
        
        <!-- Tools List -->
        <div id="toolsList">
            <!-- Sample Network/IPAM Tools -->
            <div class="tool-card" data-category="ipam" data-method="GET" data-tool="get_network">
                <div class="tool-header">
                    <div class="tool-name">
                        <span class="tool-category category-ipam">IPAM</span>
                        get_network
                    </div>
                    <span class="tool-method method-get">GET</span>
                </div>
                <div class="tool-description">
                    Retrieve network information from InfoBlox. Search by network CIDR or retrieve all networks.
                </div>
                <div class="tool-path">/wapi/v2.13.1/network</div>
                <div class="tool-actions">
                    <button class="tool-expand" onclick="toggleTool('get_network')">
                        <i class="fas fa-play"></i> Test Tool
                    </button>
                </div>
                <div class="tool-testing" id="test-get_network" style="display: none;">
                    <h6>Parameters</h6>
                    <div class="parameter-group">
                        <label class="parameter-label">
                            Network <span class="text-muted">(optional)</span>
                        </label>
                        <input type="text" class="parameter-input" id="param-get_network-network" 
                            placeholder="e.g., 10.0.0.0/24">
                        <div class="parameter-hint">Enter network in CIDR notation or leave empty to get all networks</div>
                    </div>
                    <div class="parameter-group">
                        <label class="parameter-label">
                            Max Results <span class="text-muted">(optional)</span>
                        </label>
                        <input type="number" class="parameter-input" id="param-get_network-max_results" 
                            placeholder="50" value="50">
                        <div class="parameter-hint">Maximum number of results to return</div>
                    </div>
                    <button class="execute-button" onclick="executeTool('get_network', 'GET')">
                        <i class="fas fa-rocket"></i> Execute Query
                    </button>
                    <div class="result-container" id="result-get_network"></div>
                </div>
            </div>
            
            <!-- Sample DNS Tool -->
            <div class="tool-card" data-category="dns" data-method="POST" data-tool="create_a_record">
                <div class="tool-header">
                    <div class="tool-name">
                        <span class="tool-category category-dns">DNS</span>
                        create_a_record
                    </div>
                    <span class="tool-method method-post">POST</span>
                </div>
                <div class="tool-description">
                    Create a new DNS A record in the specified zone.
                </div>
                <div class="tool-path">/wapi/v2.13.1/record:a</div>
                <div class="tool-actions">
                    <button class="tool-expand" onclick="toggleTool('create_a_record')">
                        <i class="fas fa-play"></i> Test Tool
                    </button>
                </div>
                <div class="tool-testing" id="test-create_a_record" style="display: none;">
                    <h6>Parameters</h6>
                    <div class="parameter-group">
                        <label class="parameter-label">
                            Hostname <span class="parameter-required">*</span>
                        </label>
                        <input type="text" class="parameter-input" id="param-create_a_record-name" 
                            placeholder="e.g., server1.example.com" required>
                        <div class="parameter-hint">Fully qualified domain name for the A record</div>
                    </div>
                    <div class="parameter-group">
                        <label class="parameter-label">
                            IP Address <span class="parameter-required">*</span>
                        </label>
                        <input type="text" class="parameter-input" id="param-create_a_record-ipv4addr" 
                            placeholder="e.g., 192.168.1.100" required>
                        <div class="parameter-hint">IPv4 address for the A record</div>
                    </div>
                    <div class="parameter-group">
                        <label class="parameter-label">
                            TTL <span class="text-muted">(optional)</span>
                        </label>
                        <input type="number" class="parameter-input" id="param-create_a_record-ttl" 
                            placeholder="3600">
                        <div class="parameter-hint">Time to live in seconds (default: 3600)</div>
                    </div>
                    <div class="parameter-group">
                        <label class="parameter-label">
                            Comment <span class="text-muted">(optional)</span>
                        </label>
                        <input type="text" class="parameter-input" id="param-create_a_record-comment" 
                            placeholder="e.g., Web server">
                        <div class="parameter-hint">Description or notes about this record</div>
                    </div>
                    <button class="execute-button" onclick="executeTool('create_a_record', 'POST')">
                        <i class="fas fa-plus"></i> Create Record
                    </button>
                    <div class="result-container" id="result-create_a_record"></div>
                </div>
            </div>
            
            <!-- Sample DHCP Tool -->
            <div class="tool-card" data-category="dhcp" data-method="GET" data-tool="get_dhcp_range">
                <div class="tool-header">
                    <div class="tool-name">
                        <span class="tool-category category-dhcp">DHCP</span>
                        get_dhcp_range
                    </div>
                    <span class="tool-method method-get">GET</span>
                </div>
                <div class="tool-description">
                    Get DHCP range information from InfoBlox.
                </div>
                <div class="tool-path">/wapi/v2.13.1/range</div>
                <div class="tool-actions">
                    <button class="tool-expand" onclick="toggleTool('get_dhcp_range')">
                        <i class="fas fa-play"></i> Test Tool
                    </button>
                </div>
                <div class="tool-testing" id="test-get_dhcp_range" style="display: none;">
                    <h6>Parameters</h6>
                    <div class="parameter-group">
                        <label class="parameter-label">
                            Network <span class="text-muted">(optional)</span>
                        </label>
                        <input type="text" class="parameter-input" id="param-get_dhcp_range-network" 
                            placeholder="e.g., 10.0.0.0/24">
                        <div class="parameter-hint">Filter by network (CIDR notation)</div>
                    </div>
                    <button class="execute-button" onclick="executeTool('get_dhcp_range', 'GET')">
                        <i class="fas fa-search"></i> Get DHCP Ranges
                    </button>
                    <div class="result-container" id="result-get_dhcp_range"></div>
                </div>
            </div>
            
            <!-- No Tools Message (hidden by default) -->
            <div class="no-tools" id="noToolsMessage" style="display:none;">
                <i class="fas fa-inbox"></i>
                <h5>No tools found</h5>
                <p>Try adjusting your filters or start the MCP server to discover tools.</p>
            </div>
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
// Global state
let activeFilters = {
    categories: [],
    methods: [],
    search: ''
};

// Toggle tool testing interface
function toggleTool(toolName) {
    const testDiv = document.getElementById('test-' + toolName);
    if (testDiv.style.display === 'none' || !testDiv.style.display) {
        testDiv.style.display = 'block';
    } else {
        testDiv.style.display = 'none';
    }
}

// Execute tool with parameters
function executeTool(toolName, method) {
    const resultDiv = document.getElementById('result-' + toolName);
    
    // Show loading state
    resultDiv.innerHTML = '<div class="loading"><i class="fas fa-spinner fa-spin"></i> Executing...</div>';
    resultDiv.style.display = 'block';
    
    // Collect parameters
    const params = {};
    const inputs = document.querySelectorAll(`[id^="param-${toolName}-"]`);
    inputs.forEach(input => {
        const paramName = input.id.replace(`param-${toolName}-`, '');
        const value = input.value;
        if (value) {
            params[paramName] = value;
        }
    });
    
    // Build request payload
    const payload = {
        tool: toolName,
        method: method,
        parameters: params
    };
    
    // Execute API call
    fetch('/api/process_query', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            query: `Execute ${toolName} with params: ${JSON.stringify(params)}`
        })
    })
    .then(response => response.json())
    .then(data => {
        // Display results
        if (data.error) {
            resultDiv.innerHTML = `
                <div class="result-error">
                    <i class="fas fa-exclamation-circle"></i> Error
                    <pre>${JSON.stringify(data.error, null, 2)}</pre>
                </div>
            `;
        } else {
            resultDiv.innerHTML = `
                <div class="result-success">
                    <i class="fas fa-check-circle"></i> Success
                    <pre>${JSON.stringify(data.result || data, null, 2)}</pre>
                </div>
            `;
        }
    })
    .catch(error => {
        resultDiv.innerHTML = `
            <div class="result-error">
                <i class="fas fa-exclamation-circle"></i> Request Failed
                <pre>${error.message}</pre>
            </div>
        `;
    });
}

// Apply filters to tools
function applyFilters() {
    const tools = document.querySelectorAll('.tool-card');
    let visibleCount = 0;
    
    tools.forEach(tool => {
        const category = tool.dataset.category;
        const method = tool.dataset.method;
        const toolName = tool.dataset.tool.toLowerCase();
        
        // Check category filter
        let categoryMatch = activeFilters.categories.length === 0 || 
                           activeFilters.categories.includes(category);
        
        // Check method filter
        let methodMatch = activeFilters.methods.length === 0 || 
                         activeFilters.methods.includes(method);
        
        // Check search filter
        let searchMatch = activeFilters.search === '' || 
                         toolName.includes(activeFilters.search.toLowerCase());
        
        // Show/hide tool based on all filters
        if (categoryMatch && methodMatch && searchMatch) {
            tool.style.display = 'block';
            visibleCount++;
        } else {
            tool.style.display = 'none';
        }
    });
    
    // Update stats
    document.getElementById('visibleTools').textContent = visibleCount;
    
    // Show/hide no tools message
    const noToolsMessage = document.getElementById('noToolsMessage');
    if (visibleCount === 0) {
        noToolsMessage.style.display = 'block';
    } else {
        noToolsMessage.style.display = 'none';
    }
}

// Initialize when document is ready
$(document).ready(function() {
    // Update total tools count
    const totalTools = $('.tool-card').length;
    $('#totalTools').text(totalTools);
    $('#visibleTools').text(totalTools);
    
    // Category filter checkboxes
    $('.filter-category input[type="checkbox"]').change(function() {
        activeFilters.categories = [];
        $('.filter-category input:checked').each(function() {
            activeFilters.categories.push($(this).val());
        });
        applyFilters();
    });
    
    // Method filter checkboxes
    $('.filter-method input[type="checkbox"]').change(function() {
        activeFilters.methods = [];
        $('.filter-method input:checked').each(function() {
            activeFilters.methods.push($(this).val());
        });
        applyFilters();
    });
    
    // Search filter
    $('#toolSearch').on('input', function() {
        activeFilters.search = $(this).val();
        applyFilters();
    });
    
    // Clear filters button
    $('#clearFilters').click(function() {
        // Uncheck all checkboxes
        $('.filter-category input[type="checkbox"]').prop('checked', false);
        $('.filter-method input[type="checkbox"]').prop('checked', false);
        
        // Clear search
        $('#toolSearch').val('');
        
        // Reset active filters
        activeFilters = {
            categories: [],
            methods: [],
            search: ''
        };
        
        // Apply filters (show all)
        applyFilters();
    });
    
    // Refresh tools button
    $('#refreshTools').click(function() {
        const btn = $(this);
        btn.prop('disabled', true);
        btn.html('<i class="fas fa-spinner fa-spin"></i> Refreshing...');
        
        // Simulate refresh (in real app, this would call MCP API)
        setTimeout(() => {
            // Update last update time
            const now = new Date().toLocaleTimeString();
            $('#lastUpdate').text(now);
            
            // Re-enable button
            btn.prop('disabled', false);
            btn.html('<i class="fas fa-sync"></i> Refresh');
            
            // Show success message
            showNotification('Tools refreshed successfully', 'success');
        }, 1500);
    });
    
    // Initialize last update time
    $('#lastUpdate').text(new Date().toLocaleTimeString());
});

// Show notification
function showNotification(message, type) {
    const notification = $(`
        <div class="alert alert-${type} alert-dismissible fade show position-fixed" 
             style="top: 80px; right: 20px; z-index: 9999;">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `);
    
    $('body').append(notification);
    
    // Auto-dismiss after 3 seconds
    setTimeout(() => {
        notification.alert('close');
    }, 3000);
}
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
    
    # Try to load generated tools first
    try:
        tools_file = Path.home() / '.infoblox_mcp' / 'tools' / 'discovered_tools.json'
        if tools_file.exists():
            with open(tools_file) as f:
                data = json.load(f)
                tools = data.get('tools', [])
                logger.info(f"Loaded {len(tools)} tools from {tools_file}")
    except Exception as e:
        logger.error(f"Error loading generated tools: {e}")
    
    # Try to get tools from MCP server cache as fallback
    if not tools:
        try:
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
            logger.error(f"Error discovering MCP tools from cache: {e}")
    
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
    <style>
        .config-section {
            background: #f8f9fa;
            border-radius: 12px;
            padding: 25px;
            margin-bottom: 25px;
        }
        .config-section h5 {
            color: #495057;
            margin-bottom: 20px;
            font-size: 18px;
            font-weight: 600;
        }
        .form-label {
            color: #6c757d;
            font-weight: 500;
            margin-bottom: 8px;
            font-size: 14px;
        }
        .action-buttons {
            display: flex;
            gap: 10px;
            padding: 25px;
            background: #f8f9fa;
            border-radius: 12px;
            margin-top: 25px;
        }
        
        /* Enhanced Slider Styles */
        .slider-container {
            position: relative;
            padding: 20px 0 30px;
        }
        
        .custom-slider {
            position: absolute;
            width: 100%;
            height: 6px;
            -webkit-appearance: none;
            appearance: none;
            background: transparent;
            outline: none;
            z-index: 2;
            cursor: pointer;
        }
        
        .slider-track {
            position: absolute;
            width: 100%;
            height: 6px;
            background: #e9ecef;
            border-radius: 3px;
            top: 20px;
            overflow: hidden;
        }
        
        .slider-fill {
            height: 100%;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            border-radius: 3px;
            width: 70%;
            transition: width 0.2s ease;
        }
        
        .custom-slider::-webkit-slider-thumb {
            -webkit-appearance: none;
            appearance: none;
            width: 24px;
            height: 24px;
            border-radius: 50%;
            background: white;
            border: 3px solid #667eea;
            cursor: pointer;
            box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
            transition: all 0.2s ease;
        }
        
        .custom-slider::-moz-range-thumb {
            width: 24px;
            height: 24px;
            border-radius: 50%;
            background: white;
            border: 3px solid #667eea;
            cursor: pointer;
            box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
            transition: all 0.2s ease;
        }
        
        .custom-slider::-webkit-slider-thumb:hover {
            transform: scale(1.2);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.5);
        }
        
        .custom-slider::-moz-range-thumb:hover {
            transform: scale(1.2);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.5);
        }
        
        .slider-labels {
            display: flex;
            justify-content: space-between;
            margin-top: 35px;
            font-size: 12px;
            color: #6c757d;
        }
        
        .slider-value-badge {
            position: absolute;
            top: -10px;
            left: 70%;
            transform: translateX(-50%);
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 14px;
            font-weight: 600;
            box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
            transition: left 0.2s ease;
        }
        
        .slider-value-badge::after {
            content: '';
            position: absolute;
            bottom: -4px;
            left: 50%;
            transform: translateX(-50%);
            width: 0;
            height: 0;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-top: 4px solid #764ba2;
        }
    </style>
    
    <div class="main-card">
        <div class="card-header">
            <h4 class="mb-0"><i class="fas fa-cog"></i> System Configuration</h4>
        </div>
        <div class="card-body">
            <!-- InfoBlox Settings -->
            <div class="config-section">
                <h5><i class="fas fa-server"></i> InfoBlox Connection</h5>
                <form id="infobloxForm">
                    <div class="row g-3">
                        <div class="col-md-4">
                            <label class="form-label">Grid Master IP</label>
                            <input type="text" class="form-control" id="gridMaster" 
                                value="{{ config.get('INFOBLOX_GRID_MASTER_IP', '') }}" 
                                placeholder="192.168.1.224">
                        </div>
                        <div class="col-md-4">
                            <label class="form-label">Username</label>
                            <input type="text" class="form-control" id="username" 
                                value="{{ config.get('INFOBLOX_USERNAME', '') }}"
                                placeholder="admin">
                        </div>
                        <div class="col-md-4">
                            <label class="form-label">Password</label>
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
            <div class="config-section">
                <h5><i class="fas fa-brain"></i> LLM Provider Settings</h5>
                <form id="llmForm">
                    <div class="row g-3 mb-3">
                        <div class="col-md-6">
                            <label class="form-label">Active Provider</label>
                            <select class="form-control" id="llmProvider">
                                <option value="none">Basic NLP (No LLM)</option>
                                <option value="openai">OpenAI GPT</option>
                                <option value="anthropic">Anthropic Claude</option>
                                <option value="grok">Grok</option>
                                <option value="ollama">Ollama (Local)</option>
                            </select>
                        </div>
                        <div class="col-md-6">
                            <label class="form-label">API Key</label>
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
            <div class="config-section">
                <h5><i class="fas fa-sliders-h"></i> Advanced Settings</h5>
                <div class="row g-3">
                    <div class="col-md-4">
                        <label class="form-label">Confidence Threshold</label>
                        <div class="slider-container">
                            <input type="range" class="custom-slider" min="0" max="100" value="70" id="confidenceThreshold">
                            <div class="slider-track">
                                <div class="slider-fill" id="sliderFill"></div>
                            </div>
                            <div class="slider-labels">
                                <span>0%</span>
                                <span>50%</span>
                                <span>100%</span>
                            </div>
                            <div class="slider-value-badge" id="sliderValueBadge">
                                <span id="confidenceValue">70</span>%
                            </div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <label class="form-label">Max Results</label>
                        <input type="number" class="form-control" value="50" min="1" max="1000">
                    </div>
                    <div class="col-md-4">
                        <label class="form-label">Timeout (seconds)</label>
                        <input type="number" class="form-control" value="30" min="5" max="300">
                    </div>
                </div>
            </div>
            
            <!-- Actions -->
            <div class="action-buttons">
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
        // Enhanced slider functionality
        function updateSlider() {
            const slider = $('#confidenceThreshold');
            const value = slider.val();
            const percentage = value + '%';
            
            // Update value display in badge
            $('#confidenceValue').text(value);
            
            // Update slider fill width
            $('#sliderFill').css('width', percentage);
            
            // Update badge position
            $('#sliderValueBadge').css('left', percentage);
            
            // Dynamic color changes based on value
            let gradientColor, thumbColor, badgeColor;
            
            if (value < 30) {
                gradientColor = 'linear-gradient(90deg, #dc3545 0%, #f86168 100%)';
                thumbColor = '#dc3545';
                badgeColor = 'linear-gradient(135deg, #dc3545 0%, #f86168 100%)';
            } else if (value < 70) {
                gradientColor = 'linear-gradient(90deg, #ffc107 0%, #ffdb4d 100%)';
                thumbColor = '#ffc107';
                badgeColor = 'linear-gradient(135deg, #ffc107 0%, #ffdb4d 100%)';
            } else {
                gradientColor = 'linear-gradient(90deg, #667eea 0%, #764ba2 100%)';
                thumbColor = '#667eea';
                badgeColor = 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)';
            }
            
            $('#sliderFill').css('background', gradientColor);
            $('#sliderValueBadge').css('background', badgeColor);
            
            // Update thumb color with a style tag (since pseudo-elements can't be directly modified)
            $('#sliderStyles').remove();
            $('<style id="sliderStyles">')
                .text(`.custom-slider::-webkit-slider-thumb { border-color: ${thumbColor} !important; }
                       .custom-slider::-moz-range-thumb { border-color: ${thumbColor} !important; }`)
                .appendTo('head');
        }
        
        // Bind to both input and change events for better compatibility
        $('#confidenceThreshold').on('input change', updateSlider);
        
        // Also update on mouse events for smoother interaction
        $('#confidenceThreshold').on('mousemove', function(event) {
            if (event.buttons === 1) { // Mouse is being dragged
                updateSlider();
            }
        });
        
        // Debug: Log slider changes to console
        $('#confidenceThreshold').on('input', function() {
            console.log('Slider value:', $(this).val());
        });
        
        // Initialize slider on page load
        updateSlider();
        
        // Force update after a short delay to ensure DOM is ready
        setTimeout(updateSlider, 100);
        
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
    
    # Generate dynamic HTML for tools
    from generate_tools_html import generate_tools_html
    tools_html = generate_tools_html(tools)
    
    # Replace the sample tools in the template with actual tools
    template_with_tools = MCP_TOOLS_TEMPLATE
    
    # Find and replace the sample tools section
    start_marker = '<!-- Sample Network/IPAM Tools -->'
    end_marker = '<!-- No Tools Message (hidden by default) -->'
    
    if start_marker in template_with_tools and end_marker in template_with_tools:
        start_idx = template_with_tools.find(start_marker)
        end_idx = template_with_tools.find(end_marker)
        
        # Replace the sample tools with dynamically generated tools
        template_with_tools = (
            template_with_tools[:start_idx] +
            '<!-- Dynamically Generated Tools -->\n' +
            tools_html + '\n' +
            template_with_tools[end_idx:]
        )
    
    # Render the complete MCP Tools page with embedded template
    full_page = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>InfoBlox AI - MCP Tools</title>
    
    <!-- jQuery first -->
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    
    <!-- Bootstrap CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    
    <!-- Font Awesome -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    
    <!-- Bootstrap JS -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    
    <style>
        /* Enhanced Header Styles */
        body {
            padding-top: 60px;
            font-family: 'Inter', -apple-system, system-ui, sans-serif;
            background: #f8f9fa;
        }
        
        .main-header {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            height: 60px;
            background: rgba(255, 255, 255, 0.98);
            backdrop-filter: blur(10px);
            box-shadow: 0 2px 10px rgba(0,0,0,0.08);
            z-index: 1030;
            display: flex;
            align-items: center;
            padding: 0 30px;
        }
        
        .header-content {
            display: flex;
            align-items: center;
            justify-content: space-between;
            width: 100%;
            max-width: 1400px;
            margin: 0 auto;
        }
        
        .header-left {
            display: flex;
            align-items: center;
            gap: 30px;
        }
        
        .header-brand {
            display: flex;
            align-items: center;
            gap: 12px;
            text-decoration: none;
            color: #333;
        }
        
        .brand-logo {
            width: 32px;
            height: 32px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            font-size: 18px;
        }
        
        .brand-text {
            font-size: 18px;
            font-weight: 600;
            color: #1a1a1a;
        }
        
        .header-nav {
            display: flex;
            gap: 5px;
        }
        
        .nav-pill {
            padding: 6px 16px;
            border-radius: 20px;
            background: transparent;
            color: #666;
            text-decoration: none;
            font-size: 14px;
            font-weight: 500;
            transition: all 0.2s ease;
        }
        
        .nav-pill:hover {
            background: #f0f0f0;
            color: #333;
        }
        
        .nav-pill.active {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        
        .header-right {
            display: flex;
            align-items: center;
            gap: 15px;
        }
        
        .status-indicator {
            display: flex;
            align-items: center;
            gap: 6px;
            padding: 5px 12px;
            background: #f8f9fa;
            border-radius: 15px;
            font-size: 12px;
        }
        
        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #dc3545;
            animation: pulse 2s infinite;
        }
        
        .status-dot.connected {
            background: #28a745;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        /* Content Area */
        .content-wrapper {
            padding: 40px;
            max-width: 1400px;
            margin: 0 auto;
        }
    </style>
    
    ''' + template_with_tools + '''
</head>
<body>
    <!-- Fixed Header -->
    <header class="main-header">
        <div class="header-content">
            <div class="header-left">
                <a href="/" class="header-brand">
                    <div class="brand-logo">IB</div>
                    <div class="brand-text">InfoBlox AI</div>
                </a>
                <nav class="header-nav">
                    <a href="/" class="nav-pill">Query</a>
                    <a href="/config" class="nav-pill">Config</a>
                    <a href="/mcp-config" class="nav-pill">MCP Config</a>
                    <a href="/mcp-tools" class="nav-pill active">MCP Tools</a>
                </nav>
            </div>
            <div class="header-right">
                <div class="status-indicator">
                    <span class="status-dot" id="infoblox-status"></span>
                    <span>InfoBlox</span>
                </div>
                <div class="status-indicator">
                    <span class="status-dot" id="mcp-status"></span>
                    <span>MCP</span>
                </div>
            </div>
        </div>
    </header>
    
    <!-- Main Content -->
    <div class="content-wrapper">
        <div class="page-header mb-4">
            <h4><i class="fas fa-tools"></i> MCP Tools Browser</h4>
            <p class="text-muted">Explore and test InfoBlox API tools</p>
        </div>
        
        <!-- Tools content will be rendered here -->
        <div id="mcp-tools-content"></div>
    </div>
    
    <script>
        // Initialize the MCP tools content
        $(document).ready(function() {
            $('#mcp-tools-content').html($('.tools-container').parent().html());
        });
    </script>
</body>
</html>
    '''
    
    return full_page

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
    # Run the generator script to update tools
    try:
        import subprocess
        result = subprocess.run(['python3', 'generate_mcp_tools.py'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            logger.info("Successfully generated new tools")
    except Exception as e:
        logger.error(f"Error generating tools: {e}")
    
    # Reload the tools
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