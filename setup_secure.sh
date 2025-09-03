#!/bin/bash
# setup_secure.sh: Secure setup script for Infoblox WAPI NLP system using environment variables

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    local status=$1
    local message=$2
    case $status in
        "SUCCESS")
            echo -e "${GREEN}✓${NC} $message"
            ;;
        "ERROR")
            echo -e "${RED}✗${NC} $message"
            ;;
        "INFO")
            echo -e "${BLUE}ℹ${NC} $message"
            ;;
        "WARNING")
            echo -e "${YELLOW}⚠${NC} $message"
            ;;
        *)
            echo "$message"
            ;;
    esac
}

# Function to check if environment variable is set
check_env_var() {
    local var_name=$1
    local var_value="${!var_name}"
    
    if [ -z "$var_value" ]; then
        return 1
    else
        return 0
    fi
}

# Function to prompt for environment variable if not set
prompt_for_env_var() {
    local var_name=$1
    local prompt_text=$2
    local is_secret=$3
    local default_value=$4
    
    if ! check_env_var "$var_name"; then
        if [ "$is_secret" = "true" ]; then
            read -s -p "$prompt_text: " value
            echo
        else
            if [ -n "$default_value" ]; then
                read -p "$prompt_text [$default_value]: " value
                value="${value:-$default_value}"
            else
                read -p "$prompt_text: " value
            fi
        fi
        export "$var_name=$value"
    fi
}

# Function to load .env file if it exists
load_env_file() {
    local env_file="${1:-.env}"
    
    if [ -f "$env_file" ]; then
        print_status "INFO" "Loading environment from $env_file"
        set -a  # Mark all new variables for export
        source "$env_file"
        set +a
        return 0
    else
        return 1
    fi
}

# Function to save configuration to .env file
save_env_file() {
    local env_file="${1:-.env}"
    local work_dir="${INFOBLOX_WORK_DIR:-$HOME/infoblox-wapi-nlp}"
    
    print_status "INFO" "Saving configuration to $work_dir/$env_file"
    
    cat > "$work_dir/$env_file" << EOF
# Infoblox WAPI Configuration
# Generated on $(date)

# Required: Grid Master Configuration
INFOBLOX_GRID_MASTER_IP="${INFOBLOX_GRID_MASTER_IP}"
INFOBLOX_USERNAME="${INFOBLOX_USERNAME}"
INFOBLOX_PASSWORD="${INFOBLOX_PASSWORD}"
INFOBLOX_WAPI_VERSION="${INFOBLOX_WAPI_VERSION}"

# Optional: Service Ports
INFOBLOX_SWAGGER_PORT="${INFOBLOX_SWAGGER_PORT}"
INFOBLOX_OPENWEBUI_PORT="${INFOBLOX_OPENWEBUI_PORT}"
INFOBLOX_FLASK_PORT="${INFOBLOX_FLASK_PORT}"

# Optional: API Keys
GROK_API_KEY="${GROK_API_KEY}"
GROK_API_BASE_URL="${GROK_API_BASE_URL}"

# Optional: Paths
INFOBLOX_WORK_DIR="${INFOBLOX_WORK_DIR}"

# Optional: Security Settings
INFOBLOX_SSL_VERIFY="${INFOBLOX_SSL_VERIFY}"
INFOBLOX_DEBUG="${INFOBLOX_DEBUG}"
EOF
    
    # Set restrictive permissions
    chmod 600 "$work_dir/$env_file"
    print_status "SUCCESS" "Configuration saved with restricted permissions (600)"
}

