#!/usr/bin/env python3
"""
Secure version of WAPI NLP processor using environment configuration.
"""

import os
import sys
import json
import re
import logging
import requests
import pandas as pd
from pathlib import Path

# Add current directory to path for config import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import get_config, ConfigurationError

# Disable SSL warnings if needed
requests.packages.urllib3.disable_warnings()

# Initialize configuration
try:
    config = get_config()
except ConfigurationError as e:
    print(f"Configuration error: {e}")
    sys.exit(1)

# Setup logging
logging.basicConfig(
    filename=config.get('LOG_FILE'),
    level=logging.DEBUG if config.get('DEBUG_MODE') else logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Configuration from environment
BASE_URL = config.get_wapi_url()
AUTH = config.get_auth()
SCHEMA_DIR = config.get('SCHEMA_DIR')
TRAINING_DATA_FILE = config.get('TRAINING_DATA_FILE')
SSL_VERIFY = config.get('SSL_VERIFY')

# Try to import NLP libraries (optional)
try:
    import spacy
    nlp = spacy.load('en_core_web_sm')
    NLP_AVAILABLE = True
except ImportError:
    logging.warning("spaCy not available - NLP features disabled")
    NLP_AVAILABLE = False

try:
    from transformers import pipeline
    classifier = pipeline('zero-shot-classification', model='facebook/bart-large-mnli')
    TRANSFORMER_AVAILABLE = True
except ImportError:
    logging.warning("Transformers not available - advanced classification disabled")
    TRANSFORMER_AVAILABLE = False
    classifier = None

# Try to import OpenAI for Grok (optional)
try:
    from openai import OpenAI
    grok_config = config.get_grok_config()
    if grok_config['api_key']:
        grok_client = OpenAI(
            api_key=grok_config['api_key'],
            base_url=grok_config['base_url']
        )
        GROK_AVAILABLE = True
    else:
        grok_client = None
        GROK_AVAILABLE = False
except ImportError:
    logging.warning("OpenAI library not available - Grok features disabled")
    grok_client = None
    GROK_AVAILABLE = False

# Basic intent patterns (fallback when NLP not available)
INTENT_PATTERNS = {
    'create': ['create', 'add', 'new', 'make'],
    'find': ['find', 'list', 'show', 'get', 'search', 'display'],
    'update': ['update', 'modify', 'change', 'set', 'edit'],
    'delete': ['delete', 'remove', 'destroy', 'drop']
}

def extract_entities_basic(query):
    """Basic entity extraction without NLP libraries."""
    entities = {}
    
    # Extract IP addresses
    ip_pattern = r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
    ips = re.findall(ip_pattern, query)
    if ips:
        entities['ip'] = ips[0]
    
    # Extract CIDR networks
    cidr_pattern = r'\b(?:\d{1,3}\.){3}\d{1,3}/\d{1,2}\b'
    cidrs = re.findall(cidr_pattern, query)
    if cidrs:
        entities['network'] = cidrs[0]
    
    # Extract FQDNs
    fqdn_pattern = r'\b[a-zA-Z0-9][a-zA-Z0-9-]{0,61}[a-zA-Z0-9]?\.[a-zA-Z]{2,}\b'
    fqdns = re.findall(fqdn_pattern, query)
    if fqdns:
        entities['fqdn'] = fqdns[0]
    
    # Extract MACs
    mac_pattern = r'\b(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b'
    macs = re.findall(mac_pattern, query)
    if macs:
        entities['mac'] = macs[0]
    
    # Extract comment
    if 'comment' in query.lower():
        comment_match = re.search(r'comment\s+(["\']?)([^"\']+)\1', query, re.IGNORECASE)
        if comment_match:
            entities['comment'] = comment_match.group(2)
    
    return entities

def classify_intent_basic(query):
    """Basic intent classification without ML."""
    query_lower = query.lower()
    
    for intent, keywords in INTENT_PATTERNS.items():
        for keyword in keywords:
            if keyword in query_lower:
                return f"{intent}_network", 0.7  # Default confidence
    
    return "unknown", 0.0

def load_schemas():
    """Load and parse WAPI schemas."""
    intents = {}
    
    # Default intents if no schemas available
    default_intents = {
        'create_network': {
            'method': 'POST',
            'endpoint': '/network',
            'fields': ['network', 'comment'],
            'required_fields': ['network']
        },
        'find_network': {
            'method': 'GET',
            'endpoint': '/network',
            'searchable_fields': ['network', 'comment']
        },
        'update_network': {
            'method': 'PUT',
            'endpoint': '/network/{ref}',
            'fields': ['comment', 'extattrs']
        },
        'delete_network': {
            'method': 'DELETE',
            'endpoint': '/network/{ref}'
        }
    }
    
    # Try to load schemas from directory
    if os.path.exists(SCHEMA_DIR):
        try:
            for schema_file in os.listdir(SCHEMA_DIR):
                if schema_file.endswith('_schema.json'):
                    with open(os.path.join(SCHEMA_DIR, schema_file)) as f:
                        schema = json.load(f)
                        # Parse schema and add to intents
                        object_name = schema_file.replace('_schema.json', '').replace('_', ':')
                        # ... parse schema logic ...
            logging.info(f"Loaded {len(intents)} intents from schemas")
        except Exception as e:
            logging.error(f"Error loading schemas: {e}")
    
    # Use defaults if no schemas loaded
    if not intents:
        intents = default_intents
        logging.info("Using default intents")
    
    return intents

def process_query(query):
    """Process a natural language query."""
    logging.info(f"Processing query: {query}")
    
    # Extract entities
    if NLP_AVAILABLE:
        doc = nlp(query)
        entities = {ent.label_: ent.text for ent in doc.ents}
    else:
        entities = extract_entities_basic(query)
    
    # Classify intent
    if TRANSFORMER_AVAILABLE and classifier:
        intents = load_schemas()
        result = classifier(query, list(intents.keys()), multi_label=False)
        intent = result['labels'][0]
        confidence = result['scores'][0]
    else:
        intent, confidence = classify_intent_basic(query)
    
    # Use Grok for low confidence
    if GROK_AVAILABLE and grok_client and confidence < 0.8:
        try:
            logging.info(f"Low confidence ({confidence:.2f}), using Grok")
            response = grok_client.chat.completions.create(
                model='grok-3:beta',
                messages=[
                    {'role': 'system', 'content': 'You are an Infoblox WAPI assistant.'},
                    {'role': 'user', 'content': f'Classify this query: "{query}"'}
                ],
                max_tokens=200
            )
            # Parse Grok response
            grok_result = response.choices[0].message.content
            logging.info(f"Grok response: {grok_result}")
        except Exception as e:
            logging.error(f"Grok API error: {e}")
    
    return {
        'query': query,
        'intent': intent,
        'confidence': confidence,
        'entities': entities
    }

def execute_wapi_call(intent, entities):
    """Execute WAPI call based on intent and entities."""
    intents = load_schemas()
    
    if intent not in intents:
        return {'error': f'Unknown intent: {intent}'}
    
    api = intents[intent]
    
    try:
        if api['method'] == 'GET':
            # Build query parameters
            params = {}
            for field in api.get('searchable_fields', []):
                if field in entities:
                    params[field] = entities[field]
            
            response = requests.get(
                f"{BASE_URL}{api['endpoint']}",
                params=params,
                auth=AUTH,
                verify=SSL_VERIFY
            )
            
        elif api['method'] == 'POST':
            payload = {
                field: entities.get(field)
                for field in api.get('fields', [])
                if field in entities
            }
            
            response = requests.post(
                f"{BASE_URL}{api['endpoint']}",
                json=payload,
                auth=AUTH,
                verify=SSL_VERIFY
            )
            
        else:
            return {'error': f'Method {api["method"]} not implemented'}
        
        if response.status_code >= 400:
            return {'error': f'API error: {response.status_code} - {response.text}'}
        
        return response.json()
        
    except requests.exceptions.ConnectionError:
        return {'error': 'Could not connect to Grid Master. Check INFOBLOX_GRID_MASTER_IP'}
    except Exception as e:
        return {'error': str(e)}

def test_connection():
    """Test connection to Grid Master."""
    try:
        response = requests.get(
            f"{BASE_URL}?_schema",
            auth=AUTH,
            verify=SSL_VERIFY,
            timeout=5
        )
        if response.status_code == 200:
            return True, "Connected successfully"
        elif response.status_code == 401:
            return False, "Authentication failed - check credentials"
        else:
            return False, f"Connection failed: {response.status_code}"
    except requests.exceptions.ConnectionError:
        return False, f"Cannot connect to {config.get('GRID_MASTER_IP')}"
    except Exception as e:
        return False, str(e)

def main():
    """Main function for testing."""
    print("InfoBlox WAPI NLP Processor (Secure Version)")
    print("=" * 50)
    
    # Show configuration
    print("\nConfiguration:")
    print(f"  Grid Master: {config.get('GRID_MASTER_IP')}")
    print(f"  Username: {config.get('USERNAME')}")
    print(f"  WAPI URL: {BASE_URL}")
    print(f"  NLP Available: {NLP_AVAILABLE}")
    print(f"  Grok Available: {GROK_AVAILABLE}")
    
    # Test connection
    print("\nTesting connection...")
    connected, message = test_connection()
    if connected:
        print(f"✓ {message}")
    else:
        print(f"✗ {message}")
        return
    
    # Test queries
    test_queries = [
        "Create a network with CIDR 10.0.0.0/24",
        "List all networks",
        "Find network 192.168.1.0/24",
        "Delete network 10.0.0.0/24"
    ]
    
    print("\nTest Queries:")
    for query in test_queries:
        print(f"\n  Query: {query}")
        result = process_query(query)
        print(f"  Intent: {result['intent']} (confidence: {result['confidence']:.2f})")
        print(f"  Entities: {result['entities']}")

if __name__ == "__main__":
    main()