#!/bin/bash
# Simplified script to deploy just the agent components to the Pi

# Configuration
PI_IP="192.168.0.151"
PI_USER="pi"
PI_PASSWORD="raspberry"
PI_PATH="~/family-robot"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print status messages
status() {
    echo -e "${GREEN}[*]${NC} $1"
}

error() {
    echo -e "${RED}[!]${NC} $1"
    exit 1
}

# Check connection to Pi
status "Checking connection to Raspberry Pi..."
if ! sshpass -p "$PI_PASSWORD" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 "$PI_USER@$PI_IP" "exit"; then
    error "Failed to connect to Raspberry Pi at $PI_IP"
fi

# Create directories if they don't exist
status "Creating directories on Pi..."
sshpass -p "$PI_PASSWORD" ssh -o StrictHostKeyChecking=no "$PI_USER@$PI_IP" "mkdir -p $PI_PATH/src/agent/tools $PI_PATH/src/agent/memory"

# Copy agent tools
status "Copying agent tools..."
sshpass -p "$PI_PASSWORD" scp -o StrictHostKeyChecking=no \
    ./src/agent/tools/__init__.py \
    ./src/agent/tools/base_tool.py \
    ./src/agent/tools/registry.py \
    ./src/agent/tools/object_search_tool.py \
    "$PI_USER@$PI_IP:$PI_PATH/src/agent/tools/"

# Copy agent memory
status "Copying agent memory..."
sshpass -p "$PI_PASSWORD" scp -o StrictHostKeyChecking=no \
    ./src/agent/memory/__init__.py \
    ./src/agent/memory/search_memory.py \
    "$PI_USER@$PI_IP:$PI_PATH/src/agent/memory/"

# Copy integration module
status "Copying integration module..."
sshpass -p "$PI_PASSWORD" scp -o StrictHostKeyChecking=no \
    ./src/agent/integration.py \
    "$PI_USER@$PI_IP:$PI_PATH/src/agent/"

# Create __init__.py if it doesn't exist
status "Setting up Python package structure..."
sshpass -p "$PI_PASSWORD" ssh -o StrictHostKeyChecking=no "$PI_USER@$PI_IP" "touch $PI_PATH/src/agent/__init__.py"

# Copy test script
status "Copying test script..."
sshpass -p "$PI_PASSWORD" scp -o StrictHostKeyChecking=no \
    ./scripts/test_agent.py \
    "$PI_USER@$PI_IP:$PI_PATH/"

status "${GREEN}Deployment complete!${NC}"
echo "Agent code has been deployed to $PI_IP:$PI_PATH/src/agent/"
echo "Run test with: python $PI_PATH/test_agent.py"
