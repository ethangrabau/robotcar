#!/bin/bash

# Script to generate a code dump of all files in the repository
# Creates code-dump.txt with file paths and contents

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Output file
OUTPUT_FILE="code-dump.txt"
REPO_ROOT="/Users/ethangrabau/Robot_Car"
EXCLUDE_DIRS=("__pycache__" "venv" ".git" "legacy_scripts" ".idea" ".vscode")
EXCLUDE_EXTENSIONS=("pyc" "jpg" "jpeg" "png" "gif" "zip" "tar" "gz" "mp3" "mp4" "wav" "pdf")

# Change to repository root
cd "$REPO_ROOT" || { echo -e "${RED}Error: Could not change to repository root${NC}"; exit 1; }

# Clear or create output file
echo "# Robot Car Code Dump - $(date)" > "$OUTPUT_FILE"
echo "# Repository: $REPO_ROOT" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

# Function to check if directory should be excluded
is_excluded_dir() {
  local dir="$1"
  for excluded in "${EXCLUDE_DIRS[@]}"; do
    if [[ "$dir" == *"/$excluded"* || "$dir" == *"/$excluded" ]]; then
      return 0 # True, should exclude
    fi
  done
  return 1 # False, should not exclude
}

# Function to check if file should be excluded based on extension
is_excluded_extension() {
  local file="$1"
  local ext="${file##*.}"
  for excluded in "${EXCLUDE_EXTENSIONS[@]}"; do
    if [[ "$ext" == "$excluded" ]]; then
      return 0 # True, should exclude
    fi
  done
  return 1 # False, should not exclude
}

# Function to process a file
process_file() {
  local file="$1"
  local rel_path="${file#$REPO_ROOT/}"
  
  # Skip files with excluded extensions
  if is_excluded_extension "$file"; then
    echo -e "${YELLOW}Skipping binary/large file: $rel_path${NC}"
    return
  fi
  
  # Skip very large files (>1MB)
  local size=$(wc -c < "$file")
  if (( size > 1000000 )); then
    echo -e "${YELLOW}Skipping large file ($size bytes): $rel_path${NC}"
    return
  fi
  
  echo -e "${GREEN}Processing: $rel_path${NC}"
  
  # Add file header to output
  echo "##################################################" >> "$OUTPUT_FILE"
  echo "# FILE: $rel_path" >> "$OUTPUT_FILE"
  echo "##################################################" >> "$OUTPUT_FILE"
  echo "" >> "$OUTPUT_FILE"
  
  # Add file content
  cat "$file" >> "$OUTPUT_FILE"
  
  # Add newlines after file
  echo "" >> "$OUTPUT_FILE"
  echo "" >> "$OUTPUT_FILE"
}

# Find all files and process them
echo -e "${GREEN}Generating code dump...${NC}"
file_count=0

while IFS= read -r -d '' file; do
  dir=$(dirname "$file")
  
  # Skip excluded directories
  if is_excluded_dir "$dir"; then
    continue
  fi
  
  process_file "$file"
  ((file_count++))
done < <(find "$REPO_ROOT" -type f -not -path "*/\.*" -print0)

# Add summary at the end
echo "# End of code dump - $file_count files included" >> "$OUTPUT_FILE"

echo -e "${GREEN}Code dump generated: $OUTPUT_FILE${NC}"
echo -e "${GREEN}Included $file_count files${NC}"
echo -e "${YELLOW}You can now upload this file to ChatGPT for analysis${NC}"
