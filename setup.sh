#!/bin/bash
# setup.sh: Sets up Infoblox WAPI, Open WebUI, Flask wrapper with autocomplete for all intents, and Python environment with Grok API and Docker Compose

# Configuration variables
GRID_MASTER_IP="192.168.1.222" # Grid Master IP
USERNAME="admin" # Username
PASSWORD="InfoBlox" # Password
WAPI_VERSION="v2.13.1" # WAPI version
SWAGGER_PORT="8080" # Infoblox Swagger UI port
OPENWEBUI_PORT="3000" # Open WebUI port
FLASK_PORT="5000" # Flask API port
GROK_API_KEY="your_grok_api_key" # Replace with your Grok API key

# Directories and files
WORK_DIR="$HOME/infoblox-wapi-nlp"
SCHEMA_DIR="$WORK_DIR/schemas"
PYTHON_ENV="$WORK_DIR/venv"
PYTHON_SCRIPT="$WORK_DIR/wapi_nlp.py"
FLASK_SCRIPT="$WORK_DIR/app.py"
HTML_DIR="$WORK_DIR/templates"
HTML_FILE="$HTML_DIR/index.html"
DOCKER_COMPOSE_FILE="$WORK_DIR/docker-compose.yml"
LOG_FILE="$WORK_DIR/wapi_nlp.log"
TRAINING_DATA_FILE="$WORK_DIR/training_data.csv"
GROK_CONFIG_FILE="$WORK_DIR/grok_config.json"
QUICK_START_GUIDE="$WORK_DIR/QUICK_START_GUIDE.md"

# Check prerequisites
echo "Checking prerequisites..."
for cmd in docker python3 pip3 jq; do
if ! command -v $cmd &>/dev/null; then
echo "Error: $cmd is not installed. Please install it." >&2
exit 1
fi
done

# Check if Docker is running
if ! docker info --format '{{.ServerVersion}}' &>/dev/null; then
echo "Error: Docker is not running. Please start Docker." >&2
exit 1
fi

# Create directories
echo "Creating directories..."
mkdir -p "$WORK_DIR" "$SCHEMA_DIR" "$HTML_DIR"
if [ ! -d "$WORK_DIR" ] || [ ! -d "$SCHEMA_DIR" ] || [ ! -d "$HTML_DIR" ]; then
echo "Error: Failed to create directories." >&2
exit 1
fi

# Create Grok config file
echo "Creating Grok API configuration..."
echo "{\"GROK_API_KEY\": \"$GROK_API_KEY\"}" > "$GROK_CONFIG_FILE"

# Create training data CSV
echo "Creating training data CSV..."
echo "query,intent,entities,api_result" > "$TRAINING_DATA_FILE"

# Create Docker Compose file
echo "Creating docker-compose.yml..."
cat << EOF > "$DOCKER_COMPOSE_FILE"
version: '3.8'
services:
infoblox-swagger:
image: vsethia/infoblox-wapi-swagger:v3
ports:
- "$SWAGGER_PORT:80"
container_name: infoblox-swagger
open-webui:
image: ghcr.io/open-webui/open-webui:main
ports:
- "$OPENWEBUI_PORT:8080"
container_name: open-webui
environment:
- GROK_API_KEY=$GROK_API_KEY
- GROK_API_BASE_URL=https://api.x.ai/v1
EOF
echo "docker-compose.yml created at $DOCKER_COMPOSE_FILE"

# Start Docker Compose services
echo "Starting Docker Compose services..."
docker-compose -f "$DOCKER_COMPOSE_FILE" up -d
if [ $? -ne 0 ]; then
echo "Error: Failed to start Docker Compose services." >&2
exit 1
fi
echo "Swagger UI running at http://localhost:$SWAGGER_PORT/infoblox-swagger-ui/dist/home.php"
echo "Open WebUI running at http://localhost:$OPENWEBUI_PORT"

