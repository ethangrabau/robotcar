#!/bin/bash
# Set up OpenAI API key for PiCar-X vision search

echo "Setting up OpenAI API key for PiCar-X vision search..."

# Check if API key is provided
if [ -z "$1" ]; then
  echo "Please provide your OpenAI API key as an argument"
  echo "Usage: ./setup_api_key.sh YOUR_API_KEY"
  exit 1
fi

# Create keys.py file with API key
echo "Creating keys.py file..."
cat > ~/family-robot/keys.py << EOF
# OpenAI API key
OPENAI_API_KEY = "$1"

# Optional: Assistant ID if you're using OpenAI Assistants API
OPENAI_ASSISTANT_ID = ""
EOF

echo "API key set up successfully!"
echo "You can now run the backpack finder with: ./backpack_finder.py"
