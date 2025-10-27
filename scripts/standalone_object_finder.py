#!/usr/bin/env python3
"""
Standalone Object Finder for PiCar-X
This script provides a simplified version of the object search functionality
that doesn't depend on the full agent architecture
"""

import os
import sys
import time
import base64
import logging
import argparse
import json
from typing import Dict, Any, List, Tuple, Optional
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('object_finder.log')
    ]
)
logger = logging.getLogger(__name__)

# Try to import required libraries
try:
    import cv2
    import openai
    import vilib
    from picarx import Picarx
    from robot_hat import Ultrasonic, Pin
    from picamera2 import Picamera2
except ImportError as e:
    logger.error(f"Failed to import required libraries: {e}")
    logger.error("Make sure to install: opencv-python, openai, vilib, picarx, robot_hat, picamera2")
    sys.exit(1)

# Check for OpenAI API key
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    try:
        from keys import OPENAI_API_KEY
    except ImportError:
        logger.warning("OpenAI API key not found in environment or keys.py")
        OPENAI_API_KEY = None

class StandaloneObjectFinder:
    """
    Standalone implementation of the object finder functionality
    """
    
    def __init__(self, api_key=None, confidence_threshold=0.6):
        """Initialize the object finder"""
        self.api_key = api_key or OPENAI_API_KEY
        self.confidence_threshold = confidence_threshold
        self.camera_initialized = False
        self.px = None
        self.ultrasonic = None
        self.client = None
        self.searching = False
        
        # Initialize OpenAI client
        if self.api_key:
            try:
                self.client = openai.OpenAI(api_key=self.api_key)
                logger.info("OpenAI client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
        else:
            logger.error("No OpenAI API key provided")
            sys.exit(1)
    
    def initialize_hardware(self):
        """Initialize the PiCar-X hardware"""
        try:
            # Initialize PiCar-X
            self.px = Picarx()
            logger.info("PiCar-X initialized")
            
            # Initialize ultrasonic sensor
            self.ultrasonic = Ultrasonic(trig=Pin('D2'), echo=Pin('D3'))
            logger.info("Ultrasonic sensor initialized")
            
            # Initialize camera
            vilib.init_camera()
            vilib.camera_start()
            time.sleep(2)  # Give camera time to initialize
            self.camera_initialized = True
            logger.info("Camera initialized")
            
            return True
        except Exception as e:
            logger.error(f"Failed to initialize hardware: {e}")
            return False
    
    def capture_image(self, save_path="current_view.jpg"):
        """Capture an image from the camera"""
        if not self.camera_initialized:
            logger.warning("Camera not initialized")
            return None
        
        try:
            # Use vilib.img attribute to get the current frame
            if hasattr(vilib, 'img') and vilib.img is not None:
                cv2.imwrite(save_path, vilib.img)
                logger.info(f"Image captured and saved to {save_path}")
                return save_path
            else:
                logger.warning("No image available from vilib")
                return None
        except Exception as e:
            logger.error(f"Image capture error: {e}")
            return None
    
    def check_distance(self):
        """Check distance using ultrasonic sensor with improved reliability"""
        if not self.ultrasonic:
            logger.warning("Ultrasonic sensor not initialized")
            return 100.0  # Default safe distance
        
        # Take multiple readings to improve reliability
        readings = []
        for _ in range(3):
            try:
                distance = self.ultrasonic.read()
                # Filter out invalid readings (negative or very large values)
                if 0 <= distance < 300:  # Valid range: 0-300cm
                    readings.append(distance)
                time.sleep(0.05)  # Short delay between readings
            except Exception as e:
                logger.error(f"Distance sensor error: {e}")
        
        # Calculate average of valid readings
        if readings:
            avg_distance = sum(readings) / len(readings)
            logger.info(f"Distance: {avg_distance:.2f}cm")
            return avg_distance
        else:
            logger.warning("No valid distance readings")
            return 100.0  # Default safe distance
    
    def detect_object(self, image_path, object_name):
        """Detect objects in an image using GPT-4 Vision"""
        if not self.client:
            logger.error("OpenAI client not available")
            return []
        
        if not os.path.exists(image_path):
            logger.error(f"Image file not found: {image_path}")
            return []
        
        try:
            # Encode image to base64
            with open(image_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode('utf-8')
            
            # Create prompt for GPT-4 Vision
            prompt = (
                f"Identify all objects visible in this image. I'm specifically looking for a {object_name}. "
                "For each object, provide: "
                "1. The name of the object "
                "2. A confidence score between 0 and 1 "
                "3. The approximate position in the image (left/right/center, top/bottom/middle) "
                "Format your response as a JSON array of objects."
            )
            
            # Call GPT-4 Vision API
            response = self.client.chat.completions.create(
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
            
            # Extract and parse response
            result = response.choices[0].message.content
            logger.info(f"GPT-4 Vision response: {result}")
            
            # Parse the response
            return self._parse_vision_response(result)
            
        except Exception as e:
            logger.error(f"GPT-4 Vision API error: {e}")
            return []
    
    def _parse_vision_response(self, response_text):
        """Parse the GPT-4 Vision response text"""
        try:
            # Try to extract JSON from the response
            import json
            import re
            
            # Look for JSON array in the response
            json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                objects = json.loads(json_str)
                
                # Convert to our standard format
                result = []
                for obj in objects:
                    # Extract position information
                    position = obj.get('position', '').lower()
                    
                    result.append({
                        'name': obj.get('name', 'unknown'),
                        'confidence': obj.get('confidence', 0.5),
                        'position': position
                    })
                
                return result
            
            # If no JSON found, try to extract information from text
            objects = []
            lines = response_text.split('\n')
            current_object = {}
            
            for line in lines:
                if not line.strip():
                    continue
                
                # Check for object name
                if ':' not in line and not current_object:
                    current_object = {'name': line.strip(), 'confidence': 0.7}
                
                # Check for confidence
                elif 'confidence' in line.lower():
                    try:
                        confidence = float(re.search(r'(\d+(\.\d+)?)', line).group(1))
                        if confidence > 1:
                            confidence /= 100  # Convert percentage to decimal
                        current_object['confidence'] = confidence
                    except:
                        pass
                
                # Check for position
                elif 'position' in line.lower():
                    position = line.lower().split(':')[-1].strip()
                    current_object['position'] = position
                
                # If we have a complete object, add it to the list
                if 'name' in current_object and 'confidence' in current_object:
                    if 'position' not in current_object:
                        current_object['position'] = 'center, middle'
                    
                    objects.append(current_object)
                    current_object = {}
            
            return objects
        
        except Exception as e:
            logger.error(f"Failed to parse vision response: {e}")
            return []
    
    def turn_toward_object(self, position):
        """Turn toward the detected object based on its position"""
        if not self.px:
            logger.warning("PiCar-X not initialized")
            return
        
        logger.info(f"Turning toward object at position: {position}")
        
        # Parse position string
        position = position.lower()
        
        # Determine turn angle based on horizontal position
        angle = 0
        if "left" in position:
            if "far" in position:
                angle = -45
            else:
                angle = -30
            logger.info(f"Turning left {abs(angle)} degrees")
            self.px.set_dir_servo_angle(angle)
            time.sleep(1)
        elif "right" in position:
            if "far" in position:
                angle = 45
            else:
                angle = 30
            logger.info(f"Turning right {angle} degrees")
            self.px.set_dir_servo_angle(angle)
            time.sleep(1)
        
        # Reset steering
        self.px.set_dir_servo_angle(0)
    
    def move_toward_object(self, position):
        """Move toward the detected object"""
        if not self.px:
            logger.warning("PiCar-X not initialized")
            return
        
        # First, turn toward the object
        self.turn_toward_object(position)
        
        # Check distance before moving
        distance = self.check_distance()
        if distance < 20:  # Too close, don't move
            logger.info(f"Object is too close ({distance:.2f}cm), not moving forward")
            return
        
        # Move forward based on distance
        move_time = min(distance / 100, 1.0)  # Scale move time by distance, max 1 second
        logger.info(f"Moving forward for {move_time:.2f}s")
        self.px.forward(50)  # 50% speed
        time.sleep(move_time)
        self.px.stop()
        
        # Check distance again
        distance = self.check_distance()
        logger.info(f"Distance after move: {distance:.2f}cm")
        
        # If still far, move a bit more
        if distance > 30:
            move_time = min(distance / 200, 0.5)  # Shorter move time
            logger.info(f"Still far, moving forward for {move_time:.2f}s more")
            self.px.forward(30)  # Slower speed
            time.sleep(move_time)
            self.px.stop()
            
            # Final distance check
            distance = self.check_distance()
            logger.info(f"Final distance: {distance:.2f}cm")
        
        # Celebrate finding the object
        logger.info("Object reached! Celebrating...")
        self.px.set_dir_servo_angle(30)
        time.sleep(0.5)
        self.px.set_dir_servo_angle(-30)
        time.sleep(0.5)
        self.px.set_dir_servo_angle(0)
    
    def search_for_object(self, object_name, timeout=60):
        """Search for an object using a comprehensive search pattern"""
        if not self.initialize_hardware():
            logger.error("Failed to initialize hardware")
            return False
        
        logger.info(f"Starting search for {object_name} with timeout {timeout}s")
        self.searching = True
        start_time = time.time()
        
        try:
            # First, perform a 360-degree scan in place
            scan_angles = [0, 45, 90, 135, 180, 225, 270, 315]
            
            for angle in scan_angles:
                if not self.searching or time.time() - start_time >= timeout:
                    break
                
                # Turn to the scan angle
                logger.info(f"Turning to {angle} degrees for scan")
                self.px.set_dir_servo_angle(angle % 90)  # Keep within servo limits
                time.sleep(1)
                
                # Capture image and detect objects
                image_path = self.capture_image()
                if not image_path:
                    continue
                
                # Detect objects in the image
                objects = self.detect_object(image_path, object_name)
                
                # Check if the target object is in the detected objects
                for obj in objects:
                    obj_name = obj.get('name', '').lower()
                    confidence = obj.get('confidence', 0.0)
                    position = obj.get('position', '')
                    
                    # Log what we see
                    logger.info(f"Saw {obj_name} with {confidence:.1%} confidence at {position}")
                    
                    # Check if this is our target object
                    if object_name.lower() in obj_name and confidence >= self.confidence_threshold:
                        logger.info(f"Found {object_name} with {confidence:.1%} confidence at {position}")
                        
                        # Move toward the object
                        self.move_toward_object(position)
                        
                        return True
            
            # If not found in initial scan, start exploration pattern
            logger.info(f"{object_name} not found in initial scan, starting exploration")
            
            # Set up exploration parameters
            search_angles = [0, 45, -45, 90, -90]
            
            # Continue searching until timeout
            while time.time() - start_time < timeout and self.searching:
                # Try different angles
                for angle in search_angles:
                    if not self.searching or time.time() - start_time >= timeout:
                        break
                    
                    # Turn to the search angle
                    logger.info(f"Turning to {angle} degrees for exploration")
                    self.px.set_dir_servo_angle(angle)
                    time.sleep(1)
                    
                    # Check for obstacles
                    distance = self.check_distance()
                    if distance < 20:  # cm
                        logger.warning(f"Obstacle detected at {distance}cm, adjusting path")
                        continue
                    
                    # Move forward if path is clear
                    logger.info("Moving forward to explore")
                    self.px.forward(40)
                    time.sleep(0.7)
                    self.px.stop()
                    
                    # Capture image and detect objects
                    image_path = self.capture_image()
                    if not image_path:
                        continue
                    
                    # Detect objects in the image
                    objects = self.detect_object(image_path, object_name)
                    
                    # Check if the target object is in the detected objects
                    for obj in objects:
                        obj_name = obj.get('name', '').lower()
                        confidence = obj.get('confidence', 0.0)
                        position = obj.get('position', '')
                        
                        # Log what we see
                        logger.info(f"Saw {obj_name} with {confidence:.1%} confidence at {position}")
                        
                        # Check if this is our target object
                        if object_name.lower() in obj_name and confidence >= self.confidence_threshold:
                            logger.info(f"Found {object_name} with {confidence:.1%} confidence at {position}")
                            
                            # Move toward the object
                            self.move_toward_object(position)
                            
                            return True
            
            # Object not found within timeout
            logger.info(f"Search completed, {object_name} not found within {timeout}s")
            return False
            
        except KeyboardInterrupt:
            logger.info("Search interrupted by user")
            return False
        except Exception as e:
            logger.error(f"Error during search: {e}")
            return False
        finally:
            self.searching = False
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources"""
        logger.info("Cleaning up resources")
        
        # Stop the car
        if self.px:
            self.px.stop()
        
        # Release the camera
        if self.camera_initialized:
            try:
                vilib.camera_release()
                logger.info("Camera released")
            except:
                pass
        
        logger.info("Cleanup complete")

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='PiCar-X Object Finder')
    parser.add_argument('--object', type=str, default='tennis ball', help='Object to search for')
    parser.add_argument('--timeout', type=int, default=60, help='Search timeout in seconds')
    parser.add_argument('--confidence', type=float, default=0.6, help='Confidence threshold (0.0-1.0)')
    parser.add_argument('--api-key', type=str, help='OpenAI API key (optional)')
    args = parser.parse_args()
    
    # Create the object finder
    finder = StandaloneObjectFinder(
        api_key=args.api_key,
        confidence_threshold=args.confidence
    )
    
    # Search for the object
    print(f"🔍 Starting search for {args.object} with timeout {args.timeout}s...")
    result = finder.search_for_object(args.object, args.timeout)
    
    # Display the result
    if result:
        print(f"✅ Found {args.object}!")
    else:
        print(f"❌ {args.object} not found within {args.timeout}s")

if __name__ == "__main__":
    main()
