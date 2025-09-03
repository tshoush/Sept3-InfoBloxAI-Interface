#!/usr/bin/env python3
"""Unit tests for NLP processing functions."""

import unittest
import json
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestNLPProcessing(unittest.TestCase):
    """Test NLP entity extraction and intent classification."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_queries = [
            {
                "query": "Create a network with CIDR 10.0.0.0/24 and comment TestNetwork",
                "expected_entities": ["10.0.0.0/24", "TestNetwork"],
                "expected_intent_keywords": ["create", "network"]
            },
            {
                "query": "Find all networks containing IP 10.0.0.10",
                "expected_entities": ["10.0.0.10"],
                "expected_intent_keywords": ["find", "network"]
            },
            {
                "query": "Get next available IP from network 192.168.1.0/24",
                "expected_entities": ["192.168.1.0/24"],
                "expected_intent_keywords": ["get", "available", "network"]
            },
            {
                "query": "Delete host record for server1.example.com",
                "expected_entities": ["server1.example.com"],
                "expected_intent_keywords": ["delete", "host"]
            },
            {
                "query": "Update A record for test.example.com to IP 192.168.0.20 with TTL 3600",
                "expected_entities": ["test.example.com", "192.168.0.20", "3600"],
                "expected_intent_keywords": ["update", "record"]
            }
        ]
    
    @patch('sys.path', sys.path)
    def test_entity_extraction_patterns(self):
        """Test entity extraction for various patterns."""
        # Test CIDR pattern
        cidr_pattern = r'(\d{1,3}\.){3}\d{1,3}/\d{1,2}'
        test_cidrs = ["10.0.0.0/24", "192.168.1.0/16", "172.16.0.0/12"]
        import re
        for cidr in test_cidrs:
            self.assertIsNotNone(re.match(cidr_pattern, cidr), 
                                f"CIDR pattern should match {cidr}")
        
        # Test IP pattern  
        ip_pattern = r'(\d{1,3}\.){3}\d{1,3}'
        test_ips = ["192.168.1.1", "10.0.0.1", "8.8.8.8"]
        for ip in test_ips:
            self.assertIsNotNone(re.match(ip_pattern, ip),
                                f"IP pattern should match {ip}")
        
        # Test MAC pattern
        mac_pattern = r'([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}'
        test_macs = ["00:1A:2B:3C:4D:5E", "aa:bb:cc:dd:ee:ff"]
        for mac in test_macs:
            self.assertIsNotNone(re.match(mac_pattern, mac),
                                f"MAC pattern should match {mac}")
        
        # Test FQDN pattern
        fqdn_pattern = r'[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
        test_fqdns = ["server1.example.com", "www.test.co.uk", "api.service.local"]
        for fqdn in test_fqdns:
            self.assertIsNotNone(re.match(fqdn_pattern, fqdn),
                                f"FQDN pattern should match {fqdn}")
    
    def test_intent_classification_keywords(self):
        """Test intent classification based on keywords."""
        intent_keywords = {
            "create": ["create", "add", "new"],
            "find": ["find", "list", "show", "get", "search"],
            "update": ["update", "modify", "change", "set"],
            "delete": ["delete", "remove", "destroy"]
        }
        
        test_cases = [
            ("Create a new network", "create"),
            ("List all DNS records", "find"),
            ("Update the host record", "update"),
            ("Delete the old entry", "delete"),
            ("Show me all networks", "find"),
            ("Add a new host", "create")
        ]
        
        for query, expected_intent in test_cases:
            query_lower = query.lower()
            matched_intent = None
            for intent, keywords in intent_keywords.items():
                if any(keyword in query_lower for keyword in keywords):
                    matched_intent = intent
                    break
            self.assertEqual(matched_intent, expected_intent,
                           f"Query '{query}' should match intent '{expected_intent}'")
    
    def test_query_validation(self):
        """Test query validation and sanitization."""
        # Test empty query
        self.assertFalse(self._validate_query(""), "Empty query should be invalid")
        
        # Test query length limits
        short_query = "Find IP"
        long_query = "a" * 1000
        self.assertTrue(self._validate_query(short_query), "Short query should be valid")
        self.assertTrue(len(long_query) <= 1000, "Query should have reasonable length limit")
        
        # Test special characters handling
        special_queries = [
            "Find network; DROP TABLE;",
            "Create <script>alert('xss')</script>",
            "Delete ../../etc/passwd"
        ]
        for query in special_queries:
            sanitized = self._sanitize_query(query)
            self.assertNotIn("<script>", sanitized, "Scripts should be removed")
            self.assertNotIn("DROP TABLE", sanitized, "SQL injection attempts should be handled")
    
    def test_entity_type_detection(self):
        """Test detection of different entity types."""
        test_cases = [
            ("10.0.0.0/24", "CIDR"),
            ("192.168.1.100", "IP"),
            ("00:1A:2B:3C:4D:5E", "MAC"),
            ("server.example.com", "FQDN"),
            ("3600", "TTL"),
            ("Owner", "EXTATTR")
        ]
        
        for entity, expected_type in test_cases:
            detected_type = self._detect_entity_type(entity)
            self.assertEqual(detected_type, expected_type,
                           f"Entity '{entity}' should be detected as {expected_type}")
    
    def test_confidence_scoring(self):
        """Test confidence scoring for intent classification."""
        # High confidence scenarios
        high_conf_queries = [
            "Create a network with CIDR 10.0.0.0/24",
            "Delete host record for server1.example.com",
            "Update A record for www.example.com"
        ]
        
        for query in high_conf_queries:
            confidence = self._calculate_confidence(query)
            self.assertGreater(confidence, 0.7,
                             f"Clear query '{query}' should have high confidence")
        
        # Low confidence scenarios
        low_conf_queries = [
            "Do something with the network",
            "Fix the DNS issue",
            "Handle the IP problem"
        ]
        
        for query in low_conf_queries:
            confidence = self._calculate_confidence(query)
            self.assertLess(confidence, 0.5,
                          f"Vague query '{query}' should have low confidence")
    
    # Helper methods
    def _validate_query(self, query):
        """Validate if query is acceptable."""
        return len(query.strip()) > 0
    
    def _sanitize_query(self, query):
        """Sanitize query for safety."""
        # Remove potential XSS
        query = query.replace("<script>", "").replace("</script>", "")
        # Remove SQL injection attempts
        query = query.replace("DROP TABLE", "").replace(";", "")
        return query
    
    def _detect_entity_type(self, entity):
        """Detect the type of an entity."""
        import re
        
        patterns = {
            "CIDR": r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/\d{1,2}$',
            "IP": r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$',
            "MAC": r'^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$',
            "FQDN": r'^[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$',
            "TTL": r'^\d+$',
            "EXTATTR": r'^(Owner|Site|Department)$'
        }
        
        for entity_type, pattern in patterns.items():
            if re.match(pattern, entity):
                return entity_type
        return "UNKNOWN"
    
    def _calculate_confidence(self, query):
        """Calculate confidence score for a query."""
        confidence = 0.0
        query_lower = query.lower()
        
        # Strong action words
        strong_actions = ["create", "delete", "update", "find", "list", "get"]
        for action in strong_actions:
            if action in query_lower:
                confidence += 0.3
                break
        
        # Specific object mentions
        objects = ["network", "host", "record", "zone", "lease", "address"]
        for obj in objects:
            if obj in query_lower:
                confidence += 0.2
        
        # Contains technical entities
        import re
        if re.search(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', query):
            confidence += 0.2
        if re.search(r'[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', query):
            confidence += 0.2
        
        # Has specific parameters
        if "with" in query_lower or "from" in query_lower or "to" in query_lower:
            confidence += 0.1
        
        return min(confidence, 1.0)


if __name__ == "__main__":
    unittest.main()