#!/bin/bash
# Script to deploy the agent code to a Raspberry Pi

# Configuration
PI_IP="192.168.0.151"  # Update this with your Pi's IP
PI_USER="pi"
PI_PASSWORD="raspberry"  # Default password
PI_PATH="~/family-robot"
LOCAL_AGENT_DIR="./src/agent"
LOCAL_SCRIPTS_DIR="./scripts"
REMOTE_AGENT_DIR="$PI_PATH/src/agent"
REMOTE_SCRIPTS_DIR="$PI_PATH/scripts"
SSH_KEY="$HOME/.ssh/id_rsa"  # Path to SSH key if using key-based auth

# Check for command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --ip) PI_IP="$2"; shift 2 ;;
        --user) PI_USER="$2"; shift 2 ;;
        --password) PI_PASSWORD="$2"; shift 2 ;;
        --path) PI_PATH="$2"; shift 2 ;;
        --key) SSH_KEY="$2"; shift 2 ;;
        *) echo "Unknown parameter: $1"; exit 1 ;;
    esac
done

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to run SSH commands with password
run_ssh() {
    sshpass -p "$PI_PASSWORD" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 "$PI_USER@$PI_IP" "$@"
}

# Function to run SCP with password
run_scp() {
    sshpass -p "$PI_PASSWORD" scp -o StrictHostKeyChecking=no -o ConnectTimeout=5 "$@"
}

# Function to print status messages
status() {
    echo -e "${GREEN}[*]${NC} $1"
}

error() {
    echo -e "${RED}[!]${NC} $1"
    exit 1
}

# Check if rsync is available
if ! command -v rsync &> /dev/null; then
    error "rsync is required but not installed. Please install it with 'brew install rsync'"
fi

# Check connection to Pi
status "Checking connection to Raspberry Pi..."
if ! run_ssh "exit"; then
    error "Failed to connect to Raspberry Pi at $PI_IP"
fi

# Create remote directories
status "Creating remote directories..."
run_ssh "mkdir -p $REMOTE_AGENT_DIR/tools $REMOTE_AGENT_DIR/memory $REMOTE_SCRIPTS_DIR"

# Sync agent code
status "Syncing agent code..."
rsync -avz -e "sshpass -p $PI_PASSWORD ssh -o StrictHostKeyChecking=no" \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    $LOCAL_AGENT_DIR/ $PI_USER@$PI_IP:$REMOTE_AGENT_DIR/

# Sync test scripts
status "Syncing test scripts..."
run_ssh "touch $PI_PATH/src/__init__.py $REMOTE_AGENT_DIR/__init__.py $REMOTE_AGENT_DIR/tools/__init__.py $REMOTE_AGENT_DIR/memory/__init__.py"
run_scp "$LOCAL_SCRIPTS_DIR/integration_test.py" "$PI_USER@$PI_IP:$PI_PATH/"
run_ssh "chmod +x $PI_PATH/integration_test.py"

# Deploy hardware integration components
status "Deploying hardware integration components..."
run_scp "$LOCAL_AGENT_DIR/hardware_integration.py" "$PI_USER@$PI_IP:$REMOTE_AGENT_DIR/"
run_scp "$LOCAL_AGENT_DIR/agent_system.py" "$PI_USER@$PI_IP:$REMOTE_AGENT_DIR/"
run_scp "$LOCAL_AGENT_DIR/tools/enhanced_search_tool.py" "$PI_USER@$PI_IP:$REMOTE_AGENT_DIR/tools/"

# Install dependencies
status "Installing Python dependencies..."
run_ssh "cd $PI_PATH && pip install -r requirements-agent.txt 2>/dev/null || echo 'No requirements file found, skipping'"

status "${GREEN}Deployment complete!${NC}"
echo "Agent code has been deployed to $PI_IP:$REMOTE_AGENT_DIR"
echo "Run the integration test with: python3 $PI_PATH/integration_test.py --object-name ball --timeout 30"
