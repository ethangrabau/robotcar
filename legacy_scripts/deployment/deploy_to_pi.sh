#!/bin/bash
# Script to deploy the robot code to a Raspberry Pi

# Configuration
PI_IP="192.168.0.151"  # Update this with your Pi's IP
PI_USER="pi"
PI_PASSWORD="raspberry"  # Default password
PI_PATH="~/family-robot"
LOCAL_DIR="."
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

# Install sshpass if not installed
if ! command -v sshpass &> /dev/null; then
    echo "sshpass not found. Installing..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        brew install hudochenkov/sshpass/sshpass
    else
        sudo apt-get update && sudo apt-get install -y sshpass
    fi
fi

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
    echo -e "${RED}[!] Error: $1${NC}" >&2
    exit 1
}

# Check if rsync is available
if ! command -v rsync &> /dev/null; then
    error "rsync is required but not installed. Please install it with 'brew install rsync'"
fi

# Check if SSH access is configured
status "Testing SSH connection to ${PI_USER}@${PI_IP}..."
if ! run_ssh exit; then
    error "SSH connection to ${PI_USER}@${PI_IP} failed. Please ensure:
  1. The Pi is powered on and connected to the network
  2. SSH is enabled on the Pi
  3. You have the correct IP address and credentials"
fi

# Create remote directory if it doesn't exist
status "Setting up remote directory..."
run_ssh "mkdir -p ${PI_PATH}/src" || error "Failed to create remote directory"

# Sync the code using rsync with password authentication
status "Synchronizing code..."
rsync -avz \
    --rsh="sshpass -p $PI_PASSWORD ssh -o StrictHostKeyChecking=no -l $PI_USER" \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.env' \
    --exclude='venv' \
    ${LOCAL_DIR}/src/ ${PI_IP}:${PI_PATH}/src/

# Copy requirements and setup files
rsync -avz \
    --rsh="sshpass -p $PI_PASSWORD ssh -o StrictHostKeyChecking=no -l $PI_USER" \
    requirements.txt \
    setup.py \
    ${LOCAL_DIR}/ ${PI_IP}:${PI_PATH}/

# Install dependencies
status "Installing Python dependencies..."
run_ssh "
    # Install system dependencies
    sudo apt-get update && \
    sudo apt-get install -y python3-pip python3-picamera2 python3-opencv \
    python3-numpy python3-pygame python3-serial python3-venv python3-pip

    # Create and activate virtual environment
    cd ${PI_PATH} && \
    python3 -m venv venv && \
    source venv/bin/activate && \
    
    # Upgrade pip and install wheel
    pip install --upgrade pip wheel && \
    
    # Install robot-hat from source if not available
    if ! python -c "import robot_hat" 2>/dev/null; then
        echo "Installing robot-hat from source..."
        git clone https://github.com/sunfounder/robot-hat.git /tmp/robot-hat && \
        cd /tmp/robot-hat && \
        pip install . && \
        cd - >/dev/null
    fi
    
    # Install requirements
    pip install -r requirements.txt --no-deps && \
    
    # Install picamera2 if not already installed
    if ! python -c "import picamera2" 2>/dev/null; then
        pip install picamera2
    fi
" || error "Failed to install dependencies"

# Install system dependencies
status "Installing system dependencies..."
run_ssh "
    sudo apt-get update && \
    sudo apt-get install -y python3-pip python3-venv python3-dev python3-picamera2 \
    python3-opencv python3-numpy python3-pygame python3-serial
" || error "Failed to install system dependencies"

# Set up udev rules for hardware access
status "Setting up udev rules..."
cat << EOF | run_ssh "sudo tee /etc/udev/rules.d/99-picarx.rules" > /dev/null
# USB Serial devices
SUBSYSTEM=="tty", ATTRS{idVendor}=="1a86", ATTRS{idProduct}=="7523", MODE="0666"
# I2C devices
SUBSYSTEM=="i2c-dev", GROUP="i2c", MODE="0666"
# SPI devices
SUBSYSTEM=="spidev", GROUP="spi", MODE="0666"
EOF

# Reload udev rules
run_ssh "sudo udevadm control --reload-rules && sudo udevadm trigger"

# Add user to required groups
status "Configuring user permissions..."
run_ssh "
    sudo usermod -a -G gpio,spi,i2c,audio,video,plugdev $PI_USER && \
    echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.bashrc
"

# Create a test script on the Pi
status "Creating test script on the Pi..."
cat << 'EOF' | run_ssh "cat > ${PI_PATH}/test_robot.sh"
#!/bin/bash
# Test script for the robot

# Activate virtual environment
source venv/bin/activate

# Run hardware tests
python -m scripts.test_hardware

# Run unit tests
python -m pytest tests/unit/ -v
EOF

# Make the test script executable
run_ssh "chmod +x ${PI_PATH}/test_robot.sh"

status "Deployment complete!"
echo -e "\nTo run the robot, use:"
echo -e "  ${YELLOW}./deploy_to_pi.sh --run-tests${NC}  # Run tests on the Pi"
echo -e "  ${YELLOW}./deploy_to_pi.sh --run-robot${NC}  # Start the robot on the Pi"
echo -e "  ${YELLOW}ssh ${PI_USER}@${PI_IP}${NC}           # SSH into the Pi"

# Handle command line flags
case "$1" in
    --run-tests)
        status "Running tests on the Pi..."
        run_ssh "cd ${PI_PATH} && ./test_robot.sh"
        ;;
    --run-robot)
        status "Starting robot on the Pi..."
        run_ssh "cd ${PI_PATH} && source venv/bin/activate && python -m src.main"
        ;;
esac
