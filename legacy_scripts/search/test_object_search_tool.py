#!/usr/bin/env python3
"""
Test script for the ObjectSearchTool
This script demonstrates how to use the ObjectSearchTool with the agent architecture
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

# Import our modules
try:
    from src.agent.tools.object_search_tool import ObjectSearchTool
except ImportError as e:
    logger.error(f"Error importing ObjectSearchTool: {e}")
    # Try a direct import as fallback
    sys.path.append(os.path.join(parent_dir, 'src', 'agent', 'tools'))
    from object_search_tool import ObjectSearchTool

# Mock hardware and vision for testing if not available
class MockCar:
    def __init__(self):
        self.px = None
    def cleanup(self):
        pass

class MockVision:
    def __init__(self):
        self.camera_initialized = False
        self.openai_client = None
    def cleanup(self):
        pass

def get_hardware():
    try:
        from src.agent.hardware_bridge import get_hardware
        return get_hardware()
    except ImportError:
        logger.warning("Hardware bridge not available, using mock")
        return MockCar()

def get_gpt_vision():
    try:
        from src.vision.gpt_vision import get_gpt_vision
        return get_gpt_vision()
    except ImportError:
        logger.warning("Vision system not available, using mock")
        return MockVision()

async def main():
    """Main function to test the ObjectSearchTool"""
    parser = argparse.ArgumentParser(description='Test the ObjectSearchTool')
    parser.add_argument('--object', type=str, default='tennis ball', help='Object to search for')
    parser.add_argument('--timeout', type=int, default=60, help='Search timeout in seconds')
    parser.add_argument('--confidence', type=float, default=0.5, help='Confidence threshold (0.0-1.0)')
    parser.add_argument('--area', type=str, default=None, help='Area to search in (optional)')
    args = parser.parse_args()
    
    try:
        # Initialize hardware and vision system
        print(f"🤖 Initializing hardware and vision system...")
        car = get_hardware()
        vision = get_gpt_vision()
        
        # Create the object search tool
        search_tool = ObjectSearchTool(car=car, vision_system=vision)
        
        # Execute the search
        print(f"🔍 Starting search for {args.object} with timeout {args.timeout}s...")
        result = await search_tool.execute(
            object_name=args.object,
            search_area=args.area,
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
        if 'car' in locals():
            car.cleanup()
        if 'vision' in locals():
            vision.cleanup()
        print("🧹 Cleaned up resources")

if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
