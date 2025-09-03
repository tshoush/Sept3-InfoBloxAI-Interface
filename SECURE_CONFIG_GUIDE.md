# Secure Configuration Guide for InfoBlox WAPI NLP System

## Overview

This guide explains how to securely configure and manage credentials for the InfoBlox WAPI NLP integration system. The system now uses environment variables and `.env` files instead of hardcoded credentials.

## Quick Start

### 1. Initial Setup

```bash
# Clone the repository
git clone <repository-url>
cd InfoBlox-UI

# Copy the environment template
cp .env.example .env

# Edit .env with your credentials
nano .env  # or use your preferred editor

# Run the secure setup script
chmod +x setup_secure.sh
./setup_secure.sh
```

### 2. Manual Configuration

If you prefer to configure manually, set these environment variables:

```bash
# Required variables
export INFOBLOX_GRID_MASTER_IP="192.168.1.222"
export INFOBLOX_USERNAME="admin"
export INFOBLOX_PASSWORD="your-secure-password"

# Optional variables
export GROK_API_KEY="your-grok-api-key"
export INFOBLOX_SSL_VERIFY="true"  # Enable in production
```

## Configuration Methods

### Method 1: Environment Variables (Recommended for Production)

Set environment variables in your shell profile or system:

```bash
# Add to ~/.bashrc, ~/.zshrc, or /etc/environment
export INFOBLOX_GRID_MASTER_IP="192.168.1.222"
export INFOBLOX_USERNAME="admin"
export INFOBLOX_PASSWORD="secure-password"
```

### Method 2: .env File (Recommended for Development)

Create a `.env` file in the project root:

```env
INFOBLOX_GRID_MASTER_IP=192.168.1.222
INFOBLOX_USERNAME=admin
INFOBLOX_PASSWORD=secure-password
```

**Security Notes:**
- The `.env` file is automatically excluded from git
- File permissions are set to 600 (owner read/write only)
- Never commit `.env` to version control

### Method 3: Python Configuration Module

Use the `config.py` module in your Python scripts:

```python
from config import get_config

# Load configuration
config = get_config()

# Access configuration values
grid_ip = config.get('GRID_MASTER_IP')
auth = config.get_auth()  # Returns (username, password) tuple
wapi_url = config.get_wapi_url()
```

### Method 4: Docker Compose with .env

Docker Compose automatically loads `.env` files:

```bash
# Start services with environment variables
docker-compose up -d

# Or explicitly specify env file
docker-compose --env-file .env up -d
```

## Security Best Practices

### 1. File Permissions

```bash
# Set restrictive permissions on .env
chmod 600 .env

# Verify permissions
ls -la .env
# Should show: -rw-------
```

### 2. Credential Rotation

Regularly rotate credentials:

```bash
# Update password in .env
nano .env

# Restart services
docker-compose restart
```

### 3. Production Deployment

For production environments:

1. **Use a Secrets Manager**:
   - AWS Secrets Manager
   - HashiCorp Vault
   - Azure Key Vault
   - Kubernetes Secrets

2. **Enable SSL Verification**:
   ```bash
   export INFOBLOX_SSL_VERIFY="true"
   ```

3. **Use Service Accounts**:
   - Create dedicated service accounts with minimal permissions
   - Avoid using admin accounts

4. **Implement Audit Logging**:
   ```bash
   export INFOBLOX_DEBUG="false"  # Disable debug in production
   export INFOBLOX_LOG_LEVEL="INFO"
   ```

### 4. CI/CD Integration

For automated deployments:

```yaml
# GitHub Actions example
- name: Deploy
  env:
    INFOBLOX_GRID_MASTER_IP: ${{ secrets.INFOBLOX_GRID_IP }}
    INFOBLOX_USERNAME: ${{ secrets.INFOBLOX_USERNAME }}
    INFOBLOX_PASSWORD: ${{ secrets.INFOBLOX_PASSWORD }}
  run: |
    ./setup_secure.sh
```

## Migration from Hardcoded Credentials

If migrating from the original `setup.sh`:

