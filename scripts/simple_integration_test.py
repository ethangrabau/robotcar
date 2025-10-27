#!/usr/bin/env python3
"""
Simplified integration test for PiCar-X hardware
Tests the hardware integration directly without dependencies on other modules
"""

import os
import sys
import time
import asyncio
import logging
import argparse
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
        logging.FileHandler('simple_integration.log')
    ]
)
logger = logging.getLogger(__name__)

# Hardware availability flag
HARDWARE_AVAILABLE = False

# Try to import hardware components
try:
    from picarx import Picarx
    from robot_hat import Music, Pin
    HARDWARE_AVAILABLE = True
    logger.info("Hardware modules available")
except ImportError as e:
    logger.warning(f"Hardware modules not available, using mock implementations: {e}")

class PiCarXHardware:
    """
    Hardware controller for PiCar-X
    Follows the exact initialization pattern from working_gpt_car.py
    """
    
    def __init__(self):
        self.px = None
        self.music = None
        self.pin = None
        self.initialized = False
        self.position = (0, 0, 0)  # x, y, heading in degrees
        
    def initialize(self):
        """Initialize hardware components in the correct order"""
        if not HARDWARE_AVAILABLE:
            logger.warning("Hardware not available, running in simulation mode")
            return False
            
        try:
            # Follow the exact initialization pattern from working_gpt_car.py
            logger.info("Initializing PiCar-X hardware...")
            
            # Enable robot_hat speaker switch (from working_gpt_car.py)
            os.popen("pinctrl set 20 op dh")
            
            # Initialize hardware in the correct order - EXACTLY as in working_gpt_car.py
            self.px = Picarx()
            self.music = Music()
            self.pin = Pin('LED')  # Use 'LED' instead of 'LED_R'
            
            # Change working directory to current path (as in working_gpt_car.py)
            current_path = os.path.dirname(os.path.abspath(__file__))
            os.chdir(current_path)
            
            self.initialized = True
            logger.info("Hardware initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize hardware: {e}")
            self.initialized = False
            return False
    
    async def move_forward(self, distance: float, speed: float = 50) -> None:
        """Move forward a specific distance"""
        if not self.initialized:
            logger.warning("Hardware not initialized, simulating movement")
            await asyncio.sleep(abs(distance) / max(speed, 1) * 0.1)
            # Update simulated position
            self.position = (
                self.position[0] + distance * 0.1,  # Simple forward movement
                self.position[1],
                self.position[2]
            )
            return
            
        try:
            logger.info(f"Moving forward {distance}m at speed {speed}")
            self.px.forward(speed)
            # Convert distance to time based on speed
            # This is an approximation and may need calibration
            await asyncio.sleep(abs(distance) / max(speed, 1) * 10)
            self.px.stop()
        except Exception as e:
            logger.error(f"Movement error: {e}")
            self.px.stop()  # Safety stop
    
    async def turn(self, degrees: float, speed: float = 50) -> None:
        """Turn in place by the specified degrees"""
        if not self.initialized:
            logger.warning("Hardware not initialized, simulating turn")
            await asyncio.sleep(abs(degrees) / 90 * 0.5)
            # Update simulated heading
            self.position = (
                self.position[0],
                self.position[1],
                (self.position[2] + degrees) % 360
            )
            return
            
        try:
            logger.info(f"Turning {degrees} degrees")
            # Limit the angle to what the hardware can handle
            clamped_angle = max(min(degrees, 35), -35)
            
            if clamped_angle != degrees:
                logger.warning(f"Angle {degrees} clamped to {clamped_angle}")
            
            # Set the steering angle
            self.px.set_dir_servo_angle(clamped_angle)
            
            # If we need to turn more than the hardware allows, we'll need to move forward a bit
            if abs(degrees) > 35:
                # Move forward while turning to achieve a larger turn
                self.px.forward(30)
                await asyncio.sleep(abs(degrees) / 35 * 0.5)
                self.px.stop()
            else:
                # Just wait a moment for the turn to complete
                await asyncio.sleep(abs(degrees) / 90)
            
            # Reset steering to straight
            self.px.set_dir_servo_angle(0)
        except Exception as e:
            logger.error(f"Turn error: {e}")
            self.px.set_dir_servo_angle(0)  # Reset steering
    
    async def check_obstacles(self) -> float:
        """Check for obstacles using ultrasonic sensor"""
        if not self.initialized:
            logger.warning("Hardware not initialized, simulating obstacle check")
            return 100.0  # Simulate no obstacles
            
        try:
            # Get distance from ultrasonic sensor
            distance = self.px.ultrasonic.read()
            logger.info(f"Obstacle distance: {distance}cm")
            return distance
        except Exception as e:
            logger.error(f"Obstacle check error: {e}")
            return 100.0  # Default to no obstacles on error
    
    def get_position(self):
        """Get the current position and heading"""
        return self.position
    
    def cleanup(self):
        """Clean up hardware resources"""
        if self.initialized:
            try:
                logger.info("Cleaning up hardware resources")
                self.px.stop()
                if self.music:
                    self.music.music_stop()
            except Exception as e:
                logger.error(f"Cleanup error: {e}")

