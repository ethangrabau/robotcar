#!/usr/bin/env python3
"""
Backpack Finder for PiCar-X using vilib
Uses GPT-4 Vision to search for a backpack
Based on the working hardware initialization pattern from working_gpt_car.py
"""

import os
import sys
import time
import base64
import json
import logging
import argparse
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('backpack_finder.log')
    ]
)
logger = logging.getLogger(__name__)

# Try to import hardware components
try:
    # Following the exact import pattern from working_gpt_car.py
    from picarx import Picarx
    from robot_hat import Music, Pin
    HARDWARE_AVAILABLE = True
    logger.info("Hardware modules available")
except ImportError as e:
    logger.warning(f"Hardware modules not available: {e}")
    HARDWARE_AVAILABLE = False

# Try to import OpenAI
try:
    import openai
    OPENAI_AVAILABLE = True
    logger.info("OpenAI package available")
except ImportError:
    logger.warning("OpenAI package not available")
    OPENAI_AVAILABLE = False

# Try to import vilib for camera access
try:
    from vilib import Vilib
    import cv2
    CAMERA_AVAILABLE = True
    logger.info("vilib available for camera access")
except ImportError:
    logger.warning("vilib not available")
    CAMERA_AVAILABLE = False

# Check for OpenAI API key
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    try:
        from keys import OPENAI_API_KEY
        logger.info("OpenAI API key loaded from keys.py")
    except ImportError:
        logger.warning("OpenAI API key not found in environment or keys.py")
        OPENAI_API_KEY = None

