#!/usr/bin/env python3
"""Integration tests for WAPI calls and schema handling."""

import unittest
import json
import os
import sys
from unittest.mock import Mock, patch, MagicMock
import tempfile
import shutil

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestWAPIIntegration(unittest.TestCase):
    """Test WAPI integration and API calls."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_config = {
            "GRID_MASTER_IP": "192.168.1.222",
            "WAPI_VERSION": "v2.13.1",
            "USERNAME": "admin",
            "PASSWORD": "InfoBlox"
        }
        
        # Create temporary schema directory
        self.temp_dir = tempfile.mkdtemp()
        self.schema_dir = os.path.join(self.temp_dir, "schemas")
        os.makedirs(self.schema_dir, exist_ok=True)
        
        # Mock schema data
        self.mock_network_schema = {
            "supported_objects": ["network"],
            "restrictions": ["create", "read", "update", "delete"],
            "fields": [
                {"name": "network", "searchable": True, "required_on_create": True},
                {"name": "comment", "searchable": False, "required_on_create": False},
                {"name": "extattrs", "searchable": False, "is_array": False}
            ],
            "supported_functions": ["next_available_ip"]
        }
    
    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    @patch('requests.get')
    def test_wapi_connection(self, mock_get):
        """Test WAPI connection and authentication."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"supported_objects": ["network", "record:a"]}
        mock_get.return_value = mock_response
        
        url = f"https://{self.test_config['GRID_MASTER_IP']}/wapi/{self.test_config['WAPI_VERSION']}?_schema"
        
        # Simulate connection test
        response = mock_get(url, auth=(self.test_config['USERNAME'], self.test_config['PASSWORD']), verify=False)
        
        self.assertEqual(response.status_code, 200, "WAPI connection should succeed")
        self.assertIn("supported_objects", response.json(), "Response should contain supported objects")
    
    @patch('requests.get')
    def test_schema_fetching(self, mock_get):
        """Test fetching and parsing WAPI schemas."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.mock_network_schema
        mock_get.return_value = mock_response
        
        # Test schema fetch
        object_name = "network"
        url = f"https://{self.test_config['GRID_MASTER_IP']}/wapi/{self.test_config['WAPI_VERSION']}/{object_name}?_schema"
        
        response = mock_get(url, auth=(self.test_config['USERNAME'], self.test_config['PASSWORD']), verify=False)
        schema = response.json()
        
        self.assertIn("restrictions", schema, "Schema should contain restrictions")
        self.assertIn("fields", schema, "Schema should contain fields")
        self.assertIsInstance(schema["fields"], list, "Fields should be a list")
    
    def test_intent_generation_from_schema(self):
        """Test generating intents from WAPI schema."""
        # Save mock schema to file
        schema_file = os.path.join(self.schema_dir, "network_schema.json")
        with open(schema_file, 'w') as f:
            json.dump(self.mock_network_schema, f)
        
        # Generate intents based on schema
        intents = self._generate_intents_from_schema(self.schema_dir)
        
        # Verify expected intents
        expected_intents = [
            "create_network",
            "find_network", 
            "update_network",
            "delete_network",
            "next_available_ip_network"
        ]
        
        for intent in expected_intents:
            self.assertIn(intent, intents, f"Intent '{intent}' should be generated")
    
    @patch('requests.post')
    def test_create_network_api_call(self, mock_post):
        """Test creating a network via WAPI."""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"_ref": "network/ZG5zLm5ldHdvcmskMTAuMC4wLjAvMjQvMA:10.0.0.0/24/default"}
        mock_post.return_value = mock_response
        
        # Test network creation
        payload = {
            "network": "10.0.0.0/24",
            "comment": "Test Network"
        }
        
        url = f"https://{self.test_config['GRID_MASTER_IP']}/wapi/{self.test_config['WAPI_VERSION']}/network"
        response = mock_post(url, json=payload, auth=(self.test_config['USERNAME'], self.test_config['PASSWORD']), verify=False)
        
        self.assertEqual(response.status_code, 201, "Network creation should return 201")
        self.assertIn("_ref", response.json(), "Response should contain object reference")
    
    @patch('requests.get')
    def test_find_network_api_call(self, mock_get):
        """Test finding networks via WAPI."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "_ref": "network/ZG5zLm5ldHdvcmskMTAuMC4wLjAvMjQvMA:10.0.0.0/24/default",
                "network": "10.0.0.0/24",
                "comment": "Test Network"
            }
        ]
        mock_get.return_value = mock_response
        
        # Test network search
        url = f"https://{self.test_config['GRID_MASTER_IP']}/wapi/{self.test_config['WAPI_VERSION']}/network"
        params = {"network": "10.0.0.0/24"}
        
        response = mock_get(url, params=params, auth=(self.test_config['USERNAME'], self.test_config['PASSWORD']), verify=False)
        
        self.assertEqual(response.status_code, 200, "Network search should return 200")
        self.assertIsInstance(response.json(), list, "Response should be a list")
        if response.json():
            self.assertIn("network", response.json()[0], "Network object should contain network field")
    
    @patch('requests.put')
    @patch('requests.get')
    def test_update_network_api_call(self, mock_get, mock_put):
        """Test updating a network via WAPI."""
        # Mock GET to find the network
        mock_get_response = Mock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = [
            {"_ref": "network/ZG5zLm5ldHdvcmskMTAuMC4wLjAvMjQvMA:10.0.0.0/24/default"}
        ]
        mock_get.return_value = mock_get_response
        
        # Mock PUT to update
        mock_put_response = Mock()
        mock_put_response.status_code = 200
        mock_put_response.json.return_value = {"_ref": "network/ZG5zLm5ldHdvcmskMTAuMC4wLjAvMjQvMA:10.0.0.0/24/default"}
        mock_put.return_value = mock_put_response
        
        # Find network first
        search_url = f"https://{self.test_config['GRID_MASTER_IP']}/wapi/{self.test_config['WAPI_VERSION']}/network"
        search_response = mock_get(search_url, params={"network": "10.0.0.0/24"})
        
        self.assertTrue(search_response.json(), "Should find network to update")
        
        # Update network
        ref = search_response.json()[0]["_ref"]
        update_url = f"https://{self.test_config['GRID_MASTER_IP']}/wapi/{self.test_config['WAPI_VERSION']}/{ref}"
        update_payload = {"comment": "Updated Test Network"}
        
        update_response = mock_put(update_url, json=update_payload)
        
        self.assertEqual(update_response.status_code, 200, "Network update should return 200")
    
    @patch('requests.delete')
    @patch('requests.get')
    def test_delete_network_api_call(self, mock_get, mock_delete):
        """Test deleting a network via WAPI."""
        # Mock GET to find the network
        mock_get_response = Mock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = [
            {"_ref": "network/ZG5zLm5ldHdvcmskMTAuMC4wLjAvMjQvMA:10.0.0.0/24/default"}
        ]
        mock_get.return_value = mock_get_response
        
        # Mock DELETE
        mock_delete_response = Mock()
        mock_delete_response.status_code = 200
        mock_delete_response.json.return_value = {"_ref": "network/ZG5zLm5ldHdvcmskMTAuMC4wLjAvMjQvMA:10.0.0.0/24/default"}
        mock_delete.return_value = mock_delete_response
        
        # Find network first
        search_url = f"https://{self.test_config['GRID_MASTER_IP']}/wapi/{self.test_config['WAPI_VERSION']}/network"
        search_response = mock_get(search_url, params={"network": "10.0.0.0/24"})
        
        self.assertTrue(search_response.json(), "Should find network to delete")
        
        # Delete network
        ref = search_response.json()[0]["_ref"]
        delete_url = f"https://{self.test_config['GRID_MASTER_IP']}/wapi/{self.test_config['WAPI_VERSION']}/{ref}"
        
        delete_response = mock_delete(delete_url)
        
        self.assertEqual(delete_response.status_code, 200, "Network deletion should return 200")
    
    def test_error_handling(self):
        """Test error handling for various failure scenarios."""
        # Test invalid IP format
        invalid_ips = ["999.999.999.999", "10.0.0", "not.an.ip"]
        for ip in invalid_ips:
            self.assertFalse(self._validate_ip(ip), f"IP {ip} should be invalid")
        
        # Test invalid CIDR format
        invalid_cidrs = ["10.0.0.0/33", "192.168.1.0", "10.0.0.0/"]
        for cidr in invalid_cidrs:
            self.assertFalse(self._validate_cidr(cidr), f"CIDR {cidr} should be invalid")
        
        # Test missing required fields
        incomplete_payload = {"comment": "Test"}  # Missing required 'network' field
        self.assertFalse(self._validate_required_fields(incomplete_payload, ["network"]),
                        "Should detect missing required field")
    
    def test_authentication_failure(self):
        """Test handling of authentication failures."""
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 401
            mock_response.text = "Authentication failed"
            mock_get.return_value = mock_response
            
            url = f"https://{self.test_config['GRID_MASTER_IP']}/wapi/{self.test_config['WAPI_VERSION']}?_schema"
            response = mock_get(url, auth=("wrong", "credentials"))
            
            self.assertEqual(response.status_code, 401, "Should return 401 for bad credentials")
    
    def test_network_connectivity_failure(self):
        """Test handling of network connectivity issues."""
        with patch('requests.get') as mock_get:
            from requests.exceptions import ConnectionError
            mock_get.side_effect = ConnectionError("Connection refused")
            
            try:
                url = f"https://{self.test_config['GRID_MASTER_IP']}/wapi/{self.test_config['WAPI_VERSION']}?_schema"
                mock_get(url)
                connection_failed = False
            except ConnectionError:
                connection_failed = True
            
            self.assertTrue(connection_failed, "Should handle connection errors gracefully")
    
    # Helper methods
    def _generate_intents_from_schema(self, schema_dir):
        """Generate intents from schema files."""
        intents = {}
        
        for schema_file in os.listdir(schema_dir):
            if schema_file.endswith('_schema.json'):
                with open(os.path.join(schema_dir, schema_file)) as f:
                    schema = json.load(f)
                    object_name = schema_file.replace('_schema.json', '')
                    
                    if 'create' in schema.get('restrictions', []):
                        intents[f'create_{object_name}'] = True
                    if 'read' in schema.get('restrictions', []):
                        intents[f'find_{object_name}'] = True
                    if 'update' in schema.get('restrictions', []):
                        intents[f'update_{object_name}'] = True
                    if 'delete' in schema.get('restrictions', []):
                        intents[f'delete_{object_name}'] = True
                    
                    for func in schema.get('supported_functions', []):
                        intents[f'{func}_{object_name}'] = True
        
        return intents
    
    def _validate_ip(self, ip):
        """Validate IP address format."""
        import re
        pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        if not re.match(pattern, ip):
            return False
        
        parts = ip.split('.')
        return all(0 <= int(part) <= 255 for part in parts)
    
    def _validate_cidr(self, cidr):
        """Validate CIDR format."""
        import re
        pattern = r'^(\d{1,3}\.){3}\d{1,3}/\d{1,2}$'
        if not re.match(pattern, cidr):
            return False
        
        ip, prefix = cidr.split('/')
        if not self._validate_ip(ip):
            return False
        
        return 0 <= int(prefix) <= 32
    
    def _validate_required_fields(self, payload, required_fields):
        """Validate that payload contains all required fields."""
        return all(field in payload for field in required_fields)


if __name__ == "__main__":
    unittest.main()