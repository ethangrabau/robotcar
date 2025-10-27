#!/usr/bin/env python3
"""
Test script for the ApproachObjectTool

This script demonstrates how to use the ObjectSearchTool and ApproachObjectTool together
to find and approach objects in the environment.
"""

import os
import sys
import time
import asyncio
import argparse
import logging
from pathlib import Path

# Add the parent directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('approach_test.log')
    ]
)
logger = logging.getLogger('approach_test')

# Import the tools
try:
    from src.agent.tools.object_search_tool import ObjectSearchTool
    from src.agent.tools.approach_object_tool import ApproachObjectTool
except ImportError as e:
    logger.error(f"Failed to import tools: {e}")
    sys.exit(1)

async def main():
    """Main function to run the test"""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Test the ApproachObjectTool')
    parser.add_argument('--object', type=str, default='ball', help='Object to search for')
    parser.add_argument('--timeout', type=int, default=30, help='Search timeout in seconds')
    parser.add_argument('--confidence', type=float, default=0.6, help='Confidence threshold (0.0-1.0)')
    parser.add_argument('--min-distance', type=int, default=15, help='Minimum approach distance in cm')
    parser.add_argument('--max-approach-time', type=int, default=30, help='Maximum approach time in seconds')
    parser.add_argument('--search-only', action='store_true', help='Only perform search, no approach')
    args = parser.parse_args()
    
    # Print test configuration
    print(f"🔍 Testing object search and approach for: {args.object}")
    print(f"⚙️ Configuration:")
    print(f"   - Search timeout: {args.timeout}s")
    print(f"   - Confidence threshold: {args.confidence}")
    print(f"   - Minimum approach distance: {args.min_distance}cm")
    print(f"   - Maximum approach time: {args.max_approach_time}s")
    print(f"   - Search only mode: {'Yes' if args.search_only else 'No'}")
    
    try:
        # Initialize the search tool
        search_tool = ObjectSearchTool()
        
        # Step 1: Search for the object
        print(f"\n🔍 Step 1: Searching for {args.object}...")
        search_result = await search_tool.execute(
            object_name=args.object,
            timeout=args.timeout,
            confidence_threshold=args.confidence
        )
        
        print(f"\n📊 Search Results:")
        print(f"   - Success: {'✅' if search_result.get('found', False) else '❌'}")
        print(f"   - Search time: {search_result.get('search_time', 0):.1f}s")
        print(f"   - Confidence: {search_result.get('confidence', 0):.2f}")
        print(f"   - Position: {search_result.get('position', 'unknown')}")
        print(f"   - Message: {search_result.get('message', '')}")
        
        # If search was successful and we're not in search-only mode, approach the object
        if search_result.get('found', False) and not args.search_only:
            # Initialize the approach tool
            approach_tool = ApproachObjectTool()
            
            # Step 2: Approach the object
            print(f"\n🚗 Step 2: Approaching {args.object}...")
            approach_result = await approach_tool.execute(
                object_name=args.object,
                position=search_result.get('position', 'center'),
                confidence=search_result.get('confidence', 0.6),
                max_approach_time=args.max_approach_time,
                min_distance=args.min_distance
            )
            
            print(f"\n📊 Approach Results:")
            print(f"   - Success: {'✅' if approach_result.get('success', False) else '❌'}")
            print(f"   - Approach time: {approach_result.get('approach_time', 0):.1f}s")
            print(f"   - Approach steps: {approach_result.get('approach_steps', 0)}")
            print(f"   - Final distance: {approach_result.get('final_distance', 0):.1f}cm")
            print(f"   - Message: {approach_result.get('message', '')}")
            
            # Clean up resources
            approach_tool.cleanup()
        
        # Clean up search tool resources
        search_tool.cleanup()
        
        print("\n✅ Test completed!")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        print(f"\n❌ Test failed: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    # Check for OpenAI API key
    if not os.environ.get('OPENAI_API_KEY'):
        # Try to load from .env file
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass
        
        if not os.environ.get('OPENAI_API_KEY'):
            print("⚠️ OPENAI_API_KEY environment variable not set!")
            print("Please set it before running this script:")
            print("export OPENAI_API_KEY='your-api-key'")
            sys.exit(1)
    
    # Run the async main function
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
