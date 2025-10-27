#!/usr/bin/env python3
"""
Standalone test script for the ObjectSearchTool
This script can be run directly on the Raspberry Pi to test the object search functionality
"""

import os
import sys
import time
import asyncio
import logging
import argparse
from pathlib import Path

# Add parent directory to path to import modules
parent_dir = str(Path(__file__).parent.parent)
sys.path.insert(0, parent_dir)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('object_search_test.log')
    ]
)
logger = logging.getLogger(__name__)

# Import the ObjectSearchTool class
sys.path.append(os.path.join(parent_dir, 'src', 'agent', 'tools'))
from object_search_tool import ObjectSearchTool

async def main():
    """Main function to test the ObjectSearchTool"""
    parser = argparse.ArgumentParser(description='Test the ObjectSearchTool')
    parser.add_argument('--object', type=str, default='tennis ball', help='Object to search for')
    parser.add_argument('--timeout', type=int, default=60, help='Search timeout in seconds')
    parser.add_argument('--confidence', type=float, default=0.5, help='Confidence threshold (0.0-1.0)')
    args = parser.parse_args()
    
    try:
        # Create the object search tool with direct hardware access
        print(f"🤖 Initializing object search tool...")
        search_tool = ObjectSearchTool()
        
        # Execute the search
        print(f"🔍 Starting search for {args.object} with timeout {args.timeout}s...")
        result = await search_tool.execute(
            object_name=args.object,
            timeout=args.timeout,
            confidence_threshold=args.confidence
        )
        
        # Display the result
        if result["success"]:
            print(f"✅ {result['message']}")
            print(f"📍 Position: {result.get('position', 'unknown')}")
            print(f"🎯 Confidence: {result.get('confidence', 0.0):.1%}")
            print(f"🕒 Search time: {result['search_time']:.1f}s")
        else:
            print(f"❌ {result['message']}")
            print(f"🕒 Search time: {result.get('search_time', 0.0):.1f}s")
        
    except KeyboardInterrupt:
        print("\n🛑 Search interrupted by user")
    except Exception as e:
        logger.error(f"Error: {e}")
        print(f"❌ Error: {e}")
    finally:
        # Clean up resources
        if 'search_tool' in locals():
            search_tool.cleanup()
        print("🧹 Cleaned up resources")

if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
