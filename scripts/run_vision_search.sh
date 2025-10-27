#!/bin/bash
# Run vision search test with virtual environment

# Activate the virtual environment
source ~/family-robot/venv/bin/activate

# Set OpenAI API key if available
if [ -f ~/family-robot/keys.py ]; then
    echo "Using API key from keys.py"
    export OPENAI_API_KEY=$(python3 -c "from keys import OPENAI_API_KEY; print(OPENAI_API_KEY)")
fi

# Run the vision search test
cd ~/family-robot
python3 vision_search_test.py "$@"

# Deactivate the virtual environment
deactivate
