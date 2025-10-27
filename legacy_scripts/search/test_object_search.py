#!/usr/bin/env python3
"""Test script for the ObjectSearchTool."""

import asyncio
import logging
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.agent.tools import ObjectSearchTool
from src.agent.memory import SearchMemory

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

class MockCar:
    """Mock car controller for testing."""
    
    def __init__(self):
        self.position = (0, 0, 0)  # x, y, heading
    
    async def move_forward(self, distance: float, speed: float = 0.5) -> None:
        """Simulate moving forward."""
        logger.info(f"Moving forward {distance}m at speed {speed}")
        await asyncio.sleep(abs(distance) / speed)
        self.position = (
            self.position[0] + distance * math.cos(math.radians(self.position[2])),
            self.position[1] + distance * math.sin(math.radians(self.position[2])),
            self.position[2]
        )
    
    async def turn(self, degrees: float, speed: float = 0.5) -> None:
        """Simulate turning in place."""
        logger.info(f"Turning {degrees} degrees at speed {speed}")
        await asyncio.sleep(abs(degrees) / (90 * speed))  # Rough estimate
        self.position = (
            self.position[0],
            self.position[1],
            (self.position[2] + degrees) % 360
        )

class MockVisionSystem:
    """Mock vision system for testing."""
    
    def __init__(self, objects_to_find=None):
        """Initialize with a list of objects to 'find' at specific positions."""
        self.objects_to_find = objects_to_find or []
    
    async def detect_objects(self, image=None):
        """Simulate object detection."""
        # In a real implementation, this would process an image
        return self.objects_to_find

async def test_object_search():
    """Test the ObjectSearchTool with mock components."""
    logger.info("Starting object search test")
    
    # Set up test environment
    car = MockCar()
    
    # Create a mock vision system that will find a ball at (2, 1)
    vision_system = MockVisionSystem([
        {'name': 'ball', 'confidence': 0.85, 'position': (2, 1, 0)}
    ])
    
    # Create the search tool
    search_tool = ObjectSearchTool(car, vision_system)
    
    # Test searching for the ball
    logger.info("Starting search for 'ball'")
    result = await search_tool.execute(object_name="ball", timeout=30)
    
    logger.info(f"Search result: {result}")
    
    if result.get('object_found'):
        logger.info(f"Found {result['object_name']} at {result['position']} with {result['confidence']:.1%} confidence")
    else:
        logger.warning("Failed to find the object")

if __name__ == "__main__":
    import math  # Import here to avoid circular import in MockCar
    asyncio.run(test_object_search())
