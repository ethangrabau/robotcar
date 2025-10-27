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

class BackpackFinder:
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
                Vilib.show_fps()
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
        """Check distance using ultrasonic sensor"""
        if not self.initialized:
            logger.warning("Hardware not initialized, simulating distance check")
            return 100.0  # Simulate no obstacles
        
        try:
            distance = self.px.ultrasonic.read()
            logger.info(f"Distance: {distance}cm")
            return distance
        except Exception as e:
            logger.error(f"Distance check error: {e}")
            return 100.0  # Default to no obstacles on error
    
    def capture_image(self, save_path="current_view.jpg"):
        """Capture an image from the camera using vilib"""
        if not self.camera_initialized:
            logger.warning("Camera not initialized")
            return None
        
        try:
            # Get the current frame from vilib.img (as in gpt_car.py)
            # This is the key fix - using Vilib.img instead of Vilib.get_image()
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
    
    def analyze_image_with_gpt4(self, image_path):
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
                "I'm particularly interested in finding a backpack if one is present. "
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
    
    def search_for_backpack(self, timeout=60, confidence_threshold=0.6):
        """Search for a backpack using a simple search pattern"""
        logger.info("Starting search for backpack")
        print("🔍 Searching for backpack...")
        
        start_time = time.time()
        found_backpack = False
        search_pattern = [
            # (action, parameter)
            # action can be "forward", "turn", or "scan"
            ("scan", None),  # Initial scan
            ("forward", 0.5),  # Move forward
            ("scan", None),  # Scan again
            ("turn", 45),  # Turn right
            ("forward", 0.5),  # Move forward
            ("scan", None),  # Scan again
            ("turn", -90),  # Turn left
            ("forward", 0.5),  # Move forward
            ("scan", None),  # Scan again
            ("turn", 45),  # Return to center
            ("forward", 0.5),  # Move forward
            ("scan", None),  # Final scan
        ]
        
        try:
            # Execute the search pattern
            for i, (action, param) in enumerate(search_pattern):
                # Check timeout
                if time.time() - start_time > timeout:
                    logger.warning(f"Search timed out after {timeout}s")
                    print(f"⏱️ Search timed out after {timeout}s")
                    break
                
                # Check for obstacles
                if action in ["forward", "turn"]:
                    distance = self.check_distance()
                    if distance < 20:  # Less than 20cm
                        logger.warning(f"Obstacle detected at {distance}cm, turning to avoid")
                        print(f"⚠️ Obstacle detected at {distance}cm, turning to avoid")
                        self.turn(90)  # Turn away from obstacle
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
                    logger.info("Scanning for backpack")
                    print(f"📸 Taking a picture and analyzing with GPT-4 Vision...")
                    
                    # Capture image
                    image_path = self.capture_image()
                    if not image_path:
                        logger.warning("Failed to capture image")
                        continue
                    
                    # Analyze image with GPT-4 Vision
                    objects = self.analyze_image_with_gpt4(image_path)
                    
                    # Check if we found a backpack
                    for obj in objects:
                        obj_name = obj.get("name", "").lower()
                        confidence = obj.get("confidence", 0)
                        position = obj.get("position", "unknown")
                        
                        if "backpack" in obj_name and confidence >= confidence_threshold:
                            logger.info(f"Found backpack with {confidence:.1%} confidence at {position}")
                            print(f"✅ Found backpack with {confidence:.1%} confidence at {position}!")
                            found_backpack = True
                            break
                        else:
                            # Log other objects seen
                            logger.info(f"Saw {obj_name} with {confidence:.1%} confidence")
                            print(f"👁️ Saw {obj_name} with {confidence:.1%} confidence")
                    
                    if found_backpack:
                        break
            
            # Report results
            elapsed = time.time() - start_time
            logger.info(f"Search completed in {elapsed:.1f}s")
            print(f"🕒 Search completed in {elapsed:.1f}s")
            
            if not found_backpack:
                logger.warning("Failed to find backpack")
                print("❌ Failed to find backpack")
            
            return found_backpack
        
        except Exception as e:
            logger.error(f"Search error: {e}")
            print(f"❌ Error during search: {e}")
            return False
        
        finally:
            # Stop the robot
            if self.initialized:
                self.px.stop()
    
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
    parser = argparse.ArgumentParser(description='Search for a backpack using PiCar-X and GPT-4 Vision')
    parser.add_argument('--timeout', type=int, default=60, help='Search timeout in seconds')
    parser.add_argument('--confidence', type=float, default=0.6, help='Confidence threshold (0-1)')
    parser.add_argument('--api-key', type=str, help='OpenAI API key (optional)')
    parser.add_argument('--object-name', type=str, default='backpack', help='Object to search for (default: backpack)')
    
    args = parser.parse_args()
    
    # Set API key if provided
    if args.api_key:
        os.environ["OPENAI_API_KEY"] = args.api_key
    
    print(f"Starting backpack search with timeout {args.timeout}s")
    
    # Create and run the backpack finder
    finder = None
    try:
        finder = BackpackFinder()
        finder.search_for_backpack(timeout=args.timeout, confidence_threshold=args.confidence)
    except KeyboardInterrupt:
        print("\nSearch interrupted by user")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if finder:
            finder.cleanup()

if __name__ == "__main__":
    main()
