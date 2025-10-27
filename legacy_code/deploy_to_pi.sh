#!/bin/bash
# Script to deploy updated files to Raspberry Pi

# Set your Raspberry Pi's IP address here
PI_IP="192.168.0.151"
PI_USER="pi"
PI_PATH="~/picar-x/gpt_examples"

# Add debug flags
SET_DEBUG=true  # Set to true to enable debug mode on the Pi
MAX_RETRIES=3   # Number of retries for each SCP command

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Deploying files to Raspberry Pi at ${PI_IP}...${NC}"

# Function to copy a file with retries
copy_file() {
    local src=$1
    local dest=$2
    local retry_count=0
    
    while [ $retry_count -lt $MAX_RETRIES ]; do
        echo -e "${GREEN}Copying $src to $dest (attempt $(($retry_count+1))/${MAX_RETRIES})...${NC}"
        scp "$src" "$dest"
        
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}Successfully copied $src${NC}"
            return 0
        else
            echo -e "${YELLOW}Failed to copy $src, retrying...${NC}"
            retry_count=$((retry_count+1))
            sleep 2
        fi
    done
    
    echo -e "${YELLOW}Failed to copy $src after $MAX_RETRIES attempts${NC}"
    return 1
}

# Copy the files to the Raspberry Pi
NEW_AGENT_CAR_PATH="/Users/ethangrabau/Robot_Car/new_agent_car.py"
copy_file "/Users/ethangrabau/Robot_Car/fixed_preset_actions.py" "${PI_USER}@${PI_IP}:${PI_PATH}/preset_actions.py"
copy_file "/Users/ethangrabau/Robot_Car/object_search.py" "${PI_USER}@${PI_IP}:${PI_PATH}/object_search.py"
echo "Copying $NEW_AGENT_CAR_PATH to ${PI_USER}@${PI_IP}:${PI_PATH}/agent_car.py (attempt 1/3)..."
copy_file "$NEW_AGENT_CAR_PATH" "${PI_USER}@${PI_IP}:${PI_PATH}/agent_car.py"
copy_file "/Users/ethangrabau/Robot_Car/reset_gpio.py" "${PI_USER}@${PI_IP}:${PI_PATH}/reset_gpio.py"

# Set debug mode if enabled
if [ "$SET_DEBUG" = true ]; then
    echo -e "${YELLOW}Setting debug mode on the Pi...${NC}"
    ssh ${PI_USER}@${PI_IP} "echo 'export DEBUG_MODE=true' > ${PI_PATH}/debug_mode.sh"
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}Debug mode set successfully${NC}"
    else
        echo -e "${YELLOW}Failed to set debug mode${NC}"
    fi
fi

echo -e "${YELLOW}Deployment complete!${NC}"
echo -e "${YELLOW}To run the updated code on your Pi, use:${NC}"
echo -e "${GREEN}sudo python3 agent_car.py${NC}"

echo -e "${YELLOW}If the Pi becomes unresponsive, you can try:${NC}"
echo -e "${GREEN}ssh ${PI_USER}@${PI_IP} 'sudo reboot'${NC}"
