#!/usr/bin/env python3
"""
Secure configuration management for InfoBlox WAPI NLP system.
Loads configuration from environment variables with fallback to .env file.
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Raised when configuration is invalid or missing."""
    pass


class SecureConfig:
    """Manages secure configuration from environment variables."""
    
    def __init__(self, env_file: Optional[str] = None):
        """
        Initialize configuration from environment variables.
        
        Args:
            env_file: Path to .env file (optional)
        """
        self.env_file = env_file or os.path.join(Path.home(), 'infoblox-wapi-nlp', '.env')
        self._config = {}
        self._load_env_file()
        self._load_configuration()
        self._validate_configuration()
    
    def _load_env_file(self):
        """Load environment variables from .env file if it exists."""
        if os.path.exists(self.env_file):
            try:
                with open(self.env_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            if '=' in line:
                                key, value = line.split('=', 1)
                                # Only set if not already in environment
                                if key not in os.environ:
                                    os.environ[key] = value.strip('"').strip("'")
                logger.info(f"Loaded configuration from {self.env_file}")
            except Exception as e:
                logger.warning(f"Could not load .env file: {e}")
    
    def _load_configuration(self):
        """Load configuration from environment variables."""
        # Required configurations
        self._config['GRID_MASTER_IP'] = os.environ.get('INFOBLOX_GRID_MASTER_IP', '')
        self._config['USERNAME'] = os.environ.get('INFOBLOX_USERNAME', '')
        self._config['PASSWORD'] = os.environ.get('INFOBLOX_PASSWORD', '')
        self._config['WAPI_VERSION'] = os.environ.get('INFOBLOX_WAPI_VERSION', 'v2.13.1')
        
        # Optional configurations with defaults
        self._config['SWAGGER_PORT'] = int(os.environ.get('INFOBLOX_SWAGGER_PORT', '8080'))
        self._config['OPENWEBUI_PORT'] = int(os.environ.get('INFOBLOX_OPENWEBUI_PORT', '3000'))
        self._config['FLASK_PORT'] = int(os.environ.get('INFOBLOX_FLASK_PORT', '5000'))
        
        # API Keys
        self._config['GROK_API_KEY'] = os.environ.get('GROK_API_KEY', '')
        self._config['GROK_API_BASE_URL'] = os.environ.get('GROK_API_BASE_URL', 'https://api.x.ai/v1')
        
        # Paths
        self._config['WORK_DIR'] = os.environ.get('INFOBLOX_WORK_DIR', 
                                                  os.path.join(Path.home(), 'infoblox-wapi-nlp'))
        
        # Security settings
        self._config['SSL_VERIFY'] = os.environ.get('INFOBLOX_SSL_VERIFY', 'false').lower() == 'true'
        self._config['DEBUG_MODE'] = os.environ.get('INFOBLOX_DEBUG', 'false').lower() == 'true'
        
        # Derived paths
        self._config['SCHEMA_DIR'] = os.path.join(self._config['WORK_DIR'], 'schemas')
        self._config['PYTHON_ENV'] = os.path.join(self._config['WORK_DIR'], 'venv')
        self._config['LOG_FILE'] = os.path.join(self._config['WORK_DIR'], 'wapi_nlp.log')
        self._config['TRAINING_DATA_FILE'] = os.path.join(self._config['WORK_DIR'], 'training_data.csv')
    
    def _validate_configuration(self):
        """Validate that required configuration is present."""
        required_fields = ['GRID_MASTER_IP', 'USERNAME', 'PASSWORD']
        missing_fields = []
        
        for field in required_fields:
            if not self._config.get(field):
                missing_fields.append(field)
        
        if missing_fields:
            error_msg = f"Missing required configuration: {', '.join(missing_fields)}"
            logger.error(error_msg)
            logger.info("Please set the following environment variables:")
            for field in missing_fields:
                logger.info(f"  export INFOBLOX_{field}=<value>")
            logger.info(f"Or create a .env file at {self.env_file}")
            raise ConfigurationError(error_msg)
        
        # Validate IP format
        ip = self._config['GRID_MASTER_IP']
        if not self._is_valid_ip(ip):
            raise ConfigurationError(f"Invalid IP address format: {ip}")
        
        # Warn about missing optional configurations
        if not self._config.get('GROK_API_KEY'):
            logger.warning("GROK_API_KEY not set - Grok AI features will be disabled")
    
    def _is_valid_ip(self, ip: str) -> bool:
        """Validate IP address format."""
        parts = ip.split('.')
        if len(parts) != 4:
            return False
        try:
            return all(0 <= int(part) <= 255 for part in parts)
        except ValueError:
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return self._config.get(key, default)
    
    def get_wapi_url(self) -> str:
        """Get the base WAPI URL."""
        protocol = "https" if self._config['SSL_VERIFY'] else "https"
        return f"{protocol}://{self._config['GRID_MASTER_IP']}/wapi/{self._config['WAPI_VERSION']}"
    
    def get_auth(self) -> tuple:
        """Get authentication tuple for requests."""
        return (self._config['USERNAME'], self._config['PASSWORD'])
    
    def get_grok_config(self) -> Dict[str, str]:
        """Get Grok API configuration."""
        return {
            'api_key': self._config['GROK_API_KEY'],
            'base_url': self._config['GROK_API_BASE_URL']
        }
    
    def save_grok_config(self):
        """Save Grok configuration to JSON file (for backward compatibility)."""
        grok_config_file = os.path.join(self._config['WORK_DIR'], 'grok_config.json')
        config = self.get_grok_config()
        
        # Only save if API key is present
        if config['api_key']:
            try:
                with open(grok_config_file, 'w') as f:
                    json.dump({'GROK_API_KEY': config['api_key']}, f)
                os.chmod(grok_config_file, 0o600)  # Restrict permissions
                logger.info(f"Saved Grok config to {grok_config_file} with restricted permissions")
            except Exception as e:
                logger.error(f"Failed to save Grok config: {e}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Return configuration as dictionary (with sensitive data masked)."""
        config_copy = self._config.copy()
        # Mask sensitive information
        if config_copy.get('PASSWORD'):
            config_copy['PASSWORD'] = '***MASKED***'
        if config_copy.get('GROK_API_KEY'):
            config_copy['GROK_API_KEY'] = '***MASKED***'
        return config_copy
    
    def export_for_shell(self) -> str:
        """Export configuration as shell variables."""
        exports = []
        for key, value in self._config.items():
            if key not in ['PASSWORD', 'GROK_API_KEY']:  # Don't export sensitive data
                exports.append(f'export INFOBLOX_{key}="{value}"')
        return '\n'.join(exports)


# Singleton instance
_config_instance = None


def get_config(env_file: Optional[str] = None) -> SecureConfig:
    """
    Get or create the configuration singleton.
    
    Args:
        env_file: Optional path to .env file
    
    Returns:
        SecureConfig instance
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = SecureConfig(env_file)
    return _config_instance


if __name__ == "__main__":
    """Test configuration loading."""
    try:
        config = get_config()
        print("Configuration loaded successfully!")
        print("\nConfiguration (sensitive data masked):")
        for key, value in config.to_dict().items():
            print(f"  {key}: {value}")
        
        print("\nWAPI URL:", config.get_wapi_url())
        
        # Test saving Grok config
        config.save_grok_config()
        
    except ConfigurationError as e:
        print(f"Configuration error: {e}")
        exit(1)