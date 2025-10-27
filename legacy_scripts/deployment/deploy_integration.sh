#!/bin/bash
# Script to deploy the integration components to the Pi

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

warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

# Check connection to Pi
status "Checking connection to Raspberry Pi..."
if ! sshpass -p "$PI_PASSWORD" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 "$PI_USER@$PI_IP" "exit"; then
    error "Failed to connect to Raspberry Pi at $PI_IP"
fi

# Deploy hardware bridge
status "Deploying hardware bridge..."
sshpass -p "$PI_PASSWORD" scp -o StrictHostKeyChecking=no \
    ./src/agent/hardware_bridge.py \
    "$PI_USER@$PI_IP:$PI_PATH/src/agent/"

# Deploy integration test script
status "Deploying integration test script..."
sshpass -p "$PI_PASSWORD" scp -o StrictHostKeyChecking=no \
    ./scripts/integrated_search_test.py \
    "$PI_USER@$PI_IP:$PI_PATH/"

# Make the test script executable
status "Making test script executable..."
sshpass -p "$PI_PASSWORD" ssh -o StrictHostKeyChecking=no "$PI_USER@$PI_IP" \
    "chmod +x $PI_PATH/integrated_search_test.py"

status "${GREEN}Deployment complete!${NC}"
echo "Integration components have been deployed to $PI_IP:$PI_PATH/"
echo "Run the test with: python3 ~/family-robot/integrated_search_test.py [object_name] [timeout]"
