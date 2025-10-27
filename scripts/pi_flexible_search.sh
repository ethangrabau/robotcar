#!/bin/bash
# Flexible script to search for and approach any object with configurable parameters
# Designed to run directly on the Raspberry Pi

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Display usage if help flag is provided
if [[ "$1" == "-h" || "$1" == "--help" ]]; then
  echo -e "${YELLOW}Usage: ./pi_flexible_search.sh <object_name> <timeout_seconds> [confidence_threshold]${NC}"
  echo ""
  echo "Parameters:"
  echo "  <object_name>         The object to search for (e.g., 'books', 'chair', 'water bottle')"
  echo "  <timeout_seconds>     Maximum time in seconds for the search (e.g., 60, 90)"
  echo "  [confidence_threshold] Optional confidence threshold (0.0-1.0, default: 0.6)"
  echo ""
  echo "Examples:"
  echo "  ./pi_flexible_search.sh 'coffee mug' 45"
  echo "  ./pi_flexible_search.sh 'laptop' 60 0.7"
  exit 0
fi

# Parse command line arguments with defaults
OBJECT="${1:-books}"
TIMEOUT="${2:-60}"
CONFIDENCE="${3:-0.6}"

# Validate parameters
if ! [[ "$TIMEOUT" =~ ^[0-9]+$ ]]; then
  echo -e "${RED}❌ Error: Timeout must be a positive integer${NC}"
  echo "Run ./pi_flexible_search.sh --help for usage information"
  exit 1
fi

if (( $(echo "$CONFIDENCE < 0.0" | bc -l) )) || (( $(echo "$CONFIDENCE > 1.0" | bc -l) )); then
  echo -e "${RED}❌ Error: Confidence threshold must be between 0.0 and 1.0${NC}"
  echo "Run ./pi_flexible_search.sh --help for usage information"
  exit 1
fi

echo -e "${YELLOW}🚀 Running search and approach for '$OBJECT' with ${TIMEOUT}s timeout and ${CONFIDENCE} confidence threshold...${NC}"

# Ensure the API key is set
echo -e "${GREEN}🔑 Checking for OpenAI API key...${NC}"
if [ ! -f .env ]; then
  echo -e "${YELLOW}⚠️ No .env file found. Please ensure OPENAI_API_KEY is set in your environment.${NC}"
fi

# Run the search with the specified parameters
echo -e "${GREEN}🧪 Running search and approach test...${NC}"
echo -e "${GREEN}🔍 Looking for '$OBJECT' (timeout: ${TIMEOUT}s, confidence: ${CONFIDENCE})...${NC}"
echo -e "${YELLOW}⏳ This may take a while depending on the timeout value...${NC}"

# Execute the search command
python -m scripts.test_object_search_standalone --object "$OBJECT" --timeout $TIMEOUT --confidence $CONFIDENCE

# Check the exit status
STATUS=$?
if [ $STATUS -eq 0 ]; then
  echo -e "${GREEN}✅ Test completed successfully!${NC}"
else
  echo -e "${RED}❌ Test encountered an error (exit code: $STATUS)${NC}"
fi
