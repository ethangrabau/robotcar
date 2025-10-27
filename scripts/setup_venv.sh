#!/bin/bash
# Set up a virtual environment for PiCar-X vision search

echo "Setting up virtual environment for PiCar-X vision search..."

# Install python3-venv if not already installed
echo "Installing python3-venv..."
sudo apt-get update
sudo apt-get install -y python3-venv python3-full

# Create a virtual environment
echo "Creating virtual environment..."
python3 -m venv ~/family-robot/venv

# Activate the virtual environment and install dependencies
echo "Installing dependencies in virtual environment..."
source ~/family-robot/venv/bin/activate
pip install --upgrade pip
pip install openai opencv-python gtts

# Check if dependencies are installed
echo "Checking if dependencies are installed..."
python -c "import openai; print('OpenAI installed successfully')" || echo "Failed to install OpenAI"
python -c "import cv2; print('OpenCV installed successfully')" || echo "Failed to install OpenCV"
python -c "import gtts; print('gTTS installed successfully')" || echo "Failed to install gTTS"

# Create an activation script for easy use
echo "Creating activation script..."
cat > ~/family-robot/activate_venv.sh << 'EOF'
#!/bin/bash
source ~/family-robot/venv/bin/activate
echo "Virtual environment activated. Run 'deactivate' to exit."
EOF

chmod +x ~/family-robot/activate_venv.sh

echo "Virtual environment setup complete!"
echo "To activate the virtual environment, run: source ~/family-robot/activate_venv.sh"