class ObjectFinder:
    """
    PiCar-X robot that searches for a backpack using GPT-4 Vision
    """
    
    def __init__(self):
        """Initialize the backpack finder"""
        self.px = None
        self.music = None
        self.pin = None
        self.initialized = False
        self.openai_client = None
        self.camera_initialized = False
        
        # Initialize hardware
        self._init_hardware()
        
        # Initialize OpenAI client
        if OPENAI_AVAILABLE and OPENAI_API_KEY:
            try:
                self.openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)
                logger.info("OpenAI client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
        
        # Initialize camera using vilib (following gpt_car.py pattern)
        if CAMERA_AVAILABLE:
            try:
                # Initialize camera with vilib (exactly as in gpt_car.py)
                Vilib.camera_start(vflip=False, hflip=False)
                Vilib.display(local=False, web=True)
                
                # Wait for camera to initialize
                for _ in range(100):  # Wait up to 1 second
                    if hasattr(Vilib, 'flask_start') and Vilib.flask_start:
                        break
                    time.sleep(0.01)
                
                time.sleep(0.5)  # Additional wait time as in gpt_car.py
                self.camera_initialized = True
                logger.info("Camera initialized with vilib")
            except Exception as e:
                logger.error(f"Failed to initialize camera with vilib: {e}")
    
    def _init_hardware(self):
        """Initialize hardware components following working_gpt_car.py pattern"""
        if not HARDWARE_AVAILABLE:
            logger.warning("Hardware not available, running in simulation mode")
            return
        
        try:
            # Follow the exact initialization pattern from working_gpt_car.py
            logger.info("Initializing PiCar-X hardware...")
            
            # Enable robot_hat speaker switch (from working_gpt_car.py)
            os.popen("pinctrl set 20 op dh")
            
            # Initialize hardware in the correct order
            self.px = Picarx()
            self.music = Music()
            self.pin = Pin('LED')  # Use 'LED' as in working_gpt_car.py
            
            # Change working directory to current path (as in working_gpt_car.py)
            current_path = os.path.dirname(os.path.abspath(__file__))
            os.chdir(current_path)
            
            self.initialized = True
            logger.info("Hardware initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize hardware: {e}")
            self.initialized = False
    
    def move_forward(self, speed=50, duration=1.0):
        """Move forward at the specified speed for the specified duration"""
        if not self.initialized:
            logger.warning("Hardware not initialized, simulating movement")
            time.sleep(duration)
            return
        
        try:
            logger.info(f"Moving forward at speed {speed} for {duration}s")
            self.px.forward(speed)
            time.sleep(duration)
            self.px.stop()
        except Exception as e:
            logger.error(f"Movement error: {e}")
            if self.initialized:
                self.px.stop()  # Safety stop
    
    def turn(self, angle):
        """Turn by the specified angle"""
        if not self.initialized:
            logger.warning("Hardware not initialized, simulating turn")
            time.sleep(abs(angle) / 90)
            return
        
        try:
            logger.info(f"Turning {angle} degrees")
            # Limit the angle to what the hardware can handle
            clamped_angle = max(min(angle, 35), -35)
            
            if clamped_angle != angle:
                logger.warning(f"Angle {angle} clamped to {clamped_angle}")
            
            # Set the steering angle
            self.px.set_dir_servo_angle(clamped_angle)
            
            # If we need to turn more than the hardware allows, we'll need to move forward a bit
            if abs(angle) > 35:
                # Move forward while turning to achieve a larger turn
                self.px.forward(30)
                time.sleep(abs(angle) / 35 * 0.5)
                self.px.stop()
            else:
                # Just wait a moment for the turn to complete
                time.sleep(abs(angle) / 90)
            
            # Reset steering to straight
            self.px.set_dir_servo_angle(0)
        except Exception as e:
            logger.error(f"Turn error: {e}")
            if self.initialized:
                self.px.set_dir_servo_angle(0)  # Reset steering
    
    def check_distance(self):
        """Check distance using ultrasonic sensor with improved reliability"""
        if not self.initialized:
            logger.warning("Hardware not initialized")
            return 100  # Default safe distance
        
        try:
            # Take multiple readings to improve reliability
            readings = []
            for _ in range(3):
                distance = self.px.ultrasonic.read()
                # Filter out invalid readings (negative or very large values)
                if 0 <= distance < 300:  # Valid range: 0-300cm
                    readings.append(distance)
                time.sleep(0.05)  # Short delay between readings
            
            # Calculate average of valid readings
            if readings:
                avg_distance = sum(readings) / len(readings)
                return avg_distance
            else:
                logger.warning("No valid distance readings")
                return 100  # Default safe distance
        except Exception as e:
            logger.error(f"Distance sensor error: {e}")
            return 100  # Default safe distance on error
    
    def capture_image(self, save_path="current_view.jpg"):
        """Capture an image from the camera using vilib"""
        if not self.camera_initialized:
            logger.warning("Camera not initialized")
            return None
        
        try:
            # Get the current frame from vilib.img (as in gpt_car.py)
            if not hasattr(Vilib, 'img') or Vilib.img is None:
                logger.warning("No image available from vilib")
                return None
                
            # Save the image
            cv2.imwrite(save_path, Vilib.img)
            logger.info(f"Image captured and saved to {save_path}")
            return save_path
        except Exception as e:
            logger.error(f"Image capture error: {e}")
            return None
    
    def analyze_image_with_gpt4(self, image_path, object_name="tennis ball"):
        """Analyze an image using GPT-4 Vision to find objects"""
        if not self.openai_client:
            logger.warning("OpenAI client not available")
            return []
        
        if not os.path.exists(image_path):
            logger.warning(f"Image file not found: {image_path}")
            return []
        
        try:
            # Encode image to base64
            with open(image_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode('utf-8')
            
            # Call GPT-4 Vision API
            prompt = (
                "Identify all objects visible in this image. "
                "I'm particularly interested in finding a " + object_name + " if one is present. "
                "For each object, provide: "
                "1. The name of the object "
                "2. A confidence score between 0 and 1 "
                "3. The approximate position in the image (left/right/center, top/bottom/middle) "
                "Format your response as a JSON array of objects."
            )
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=1000
            )
            
            # Extract response
            result = response.choices[0].message.content
            logger.info(f"GPT-4 Vision response: {result}")
            
            # Try to parse JSON from the response
            try:
                # Look for JSON array in the response
                import re
                json_match = re.search(r'\[.*\]', result, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                    objects = json.loads(json_str)
                    return objects
            except Exception as e:
                logger.error(f"Failed to parse JSON from response: {e}")
            
            # If JSON parsing fails, return a simple representation
            return [{"name": "unknown", "confidence": 0.5, "position": "unknown"}]
        
        except Exception as e:
            logger.error(f"GPT-4 Vision API error: {e}")
            return []
    
    def search_for_object(self, object_name="tennis ball", timeout=60, confidence_threshold=0.6):
        """Search for a tennis ball using a comprehensive search pattern"""
        logger.info(f"Starting search for {object_name}")
        print(f"🔍 Searching for {object_name}...")
        
        start_time = time.time()
        found_object = False
        
        # First do a full 360-degree scan in place
        full_scan_angles = [0, 45, 90, 135, 180, 225, 270, 315, 0]  # Return to original position
        
        try:
            # First do a full 360-degree scan in place
            logger.info("Starting 360-degree scan")
            print("🔄 Starting 360-degree scan...")
            
            for angle in full_scan_angles:
                # Check timeout
                if time.time() - start_time > timeout:
                    logger.warning(f"Search timed out after {timeout}s")
                    print(f"⏱️ Search timed out after {timeout}s")
                    break
                
                # Turn to the specified angle
                if angle != 0 or full_scan_angles.index(angle) == 0:  # Skip the last 0 turn
                    logger.info(f"Turning to {angle} degrees for scan")
                    print(f"🔄 Turning to {angle} degrees for scan...")
                    
                    # Calculate relative angle to turn
                    if full_scan_angles.index(angle) == 0:
                        # First angle, just set position
                        self.turn(angle)
                    else:
                        # Calculate difference from previous angle
                        prev_angle = full_scan_angles[full_scan_angles.index(angle) - 1]
                        diff = angle - prev_angle
                        # Handle wrap-around (e.g., from 315 to 0)
                        if diff < -180:
                            diff += 360
                        elif diff > 180:
                            diff -= 360
                        self.turn(diff)
                
                # Scan at this angle
                logger.info(f"Scanning at {angle} degrees")
                print(f"📸 Taking a picture at {angle} degrees...")
                
                # Capture image
                image_path = self.capture_image()
                if not image_path:
                    logger.warning("Failed to capture image")
                    continue
                
                # Analyze image with GPT-4 Vision
                objects = self.analyze_image_with_gpt4(image_path, object_name)
                
                # Check if we found the object
                for obj in objects:
                    obj_name = obj.get("name", "").lower()
                    confidence = obj.get("confidence", 0)
                    position = obj.get("position", "unknown")
                    
                    if object_name.lower() in obj_name and confidence >= confidence_threshold:
                        logger.info(f"Found {object_name} with {confidence:.1%} confidence at {position}")
                        print(f"✅ Found {object_name} with {confidence:.1%} confidence at {position}!")
                        found_object = True
                        # Move toward the object
                        self.move_toward_object(position)
                        break
                    else:
                        # Log other objects seen
                        logger.info(f"Saw {obj_name} with {confidence:.1%} confidence")
                        print(f"👁️ Saw {obj_name} with {confidence:.1%} confidence")
                
                if found_object:
                    break
            
            # If object not found in initial scan, do a more thorough search
            if not found_object and time.time() - start_time < timeout:
                logger.info(f"{object_name} not found in initial scan, starting exploration")
                print(f"🔍 {object_name} not found in initial scan, exploring the area...")
                
                # Define a more thorough search pattern
                search_pattern = [
                    # Move forward and scan
                    ("forward", 0.5),
                    ("scan", None),
                    
                    # Turn right and scan
                    ("turn", 90),
                    ("scan", None),
                    
                    # Move forward and scan
                    ("forward", 0.5),
                    ("scan", None),
                    
                    # Turn left and scan
                    ("turn", -90),
                    ("scan", None),
                    
                    # Move forward and scan
                    ("forward", 0.5),
                    ("scan", None),
                    
                    # Turn left and scan
                    ("turn", -90),
                    ("scan", None),
                    
                    # Move forward and scan
                    ("forward", 0.5),
                    ("scan", None),
                ]
                
                for action, param in search_pattern:
                    # Check timeout
                    if time.time() - start_time > timeout:
                        logger.warning(f"Search timed out after {timeout}s")
                        print(f"⏱️ Search timed out after {timeout}s")
                        break
                    
                    # Check for obstacles
                    distance = self.check_distance()
                    if distance < 20:  # Less than 20cm
                        logger.warning(f"Obstacle detected at {distance}cm, adjusting path")
                        print(f"⚠️ Obstacle detected at {distance}cm, adjusting path")
                        
                        # Try to find a clear path
                        clear_path_found = False
                        for test_angle in [45, -45, 90, -90]:
                            self.turn(test_angle)
                            test_distance = self.check_distance()
                            if test_distance > 30:  # Found a clear path
                                logger.info(f"Found clear path at angle {test_angle}, distance {test_distance}cm")
                                print(f"🛣️ Found clear path, continuing search...")
                                clear_path_found = True
                                break
                        
                        if not clear_path_found:
                            logger.warning("No clear path found, reversing direction")
                            print("⚠️ No clear path found, reversing direction")
                            self.turn(180)
                        
                        continue
                    
                    # Execute the action
                    if action == "forward":
                        logger.info(f"Moving forward for {param}s")
                        print(f"🚗 Moving forward...")
                        self.move_forward(speed=50, duration=param)
                    
                    elif action == "turn":
                        logger.info(f"Turning {param} degrees")
                        print(f"🔄 Turning {param} degrees...")
                        self.turn(param)
                    
                    elif action == "scan":
                        logger.info("Scanning for " + object_name)
                        print(f"📸 Taking a picture and analyzing with GPT-4 Vision...")
                        
                        # Capture image
                        image_path = self.capture_image()
                        if not image_path:
                            logger.warning("Failed to capture image")
                            continue
                        
                        # Analyze image with GPT-4 Vision
                        objects = self.analyze_image_with_gpt4(image_path, object_name)
                        
                        # Check if we found the object
                        for obj in objects:
                            obj_name = obj.get("name", "").lower()
                            confidence = obj.get("confidence", 0)
                            position = obj.get("position", "unknown")
                            
                            if object_name.lower() in obj_name and confidence >= confidence_threshold:
                                logger.info(f"Found {object_name} with {confidence:.1%} confidence at {position}")
                                print(f"✅ Found {object_name} with {confidence:.1%} confidence at {position}!")
                                found_object = True
                                # Move toward the object
                                self.move_toward_object(position)
                                break
                            else:
                                # Log other objects seen
                                logger.info(f"Saw {obj_name} with {confidence:.1%} confidence")
                                print(f"👁️ Saw {obj_name} with {confidence:.1%} confidence")
                        
                        if found_object:
                            break
            
            # Report results
            elapsed = time.time() - start_time
            logger.info(f"Search completed in {elapsed:.1f}s")
            print(f"🕒 Search completed in {elapsed:.1f}s")
            
            if not found_object:
                logger.warning(f"Failed to find {object_name}")
                print(f"❌ Failed to find {object_name}")
            
            return found_object
        
        except Exception as e:
            logger.error(f"Search error: {e}")
            print(f"❌ Error during search: {e}")
            return False
        
        finally:
            # Stop the robot
            if self.initialized:
                self.px.stop()
    
    def move_toward_object(self, position):
        """Move toward the detected object based on its position with improved approach"""
        if not position:
            logger.warning("No position information available")
            return
        
        # Parse position information (format is typically "left/right/center, top/middle/bottom")
        position = position.lower()
        logger.info(f"Moving toward object at position: {position}")
        print(f"🚗 Moving toward object at {position}...")
        
        # First, turn toward the object based on horizontal position
        turn_angle = 0
        if "left" in position:
            # Adjust turn angle based on position descriptor
            if "far" in position:
                turn_angle = -45
            else:
                turn_angle = -30
            logger.info(f"Object is on the left, turning {turn_angle} degrees")
            print(f"🔄 Turning left {abs(turn_angle)} degrees toward object...")
            self.turn(turn_angle)
        elif "right" in position:
            # Adjust turn angle based on position descriptor
            if "far" in position:
                turn_angle = 45
            else:
                turn_angle = 30
            logger.info(f"Object is on the right, turning {turn_angle} degrees")
            print(f"🔄 Turning right {turn_angle} degrees toward object...")
            self.turn(turn_angle)
        
        # Wait a moment for the turn to complete
        time.sleep(0.5)
        
        # Check distance before moving forward
        distance = self.check_distance()
        
        # Handle invalid distance readings
        if distance < 0 or distance > 300:
            logger.warning(f"Invalid distance reading: {distance}cm, using default")
            distance = 50  # Use a reasonable default
        
        if distance < 20:  # Less than 20cm
            logger.warning(f"Obstacle detected at {distance}cm, cannot approach further")
            print(f"⚠️ Obstacle at {distance}cm, cannot approach further")
            return
        
        # Calculate approach distance based on current distance
        # Move shorter distances for more precise positioning
        approach_time = min(distance / 100, 1.0)  # Scale approach time by distance, max 1 second
        
        # Move forward toward the object
        logger.info(f"Moving forward toward object for {approach_time:.1f}s")
        print(f"🚗 Moving forward toward object for {approach_time:.1f}s...")
        
        # Move forward with appropriate speed based on distance
        speed = 40 if distance > 50 else 30  # Slower when closer
        self.move_forward(speed=speed, duration=approach_time)
        
        # Check distance again
        new_distance = self.check_distance()
        
        # Handle invalid distance readings
        if new_distance < 0 or new_distance > 300:
            logger.warning(f"Invalid distance reading: {new_distance}cm, using default")
            new_distance = 30  # Use a reasonable default
        
        if new_distance < 20:  # Less than 20cm
            logger.info(f"Reached object at {new_distance}cm")
            print(f"🎉 Reached object! Distance: {new_distance}cm")
            # Celebrate by turning in place
            self.turn(20)
            time.sleep(0.3)
            self.turn(-40)
            time.sleep(0.3)
            self.turn(20)
        elif new_distance < distance - 10:  # Made progress, try once more
            # Move a bit more if still far away but we're getting closer
            logger.info(f"Getting closer, distance: {new_distance}cm (was {distance}cm)")
            print(f"🚗 Getting closer, distance: {new_distance}cm...")
            
            # Calculate new approach time
            approach_time = min(new_distance / 150, 0.8)  # Shorter time for fine positioning
            self.move_forward(speed=25, duration=approach_time)  # Slower speed for precision
            
            # Final distance check
            final_distance = self.check_distance()
            if 0 <= final_distance < 300:  # Valid reading
                logger.info(f"Final distance to object: {final_distance}cm")
                print(f"🎉 Final distance to object: {final_distance}cm")
            else:
                logger.warning(f"Invalid final distance reading: {final_distance}cm")
                print("🎉 Reached destination!")
        else:
            # Didn't get much closer, might be a false positive or object is not directly ahead
            logger.info(f"Approach complete, final distance: {new_distance}cm")
            print(f"🎉 Approach complete, final distance: {new_distance}cm")
    
    def cleanup(self):
        """Clean up resources"""
        logger.info("Cleaning up resources")
        
        # Clean up hardware
        if self.initialized:
            try:
                self.px.stop()
                if self.music:
                    self.music.music_stop()
            except Exception as e:
                logger.error(f"Hardware cleanup error: {e}")
        
        # Clean up camera
        if self.camera_initialized:
            try:
                Vilib.camera_close()
                logger.info("Camera closed")
            except Exception as e:
                logger.error(f"Camera cleanup error: {e}")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="PiCar-X Object Finder")
    parser.add_argument("--timeout", type=int, default=60, help="Search timeout in seconds")
    parser.add_argument("--confidence", type=float, default=0.6, help="Confidence threshold (0-1)")
    parser.add_argument("--api-key", type=str, help="OpenAI API key")
    parser.add_argument("--object", type=str, default="tennis ball", help="Object to search for")
    args = parser.parse_args()
    
    # Initialize the object finder
    finder = ObjectFinder()
    
    # Start the search
    print(f"Starting {args.object} search with timeout {args.timeout}s")
    try:
        finder.search_for_object(object_name=args.object, timeout=args.timeout, confidence_threshold=args.confidence)
    except KeyboardInterrupt:
        print("\nSearch interrupted by user")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if finder:
            finder.cleanup()

if __name__ == "__main__":
    main()