1. **Extract Current Values**:
   ```bash
   grep "GRID_MASTER_IP\|USERNAME\|PASSWORD" setup.sh
   ```

2. **Create .env File**:
   ```bash
   cp .env.example .env
   # Add extracted values to .env
   ```

3. **Use New Setup Script**:
   ```bash
   ./setup_secure.sh
   ```

4. **Update Existing Scripts**:
   Replace hardcoded values with environment variables:
   
   ```python
   # Old way
   GRID_MASTER_IP = "192.168.1.222"
   
   # New way
   import os
   GRID_MASTER_IP = os.environ.get('INFOBLOX_GRID_MASTER_IP')
   ```

## Troubleshooting

### Missing Configuration

If you see "Missing required configuration" errors:

```bash
# Check which variables are set
env | grep INFOBLOX

# Source the .env file
source .env

# Or export manually
export INFOBLOX_GRID_MASTER_IP="192.168.1.222"
```

### Permission Denied

If you get permission errors:

```bash
# Fix file permissions
chmod 600 .env
chmod +x setup_secure.sh
```

### Docker Environment Issues

If Docker containers can't read environment:

```bash
# Verify docker-compose.yml uses variables
docker-compose config

# Check container environment
docker exec infoblox-swagger env | grep INFOBLOX
```

## Configuration Reference

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `INFOBLOX_GRID_MASTER_IP` | Grid Master IP address | `192.168.1.222` |
| `INFOBLOX_USERNAME` | Infoblox username | `admin` |
| `INFOBLOX_PASSWORD` | Infoblox password | `SecurePass123!` |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `INFOBLOX_WAPI_VERSION` | WAPI version | `v2.13.1` |
| `INFOBLOX_SWAGGER_PORT` | Swagger UI port | `8080` |
| `INFOBLOX_OPENWEBUI_PORT` | Open WebUI port | `3000` |
| `INFOBLOX_FLASK_PORT` | Flask API port | `5000` |
| `GROK_API_KEY` | Grok API key | (empty) |
| `INFOBLOX_SSL_VERIFY` | Enable SSL verification | `false` |
| `INFOBLOX_DEBUG` | Enable debug mode | `false` |
| `INFOBLOX_WORK_DIR` | Working directory | `~/infoblox-wapi-nlp` |

## Advanced Configuration

### Custom CA Certificates

For self-signed certificates:

```bash
# Set custom CA certificate path
export INFOBLOX_CA_CERT_PATH="/path/to/ca-cert.pem"
export INFOBLOX_SSL_VERIFY="true"
```

### Proxy Configuration

If behind a corporate proxy:

```bash
export HTTP_PROXY="http://proxy.company.com:8080"
export HTTPS_PROXY="http://proxy.company.com:8080"
export NO_PROXY="localhost,127.0.0.1"
```

### Multi-Environment Setup

Manage multiple environments:

```bash
# Development
cp .env.example .env.development
export ENV_FILE=.env.development

# Staging
cp .env.example .env.staging
export ENV_FILE=.env.staging

# Production
cp .env.example .env.production
export ENV_FILE=.env.production

# Load specific environment
source $ENV_FILE
```

## Compliance and Auditing

### Logging Configuration Changes

Track configuration changes:

```bash
# Enable audit logging
export INFOBLOX_AUDIT_LOG="/var/log/infoblox-audit.log"

# Log configuration access
echo "$(date): Configuration accessed by $(whoami)" >> $INFOBLOX_AUDIT_LOG
```

### Compliance Checklist

- [ ] Credentials stored in environment variables or secure vault
- [ ] `.env` file has restrictive permissions (600)
- [ ] `.env` is in `.gitignore`
- [ ] SSL verification enabled in production
- [ ] Service accounts used instead of admin accounts
- [ ] Regular credential rotation schedule
- [ ] Audit logging enabled
- [ ] No credentials in Docker images
- [ ] Secrets encrypted at rest
- [ ] Access controls implemented

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review logs: `tail -f ~/infoblox-wapi-nlp/wapi_nlp.log`
3. Test configuration: `python config.py`
4. Verify environment: `env | grep INFOBLOX`