# Fetch WAPI objects
echo "Fetching WAPI objects..."
SUPPORTED_OBJECTS=$(curl -s -k -u "$USERNAME:$PASSWORD" "https://$GRID_MASTER_IP/wapi/$WAPI_VERSION?_schema" | jq -r '.supported_objects[]')
if [ -z "$SUPPORTED_OBJECTS" ]; then
echo "Error: Failed to fetch WAPI objects." >&2
exit 1
fi

# Fetch schemas
echo "Fetching WAPI schemas..."
for OBJECT in $SUPPORTED_OBJECTS; do
SCHEMA_FILE="$SCHEMA_DIR/${OBJECT//:/_}_schema.json"
echo "Fetching schema for $OBJECT..."
curl -s -k -u "$USERNAME:$PASSWORD" "https://$GRID_MASTER_IP/wapi/$WAPI_VERSION/$OBJECT?_schema&_schema_version=2&_schema_searchable=1" -o "$SCHEMA_FILE"
if [ -f "$SCHEMA_FILE" ]; then
echo "Schema saved: $SCHEMA_FILE"
fi
done

# Set up Python environment
echo "Setting up Python environment..."
python3 -m venv "$PYTHON_ENV"
source "$PYTHON_ENV/bin/activate"
pip3 install requests spacy transformers torch pandas openai flask
if [ $? -ne 0 ]; then
echo "Error: Failed to set up Python environment." >&2
exit 1
fi
python3 -m spacy download en_core_web_sm
if [ $? -ne 0 ]; then
echo "Error: Failed to download spaCy model." >&2
exit 1
fi
echo "Python environment ready"
deactivate

# Create wapi_nlp.py
echo "Creating wapi_nlp.py..."
cat << 'EOF' > "$PYTHON_SCRIPT"
import os
import json
import re
import logging
import requests
import spacy
import pandas as pd
from spacy.language import Language
from spacy.pipeline import EntityRuler
from transformers import pipeline
from openai import OpenAI

