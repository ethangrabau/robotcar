#!/usr/bin/env python3
"""
Integrated test for object search with hardware bridge
Combines the agent tools with the hardware bridge for a complete test
"""

import os
import sys
import time
import asyncio
import logging
from pathlib import Path

# Add the project root to the Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('integrated_search.log')
    ]
)
logger = logging.getLogger(__name__)

# Import our components
try:
    from src.agent.hardware_bridge import get_hardware
    from src.agent.tools.object_search_tool import ObjectSearchTool
    from src.agent.memory.search_memory import SearchMemory
    logger.info("Successfully imported agent components")
except ImportError as e:
    logger.error(f"Failed to import agent components: {e}")
    sys.exit(1)

class SimpleVisionSystem:
    """
    Simple vision system for testing
    In a real implementation, this would use the camera and GPT-4 Vision
    """
    
    def __init__(self, mock_objects=None):
        self.mock_objects = mock_objects or []
        self.scan_count = 0
    
    async def detect_objects(self, image=None):
        """Simulate object detection with increasingly likely detection"""
        self.scan_count += 1
        logger.info(f"Scanning for objects (scan #{self.scan_count})")
        
        # If we have mock objects and this is the 3rd scan, "find" them
        if self.mock_objects and self.scan_count >= 3:
            logger.info(f"Found objects: {self.mock_objects}")
            return self.mock_objects
        
        # Otherwise, return empty list (nothing found)
        logger.info("No objects detected")
        return []

async def run_integrated_test(object_name="ball", timeout=30):
    """Run an integrated test of the object search with hardware bridge"""
    logger.info(f"Starting integrated test for object: {object_name}")
    
    try:
        # Get the hardware controller
        hardware = get_hardware()
        if not hardware.initialized and hardware.HARDWARE_AVAILABLE:
            logger.error("Failed to initialize hardware")
            return
        
        # Create a simple vision system that will find our object after a few scans
        vision = SimpleVisionSystem([
            {'name': object_name, 'confidence': 0.85, 'position': (2, 1, 0)}
        ])
        
        # Create a search memory
        memory = SearchMemory()
        
        # Create the object search tool
        search_tool = ObjectSearchTool(
            car=hardware,
            vision_system=vision,
            memory=memory
        )
        
        # Run the search
        logger.info(f"Starting search for {object_name}")
        start_time = time.time()
        result = await search_tool.execute(
            object_name=object_name,
            timeout=timeout
        )
        elapsed = time.time() - start_time
        
        # Log the result
        if result.get('status') == 'success':
            logger.info(f"✅ Found {object_name} at {result.get('location')} in {elapsed:.1f}s")
            print(f"✅ Found {object_name} at {result.get('location')} in {elapsed:.1f}s")
        else:
            logger.warning(f"❌ Failed to find {object_name}: {result.get('message')}")
            print(f"❌ Failed to find {object_name}: {result.get('message')}")
        
        return result
    
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Clean up hardware
        if 'hardware' in locals() and hardware:
            hardware.cleanup()

def main():
    """Main entry point"""
    # Parse command line arguments
    if len(sys.argv) > 1:
        object_name = sys.argv[1]
    else:
        object_name = "ball"
    
    timeout = 30
    if len(sys.argv) > 2:
        try:
            timeout = int(sys.argv[2])
        except ValueError:
            pass
    
    print(f"Starting integrated search test for '{object_name}' with {timeout}s timeout")
    
    try:
        # Run the test
        asyncio.run(run_integrated_test(object_name, timeout))
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
