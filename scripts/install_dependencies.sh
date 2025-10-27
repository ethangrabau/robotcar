#!/bin/bash
# Install dependencies for PiCar-X vision search

echo "Installing dependencies for PiCar-X vision search..."

# Update package lists
echo "Updating package lists..."
sudo apt-get update

# Install Python dependencies
echo "Installing Python dependencies..."
pip3 install --upgrade pip
pip3 install openai
pip3 install opencv-python
pip3 install gtts

# Check if dependencies are installed
echo "Checking if dependencies are installed..."
python3 -c "import openai; print('OpenAI installed successfully')" || echo "Failed to install OpenAI"
python3 -c "import cv2; print('OpenCV installed successfully')" || echo "Failed to install OpenCV"
python3 -c "import gtts; print('gTTS installed successfully')" || echo "Failed to install gTTS"

echo "Dependency installation complete!"