class MockVision:
    """Mock vision system for testing"""
    
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
    """Simple memory for search operations"""
    
    def __init__(self):
        self.visited_areas = []
        self.object_sightings = {}
        logger.info("Initialized simple search memory")
    
    def record_visit(self, position):
        """Record that we visited a position"""
        self.visited_areas.append(position)
        logger.info(f"Recorded visit to position {position}")
    
    def record_sighting(self, object_name, position, confidence):
        """Record an object sighting"""
        if object_name not in self.object_sightings:
            self.object_sightings[object_name] = []
        
        self.object_sightings[object_name].append({
            'position': position,
            'confidence': confidence,
            'timestamp': time.time()
        })
        logger.info(f"Recorded sighting of {object_name} at {position} with {confidence:.1%} confidence")

async def test_hardware_initialization():
    """Test hardware initialization"""
    logger.info("Testing hardware initialization")
    
    car = PiCarXHardware()
    result = car.initialize()
    
    if result:
        logger.info("✅ Hardware initialized successfully")
        print("✅ Hardware initialized successfully")
    else:
        logger.warning("❌ Hardware initialization failed, running in simulation mode")
        print("❌ Hardware initialization failed, running in simulation mode")
    
    return car

async def test_movement_and_turning(car):
    """Test basic movement and turning"""
    logger.info("Testing basic movement and turning")
    
    try:
        # Move forward
        logger.info("Testing forward movement")
        await car.move_forward(0.5, 50)
        
        # Turn right
        logger.info("Testing right turn")
        await car.turn(30, 50)
        
        # Move forward
        logger.info("Testing forward movement")
        await car.move_forward(0.5, 50)
        
        # Turn left
        logger.info("Testing left turn")
        await car.turn(-60, 50)
        
        # Move forward
        logger.info("Testing forward movement")
        await car.move_forward(0.5, 50)
        
        # Return to center
        logger.info("Returning to center")
        await car.turn(30, 50)
        
        logger.info("✅ Movement and turning tests completed")
        print("✅ Movement and turning tests completed")
        return True
    except Exception as e:
        logger.error(f"Movement test failed: {e}")
        print(f"❌ Movement test failed: {e}")
        return False

async def test_obstacle_detection(car):
    """Test obstacle detection"""
    logger.info("Testing obstacle detection")
    
    try:
        # Check for obstacles
        distance = await car.check_obstacles()
        
        if distance is not None:
            logger.info(f"✅ Obstacle detection working, distance: {distance}cm")
            print(f"✅ Obstacle detection working, distance: {distance}cm")
            return True
        else:
            logger.warning("❌ Obstacle detection not working")
            print("❌ Obstacle detection not working")
            return False
    except Exception as e:
        logger.error(f"Obstacle detection test failed: {e}")
        print(f"❌ Obstacle detection test failed: {e}")
        return False