# Setup logging
logging.basicConfig(filename='$LOG_FILE', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configuration
GRID_MASTER_IP = '$GRID_MASTER_IP'
WAPI_VERSION = '$WAPI_VERSION'
AUTH = ('$USERNAME', '$PASSWORD')
BASE_URL = f'https://{GRID_MASTER_IP}/wapi/{WAPI_VERSION}'
SCHEMA_DIR = '$SCHEMA_DIR'
TRAINING_DATA_FILE = '$TRAINING_DATA_FILE'
GROK_CONFIG_FILE = '$GROK_CONFIG_FILE'

# Load Grok API key
with open(GROK_CONFIG_FILE) as f:
grok_config = json.load(f)
GROK_API_KEY = grok_config['GROK_API_KEY']
GROK_API_BASE_URL = 'https://api.x.ai/v1'

# Disable SSL warnings
requests.packages.urllib3.disable_warnings()

# Initialize NLP models
nlp = spacy.load('en_core_web_sm')
classifier = pipeline('zero-shot-classification', model='facebook/bart-large-mnli')
grok_client = OpenAI(api_key=GROK_API_KEY, base_url=GROK_API_BASE_URL)

# Add custom entities
def add_custom_entities(nlp):
ruler = nlp.add_pipe('entity_ruler', before='ner')
patterns = [
{'label': 'CIDR', 'pattern': [{'TEXT': {'REGEX': r'(\d{1,3}\.){3}\d{1,3}/\d{1,2}'}}]},
{'label': 'IP', 'pattern': [{'TEXT': {'REGEX': r'(\d{1,3}\.){3}\d{1,3}'}}]},
{'label': 'MAC', 'pattern': [{'TEXT': {'REGEX': r'([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}'}}]},
{'label': 'FQDN', 'pattern': [{'TEXT': {'REGEX': r'[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'}}]},
{'label': 'TTL', 'pattern': [{'TEXT': {'REGEX': r'^\d+$'}, 'POS': 'NUM'}]},
{'label': 'EXTATTR', 'pattern': [{'TEXT': {'REGEX': r'(Owner|Site|Department)'}}]}
]
ruler.add_patterns(patterns)
return nlp

nlp = add_custom_entities(nlp)

# Load schemas and generate intents
def load_schemas():
intents = {
'get_next_available_ip_network': {
'method': 'GET',
'endpoint': '/network',
'searchable_fields': ['network'],
'query_params': '_return_fields=next_available_ip',
'example': 'Get next available IP from network 10.0.0.0/24'
},
'set_extattr_network': {
'method': 'PUT',
'endpoint': '/network/{ref}',
'fields': ['extattrs'],
'example': 'Set extensible attribute Owner to Admin for network 10.0.0.0/24'
},
'find_network_utilization': {
'method': 'GET',
'endpoint': '/network',
'searchable_fields': ['network'],
'query_params': '_return_fields=utilization',
'example': 'Show network 192.168.1.0/24 utilization'
}
}
for schema_file in os.listdir(SCHEMA_DIR):
if schema_file.endswith('_schema.json'):
with open(os.path.join(SCHEMA_DIR, schema_file)) as f:
schema = json.load(f)
object_name = schema_file.replace('_schema.json', '').replace('_', ':')
restrictions = schema.get('restrictions', [])
fields = [f['name'] for f in schema['fields'] if not f.get('is_array')]
searchable_fields = [f['name'] for f in schema['fields'] if f.get('searchable')]
required_fields = [f['name'] for f in schema['fields'] if f.get('required_on_create')]

if 'create' in restrictions:
intents[f'create_{object_name}'] = {
'method': 'POST',
'endpoint': f'/{object_name}',
'fields': fields,
'required_fields': required_fields,
'example': f'Create a {object_name} with required fields'
}
if 'read' in restrictions:
intents[f'find_{object_name}'] = {
'method': 'GET',
'endpoint': f'/{object_name}',
'searchable_fields': searchable_fields,
'example': f'List all {object_name}s'
}
if 'update' in restrictions:
intents[f'update_{object_name}'] = {
'method': 'PUT',
'endpoint': f'/{object_name}/{ref}',
'fields': fields,
'example': f'Update {object_name} with new values'
}
if 'delete' in restrictions:
intents[f'delete_{object_name}'] = {
'method': 'DELETE',
'endpoint': f'/{object_name}/{ref}',
'fields': [],
'example': f'Delete {object_name}'
}
for func in schema.get('supported_functions', []):
intents[f'{func}_{object_name}'] = {
'method': 'POST',
'endpoint': f'/{object_name}/{ref}?_function={func}',
'fields': [],
'example': f'Perform {func} on {object_name}'
}
return intents

dynamic_intents = load_schemas()

# Get suggestions for autocomplete
def get_suggestions(query):
suggestions = []
query_lower = query.lower()
for intent, details in dynamic_intents.items():
if ('list' in query_lower or 'find' in query_lower or 'show' in query_lower or
'create' in query_lower or 'add' in query_lower or
'update' in query_lower or 'modify' in query_lower or
'delete' in query_lower or 'remove' in query_lower or
query_lower in intent.lower()):
suggestions.append({
'label': details.get('example', f'Run {intent}'),
'value': details.get('example', f'Run {intent}')
})
return suggestions[:10] # Limit to 10 suggestions for performance

# Intent classification
def classify_intent(query):
candidate_labels = list(dynamic_intents.keys())
result = classifier(query, candidate_labels, multi_label=False)
return result['labels'][0], result['scores'][0]

# Grok-enhanced classification
def grok_classify_intent(query, initial_intent, initial_confidence):
if initial_confidence < 0.8:
logging.info(f'Low confidence ({initial_confidence:.2f}) for {initial_intent}. Using Grok...')
prompt = f'''
You are an expert in Infoblox WAPI. Given the query, identify the intent and parameters.
Query: "{query}"
Possible intents: {', '.join(dynamic_intents.keys())}
Return JSON: {{"intent": "intent_name", "entities": {{"key": "value"}}}}
'''
try:
response = grok_client.chat.completions.create(
model='grok-3:beta',
messages=[
{'role': 'system', 'content': 'You are an Infoblox WAPI assistant.'},
{'role': 'user', 'content': prompt}
],
max_tokens=200,
temperature=0.7
)
grok_result = json.loads(response.choices[0].message.content)
return grok_result['intent'], grok_result['entities'], 0.9
except Exception as e:
logging.error(f'Grok API failed: {str(e)}')
return initial_intent, {}, initial_confidence
return initial_intent, {}, initial_confidence

# Entity extraction
def extract_entities(query):
doc = nlp(query)
entities = {}
for ent in doc.ents:
if ent.label_ in ['CIDR', 'IP', 'MAC', 'FQDN', 'TTL', 'EXTATTR']:
entities[ent.label_.lower()] = ent.text
query_lower = query.lower()
if 'comment' in query_lower:
for token in doc:
if token.text.lower() == 'comment' and token.head.text:
entities['comment'] = token.head.text
if 'extattrs' in query_lower:
for token in doc:
if token.text in ['Owner', 'Site', 'Department']:
entities['extattrs'] = {token.text: {'value': token.head.text}}
if 'utilization' in query_lower:
entities['utilization'] = True
return entities

# Validate entities
def validate_entities(intent, entities):
if intent not in dynamic_intents:
return False, f'Intent {intent} not supported'
api = dynamic_intents[intent]
if 'required_fields' in api:
for field in api['required_fields']:
if field not in entities:
return False, f'Missing required field: {field}'
return True, ''

# Save successful prompt
def save_successful_prompt(query, intent, entities, api_result):
if 'error' not in api_result:
df = pd.DataFrame([{
'query': query,
'intent': intent,
'entities': json.dumps(entities),
'api_result': json.dumps(api_result)
}])
df.to_csv(TRAINING_DATA_FILE, mode='a', header=False, index=False)
logging.info(f'Saved prompt to {TRAINING_DATA_FILE}: {query}')

# Execute API call
def execute_api_call(query, intent, entities):
logging.info(f'Executing intent: {intent}, Entities: {entities}')
if intent not in dynamic_intents:
logging.error(f'Intent not supported: {intent}')
return {'error': f'Intent {intent} not supported'}

api = dynamic_intents[intent]
url = f'{BASE_URL}{api["endpoint"].format(**entities)}'

try:
if api['method'] == 'POST':
payload = {k: entities.get(k) for k in api.get('fields', []) if k in entities}
valid, error = validate_entities(intent, entities)
if not valid:
logging.error(error)
return {'error': error}
response = requests.post(url, auth=AUTH, verify=False, json=payload)
elif api['method'] == 'GET':
query_params = api.get('query_params', '')
query_params += '&' if query_params else ''
query_params += '&'.join(f'{k}={entities[k]}' for k in api.get('searchable_fields', []) if k in entities)
response = requests.get(f'{url}?{query_params}', auth=AUTH, verify=False)
elif api['method'] == 'PUT':
if '{ref}' in api['endpoint']:
object_name = intent.split('_', 1)[1]
search_field = api.get('searchable_fields', [list(entities.keys())[0]])[0]
lookup_url = f'{BASE_URL}/{object_name}?{search_field}={entities[search_field]}'
lookup_response = requests.get(lookup_url, auth=AUTH, verify=False)
if lookup_response.status_code == 200 and lookup_response.json():
ref = lookup_response.json()[0]['_ref']
url = f'{BASE_URL}/{object_name}/{ref}'
payload = {k: entities.get(k) for k in api.get('fields', []) if k in entities}
response = requests.put(url, auth=AUTH, verify=False, json=payload)
else:
logging.error('Object reference not found')
return {'error': 'Object reference not found'}
else:
response = requests.put(url, auth=AUTH, verify=False, json=payload)
elif api['method'] == 'DELETE':
if '{ref}' in api['endpoint']:
object_name = intent.split('_', 1)[1]
search_field = api.get('searchable_fields', [list(entities.keys())[0]])[0]
lookup_url = f'{BASE_URL}/{object_name}?{search_field}={entities[search_field]}'
lookup_response = requests.get(lookup_url, auth=AUTH, verify=False)
if lookup_response.status_code == 200 and lookup_response.json():
ref = lookup_response.json()[0]['_ref']
url = f'{BASE_URL}/{object_name}/{ref}'
response = requests.delete(url, auth=AUTH, verify=False)
else:
logging.error('Object reference not found')
return {'error': 'Object reference not found'}
else:
response = requests.delete(url, auth=AUTH, verify=False)
else:
logging.error(f'Method {api["method"]} not implemented')
return {'error': f'Method {api["method"]} not implemented'}

if response.status_code >= 400:
logging.error(f'API error: {response.status_code} - {response.text}')
return {'error': f'API error: {response.status_code} - {response.text}'}
result = response.json()
logging.info(f'API result: {result}')
save_successful_prompt(query, intent, entities, result)
return result
except Exception as e:
logging.error(f'API call failed: {str(e)}')
return {'error': f'API call failed: {str(e)}'}

# Open WebUI integration
def process_open_webui_request(user_input):
intent, confidence = classify_intent(user_input)
entities = extract_entities(user_input)
if confidence < 0.8:
intent, entities, confidence = grok_classify_intent(user_input, intent, confidence)
result = execute_api_call(user_input, intent, entities)
return {
'intent': intent,
'confidence': confidence,
'entities': entities,
'result': result
}

# Example usage
if __name__ == '__main__':
queries = [
'Create a network with CIDR 10.0.0.0/24 and comment TestNetwork',
'Find all networks containing IP 10.0.0.10',
'Get next available IP from network 10.0.0.0/24',
'Set extensible attribute Owner to Admin for network 10.0.0.0/24',
'Create a host record for server1.example.com with IP 192.168.0.10',
'Create a CNAME record for www.example.com pointing to server1.example.com',
'Update A record for test.example.com to IP 192.168.0.20 with TTL 3600',
'Delete host record for server1.example.com',
'Find lease for IP 192.168.0.100',
'Create a fixed address for IP 192.168.0.50 with MAC 00:1A:2B:3C:4D:5E',
'Release lease for IP 192.168.0.100',
'Create a DNS zone for example.com with comment PrimaryZone',
'Find all host records matching name infoblox.localdomain',
'Show network 192.168.1.0/24 utilization'
]
for query in queries:
print(f'\nQuery: {query}')
result = process_open_webui_request(query)
print(f'Intent: {result["intent"]} (Confidence: {result["confidence"]:.2f})')
print(f'Entities: {result["entities"]}')
print(f'API Result: {result["result"]}')
EOF
echo "wapi_nlp.py created at $PYTHON_SCRIPT"

# Create app.py (Flask wrapper with suggestions endpoint)
echo "Creating Flask wrapper (app.py)..."
cat << EOF > "$FLASK_SCRIPT"
from flask import Flask, request, jsonify, render_template
from wapi_nlp import process_open_webui_request, get_suggestions

app = Flask(__name__)

@app.route('/')
def home():
return render_template('index.html')

@app.route('/api/process_query', methods=['POST'])
def process_query():
data = request.get_json()
query = data.get('query')
if not query:
return jsonify({'error': 'No query provided'}), 400
result = process_open_webui_request(query)
return jsonify(result)

@app.route('/api/suggestions', methods=['GET'])
def suggestions():
query = request.args.get('query', '')
suggestions = get_suggestions(query)
return jsonify(suggestions)

if __name__ == '__main__':
app.run(host='0.0.0.0', port=$FLASK_PORT)
EOF
echo "Flask wrapper created at $FLASK_SCRIPT"

# Create index.html (Frontend with autocomplete)
echo "Creating index.html..."
cat << EOF > "$HTML_FILE"
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Infoblox WAPI Query</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<link href="https://code.jquery.com/ui/1.12.1/themes/base/jquery-ui.css" rel="stylesheet">
<style>
body { background-color: #f8f9fa; }
.container { max-width: 800px; margin-top: 50px; }
#response { white-space: pre-wrap; font-family: monospace; background-color: #fff; padding: 15px; border-radius: 5px; }
.ui-autocomplete { max-height: 200px; overflow-y: auto; overflow-x: hidden; z-index: 1000; }
</style>
</head>
<body>
<div class="container">
<h1 class="text-center mb-4">Infoblox WAPI Query Interface</h1>
<div class="card">
<div class="card-body">
<form id="queryForm">
<div class="mb-3">
<label for="queryInput" class="form-label">Enter your query:</label>
<input type="text" class="form-control" id="queryInput" placeholder="e.g., Create a network with CIDR 10.0.0.0/24 or List all networks">
</div>
<button type="submit" class="btn btn-primary">Submit</button>
</form>
<div id="response" class="mt-3"></div>
</div>
</div>
</div>
<script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
<script src="https://code.jquery.com/ui/1.12.1/jquery-ui.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
<script>
$(document).ready(function() {
$('#queryInput').autocomplete({
source: function(request, response) {
$.ajax({
url: '/api/suggestions',
data: { query: request.term },
dataType: 'json',
success: function(data) {
response(data.map(item => ({
label: item.label,
value: item.value
})));
},
error: function() {
response([]);
}
});
},
minLength: 2,
delay: 300
});
});

document.getElementById('queryForm').addEventListener('submit', async (e) => {
e.preventDefault();
const query = document.getElementById('queryInput').value;
const responseDiv = document.getElementById('response');
responseDiv.textContent = 'Processing...';
try {
const response = await fetch('/api/process_query', {
method: 'POST',
headers: { 'Content-Type': 'application/json' },
body: JSON.stringify({ query })
});
const result = await response.json();
responseDiv.textContent = JSON.stringify(result, null, 2);
} catch (error) {
responseDiv.textContent = 'Error: ' + error.message;
}
});
</script>
</body>
</html>
EOF
echo "index.html created at $HTML_FILE"

# Create Quick Start Guide
echo "Creating Quick Start Guide..."
cat << EOF > "$QUICK_START_GUIDE"
# Infoblox WAPI Intents System Quick Start Guide

This guide sets up an Infoblox WAPI intents system with Open WebUI, a Flask web interface with autocomplete for all WAPI intents, and Grok API integration for enhanced NLP on Unix-like systems. It processes natural language queries, executes WAPI calls, and stores successful prompts for training.

## Prerequisites
- **Docker**: Install from [Docker](https://www.docker.com/get-started) and ensure it's running.
- **Python 3**: Install with `sudo apt-get install python3 python3-pip` (Ubuntu) or `brew install python` (macOS).
- **jq**: Install with `sudo apt-get install jq` (Ubuntu) or `brew install jq` (macOS).
- **Grok API Key**: Obtain from [xAI API](https://x.ai/api).

## Setup
1. **Run the Setup Script**:
\`\`\`bash
chmod +x setup.sh
./setup.sh
\`\`\`
This creates all files and sets up the environment in $WORK_DIR.

2. **Update Grok API Key**:
- Edit $GROK_CONFIG_FILE.
- Replace \`"your_grok_api_key"\` with your Grok API key.

## Running the System
1. **Start Docker Compose Services**:
\`\`\`bash
docker-compose -f "$DOCKER_COMPOSE_FILE" up -d
\`\`\`

2. **Start Flask API and Web Interface**:
\`\`\`bash
source "$PYTHON_ENV/bin/activate"
python3 "$FLASK_SCRIPT"
\`\`\`

3. **Access Interfaces**:
- **Web Interface**: [http://localhost:$FLASK_PORT](http://localhost:$FLASK_PORT)
- Enter queries (e.g., "Create a network with CIDR 10.0.0.0/24").
- Type "list," "find," "show," "create," "update," "delete" to see autocomplete suggestions for all WAPI intents.
- View JSON results (intent, confidence, entities, WAPI response).
- **Open WebUI**: [http://localhost:$OPENWEBUI_PORT](http://localhost:$OPENWEBUI_PORT)
- Complete admin setup.
- Add custom API endpoint:
- URL: \`http://localhost:$FLASK_PORT/api/process_query\`
- Method: POST
- Payload: \`{"query": "<user_input>"}\`
- **Swagger UI**: [http://localhost:$SWAGGER_PORT/infoblox-swagger-ui/dist/home.php](http://localhost:$SWAGGER_PORT/infoblox-swagger-ui/dist/home.php) (use browser with CORS disabled, e.g., Chrome with \`--disable-web-security\`).

4. **Test Directly** (Optional):
\`\`\`bash
python3 "$PYTHON_SCRIPT"
\`\`\`

5. **Stop Services**:
\`\`\`bash
docker-compose -f "$DOCKER_COMPOSE_FILE" down
\`\`\`

## Features
- **Autocomplete**: Suggests all WAPI intents (GET, POST, PUT, DELETE, custom functions) when typing keywords like "list," "create," "update," "delete" (e.g., "Create a network with CIDR 10.0.0.0/24").
- **NLP Processing**: Uses spaCy and \`bart-large-mnli\` for intent classification, with Grok API for low-confidence (<80%) queries.
- **WAPI Integration**: Executes network, DNS, and DHCP operations against \`https://$GRID_MASTER_IP/wapi/$WAPI_VERSION\`.
- **Training Data**: Successful prompts saved in \`$TRAINING_DATA_FILE\`.
- **Interfaces**: Flask web interface and Open WebUI for query input and result display.

## Example Queries
- Create: "Create a network with CIDR 10.0.0.0/24 and comment TestNetwork"
- Find: "List all networks"
- Update: "Update A record for test.example.com to IP 192.168.0.20"
- Delete: "Delete host record for server1.example.com"
- Custom: "Release lease for IP 192.168.0.100"

## Troubleshooting
- **Logs**: Check \`$LOG_FILE\`.
- **WAPI Test**:
\`\`\`bash
curl -k -u "$USERNAME:$PASSWORD" "https://$GRID_MASTER_IP/wapi/$WAPI_VERSION?_schema"
\`\`\`
- **Grok API Test**:
\`\`\`bash
curl -H "Authorization: Bearer $GROK_API_KEY" "https://api.x.ai/v1/models"
\`\`\`
- **Flask Test**:
\`\`\`bash
curl -X POST -H "Content-Type: application/json" -d '{"query": "Create a network with CIDR 10.0.0.0/24"}' "http://localhost:$FLASK_PORT/api/process_query"
\`\`\`
- **Suggestions Test**:
\`\`\`bash
curl "http://localhost:$FLASK_PORT/api/suggestions?query=create"
\`\`\`
- **Open WebUI**: Check logs with \`docker logs open-webui\`.

## Notes
- **Security**: Replace \`verify=False\` in \`$PYTHON_SCRIPT\` with SSL verification for production.
- **Training**: Use \`$TRAINING_DATA_FILE\` to fine-tune NLP models.
- **Support**: For issues, check logs or contact support.

*Generated on $(date) by setup.sh*
EOF
echo "Quick Start Guide created at $QUICK_START_GUIDE"

# Make setup.sh executable
chmod +x "$PYTHON_SCRIPT" "$FLASK_SCRIPT" "$DOCKER_COMPOSE_FILE" "$WORK_DIR/setup.sh"

# Instructions
echo "Setup complete!"
echo "Files created:"
echo "- $QUICK_START_GUIDE (Quick Start Guide)"
echo "- $GROK_CONFIG_FILE (Grok API key)"
echo "- $TRAINING_DATA_FILE (successful prompts)"
echo "- $PYTHON_SCRIPT (core logic)"
echo "- $FLASK_SCRIPT (Flask API)"
echo "- $HTML_FILE (web interface with autocomplete)"
echo "- $DOCKER_COMPOSE_FILE (Docker Compose configuration)"
echo "- $SCHEMA_DIR/* (WAPI schemas)"
echo "- $LOG_FILE (logs)"
echo "- $PYTHON_ENV (Python environment)"
echo "Next steps: Follow instructions in $QUICK_START_GUIDE"
