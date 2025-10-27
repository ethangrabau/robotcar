#!/usr/bin/env python3
"""
Simple test for object search functionality
Minimizes dependencies while testing core functionality
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
        logging.FileHandler('simple_search.log')
    ]
)
logger = logging.getLogger(__name__)

# Mock classes to avoid dependencies
class MockCar:
    """Mock car controller for testing."""
    
    def __init__(self):
        self.position = (0, 0, 0)  # x, y, heading
        logger.info("Initialized mock car")
    
    async def move_forward(self, distance, speed=50):
        logger.info(f"Mock: Moving forward {distance}m at speed {speed}")
        await asyncio.sleep(0.5)
        # Update position (simplified)
        self.position = (self.position[0] + distance, self.position[1], self.position[2])
    
    async def turn(self, degrees, speed=50):
        logger.info(f"Mock: Turning {degrees} degrees at speed {speed}")
        await asyncio.sleep(0.5)
        # Update heading (simplified)
        self.position = (self.position[0], self.position[1], 
                        (self.position[2] + degrees) % 360)
    
    def get_position(self):
        return self.position
    
    def cleanup(self):
        logger.info("Mock: Cleaning up car resources")

class MockVision:
    """Mock vision system for testing."""
    
    def __init__(self, objects_to_find=None):
        self.objects_to_find = objects_to_find or []
        self.scan_count = 0
        logger.info("Initialized mock vision system")
    
    async def detect_objects(self, image=None):
        """Simulate object detection with increasingly likely detection"""
        self.scan_count += 1
        logger.info(f"Mock: Scanning for objects (scan #{self.scan_count})")
        
        # If this is the 3rd scan, "find" the objects
        if self.scan_count >= 3:
            logger.info(f"Mock: Found objects: {self.objects_to_find}")
            return self.objects_to_find
        
        # Otherwise, return empty list (nothing found)
        logger.info("Mock: No objects detected")
        return []

class SimpleSearchMemory:
    """Simple memory for search operations."""
    
    def __init__(self):
        self.visited_areas = []
        self.object_sightings = {}
        logger.info("Initialized simple search memory")
    
    def record_visit(self, position):
        """Record that we visited a position."""
        self.visited_areas.append(position)
        logger.info(f"Recorded visit to position {position}")
    
    def record_sighting(self, object_name, position, confidence):
        """Record an object sighting."""
        if object_name not in self.object_sightings:
            self.object_sightings[object_name] = []
        
        self.object_sightings[object_name].append({
            'position': position,
            'confidence': confidence,
            'timestamp': time.time()
        })
        logger.info(f"Recorded sighting of {object_name} at {position} with {confidence:.1%} confidence")

class SimpleSearchTool:
    """Simple search tool implementation."""
    
    def __init__(self, car, vision_system, memory=None):
        self.car = car
        self.vision_system = vision_system
        self.memory = memory or SimpleSearchMemory()
        self.is_searching = False
        logger.info("Initialized simple search tool")
    
    async def execute(self, object_name, timeout=30):
        """Execute a search for the specified object."""
        logger.info(f"Starting search for {object_name}")
        self.is_searching = True
        start_time = time.time()
        
        try:
            # Simple search pattern
            search_patterns = [
                # Each tuple is (turn_degrees, move_distance)
                (0, 1),    # Forward
                (45, 0),   # Turn right
                (0, 1),    # Forward
                (-90, 0),  # Turn left
                (0, 1),    # Forward
            ]
            
            # Execute the search pattern
            for pattern_idx, (turn_degrees, move_distance) in enumerate(search_patterns):
                # Check timeout
                if time.time() - start_time > timeout:
                    logger.warning(f"Search timed out after {timeout}s")
                    return {
                        "status": "timeout",
                        "message": f"Search timed out after {timeout}s"
                    }
                
                # Execute the pattern step
                logger.info(f"Executing search pattern step {pattern_idx+1}/{len(search_patterns)}")
                
                # Turn if needed
                if turn_degrees != 0:
                    await self.car.turn(turn_degrees)
                
                # Move if needed
                if move_distance != 0:
                    await self.car.move_forward(move_distance)
                
                # Record the visit
                current_position = self.car.get_position()
                self.memory.record_visit(current_position)
                
                # Scan for objects
                logger.info(f"Scanning for {object_name}")
                detected_objects = await self.vision_system.detect_objects()
                
                # Check if we found the target object
                for obj in detected_objects:
                    if obj['name'].lower() == object_name.lower():
                        # Record the sighting
                        self.memory.record_sighting(
                            object_name=obj['name'],
                            position=obj['position'],
                            confidence=obj['confidence']
                        )
                        
                        # Return success
                        logger.info(f"Found {object_name} at {obj['position']} with {obj['confidence']:.1%} confidence")
                        return {
                            "status": "success",
                            "object_name": object_name,
                            "location": obj['position'],
                            "confidence": obj['confidence']
                        }
            
            # If we get here, we didn't find the object
            logger.warning(f"Failed to find {object_name}")
            return {
                "status": "not_found",
                "message": f"Failed to find {object_name} after completing search pattern"
            }
            
        finally:
            self.is_searching = False
            elapsed = time.time() - start_time
            logger.info(f"Search completed in {elapsed:.1f}s")

async def run_test(object_name="ball", timeout=30):
    """Run a test of the simple search tool."""
    logger.info(f"Starting test for object: {object_name}")
    
    try:
        # Create mock components
        car = MockCar()
        vision = MockVision([
            {'name': object_name, 'confidence': 0.85, 'position': (2, 1, 0)}
        ])
        memory = SimpleSearchMemory()
        
        # Create the search tool
        search_tool = SimpleSearchTool(car, vision, memory)
        
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
        # Clean up
        if 'car' in locals() and car:
            car.cleanup()

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
    
    print(f"Starting simple search test for '{object_name}' with {timeout}s timeout")
    
    try:
        # Run the test
        asyncio.run(run_test(object_name, timeout))
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
