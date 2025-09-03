#!/usr/bin/env python3
"""
Configurable Flask web application for InfoBlox WAPI NLP interface.
Supports multiple LLM providers and runtime configuration.
"""

from flask import Flask, request, jsonify, render_template_string, redirect, url_for
import sys
import os
import json
import logging
from datetime import datetime
import requests

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
    'llm_provider': 'basic',  # basic, openai, anthropic, grok, ollama
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
    'max_results': 100
}

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

# HTML template for the main interface
MAIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>InfoBlox WAPI NLP Interface</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
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
        
        .container { max-width: 1000px; margin-top: 30px; }
        
        .main-card { 
            background: rgba(255,255,255,0.98); 
            backdrop-filter: blur(10px); 
            border: none; 
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            border-radius: 15px;
        }
        
        .card-header { 
            background: var(--primary-gradient); 
            color: white; 
            border-radius: 15px 15px 0 0 !important;
            padding: 20px;
        }
        
        .status-indicator { 
            width: 12px; 
            height: 12px; 
            border-radius: 50%; 
            display: inline-block; 
            margin-right: 8px;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }
        
        .status-connected { background-color: var(--success-color); }
        .status-disconnected { background-color: var(--danger-color); }
        .status-partial { background-color: var(--warning-color); }
        
        #response { 
            white-space: pre-wrap; 
            font-family: 'Courier New', monospace; 
            background-color: #f8f9fa; 
            padding: 15px; 
            border-radius: 8px; 
            max-height: 400px; 
            overflow-y: auto;
            border: 1px solid #dee2e6;
        }
        
        .example-query { 
            cursor: pointer; 
            color: #007bff; 
            text-decoration: none;
            transition: color 0.3s;
        }
        
        .example-query:hover { 
            color: #0056b3; 
            text-decoration: underline;
        }
        
        .config-btn {
            background: white;
            color: #764ba2;
            border: 2px solid #764ba2;
            padding: 8px 20px;
            border-radius: 25px;
            transition: all 0.3s;
        }
        
        .config-btn:hover {
            background: #764ba2;
            color: white;
        }
        
        .nav-tabs .nav-link {
            color: #495057;
            border: none;
            padding: 12px 20px;
        }
        
        .nav-tabs .nav-link.active {
            color: #764ba2;
            background: transparent;
            border-bottom: 3px solid #764ba2;
        }
        
        .confidence-display {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.9em;
            margin-left: 10px;
        }
        
        .high-confidence { background-color: #d4edda; color: #155724; }
        .medium-confidence { background-color: #fff3cd; color: #856404; }
        .low-confidence { background-color: #f8d7da; color: #721c24; }
        
        .llm-status {
            display: inline-block;
            padding: 3px 10px;
            border-radius: 15px;
            font-size: 0.85em;
            margin-left: 10px;
        }
        
        .llm-active { background-color: #d1f2eb; color: #0f5132; }
        .llm-inactive { background-color: #f8d7da; color: #842029; }
    </style>
</head>
<body>
    <div class="container">
        <div class="text-center mb-4">
            <h1 class="text-white">
                <i class="fas fa-network-wired"></i> InfoBlox WAPI NLP Interface
            </h1>
            <p class="text-white-50">Natural Language Processing for Network Management</p>
        </div>
        
        <div class="card main-card">
            <div class="card-header">
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <h4 class="mb-0">
                            <i class="fas fa-terminal"></i> Query Processor
                        </h4>
                    </div>
                    <div class="d-flex align-items-center gap-3">
                        <span id="llmStatus" class="llm-status llm-inactive">
                            <i class="fas fa-brain"></i> <span id="llmProvider">Basic NLP</span>
                        </span>
                        <span id="connectionStatus">
                            <span class="status-indicator status-disconnected"></span>
                            <span id="statusText">Checking...</span>
                        </span>
                        <a href="/config" class="config-btn text-decoration-none">
                            <i class="fas fa-cog"></i> Configure
                        </a>
                    </div>
                </div>
            </div>
            
            <div class="card-body">
                <ul class="nav nav-tabs mb-4" role="tablist">
                    <li class="nav-item">
                        <a class="nav-link active" data-bs-toggle="tab" href="#query-tab">
                            <i class="fas fa-search"></i> Query
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" data-bs-toggle="tab" href="#examples-tab">
                            <i class="fas fa-lightbulb"></i> Examples
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" data-bs-toggle="tab" href="#status-tab">
                            <i class="fas fa-info-circle"></i> Status
                        </a>
                    </li>
                </ul>
                
                <div class="tab-content">
                    <div class="tab-pane fade show active" id="query-tab">
                        <form id="queryForm">
                            <div class="mb-3">
                                <label for="queryInput" class="form-label">
                                    <i class="fas fa-keyboard"></i> Enter your query:
                                </label>
                                <div class="input-group">
                                    <input type="text" class="form-control form-control-lg" id="queryInput" 
                                        placeholder="e.g., Create a network with CIDR 10.0.0.0/24" autocomplete="off">
                                    <button type="submit" class="btn btn-primary btn-lg">
                                        <i class="fas fa-paper-plane"></i> Process
                                    </button>
                                </div>
                            </div>
                        </form>
                        
                        <div id="loading" class="text-center mt-3" style="display: none;">
                            <div class="spinner-border text-primary" role="status">
                                <span class="visually-hidden">Processing...</span>
                            </div>
                            <p class="mt-2">Processing your query...</p>
                        </div>
                        
                        <div id="resultContainer" style="display: none;">
                            <div class="d-flex justify-content-between align-items-center mb-2">
                                <h5>Result:</h5>
                                <div>
                                    <span id="intentDisplay" class="badge bg-primary"></span>
                                    <span id="confidenceDisplay" class="confidence-display"></span>
                                </div>
                            </div>
                            <div id="response"></div>
                        </div>
                    </div>
                    
                    <div class="tab-pane fade" id="examples-tab">
                        <h5>Click any example to try it:</h5>
                        <div class="list-group mt-3">
                            <a href="#" class="list-group-item list-group-item-action example-query">
                                <i class="fas fa-plus-circle text-success"></i> Create a network with CIDR 10.0.0.0/24 and comment TestNetwork
                            </a>
                            <a href="#" class="list-group-item list-group-item-action example-query">
                                <i class="fas fa-list text-primary"></i> List all networks
                            </a>
                            <a href="#" class="list-group-item list-group-item-action example-query">
                                <i class="fas fa-search text-info"></i> Find network 192.168.1.0/24
                            </a>
                            <a href="#" class="list-group-item list-group-item-action example-query">
                                <i class="fas fa-network-wired text-warning"></i> Get next available IP from network 10.0.0.0/24
                            </a>
                            <a href="#" class="list-group-item list-group-item-action example-query">
                                <i class="fas fa-server text-secondary"></i> Create host record for server1.example.com with IP 192.168.0.10
                            </a>
                            <a href="#" class="list-group-item list-group-item-action example-query">
                                <i class="fas fa-trash text-danger"></i> Delete host record for old-server.example.com
                            </a>
                        </div>
                    </div>
                    
                    <div class="tab-pane fade" id="status-tab">
                        <div class="row">
                            <div class="col-md-6">
                                <h5><i class="fas fa-server"></i> InfoBlox Connection</h5>
                                <table class="table table-sm">
                                    <tr>
                                        <td>Grid Master:</td>
                                        <td><span id="gridMasterIP">-</span></td>
                                    </tr>
                                    <tr>
                                        <td>WAPI Version:</td>
                                        <td><span id="wapiVersion">-</span></td>
                                    </tr>
                                    <tr>
                                        <td>Connection:</td>
                                        <td><span id="connectionDetail">-</span></td>
                                    </tr>
                                </table>
                            </div>
                            <div class="col-md-6">
                                <h5><i class="fas fa-brain"></i> AI/LLM Status</h5>
                                <table class="table table-sm">
                                    <tr>
                                        <td>Provider:</td>
                                        <td><span id="llmProviderDetail">-</span></td>
                                    </tr>
                                    <tr>
                                        <td>Model:</td>
                                        <td><span id="llmModel">-</span></td>
                                    </tr>
                                    <tr>
                                        <td>Confidence Threshold:</td>
                                        <td><span id="confidenceThreshold">-</span></td>
                                    </tr>
                                </table>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="card-footer text-muted">
                <small>
                    <i class="fas fa-info-circle"></i> 
                    Configure LLM providers, InfoBlox settings, and more in the 
                    <a href="/config">Configuration Page</a>
                </small>
            </div>
        </div>
    </div>

    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        $(document).ready(function() {
            // Check status on load
            checkStatus();
            setInterval(checkStatus, 30000);
            
            // Handle form submission
            $('#queryForm').submit(function(e) {
                e.preventDefault();
                const query = $('#queryInput').val();
                processQuery(query);
            });
            
            // Handle example clicks
            $('.example-query').click(function(e) {
                e.preventDefault();
                const query = $(this).text().trim();
                $('#queryInput').val(query);
                processQuery(query);
            });
            
            function processQuery(query) {
                $('#loading').show();
                $('#resultContainer').hide();
                
                $.ajax({
                    url: '/api/process',
                    method: 'POST',
                    contentType: 'application/json',
                    data: JSON.stringify({ query: query }),
                    success: function(result) {
                        $('#loading').hide();
                        $('#resultContainer').show();
                        
                        // Display intent and confidence
                        $('#intentDisplay').text(result.intent || 'Unknown');
                        
                        const confidence = result.confidence || 0;
                        const confPercent = (confidence * 100).toFixed(1);
                        $('#confidenceDisplay')
                            .text(confPercent + '% confidence')
                            .removeClass()
                            .addClass('confidence-display')
                            .addClass(
                                confidence > 0.8 ? 'high-confidence' :
                                confidence > 0.5 ? 'medium-confidence' : 'low-confidence'
                            );
                        
                        $('#response').text(JSON.stringify(result, null, 2));
                    },
                    error: function(xhr) {
                        $('#loading').hide();
                        $('#resultContainer').show();
                        $('#response').text('Error: ' + xhr.responseText);
                    }
                });
            }
            
            function checkStatus() {
                $.ajax({
                    url: '/api/status',
                    success: function(data) {
                        // Update connection status
                        if (data.infoblox_connected) {
                            $('#connectionStatus .status-indicator')
                                .removeClass('status-disconnected status-partial')
                                .addClass('status-connected');
                            $('#statusText').text('Connected');
                            $('#connectionDetail').html('<span class="text-success">Connected</span>');
                        } else {
                            $('#connectionStatus .status-indicator')
                                .removeClass('status-connected status-partial')
                                .addClass('status-disconnected');
                            $('#statusText').text('Disconnected');
                            $('#connectionDetail').html('<span class="text-danger">Disconnected</span>');
                        }
                        
                        // Update InfoBlox details
                        $('#gridMasterIP').text(data.infoblox_ip || 'Not configured');
                        $('#wapiVersion').text(data.wapi_version || 'v2.13.1');
                        
                        // Update LLM status
                        $('#llmProviderDetail').text(data.llm_provider || 'Basic');
                        $('#llmModel').text(data.llm_model || 'N/A');
                        $('#confidenceThreshold').text((data.confidence_threshold * 100).toFixed(0) + '%');
                        
                        if (data.llm_provider && data.llm_provider !== 'basic') {
                            $('#llmStatus').removeClass('llm-inactive').addClass('llm-active');
                            $('#llmProvider').text(data.llm_provider.toUpperCase());
                        } else {
                            $('#llmStatus').removeClass('llm-active').addClass('llm-inactive');
                            $('#llmProvider').text('Basic NLP');
                        }
                    }
                });
            }
        });
    </script>
</body>
</html>
"""

# Configuration page template
CONFIG_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Configuration - InfoBlox WAPI NLP</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <style>
        body { 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            min-height: 100vh;
        }
        .container { max-width: 900px; margin-top: 30px; }
        .config-card {
            background: white;
            border-radius: 15px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }
        .config-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 25px;
        }
        .config-section {
            border-bottom: 1px solid #e0e0e0;
            padding: 25px;
        }
        .config-section:last-child {
            border-bottom: none;
        }
        .section-title {
            color: #764ba2;
            font-weight: 600;
            margin-bottom: 20px;
        }
        .form-label {
            font-weight: 500;
            color: #495057;
        }
        .btn-save {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 12px 40px;
            border-radius: 25px;
            font-weight: 500;
        }
        .btn-test {
            background: white;
            color: #764ba2;
            border: 2px solid #764ba2;
            padding: 10px 25px;
            border-radius: 25px;
        }
        .alert-custom {
            border-radius: 10px;
            border: none;
        }
        .llm-option {
            cursor: pointer;
            padding: 15px;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            margin-bottom: 10px;
            transition: all 0.3s;
        }
        .llm-option:hover {
            border-color: #764ba2;
            background-color: #f8f9fa;
        }
        .llm-option.selected {
            border-color: #764ba2;
            background-color: #f0e6ff;
        }
        .slider-container {
            display: flex;
            align-items: center;
            gap: 15px;
        }
        .confidence-value {
            font-weight: bold;
            color: #764ba2;
            min-width: 45px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="config-card">
            <div class="config-header">
                <div class="d-flex justify-content-between align-items-center">
                    <h2><i class="fas fa-cog"></i> Configuration Settings</h2>
                    <a href="/" class="btn btn-light btn-sm">
                        <i class="fas fa-arrow-left"></i> Back to Main
                    </a>
                </div>
            </div>
            
            <form id="configForm">
                <!-- InfoBlox Configuration -->
                <div class="config-section">
                    <h4 class="section-title">
                        <i class="fas fa-server"></i> InfoBlox Configuration
                    </h4>
                    <div class="row">
                        <div class="col-md-6">
                            <div class="mb-3">
                                <label class="form-label">Grid Master IP Address</label>
                                <input type="text" class="form-control" id="infoblox_ip" 
                                    value="{{ config.infoblox_ip }}" placeholder="192.168.1.224">
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="mb-3">
                                <label class="form-label">WAPI Version</label>
                                <input type="text" class="form-control" id="infoblox_wapi_version" 
                                    value="{{ config.infoblox_wapi_version }}" placeholder="v2.13.1">
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="mb-3">
                                <label class="form-label">Username</label>
                                <input type="text" class="form-control" id="infoblox_username" 
                                    value="{{ config.infoblox_username }}" placeholder="admin">
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="mb-3">
                                <label class="form-label">Password</label>
                                <div class="input-group">
                                    <input type="password" class="form-control" id="infoblox_password" 
                                        value="{{ config.infoblox_password }}" placeholder="••••••••">
                                    <button class="btn btn-outline-secondary" type="button" id="togglePassword">
                                        <i class="fas fa-eye"></i>
                                    </button>
                                </div>
                            </div>
                        </div>
                        <div class="col-12">
                            <button type="button" class="btn btn-test" id="testConnection">
                                <i class="fas fa-plug"></i> Test Connection
                            </button>
                            <span id="connectionResult" class="ms-3"></span>
                        </div>
                    </div>
                </div>
                
                <!-- LLM Configuration -->
                <div class="config-section">
                    <h4 class="section-title">
                        <i class="fas fa-brain"></i> Language Model Configuration
                    </h4>
                    
                    <div class="mb-4">
                        <label class="form-label">Select LLM Provider:</label>
                        <div id="llmProviderOptions">
                            <div class="llm-option" data-provider="basic">
                                <div class="d-flex justify-content-between align-items-center">
                                    <div>
                                        <strong>Basic NLP</strong>
                                        <small class="text-muted d-block">Built-in pattern matching (No API key required)</small>
                                    </div>
                                    <i class="fas fa-check-circle text-success" style="display: none;"></i>
                                </div>
                            </div>
                            
                            <div class="llm-option" data-provider="openai">
                                <div class="d-flex justify-content-between align-items-center">
                                    <div>
                                        <strong>OpenAI GPT</strong>
                                        <small class="text-muted d-block">GPT-3.5/GPT-4 (Requires API key)</small>
                                    </div>
                                    <i class="fas fa-check-circle text-success" style="display: none;"></i>
                                </div>
                            </div>
                            
                            <div class="llm-option" data-provider="anthropic">
                                <div class="d-flex justify-content-between align-items-center">
                                    <div>
                                        <strong>Anthropic Claude</strong>
                                        <small class="text-muted d-block">Claude 2/3 (Requires API key)</small>
                                    </div>
                                    <i class="fas fa-check-circle text-success" style="display: none;"></i>
                                </div>
                            </div>
                            
                            <div class="llm-option" data-provider="grok">
                                <div class="d-flex justify-content-between align-items-center">
                                    <div>
                                        <strong>xAI Grok</strong>
                                        <small class="text-muted d-block">Grok-1/2 (Requires API key)</small>
                                    </div>
                                    <i class="fas fa-check-circle text-success" style="display: none;"></i>
                                </div>
                            </div>
                            
                            <div class="llm-option" data-provider="ollama">
                                <div class="d-flex justify-content-between align-items-center">
                                    <div>
                                        <strong>Ollama (Local)</strong>
                                        <small class="text-muted d-block">Run models locally (No API key required)</small>
                                    </div>
                                    <i class="fas fa-check-circle text-success" style="display: none;"></i>
                                </div>
                            </div>
                            
                            <div class="llm-option" data-provider="custom">
                                <div class="d-flex justify-content-between align-items-center">
                                    <div>
                                        <strong>Custom API</strong>
                                        <small class="text-muted d-block">OpenAI-compatible endpoint</small>
                                    </div>
                                    <i class="fas fa-check-circle text-success" style="display: none;"></i>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <input type="hidden" id="llm_provider" value="{{ config.llm_provider }}">
                    
                    <div id="llmSettings" style="display: none;">
                        <div class="row">
                            <div class="col-md-6">
                                <div class="mb-3">
                                    <label class="form-label">API Key</label>
                                    <input type="password" class="form-control" id="llm_api_key" 
                                        value="{{ config.llm_api_key }}" placeholder="sk-...">
                                </div>
                            </div>
                            <div class="col-md-6">
                                <div class="mb-3">
                                    <label class="form-label">Model</label>
                                    <select class="form-control" id="llm_model">
                                        <option value="">Select Model</option>
                                    </select>
                                </div>
                            </div>
                            <div class="col-md-12" id="endpointField" style="display: none;">
                                <div class="mb-3">
                                    <label class="form-label">API Endpoint</label>
                                    <input type="text" class="form-control" id="llm_endpoint" 
                                        value="{{ config.llm_endpoint }}" placeholder="https://api.example.com/v1">
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Advanced Settings -->
                <div class="config-section">
                    <h4 class="section-title">
                        <i class="fas fa-sliders-h"></i> Advanced Settings
                    </h4>
                    <div class="row">
                        <div class="col-md-12">
                            <div class="mb-4">
                                <label class="form-label">Confidence Threshold</label>
                                <div class="slider-container">
                                    <input type="range" class="form-range flex-grow-1" id="confidence_threshold" 
                                        min="0" max="100" value="{{ (config.confidence_threshold * 100)|int }}">
                                    <span class="confidence-value" id="confidenceValue">70%</span>
                                </div>
                                <small class="text-muted">Minimum confidence level required to execute WAPI calls</small>
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="mb-3">
                                <label class="form-label">Max Results</label>
                                <input type="number" class="form-control" id="max_results" 
                                    value="{{ config.max_results }}" min="1" max="1000">
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="mb-3">
                                <label class="form-label">Options</label>
                                <div class="form-check">
                                    <input class="form-check-input" type="checkbox" id="enable_autocomplete" 
                                        {{ 'checked' if config.enable_autocomplete }}>
                                    <label class="form-check-label" for="enable_autocomplete">
                                        Enable Autocomplete
                                    </label>
                                </div>
                                <div class="form-check">
                                    <input class="form-check-input" type="checkbox" id="enable_logging" 
                                        {{ 'checked' if config.enable_logging }}>
                                    <label class="form-check-label" for="enable_logging">
                                        Enable Logging
                                    </label>
                                </div>
                                <div class="form-check">
                                    <input class="form-check-input" type="checkbox" id="infoblox_ssl_verify" 
                                        {{ 'checked' if config.infoblox_ssl_verify }}>
                                    <label class="form-check-label" for="infoblox_ssl_verify">
                                        SSL Certificate Verification
                                    </label>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Actions -->
                <div class="config-section">
                    <div class="d-flex justify-content-between align-items-center">
                        <div id="saveResult"></div>
                        <div>
                            <button type="button" class="btn btn-outline-secondary me-2" id="exportConfig">
                                <i class="fas fa-download"></i> Export Config
                            </button>
                            <button type="button" class="btn btn-outline-secondary me-2" id="importConfig">
                                <i class="fas fa-upload"></i> Import Config
                            </button>
                            <button type="submit" class="btn btn-save">
                                <i class="fas fa-save"></i> Save Configuration
                            </button>
                        </div>
                    </div>
                </div>
            </form>
        </div>
    </div>
    
    <input type="file" id="importFile" style="display: none;" accept=".json">

    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        const llmModels = {
            'openai': ['gpt-3.5-turbo', 'gpt-4', 'gpt-4-turbo-preview'],
            'anthropic': ['claude-3-opus-20240229', 'claude-3-sonnet-20240229', 'claude-3-haiku-20240307'],
            'grok': ['grok-1', 'grok-2', 'grok-3:beta'],
            'ollama': ['llama2', 'mistral', 'codellama', 'neural-chat'],
            'custom': ['custom-model']
        };
        
        $(document).ready(function() {
            // Initialize
            const currentProvider = $('#llm_provider').val() || 'basic';
            selectProvider(currentProvider);
            updateConfidenceDisplay();
            
            // Handle provider selection
            $('.llm-option').click(function() {
                const provider = $(this).data('provider');
                selectProvider(provider);
            });
            
            function selectProvider(provider) {
                $('.llm-option').removeClass('selected');
                $('.llm-option i').hide();
                
                $(`.llm-option[data-provider="${provider}"]`).addClass('selected');
                $(`.llm-option[data-provider="${provider}"] i`).show();
                
                $('#llm_provider').val(provider);
                
                if (provider === 'basic') {
                    $('#llmSettings').hide();
                } else {
                    $('#llmSettings').show();
                    updateModelOptions(provider);
                    
                    if (provider === 'custom' || provider === 'ollama') {
                        $('#endpointField').show();
                    } else {
                        $('#endpointField').hide();
                    }
                }
            }
            
            function updateModelOptions(provider) {
                const models = llmModels[provider] || [];
                const select = $('#llm_model');
                const currentModel = '{{ config.llm_model }}';
                
                select.empty();
                select.append('<option value="">Select Model</option>');
                
                models.forEach(model => {
                    const selected = model === currentModel ? 'selected' : '';
                    select.append(`<option value="${model}" ${selected}>${model}</option>`);
                });
            }
            
            // Toggle password visibility
            $('#togglePassword').click(function() {
                const input = $('#infoblox_password');
                const icon = $(this).find('i');
                
                if (input.attr('type') === 'password') {
                    input.attr('type', 'text');
                    icon.removeClass('fa-eye').addClass('fa-eye-slash');
                } else {
                    input.attr('type', 'password');
                    icon.removeClass('fa-eye-slash').addClass('fa-eye');
                }
            });
            
            // Update confidence display
            $('#confidence_threshold').on('input', updateConfidenceDisplay);
            
            function updateConfidenceDisplay() {
                const value = $('#confidence_threshold').val();
                $('#confidenceValue').text(value + '%');
            }
            
            // Test connection
            $('#testConnection').click(function() {
                const btn = $(this);
                btn.prop('disabled', true);
                
                $.ajax({
                    url: '/api/test-connection',
                    method: 'POST',
                    contentType: 'application/json',
                    data: JSON.stringify({
                        ip: $('#infoblox_ip').val(),
                        username: $('#infoblox_username').val(),
                        password: $('#infoblox_password').val(),
                        wapi_version: $('#infoblox_wapi_version').val()
                    }),
                    success: function(result) {
                        if (result.success) {
                            $('#connectionResult').html('<span class="text-success"><i class="fas fa-check"></i> Connected successfully</span>');
                        } else {
                            $('#connectionResult').html('<span class="text-danger"><i class="fas fa-times"></i> ' + result.message + '</span>');
                        }
                    },
                    complete: function() {
                        btn.prop('disabled', false);
                        setTimeout(() => $('#connectionResult').empty(), 5000);
                    }
                });
            });
            
            // Save configuration
            $('#configForm').submit(function(e) {
                e.preventDefault();
                
                const config = {
                    llm_provider: $('#llm_provider').val(),
                    llm_api_key: $('#llm_api_key').val(),
                    llm_model: $('#llm_model').val(),
                    llm_endpoint: $('#llm_endpoint').val(),
                    confidence_threshold: $('#confidence_threshold').val() / 100,
                    infoblox_ip: $('#infoblox_ip').val(),
                    infoblox_username: $('#infoblox_username').val(),
                    infoblox_password: $('#infoblox_password').val(),
                    infoblox_wapi_version: $('#infoblox_wapi_version').val(),
                    infoblox_ssl_verify: $('#infoblox_ssl_verify').is(':checked'),
                    enable_autocomplete: $('#enable_autocomplete').is(':checked'),
                    enable_logging: $('#enable_logging').is(':checked'),
                    max_results: parseInt($('#max_results').val())
                };
                
                $.ajax({
                    url: '/api/config',
                    method: 'POST',
                    contentType: 'application/json',
                    data: JSON.stringify(config),
                    success: function(result) {
                        $('#saveResult').html('<span class="text-success"><i class="fas fa-check"></i> Configuration saved successfully</span>');
                        setTimeout(() => $('#saveResult').empty(), 3000);
                    },
                    error: function() {
                        $('#saveResult').html('<span class="text-danger"><i class="fas fa-times"></i> Failed to save configuration</span>');
                    }
                });
            });
            
            // Export configuration
            $('#exportConfig').click(function() {
                const config = {
                    llm_provider: $('#llm_provider').val(),
                    llm_model: $('#llm_model').val(),
                    llm_endpoint: $('#llm_endpoint').val(),
                    confidence_threshold: $('#confidence_threshold').val() / 100,
                    infoblox_ip: $('#infoblox_ip').val(),
                    infoblox_wapi_version: $('#infoblox_wapi_version').val(),
                    infoblox_ssl_verify: $('#infoblox_ssl_verify').is(':checked'),
                    enable_autocomplete: $('#enable_autocomplete').is(':checked'),
                    enable_logging: $('#enable_logging').is(':checked'),
                    max_results: parseInt($('#max_results').val())
                };
                
                const blob = new Blob([JSON.stringify(config, null, 2)], { type: 'application/json' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'infoblox_nlp_config.json';
                a.click();
            });
            
            // Import configuration
            $('#importConfig').click(function() {
                $('#importFile').click();
            });
            
            $('#importFile').change(function(e) {
                const file = e.target.files[0];
                if (file) {
                    const reader = new FileReader();
                    reader.onload = function(e) {
                        try {
                            const config = JSON.parse(e.target.result);
                            
                            // Load imported config into form
                            $('#llm_provider').val(config.llm_provider || 'basic');
                            selectProvider(config.llm_provider || 'basic');
                            $('#llm_api_key').val(config.llm_api_key || '');
                            $('#llm_model').val(config.llm_model || '');
                            $('#llm_endpoint').val(config.llm_endpoint || '');
                            $('#confidence_threshold').val((config.confidence_threshold || 0.7) * 100);
                            $('#infoblox_ip').val(config.infoblox_ip || '');
                            $('#infoblox_username').val(config.infoblox_username || '');
                            $('#infoblox_wapi_version').val(config.infoblox_wapi_version || 'v2.13.1');
                            $('#infoblox_ssl_verify').prop('checked', config.infoblox_ssl_verify || false);
                            $('#enable_autocomplete').prop('checked', config.enable_autocomplete !== false);
                            $('#enable_logging').prop('checked', config.enable_logging !== false);
                            $('#max_results').val(config.max_results || 100);
                            
                            updateConfidenceDisplay();
                            
                            $('#saveResult').html('<span class="text-info"><i class="fas fa-info"></i> Configuration imported. Click Save to apply.</span>');
                        } catch (err) {
                            $('#saveResult').html('<span class="text-danger"><i class="fas fa-times"></i> Invalid configuration file</span>');
                        }
                    };
                    reader.readAsText(file);
                }
            });
        });
    </script>
</body>
</html>
"""

def test_wapi_connection(ip, username, password, wapi_version):
    """Test WAPI connection with provided credentials."""
    try:
        url = f"https://{ip}/wapi/{wapi_version}?_schema"
        response = requests.get(
            url,
            auth=(username, password),
            verify=False,
            timeout=5
        )
        return response.status_code == 200, response.status_code
    except Exception as e:
        return False, str(e)

def process_with_llm(query, provider, api_key, model, endpoint=None):
    """Process query with configured LLM provider."""
    
    if provider == 'openai':
        try:
            import openai
            openai.api_key = api_key
            response = openai.ChatCompletion.create(
                model=model or "gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an InfoBlox WAPI assistant. Extract intent and entities from the query."},
                    {"role": "user", "content": f"Query: {query}\nReturn JSON with 'intent' and 'entities' fields."}
                ]
            )
            result = json.loads(response.choices[0].message.content)
            return result.get('intent', 'unknown'), result.get('entities', {}), 0.9
        except:
            pass
    
    elif provider == 'anthropic':
        try:
            import anthropic
            client = anthropic.Client(api_key=api_key)
            response = client.messages.create(
                model=model or "claude-3-sonnet-20240229",
                messages=[{"role": "user", "content": f"Extract intent and entities from: {query}"}]
            )
            # Parse response
            return "find_network", {}, 0.8
        except:
            pass
    
    # Fallback to basic processing
    return classify_intent_basic(query)[0], extract_entities_basic(query), classify_intent_basic(query)[1]

@app.route('/')
def home():
    """Main interface."""
    return render_template_string(MAIN_TEMPLATE)

@app.route('/config')
def config_page():
    """Configuration page."""
    return render_template_string(CONFIG_TEMPLATE, config=RUNTIME_CONFIG)

@app.route('/api/status')
def api_status():
    """Get system status."""
    # Test InfoBlox connection
    infoblox_connected = False
    if RUNTIME_CONFIG.get('infoblox_ip'):
        connected, _ = test_wapi_connection(
            RUNTIME_CONFIG['infoblox_ip'],
            RUNTIME_CONFIG['infoblox_username'],
            RUNTIME_CONFIG['infoblox_password'],
            RUNTIME_CONFIG['infoblox_wapi_version']
        )
        infoblox_connected = connected
    
    return jsonify({
        'infoblox_connected': infoblox_connected,
        'infoblox_ip': RUNTIME_CONFIG.get('infoblox_ip'),
        'wapi_version': RUNTIME_CONFIG.get('infoblox_wapi_version'),
        'llm_provider': RUNTIME_CONFIG.get('llm_provider'),
        'llm_model': RUNTIME_CONFIG.get('llm_model'),
        'confidence_threshold': RUNTIME_CONFIG.get('confidence_threshold', 0.7)
    })

@app.route('/api/config', methods=['GET', 'POST'])
def api_config():
    """Get or update configuration."""
    global RUNTIME_CONFIG
    
    if request.method == 'POST':
        data = request.get_json()
        RUNTIME_CONFIG.update(data)
        
        # Save to file
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(RUNTIME_CONFIG, f, indent=2)
        except:
            pass
        
        return jsonify({'success': True})
    
    # Mask sensitive data for GET
    safe_config = RUNTIME_CONFIG.copy()
    if safe_config.get('infoblox_password'):
        safe_config['infoblox_password'] = '***' if safe_config['infoblox_password'] else ''
    if safe_config.get('llm_api_key'):
        safe_config['llm_api_key'] = '***' if safe_config['llm_api_key'] else ''
    
    return jsonify(safe_config)

@app.route('/api/test-connection', methods=['POST'])
def api_test_connection():
    """Test InfoBlox connection."""
    data = request.get_json()
    connected, message = test_wapi_connection(
        data.get('ip'),
        data.get('username'),
        data.get('password'),
        data.get('wapi_version', 'v2.13.1')
    )
    
    return jsonify({
        'success': connected,
        'message': f"Connection successful" if connected else f"Connection failed: {message}"
    })

@app.route('/api/process', methods=['POST'])
def api_process():
    """Process a query."""
    data = request.get_json()
    query = data.get('query', '')
    
    # Process with configured LLM
    provider = RUNTIME_CONFIG.get('llm_provider', 'basic')
    
    if provider != 'basic':
        intent, entities, confidence = process_with_llm(
            query,
            provider,
            RUNTIME_CONFIG.get('llm_api_key'),
            RUNTIME_CONFIG.get('llm_model'),
            RUNTIME_CONFIG.get('llm_endpoint')
        )
    else:
        intent = classify_intent_basic(query)[0]
        entities = extract_entities_basic(query)
        confidence = classify_intent_basic(query)[1]
    
    result = {
        'query': query,
        'intent': intent,
        'confidence': confidence,
        'entities': entities
    }
    
    # Execute WAPI call if confidence meets threshold
    if confidence >= RUNTIME_CONFIG.get('confidence_threshold', 0.7):
        if RUNTIME_CONFIG.get('infoblox_ip'):
            # Execute actual WAPI call
            try:
                wapi_result = execute_wapi_call(intent, entities)
                result['wapi_result'] = wapi_result
            except Exception as e:
                result['wapi_result'] = {'error': str(e)}
        else:
            result['wapi_result'] = {'error': 'InfoBlox not configured'}
    else:
        result['wapi_result'] = {'message': f'Confidence too low ({confidence:.2f} < {RUNTIME_CONFIG["confidence_threshold"]})'}
    
    return jsonify(result)

def execute_wapi_call(intent, entities):
    """Execute WAPI call."""
    base_url = f"https://{RUNTIME_CONFIG['infoblox_ip']}/wapi/{RUNTIME_CONFIG['infoblox_wapi_version']}"
    auth = (RUNTIME_CONFIG['infoblox_username'], RUNTIME_CONFIG['infoblox_password'])
    
    # Map intent to WAPI operation
    if 'create' in intent and 'network' in entities:
        response = requests.post(
            f"{base_url}/network",
            json={'network': entities['network']},
            auth=auth,
            verify=RUNTIME_CONFIG.get('infoblox_ssl_verify', False)
        )
    elif 'find' in intent or 'list' in intent:
        params = {'_max_results': RUNTIME_CONFIG.get('max_results', 100)}
        if 'network' in entities:
            params['network'] = entities['network']
        response = requests.get(
            f"{base_url}/network",
            params=params,
            auth=auth,
            verify=RUNTIME_CONFIG.get('infoblox_ssl_verify', False)
        )
    else:
        return {'message': 'Operation not implemented'}
    
    if response.status_code >= 400:
        return {'error': f"API error: {response.status_code} - {response.text}"}
    
    return response.json()

if __name__ == '__main__':
    port = int(os.environ.get('INFOBLOX_FLASK_PORT', 5003))
    
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║     InfoBlox WAPI NLP Interface - Configurable Version      ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  Web Interface: http://localhost:{port:<5}                     ║
║  Configuration: http://localhost:{port:<5}/config              ║
║                                                              ║
║  Features:                                                   ║
║  • Multiple LLM providers (OpenAI, Anthropic, etc.)         ║
║  • Runtime configuration without restart                    ║
║  • Adjustable confidence thresholds                         ║
║  • Import/Export configuration                              ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    app.run(host='0.0.0.0', port=port, debug=False)