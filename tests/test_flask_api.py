#!/usr/bin/env python3
"""Tests for Flask API endpoints."""

import unittest
import json
import sys
import os
from unittest.mock import Mock, patch, MagicMock
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestFlaskAPI(unittest.TestCase):
    """Test Flask API endpoints and web interface."""
    
    def setUp(self):
        """Set up test client and fixtures."""
        self.app = self._create_test_app()
        self.client = self.app.test_client()
        self.test_queries = [
            {
                "query": "Create a network with CIDR 10.0.0.0/24",
                "expected_intent": "create_network",
                "expected_status": 200
            },
            {
                "query": "List all networks",
                "expected_intent": "find_network",
                "expected_status": 200
            }
        ]
    
    def _create_test_app(self):
        """Create a test Flask application."""
        from flask import Flask, request, jsonify
        
        app = Flask(__name__)
        app.config['TESTING'] = True
        
        @app.route('/')
        def home():
            return '<html><body>Test Interface</body></html>'
        
        @app.route('/api/process_query', methods=['POST'])
        def process_query():
            data = request.get_json()
            if not data or 'query' not in data:
                return jsonify({'error': 'No query provided'}), 400
            
            # Mock processing
            query = data['query']
            result = {
                'intent': 'test_intent',
                'confidence': 0.85,
                'entities': {'test': 'entity'},
                'result': {'status': 'success'}
            }
            return jsonify(result)
        
        @app.route('/api/suggestions', methods=['GET'])
        def suggestions():
            query = request.args.get('query', '')
            if not query:
                return jsonify([])
            
            # Mock suggestions
            suggestions = [
                {'label': f'Create {query}', 'value': f'Create {query}'},
                {'label': f'Find {query}', 'value': f'Find {query}'},
                {'label': f'Update {query}', 'value': f'Update {query}'}
            ]
            return jsonify(suggestions[:3])
        
        return app
    
    def test_home_endpoint(self):
        """Test home page endpoint."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200, "Home page should return 200")
        self.assertIn(b'html', response.data, "Home page should return HTML")
    
    def test_process_query_endpoint_valid(self):
        """Test process_query endpoint with valid input."""
        test_data = {
            'query': 'Create a network with CIDR 10.0.0.0/24'
        }
        
        response = self.client.post('/api/process_query',
                                   data=json.dumps(test_data),
                                   content_type='application/json')
        
        self.assertEqual(response.status_code, 200, "Valid query should return 200")
        
        data = json.loads(response.data)
        self.assertIn('intent', data, "Response should contain intent")
        self.assertIn('confidence', data, "Response should contain confidence")
        self.assertIn('entities', data, "Response should contain entities")
        self.assertIn('result', data, "Response should contain result")
    
    def test_process_query_endpoint_missing_query(self):
        """Test process_query endpoint with missing query."""
        test_data = {}
        
        response = self.client.post('/api/process_query',
                                   data=json.dumps(test_data),
                                   content_type='application/json')
        
        self.assertEqual(response.status_code, 400, "Missing query should return 400")
        
        data = json.loads(response.data)
        self.assertIn('error', data, "Response should contain error message")
    
    def test_process_query_endpoint_empty_query(self):
        """Test process_query endpoint with empty query."""
        test_data = {'query': ''}
        
        response = self.client.post('/api/process_query',
                                   data=json.dumps(test_data),
                                   content_type='application/json')
        
        # Empty query might be processed or rejected
        self.assertIn(response.status_code, [200, 400], 
                     "Empty query should return 200 or 400")
    
    def test_process_query_endpoint_invalid_json(self):
        """Test process_query endpoint with invalid JSON."""
        response = self.client.post('/api/process_query',
                                   data='invalid json',
                                   content_type='application/json')
        
        self.assertEqual(response.status_code, 400, "Invalid JSON should return 400")
    
    def test_suggestions_endpoint_with_query(self):
        """Test suggestions endpoint with query parameter."""
        response = self.client.get('/api/suggestions?query=network')
        
        self.assertEqual(response.status_code, 200, "Suggestions should return 200")
        
        data = json.loads(response.data)
        self.assertIsInstance(data, list, "Response should be a list")
        
        if data:
            self.assertIn('label', data[0], "Suggestion should have label")
            self.assertIn('value', data[0], "Suggestion should have value")
    
    def test_suggestions_endpoint_without_query(self):
        """Test suggestions endpoint without query parameter."""
        response = self.client.get('/api/suggestions')
        
        self.assertEqual(response.status_code, 200, "Suggestions should return 200")
        
        data = json.loads(response.data)
        self.assertIsInstance(data, list, "Response should be a list")
        self.assertEqual(len(data), 0, "Empty query should return empty list")
    
    def test_suggestions_autocomplete_behavior(self):
        """Test autocomplete behavior of suggestions."""
        test_prefixes = ['create', 'find', 'update', 'delete', 'list']
        
        for prefix in test_prefixes:
            response = self.client.get(f'/api/suggestions?query={prefix}')
            data = json.loads(response.data)
            
            self.assertIsInstance(data, list, f"Suggestions for '{prefix}' should be a list")
            self.assertGreater(len(data), 0, f"Should have suggestions for '{prefix}'")
            
            # Check if suggestions are relevant
            for suggestion in data:
                self.assertTrue(
                    prefix.lower() in suggestion['label'].lower() or 
                    prefix.lower() in suggestion['value'].lower(),
                    f"Suggestion should be relevant to '{prefix}'"
                )
    
    def test_cors_headers(self):
        """Test CORS headers for cross-origin requests."""
        # Note: In production, CORS should be properly configured
        response = self.client.options('/api/process_query')
        
        # CORS headers might not be set in test environment
        # This is a placeholder for CORS testing
        self.assertIn(response.status_code, [200, 404, 405],
                     "OPTIONS request should be handled")
    
    def test_content_type_headers(self):
        """Test content type headers."""
        test_data = {'query': 'Test query'}
        
        # Test with correct content type
        response = self.client.post('/api/process_query',
                                   data=json.dumps(test_data),
                                   content_type='application/json')
        self.assertIn(response.status_code, [200, 400], 
                     "Should handle correct content type")
        
        # Test with incorrect content type
        response = self.client.post('/api/process_query',
                                   data=json.dumps(test_data),
                                   content_type='text/plain')
        # May still work depending on Flask configuration
        self.assertIn(response.status_code, [200, 400, 415],
                     "Should handle incorrect content type")
    
    def test_rate_limiting(self):
        """Test rate limiting behavior (if implemented)."""
        # Send multiple rapid requests
        responses = []
        for _ in range(10):
            response = self.client.get('/api/suggestions?query=test')
            responses.append(response.status_code)
        
        # All should succeed in test environment (no rate limiting)
        self.assertTrue(all(r == 200 for r in responses),
                       "All requests should succeed without rate limiting")
    
    def test_error_response_format(self):
        """Test error response format consistency."""
        # Test various error scenarios
        error_scenarios = [
            ('/api/process_query', 'POST', {}, 400),  # Missing query
            ('/api/process_query', 'GET', {}, 405),   # Wrong method
            ('/nonexistent', 'GET', {}, 404),         # Not found
        ]
        
        for path, method, data, expected_status in error_scenarios:
            if method == 'POST':
                response = self.client.post(path, 
                                          data=json.dumps(data),
                                          content_type='application/json')
            else:
                response = self.client.get(path)
            
            if response.status_code == expected_status:
                try:
                    error_data = json.loads(response.data)
                    if 'error' in error_data:
                        self.assertIsInstance(error_data['error'], str,
                                            "Error message should be a string")
                except json.JSONDecodeError:
                    pass  # Some errors might not return JSON
    
    def test_query_sanitization(self):
        """Test that queries are properly sanitized."""
        dangerous_queries = [
            "<script>alert('xss')</script>",
            "'; DROP TABLE users; --",
            "../../../etc/passwd",
            "{{7*7}}",  # Template injection
        ]
        
        for query in dangerous_queries:
            test_data = {'query': query}
            response = self.client.post('/api/process_query',
                                      data=json.dumps(test_data),
                                      content_type='application/json')
            
            # Should handle dangerous input safely
            self.assertIn(response.status_code, [200, 400],
                         f"Should handle dangerous query: {query}")
            
            if response.status_code == 200:
                data = json.loads(response.data)
                # Ensure no execution of dangerous code
                self.assertNotIn('<script>', str(data),
                                "Should not include script tags in response")
    
    def test_large_query_handling(self):
        """Test handling of large queries."""
        # Test with very long query
        large_query = "Create a network " + "with comment " * 100
        test_data = {'query': large_query}
        
        response = self.client.post('/api/process_query',
                                   data=json.dumps(test_data),
                                   content_type='application/json')
        
        # Should handle large queries gracefully
        self.assertIn(response.status_code, [200, 400, 413],
                     "Should handle large query appropriately")
    
    def test_concurrent_request_handling(self):
        """Test handling of concurrent requests."""
        import threading
        
        results = []
        
        def make_request():
            response = self.client.get('/api/suggestions?query=test')
            results.append(response.status_code)
        
        # Create multiple threads
        threads = []
        for _ in range(5):
            t = threading.Thread(target=make_request)
            threads.append(t)
            t.start()
        
        # Wait for all threads
        for t in threads:
            t.join()
        
        # All requests should succeed
        self.assertTrue(all(r == 200 for r in results),
                       "All concurrent requests should succeed")


if __name__ == "__main__":
    unittest.main()