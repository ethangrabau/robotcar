#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
PI_USER="pi"
PI_IP="192.168.0.151"
PI_PASSWORD="raspberry"
PI_PATH="/home/pi/Robot_Car"
SOURCE_FILE="/Users/ethangrabau/Robot_Car/src/agent/tools/object_search_tool.py"
DEST_DIR="$PI_PATH/src/agent/tools"
FLEXIBLE_SEARCH_SCRIPT="/tmp/robot_car_transfer/pi_flexible_search.sh"
PI_FLEXIBLE_SEARCH_PATH="$PI_PATH/scripts"

# Check if files exist
if [ ! -f "$SOURCE_FILE" ]; then
    echo "Error: Source file $SOURCE_FILE not found"
    exit 1
fi

if [ ! -f "$FLEXIBLE_SEARCH_SCRIPT" ]; then
    echo "Error: Flexible search script $FLEXIBLE_SEARCH_SCRIPT not found"
    exit 1
fi

echo -e "${YELLOW}Deploying enhanced object approach functionality...${NC}"

# Transfer the updated object_search_tool.py to the Pi
echo -e "${GREEN}Transferring updated object_search_tool.py to Raspberry Pi...${NC}"
sshpass -p "$PI_PASSWORD" scp "$SOURCE_FILE" "$PI_USER@$PI_IP:$DEST_DIR/"

if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to transfer object_search_tool.py. Check connection to Pi.${NC}"
    exit 1
fi

# Transfer the flexible search script to the Pi
echo -e "${GREEN}Transferring flexible search script to Raspberry Pi...${NC}"
sshpass -p "$PI_PASSWORD" scp "$FLEXIBLE_SEARCH_SCRIPT" "$PI_USER@$PI_IP:$PI_FLEXIBLE_SEARCH_PATH/pi_flexible_search.sh"

if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to transfer pi_flexible_search.sh. Check connection to Pi.${NC}"
    exit 1
fi

# Make the script executable
echo -e "${GREEN}Making pi_flexible_search.sh executable on the Pi...${NC}"
sshpass -p "$PI_PASSWORD" ssh "$PI_USER@$PI_IP" "chmod +x $PI_FLEXIBLE_SEARCH_PATH/pi_flexible_search.sh"

echo -e "${GREEN}Deployment complete!${NC}"
echo -e "${YELLOW}To test the updated approach algorithm, run this command from your computer:${NC}"
echo -e "${GREEN}sshpass -p \"$PI_PASSWORD\" ssh $PI_USER@$PI_IP \"cd $PI_PATH && python -m src.agent.tools.object_search_tool banana 120 0.6\"${NC}"
echo -e "${YELLOW}Or use the flexible search script:${NC}"
echo -e "${GREEN}sshpass -p \"$PI_PASSWORD\" ssh $PI_USER@$PI_IP \"$PI_FLEXIBLE_SEARCH_PATH/pi_flexible_search.sh banana 120 0.6\"${NC}"
echo -e "${YELLOW}Try with different objects and positions to test the improved approach behavior${NC}"
echo -e "${YELLOW}For example:${NC}"
echo -e "${GREEN}sshpass -p \"$PI_PASSWORD\" ssh $PI_USER@$PI_IP \"cd $PI_PATH && python -m src.agent.tools.object_search_tool water_bottle 120 0.6\"${NC}"
