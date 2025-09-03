#!/usr/bin/env python3
"""
Secure Flask web application for InfoBlox WAPI NLP interface.
"""

from flask import Flask, request, jsonify, render_template_string
import sys
import os
import logging

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import get_config, ConfigurationError
from wapi_nlp_secure import process_query, execute_wapi_call, test_connection

# Initialize configuration
try:
    config = get_config()
except ConfigurationError as e:
    print(f"Configuration error: {e}")
    sys.exit(1)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# HTML template for the web interface
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>InfoBlox WAPI NLP Interface</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://code.jquery.com/ui/1.12.1/themes/base/jquery-ui.css" rel="stylesheet">
    <style>
        body { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; }
        .container { max-width: 900px; margin-top: 50px; }
        .card { background: rgba(255,255,255,0.95); backdrop-filter: blur(10px); border: none; box-shadow: 0 10px 40px rgba(0,0,0,0.2); }
        .card-header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; }
        #response { white-space: pre-wrap; font-family: 'Courier New', monospace; background-color: #f8f9fa; padding: 15px; border-radius: 5px; max-height: 400px; overflow-y: auto; }
        .status-indicator { width: 10px; height: 10px; border-radius: 50%; display: inline-block; margin-right: 5px; }
        .status-connected { background-color: #28a745; }
        .status-disconnected { background-color: #dc3545; }
        .example-queries { background-color: #f0f0f0; padding: 10px; border-radius: 5px; margin-top: 10px; }
        .example-query { cursor: pointer; color: #007bff; text-decoration: underline; }
        .example-query:hover { color: #0056b3; }
        .ui-autocomplete { max-height: 200px; overflow-y: auto; background: white; border: 1px solid #ccc; }
    </style>
</head>
<body>
    <div class="container">
        <h1 class="text-center text-white mb-4">
            <i class="bi bi-cpu"></i> InfoBlox WAPI NLP Interface
        </h1>
        <div class="card">
            <div class="card-header">
                <h4 class="mb-0">
                    Natural Language Query Processor
                    <span id="connectionStatus" class="float-end">
                        <span class="status-indicator status-disconnected"></span>
                        <span id="statusText">Checking...</span>
                    </span>
                </h4>
            </div>
            <div class="card-body">
                <form id="queryForm">
                    <div class="mb-3">
                        <label for="queryInput" class="form-label">Enter your query:</label>
                        <div class="input-group">
                            <input type="text" class="form-control" id="queryInput" 
                                placeholder="e.g., Create a network with CIDR 10.0.0.0/24">
                            <button type="submit" class="btn btn-primary">
                                <i class="bi bi-send"></i> Process
                            </button>
                        </div>
                    </div>
                </form>
                
                <div class="example-queries">
                    <strong>Example queries:</strong><br>
                    <span class="example-query">Create a network with CIDR 10.0.0.0/24 and comment TestNetwork</span><br>
                    <span class="example-query">List all networks</span><br>
                    <span class="example-query">Find network 192.168.1.0/24</span><br>
                    <span class="example-query">Get next available IP from network 10.0.0.0/24</span><br>
                    <span class="example-query">Create host record for server1.example.com with IP 192.168.0.10</span>
                </div>
                
                <div id="loading" class="text-center mt-3" style="display: none;">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Processing...</span>
                    </div>
                </div>
                
                <div id="response" class="mt-3" style="display: none;"></div>
            </div>
            <div class="card-footer text-muted">
                <small>
                    Grid Master: {{ grid_master }} | 
                    WAPI Version: {{ wapi_version }} |
                    <span id="configStatus">Configuration: Loaded</span>
                </small>
            </div>
        </div>
    </div>

    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <script src="https://code.jquery.com/ui/1.12.1/jquery-ui.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        $(document).ready(function() {
            // Check connection status
            checkConnection();
            setInterval(checkConnection, 30000); // Check every 30 seconds
            
            // Setup autocomplete
            $('#queryInput').autocomplete({
                source: function(request, response) {
                    $.ajax({
                        url: '/api/suggestions',
                        data: { query: request.term },
                        dataType: 'json',
                        success: function(data) {
                            response(data);
                        },
                        error: function() {
                            response([]);
                        }
                    });
                },
                minLength: 2,
                delay: 300
            });
            
            // Handle example query clicks
            $('.example-query').click(function() {
                $('#queryInput').val($(this).text());
                $('#queryForm').submit();
            });
            
            // Handle form submission
            $('#queryForm').submit(function(e) {
                e.preventDefault();
                const query = $('#queryInput').val();
                
                $('#loading').show();
                $('#response').hide();
                
                $.ajax({
                    url: '/api/process',
                    method: 'POST',
                    contentType: 'application/json',
                    data: JSON.stringify({ query: query }),
                    success: function(result) {
                        $('#loading').hide();
                        $('#response').show();
                        $('#response').text(JSON.stringify(result, null, 2));
                        
                        // Highlight based on result
                        if (result.error) {
                            $('#response').addClass('border-danger');
                        } else {
                            $('#response').removeClass('border-danger');
                        }
                    },
                    error: function(xhr) {
                        $('#loading').hide();
                        $('#response').show();
                        $('#response').text('Error: ' + xhr.responseText);
                        $('#response').addClass('border-danger');
                    }
                });
            });
        });
        
        function checkConnection() {
            $.ajax({
                url: '/api/status',
                success: function(data) {
                    if (data.connected) {
                        $('#connectionStatus .status-indicator')
                            .removeClass('status-disconnected')
                            .addClass('status-connected');
                        $('#statusText').text('Connected');
                    } else {
                        $('#connectionStatus .status-indicator')
                            .removeClass('status-connected')
                            .addClass('status-disconnected');
                        $('#statusText').text('Disconnected');
                    }
                },
                error: function() {
                    $('#connectionStatus .status-indicator')
                        .removeClass('status-connected')
                        .addClass('status-disconnected');
                    $('#statusText').text('Error');
                }
            });
        }
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    """Render the home page."""
    return render_template_string(
        HTML_TEMPLATE,
        grid_master=config.get('GRID_MASTER_IP'),
        wapi_version=config.get('WAPI_VERSION')
    )

@app.route('/api/status')
def api_status():
    """Check connection status."""
    connected, message = test_connection()
    return jsonify({
        'connected': connected,
        'message': message,
        'grid_master': config.get('GRID_MASTER_IP'),
        'wapi_version': config.get('WAPI_VERSION')
    })

@app.route('/api/process', methods=['POST'])
def api_process():
    """Process a natural language query."""
    try:
        data = request.get_json()
        if not data or 'query' not in data:
            return jsonify({'error': 'No query provided'}), 400
        
        query = data['query']
        logger.info(f"Processing query: {query}")
        
        # Process the query
        result = process_query(query)
        
        # Execute WAPI call if intent is clear
        if result['confidence'] > 0.5:
            wapi_result = execute_wapi_call(result['intent'], result['entities'])
            result['wapi_result'] = wapi_result
        else:
            result['wapi_result'] = {'message': 'Low confidence - no action taken'}
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/suggestions')
def api_suggestions():
    """Get query suggestions for autocomplete."""
    query = request.args.get('query', '')
    
    suggestions = [
        "Create a network with CIDR",
        "List all networks",
        "Find network",
        "Delete network",
        "Create host record",
        "Update A record",
        "Get next available IP",
        "Show network utilization",
        "Create DNS zone",
        "Find all host records"
    ]
    
    # Filter suggestions based on query
    filtered = [s for s in suggestions if query.lower() in s.lower()]
    
    return jsonify(filtered[:10])

@app.route('/api/config')
def api_config():
    """Get current configuration (masked)."""
    return jsonify(config.to_dict())

@app.route('/health')
def health():
    """Health check endpoint."""
    connected, message = test_connection()
    return jsonify({
        'status': 'healthy' if connected else 'unhealthy',
        'message': message
    }), 200 if connected else 503

if __name__ == '__main__':
    port = config.get('FLASK_PORT', 5000)
    debug = config.get('DEBUG_MODE', False)
    
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║     InfoBlox WAPI NLP Interface - Secure Version            ║
╠══════════════════════════════════════════════════════════════╣
║  Configuration:                                              ║
║    Grid Master: {config.get('GRID_MASTER_IP'):20}         ║
║    WAPI Version: {config.get('WAPI_VERSION'):20}        ║
║    Flask Port: {port:20}                  ║
║                                                              ║
║  Starting Flask server...                                    ║
║    Web Interface: http://localhost:{port:5}                     ║
║    API Endpoint: http://localhost:{port:5}/api/process          ║
║    Health Check: http://localhost:{port:5}/health               ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    app.run(host='0.0.0.0', port=port, debug=debug)