# Main setup function
main() {
    echo "========================================="
    echo "Infoblox WAPI NLP System - Secure Setup"
    echo "========================================="
    echo
    
    # Check prerequisites
    print_status "INFO" "Checking prerequisites..."
    for cmd in docker python3 pip3 jq; do
        if ! command -v $cmd &>/dev/null; then
            print_status "ERROR" "$cmd is not installed. Please install it."
            exit 1
        fi
    done
    print_status "SUCCESS" "All prerequisites installed"
    
    # Check if Docker is running
    if ! docker info --format '{{.ServerVersion}}' &>/dev/null; then
        print_status "ERROR" "Docker is not running. Please start Docker."
        exit 1
    fi
    print_status "SUCCESS" "Docker is running"
    
    # Try to load existing .env file
    if ! load_env_file ".env"; then
        print_status "WARNING" "No .env file found. Will create one."
    fi
    
    echo
    echo "========================================="
    echo "Configuration Setup"
    echo "========================================="
    echo
    
    # Prompt for required configuration
    print_status "INFO" "Please provide the following configuration:"
    echo
    
    prompt_for_env_var "INFOBLOX_GRID_MASTER_IP" "Grid Master IP address" false ""
    prompt_for_env_var "INFOBLOX_USERNAME" "Infoblox username" false "admin"
    prompt_for_env_var "INFOBLOX_PASSWORD" "Infoblox password" true ""
    prompt_for_env_var "INFOBLOX_WAPI_VERSION" "WAPI version" false "v2.13.1"
    
    # Optional configuration with defaults
    prompt_for_env_var "INFOBLOX_SWAGGER_PORT" "Swagger UI port" false "8080"
    prompt_for_env_var "INFOBLOX_OPENWEBUI_PORT" "Open WebUI port" false "3000"
    prompt_for_env_var "INFOBLOX_FLASK_PORT" "Flask API port" false "5000"
    
    # API Keys
    echo
    prompt_for_env_var "GROK_API_KEY" "Grok API key (optional, press Enter to skip)" false ""
    prompt_for_env_var "GROK_API_BASE_URL" "Grok API URL" false "https://api.x.ai/v1"
    
    # Paths
    prompt_for_env_var "INFOBLOX_WORK_DIR" "Working directory" false "$HOME/infoblox-wapi-nlp"
    
    # Security settings
    prompt_for_env_var "INFOBLOX_SSL_VERIFY" "Enable SSL verification (true/false)" false "false"
    prompt_for_env_var "INFOBLOX_DEBUG" "Enable debug mode (true/false)" false "false"
    
    # Set derived variables
    export INFOBLOX_SCHEMA_DIR="$INFOBLOX_WORK_DIR/schemas"
    export INFOBLOX_PYTHON_ENV="$INFOBLOX_WORK_DIR/venv"
    export INFOBLOX_LOG_FILE="$INFOBLOX_WORK_DIR/wapi_nlp.log"
    export INFOBLOX_TRAINING_DATA_FILE="$INFOBLOX_WORK_DIR/training_data.csv"
    
    # Create directories
    print_status "INFO" "Creating directories..."
    mkdir -p "$INFOBLOX_WORK_DIR" "$INFOBLOX_SCHEMA_DIR" "$INFOBLOX_WORK_DIR/templates"
    
    # Save configuration
    save_env_file ".env"
    
    # Also create .env.example without sensitive data
    cat > "$INFOBLOX_WORK_DIR/.env.example" << EOF
# Infoblox WAPI Configuration Template
# Copy this file to .env and fill in your values

# Required: Grid Master Configuration
INFOBLOX_GRID_MASTER_IP=192.168.1.222
INFOBLOX_USERNAME=admin
INFOBLOX_PASSWORD=your_password_here
INFOBLOX_WAPI_VERSION=v2.13.1

# Optional: Service Ports
INFOBLOX_SWAGGER_PORT=8080
INFOBLOX_OPENWEBUI_PORT=3000
INFOBLOX_FLASK_PORT=5000

# Optional: API Keys
GROK_API_KEY=your_grok_api_key_here
GROK_API_BASE_URL=https://api.x.ai/v1

# Optional: Paths
INFOBLOX_WORK_DIR=$HOME/infoblox-wapi-nlp

# Optional: Security Settings
INFOBLOX_SSL_VERIFY=false
INFOBLOX_DEBUG=false
EOF
    
    echo
    echo "========================================="
    echo "Testing Configuration"
    echo "========================================="
    echo
    
    # Test configuration with Python
    print_status "INFO" "Testing configuration with Python..."
    python3 << EOF
import os
import sys
sys.path.insert(0, '.')

try:
    from config import get_config
    config = get_config('$INFOBLOX_WORK_DIR/.env')
    print("✓ Configuration loaded successfully")
    print(f"  Grid Master: {config.get('GRID_MASTER_IP')}")
    print(f"  WAPI URL: {config.get_wapi_url()}")
    print(f"  Work Dir: {config.get('WORK_DIR')}")
except Exception as e:
    print(f"✗ Configuration error: {e}")
    sys.exit(1)
EOF
    
    if [ $? -eq 0 ]; then
        print_status "SUCCESS" "Configuration test passed"
    else
        print_status "ERROR" "Configuration test failed"
        exit 1
    fi
    
    echo
    echo "========================================="
    echo "Docker Compose Setup"
    echo "========================================="
    echo
    
    # Create Docker Compose file with environment variables
    print_status "INFO" "Creating docker-compose.yml..."
    cat > "$INFOBLOX_WORK_DIR/docker-compose.yml" << EOF
version: '3.8'
services:
  infoblox-swagger:
    image: vsethia/infoblox-wapi-swagger:v3
    ports:
      - "\${INFOBLOX_SWAGGER_PORT:-8080}:80"
    container_name: infoblox-swagger
    environment:
      - GRID_MASTER_IP=\${INFOBLOX_GRID_MASTER_IP}
      - WAPI_VERSION=\${INFOBLOX_WAPI_VERSION}
    restart: unless-stopped
    
  open-webui:
    image: ghcr.io/open-webui/open-webui:main
    ports:
      - "\${INFOBLOX_OPENWEBUI_PORT:-3000}:8080"
    container_name: open-webui
    environment:
      - GROK_API_KEY=\${GROK_API_KEY}
      - GROK_API_BASE_URL=\${GROK_API_BASE_URL:-https://api.x.ai/v1}
    restart: unless-stopped
    volumes:
      - open-webui-data:/app/backend/data

volumes:
  open-webui-data:
EOF
    
    print_status "SUCCESS" "Docker Compose configuration created"
    
    # Start Docker services
    print_status "INFO" "Starting Docker services..."
    cd "$INFOBLOX_WORK_DIR"
    if docker-compose up -d; then
        print_status "SUCCESS" "Docker services started"
        echo
        print_status "INFO" "Services available at:"
        echo "  - Swagger UI: http://localhost:${INFOBLOX_SWAGGER_PORT}"
        echo "  - Open WebUI: http://localhost:${INFOBLOX_OPENWEBUI_PORT}"
    else
        print_status "WARNING" "Failed to start Docker services"
    fi
    
    echo
    echo "========================================="
    echo "Python Environment Setup"
    echo "========================================="
    echo
    
    # Set up Python environment
    print_status "INFO" "Creating Python virtual environment..."
    python3 -m venv "$INFOBLOX_PYTHON_ENV"
    
    print_status "INFO" "Installing Python dependencies..."
    source "$INFOBLOX_PYTHON_ENV/bin/activate"
    pip install --upgrade pip
    pip install requests spacy transformers torch pandas openai flask python-dotenv
    python -m spacy download en_core_web_sm
    deactivate
    
    print_status "SUCCESS" "Python environment ready"
    
    echo
    echo "========================================="
    echo "Setup Complete!"
    echo "========================================="
    echo
    print_status "SUCCESS" "Secure configuration has been created"
    echo
    echo "Configuration files created:"
    echo "  - $INFOBLOX_WORK_DIR/.env (your configuration)"
    echo "  - $INFOBLOX_WORK_DIR/.env.example (template for sharing)"
    echo "  - $INFOBLOX_WORK_DIR/docker-compose.yml"
    echo
    echo "To use this configuration:"
    echo "  1. Source the environment: source $INFOBLOX_WORK_DIR/.env"
    echo "  2. Or use the Python config module: from config import get_config"
    echo
    echo "Security notes:"
    echo "  - .env file has restricted permissions (600)"
    echo "  - Never commit .env to version control"
    echo "  - Share .env.example instead"
    echo "  - Consider using a secrets manager in production"
    echo
    print_status "INFO" "Next step: Run the application with: python wapi_nlp.py"
}

# Run main function
main "$@"