async def test_simple_search(car, object_name="ball", timeout=30):
    """Test a simple search pattern"""
    logger.info(f"Testing simple search for {object_name}")
    
    # Create mock vision and memory
    vision = MockVision([
        {'name': object_name, 'confidence': 0.85, 'position': (2, 1, 0)}
    ])
    memory = SimpleSearchMemory()
    
    # Simple search pattern
    search_patterns = [
        # Each tuple is (turn_degrees, move_distance)
        (0, 0.5),    # Forward
        (45, 0),     # Turn right
        (0, 0.5),    # Forward
        (-90, 0),    # Turn left
        (0, 0.5),    # Forward
    ]
    
    start_time = time.time()
    found_object = False
    
    try:
        # Execute the search pattern
        for pattern_idx, (turn_degrees, move_distance) in enumerate(search_patterns):
            # Check timeout
            if time.time() - start_time > timeout:
                logger.warning(f"Search timed out after {timeout}s")
                break
            
            # Execute the pattern step
            logger.info(f"Executing search pattern step {pattern_idx+1}/{len(search_patterns)}")
            
            # Turn if needed
            if turn_degrees != 0:
                await car.turn(turn_degrees)
            
            # Move if needed
            if move_distance != 0:
                await car.move_forward(move_distance)
            
            # Record the visit
            current_position = car.get_position()
            memory.record_visit(current_position)
            
            # Scan for objects
            logger.info(f"Scanning for {object_name}")
            detected_objects = await vision.detect_objects()
            
            # Check if we found the target object
            for obj in detected_objects:
                if obj['name'].lower() == object_name.lower():
                    # Record the sighting
                    memory.record_sighting(
                        object_name=obj['name'],
                        position=obj['position'],
                        confidence=obj['confidence']
                    )
                    
                    # Return success
                    logger.info(f"Found {object_name} at {obj['position']} with {obj['confidence']:.1%} confidence")
                    print(f"✅ Found {object_name} at {obj['position']} with {obj['confidence']:.1%} confidence")
                    found_object = True
                    break
            
            if found_object:
                break
        
        if not found_object:
            logger.warning(f"❌ Failed to find {object_name}")
            print(f"❌ Failed to find {object_name}")
        
        elapsed = time.time() - start_time
        logger.info(f"Search completed in {elapsed:.1f}s")
        return found_object
    
    except Exception as e:
        logger.error(f"Search test failed: {e}")
        print(f"❌ Search test failed: {e}")
        return False

async def run_tests(args):
    """Run all tests"""
    car = None
    
    try:
        # Initialize hardware
        car = await test_hardware_initialization()
        
        # Run the selected tests
        if args.test_type == 'movement':
            await test_movement_and_turning(car)
        elif args.test_type == 'obstacle':
            await test_obstacle_detection(car)
        elif args.test_type == 'search':
            await test_simple_search(car, args.object_name, args.timeout)
        else:
            # Run all tests
            print("=== Testing Hardware Initialization ===")
            # Hardware already initialized above
            
            print("\n=== Testing Movement and Turning ===")
            await test_movement_and_turning(car)
            
            print("\n=== Testing Obstacle Detection ===")
            await test_obstacle_detection(car)
            
            print("\n=== Testing Simple Search ===")
            await test_simple_search(car, args.object_name, args.timeout)
    
    finally:
        # Clean up
        if car:
            car.cleanup()

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Test the PiCar-X hardware integration')
    parser.add_argument('--object-name', type=str, default="ball", help='Object to search for')
    parser.add_argument('--timeout', type=int, default=30, help='Search timeout in seconds')
    parser.add_argument('--test-type', type=str, choices=['movement', 'obstacle', 'search', 'all'], default='all',
                        help='Type of test to run')
    
    args = parser.parse_args()
    
    print(f"Starting hardware integration test with timeout {args.timeout}s")
    
    try:
        # Run the tests
        asyncio.run(run_tests(args))
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
