#!/usr/bin/env python3
"""
Vision-based search test for PiCar-X
Uses GPT-4 Vision to search for specific objects
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
        logging.FileHandler('vision_search.log')
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

async def vision_search(car, vision, object_name="backpack", timeout=60, confidence_threshold=0.6):
    """
    Search for an object using vision
    Uses a spiral search pattern and GPT-4 Vision for object detection
    """
    logger.info(f"Starting vision search for {object_name}")
    print(f"🔍 Searching for {object_name}...")
    
    # Create memory
    memory = SimpleSearchMemory()
    
    # Spiral search pattern parameters
    spiral_steps = 5  # Number of steps in the spiral
    step_size = 0.3   # Distance to move in each step (meters)
    turn_angle = 45   # Angle to turn after each step (degrees)
    
    start_time = time.time()
    found_object = False
    
    try:
        # Execute the spiral search pattern
        for step in range(spiral_steps):
            # Check timeout
            if time.time() - start_time > timeout:
                logger.warning(f"Search timed out after {timeout}s")
                print(f"⏱️ Search timed out after {timeout}s")
                break
            
            # Calculate step distance (increases with spiral)
            step_distance = step_size * (1 + step * 0.2)
            
            # Check for obstacles
            distance = await car.check_obstacles()
            if distance < 20:  # Less than 20cm
                logger.warning(f"Obstacle detected at {distance}cm, turning to avoid")
                print(f"⚠️ Obstacle detected at {distance}cm, turning to avoid")
                await car.turn(90)  # Turn away from obstacle
                continue
            
            # Move forward
            logger.info(f"Moving forward {step_distance}m (step {step+1}/{spiral_steps})")
            await car.move_forward(step_distance)
            
            # Record the visit
            current_position = car.get_position()
            memory.record_visit(current_position)
            
            # Scan for objects with vision
            logger.info(f"Scanning for {object_name}")
            print(f"📸 Taking a picture and analyzing with GPT-4 Vision...")
            
            # Capture image and detect objects
            detected_objects = await vision.detect_objects()
            
            # Check if we found the target object
            for obj in detected_objects:
                obj_name = obj['name'].lower()
                confidence = obj['confidence']
                
                # Check if this matches our target object
                if object_name.lower() in obj_name and confidence >= confidence_threshold:
                    # Record the sighting
                    memory.record_sighting(
                        object_name=obj['name'],
                        position=obj['position'],
                        confidence=confidence
                    )
                    
                    # Return success
                    logger.info(f"Found {obj_name} at {obj['position']} with {confidence:.1%} confidence")
                    print(f"✅ Found {obj_name} at {obj['position']} with {confidence:.1%} confidence!")
                    found_object = True
                    break
                else:
                    # Log other objects seen
                    logger.info(f"Saw {obj_name} with {confidence:.1%} confidence, but looking for {object_name}")
                    print(f"👁️ Saw {obj_name} with {confidence:.1%} confidence, but looking for {object_name}")
            
            if found_object:
                break
            
            # Turn for next step in spiral
            logger.info(f"Turning {turn_angle} degrees")
            await car.turn(turn_angle)
        
        if not found_object:
            logger.warning(f"❌ Failed to find {object_name}")
            print(f"❌ Failed to find {object_name}")
        
        elapsed = time.time() - start_time
        logger.info(f"Search completed in {elapsed:.1f}s")
        print(f"🕒 Search completed in {elapsed:.1f}s")
        
        return found_object, memory.object_sightings
    
    except Exception as e:
        logger.error(f"Vision search failed: {e}")
        print(f"❌ Vision search failed: {e}")
        return False, {}

async def run_vision_search(args):
    """Run the vision-based search"""
    car = None
    vision = None
    
    try:
        # Initialize hardware
        car = PiCarXHardware()
        result = car.initialize()
        
        if result:
            logger.info("✅ Hardware initialized successfully")
            print("✅ Hardware initialized successfully")
        else:
            logger.warning("❌ Hardware initialization failed, running in simulation mode")
            print("❌ Hardware initialization failed, running in simulation mode")
        
        # Initialize vision
        try:
            # Import the GPT Vision module
            from src.vision.gpt_vision import get_gpt_vision
            vision = get_gpt_vision()
            logger.info("Vision system initialized")
            print("📷 Vision system initialized")
        except Exception as e:
            logger.error(f"Failed to initialize vision: {e}")
            print(f"❌ Failed to initialize vision: {e}")
            return
        
        # Run the vision search
        found, sightings = await vision_search(
            car=car,
            vision=vision,
            object_name=args.object_name,
            timeout=args.timeout,
            confidence_threshold=args.confidence
        )
        
        # Print summary of what we found
        if found:
            print("\n=== Search Results ===")
            print(f"✅ Successfully found {args.object_name}!")
            
            # Print details of all sightings
            for obj_name, obj_sightings in sightings.items():
                print(f"\n{obj_name}:")
                for sighting in obj_sightings:
                    print(f"  - Position: {sighting['position']}, Confidence: {sighting['confidence']:.1%}")
        else:
            print("\n=== Search Results ===")
            print(f"❌ Did not find {args.object_name}")
            
            # Print what we did see
            if sightings:
                print("\nOther objects detected:")
                for obj_name, obj_sightings in sightings.items():
                    print(f"  - {obj_name}: {len(obj_sightings)} sightings")
    
    finally:
        # Clean up
        if car:
            car.cleanup()
        
        if vision:
            vision.cleanup()

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Vision-based search for PiCar-X')
    parser.add_argument('--object-name', type=str, default="backpack", help='Object to search for')
    parser.add_argument('--timeout', type=int, default=60, help='Search timeout in seconds')
    parser.add_argument('--confidence', type=float, default=0.6, help='Confidence threshold (0-1)')
    
    args = parser.parse_args()
    
    print(f"Starting vision search for {args.object_name} with timeout {args.timeout}s")
    
    try:
        # Run the vision search
        asyncio.run(run_vision_search(args))
    except KeyboardInterrupt:
        print("\nSearch interrupted by user")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
