"""
Object Search Tool for the Robot Agent

This tool enables the agent to search for any object in the environment
using GPT-4 Vision for object detection and PiCar-X for movement.
"""

import os
import sys
import time
import base64
import json
import logging
import asyncio
from typing import Dict, Any, Optional, List
from pathlib import Path

# Import agent tool base classes
try:
    from .base_tool import BaseTool, ToolExecutionError
except ImportError:
    # For standalone testing
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent))
    try:
        from base_tool import BaseTool, ToolExecutionError
    except ImportError:
        # Define minimal versions for testing
        class BaseTool:
            """Minimal BaseTool implementation for testing"""
            def __init__(self):
                self.name = "base_tool"
                self.description = "Base tool class"
                self.parameters = {}
            
            async def execute(self, **kwargs):
                """Execute the tool"""
                raise NotImplementedError
        
        class ToolExecutionError(Exception):
            """Error raised when tool execution fails"""
            pass

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

class ObjectSearchTool(BaseTool):
    """
    Tool for searching for objects in the environment.
    
    This is a high-level tool that combines movement, vision, and navigation
    to search for objects in the environment using GPT-4 Vision for object detection.
    """
    
    name = "search_for_object"
    description = "Search for an object in the environment. Returns when found or search is complete."
    
    parameters = {
        "object_name": {
            "type": str,
            "description": "Name or description of the object to find",
            "required": True
        },
        "search_area": {
            "type": str,
            "description": "Optional area to search (e.g., 'living_room', 'kitchen')",
            "required": False
        },
        "timeout": {
            "type": int,
            "description": "Maximum search time in seconds (default: 120)",
            "required": False,
            "default": 120
        },
        "confidence_threshold": {
            "type": float,
            "description": "Confidence threshold for object detection (0.0-1.0)",
            "required": False,
            "default": 0.7
        }
    }
    
    def __init__(self, car=None, vision_system=None, navigator=None):
        """Initialize the object search tool.
        
        Args:
            car: Optional car controller interface. If None, will initialize hardware directly.
            vision_system: Optional vision system interface. If None, will initialize camera directly.
            navigator: Optional navigator for room-level navigation.
        """
        # Store agent interfaces if provided
        self.car = car
        self.vision_system = vision_system
        self.navigator = navigator
        self.memory = SearchMemory()  # Memory for search history
        
        # Initialize state variables
        self.px = None
        self.music = None
        self.pin = None
        self.initialized = False
        self.openai_client = None
        self.camera_initialized = False
        
        # If car interface is provided, use its hardware
        if self.car is not None and hasattr(self.car, 'px'):
            self.px = self.car.px
            self.initialized = self.px is not None
            logger.info("Using car interface for hardware access")
        else:
            # Otherwise initialize hardware directly
            self._init_hardware()
        
        # If vision system is provided, use its OpenAI client
        if self.vision_system is not None and hasattr(self.vision_system, 'openai_client'):
            self.openai_client = self.vision_system.openai_client
            logger.info("Using vision system's OpenAI client")
        elif OPENAI_AVAILABLE and OPENAI_API_KEY:
            # Otherwise initialize OpenAI client directly
            try:
                self.openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)
                logger.info("OpenAI client initialized directly")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
        
        # If vision system is provided, use its camera
        if self.vision_system is not None and hasattr(self.vision_system, 'camera_initialized'):
            self.camera_initialized = self.vision_system.camera_initialized
            logger.info("Using vision system's camera")
        elif CAMERA_AVAILABLE:
            # Otherwise initialize camera directly
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
                logger.info("Camera initialized with vilib directly")
            except Exception as e:
                logger.error(f"Failed to initialize camera with vilib: {e}")
    
    async def execute(self, **kwargs):
        """Execute the object search.
        
        Args:
            object_name: Name or description of the object to find
            search_area: Optional area to search (e.g., 'living_room', 'kitchen')
            timeout: Maximum search time in seconds (default: 120)
            confidence_threshold: Confidence threshold for object detection (0.0-1.0)
            
        Returns:
            Dict containing search results
        """
        # Extract parameters
        object_name = kwargs.get("object_name")
        search_area = kwargs.get("search_area")
        timeout = kwargs.get("timeout", 120)
        confidence_threshold = kwargs.get("confidence_threshold", 0.7)
        
        logger.info(f"Starting search for {object_name} with timeout {timeout}s and confidence threshold {confidence_threshold}")
        
        # If a specific area is requested and we have a navigator, go there first
        if search_area and self.navigator:
            logger.info(f"Navigating to {search_area} before searching")
            # This would call the navigator to move to the specified area
            # await self.navigator.navigate_to(search_area)
        
        # Execute the search
        try:
            # Call the existing search_for_object method
            result = self.search_for_object(object_name, timeout, confidence_threshold)
            
            # Format the result for the agent
            return {
                "success": result.get("found", False),
                "object_name": object_name,
                "confidence": result.get("confidence", 0.0),
                "position": result.get("position", "unknown"),
                "search_time": result.get("search_time", 0.0),
                "message": result.get("message", "Search completed")
            }
        except Exception as e:
            logger.error(f"Error during object search: {e}")
            return {
                "success": False,
                "object_name": object_name,
                "message": f"Error during search: {str(e)}"
            }
    
    def _init_hardware(self):
        """Initialize hardware components following working_gpt_car.py pattern"""
        if not HARDWARE_AVAILABLE:
            logger.warning("Hardware modules not available, running in simulation mode")
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
                        self.move_toward_object(object_name, position)
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
                            
                            # Store all detections in memory
                            self.memory.add("detected_objects", {
                                "name": obj_name,
                                "confidence": confidence,
                                "position": position,
                                "timestamp": time.time()
                            })
                            
                            if object_name.lower() in obj_name and confidence >= confidence_threshold:
                                logger.info(f"Found {object_name} with {confidence:.1%} confidence at {position}")
                                print(f"✅ Found {object_name} with {confidence:.1%} confidence at {position}!")
                                found_object = True
                                
                                # Store the successful detection in memory
                                self.memory.set("last_confidence", confidence)
                                self.memory.set("last_position", position)
                                self.memory.set("last_detection_time", time.time())
                                
                                # Move toward the object
                                self.move_toward_object(object_name, position)
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
            
            # Prepare result dictionary
            result = {
                "found": found_object,
                "search_time": elapsed,
                "confidence": self.memory.get("last_confidence", 0.0),
                "position": self.memory.get("last_position", "unknown"),
            }
            
            if found_object:
                result["message"] = f"Found {object_name} in {elapsed:.1f}s"
            else:
                logger.warning(f"Failed to find {object_name}")
                print(f"❌ Failed to find {object_name}")
                result["message"] = f"Failed to find {object_name} after {elapsed:.1f}s"
            
            return result
        
        except Exception as e:
            logger.error(f"Search error: {e}")
            print(f"❌ Error during search: {e}")
            return {
                "found": False,
                "search_time": time.time() - start_time,
                "message": f"Error during search: {str(e)}"
            }
        
        finally:
            # Stop the robot
            if self.initialized:
                self.px.stop()
    
    def extract_position_details(self, position_str):
        """Extract detailed position information from position string
        
        Args:
            position_str (str): Position string from GPT-4 Vision (e.g., "left top", "center")
            
        Returns:
            dict: Detailed position information including horizontal, vertical, and quadrant
        """
        if not position_str:
            return {
                "original": "",
                "horizontal": "center",
                "vertical": "middle",
                "quadrant": 5,
                "distance_estimate": "unknown"
            }
            
        position_str = position_str.lower()
        
        # Initialize position details
        position = {
            "original": position_str,
            "horizontal": "center",  # left, center, right
            "vertical": "middle",   # top, middle, bottom
            "quadrant": 5,          # Numeric quadrant (1-9, with 5 being center)
            "distance_estimate": "unknown"
        }
        
        # Extract horizontal position
        if "left" in position_str:
            position["horizontal"] = "left"
        elif "right" in position_str:
            position["horizontal"] = "right"
        
        # Extract vertical position
        if "top" in position_str:
            position["vertical"] = "top"
        elif "bottom" in position_str:
            position["vertical"] = "bottom"
        
        # Determine quadrant (like numpad)
        # 7 8 9
        # 4 5 6
        # 1 2 3
        quadrant_map = {
            ("left", "top"): 7,
            ("center", "top"): 8,
            ("right", "top"): 9,
            ("left", "middle"): 4,
            ("center", "middle"): 5,
            ("right", "middle"): 6,
            ("left", "bottom"): 1,
            ("center", "bottom"): 2,
            ("right", "bottom"): 3
        }
        
        position["quadrant"] = quadrant_map.get(
            (position["horizontal"], position["vertical"]), 5
        )
        
        # Try to extract any distance information if present
        distance_keywords = ["close", "near", "far", "distant"]
        for keyword in distance_keywords:
            if keyword in position_str:
                position["distance_estimate"] = keyword
                break
                
        return position
    
    def move_toward_object(self, object_name, position):
        """Enhanced iterative movement toward detected object to get very close (under 10cm)
        
        Args:
            object_name: Name of the object to approach
            position: Position string of the object (e.g., "left, top")
            
        Returns:
            Final distance to the object in cm
        """
        if not position:
            logger.warning("No position information available")
            return 100  # Return a default distance
        
        # Extract detailed position information
        position_details = self.extract_position_details(position)
        
        # Add a brief pause after detection to ensure stability
        logger.info("Pausing briefly to stabilize after object detection")
        print("⏱️ Pausing briefly to stabilize after object detection...")
        time.sleep(0.5)
        
        # Capture another image to confirm object position before moving
        logger.info("Confirming object position before moving")
        print("🔍 Confirming object position before moving...")
        confirm_image_path = self.capture_image()
        if confirm_image_path:
            confirm_objects = self.analyze_image_with_gpt4(confirm_image_path, object_name)
            object_confirmed = False
            confirmed_position = position
            
            for obj in confirm_objects:
                obj_name = obj.get("name", "").lower()
                confidence = obj.get("confidence", 0)
                obj_position = obj.get("position", "unknown")
                
                if object_name.lower() in obj_name.lower() and confidence >= 0.6:
                    object_confirmed = True
                    confirmed_position = obj_position
                    logger.info(f"Confirmed {object_name} at {obj_position} with {confidence*100:.1f}% confidence")
                    print(f"✅ Confirmed {object_name} at {obj_position} with {confidence*100:.1f}% confidence")
                    break
            
            if not object_confirmed:
                logger.warning(f"Could not confirm {object_name} position before moving")
                print(f"⚠️ Could not confirm {object_name} position before moving")
                # Return early if we can't confirm the object
                return 100
            
            # Use the confirmed position for movement
            position_details = self.extract_position_details(confirmed_position)
        
        # First, turn toward the object based on horizontal position
        turn_angle = 0
        if position_details["horizontal"] == "left":
            # Adjust turn angle based on position descriptor
            if position_details["distance_estimate"] == "far":
                turn_angle = -30  # Reduced from -45 for more cautious turning
            else:
                turn_angle = -20  # Reduced from -30 for more cautious turning
            logger.info(f"Object is on the left, turning {turn_angle} degrees")
            print(f"🔄 Turning left {abs(turn_angle)} degrees toward object...")
            self.turn(turn_angle)
        elif position_details["horizontal"] == "right":
            # Adjust turn angle based on position descriptor
            if position_details["distance_estimate"] == "far":
                turn_angle = 30  # Reduced from 45 for more cautious turning
            else:
                turn_angle = 20  # Reduced from 30 for more cautious turning
            logger.info(f"Object is on the right, turning {turn_angle} degrees")
            print(f"🔄 Turning right {turn_angle} degrees toward object...")
            self.turn(turn_angle)
        
        # Wait a moment for the turn to complete
        time.sleep(0.2)  # Reduced from 0.5 for better performance
        
        # Get initial distance measurement
        initial_distance = self.check_distance()
        
        # Handle invalid distance readings
        if initial_distance < 0 or initial_distance > 300:
            initial_distance = 50  # Use a reasonable default
        
        logger.info(f"Initial distance to object: {initial_distance}cm")
        print(f"📏 Initial distance to object: {initial_distance}cm")
        
        # Target minimum distance (but not too close)
        target_distance = 8  # Target getting within 8cm
        current_distance = initial_distance
        
        # Iterative approach - get progressively closer with multiple movements
        max_iterations = 8  # Allow up to 8 approach iterations
        position_check_interval = 1  # Check position every iteration (more frequent verification)
        
        for i in range(max_iterations):
            # Check if we've reached target distance or are close enough to stop
            if current_distance <= 15 or i >= max_iterations:  # Reduced from 20cm to 15cm for closer approach
                logger.info(f"Target distance reached: {current_distance}cm")
                print(f"🎥 Target distance reached: {current_distance}cm")
                break
            
            # Safety check - if very close, stop
            if current_distance < 5:
                logger.warning(f"Very close to object ({current_distance}cm), stopping for safety")
                print(f"⚠️ Very close to object ({current_distance}cm), stopping for safety")
                break
            
            # Periodically verify object position and adjust direction
            # More frequent verification (every iteration)
            if i % position_check_interval == 0:
                logger.info(f"Verifying object position at iteration {i}")
                print(f"🔍 Verifying object position...")
                
                # Capture image and analyze
                image_path = self.capture_image()
                if image_path:
                    objects = self.analyze_image_with_gpt4(image_path, object_name)
                    found_object = False
                    
                    for obj in objects:
                        obj_name = obj.get("name", "").lower()
                        confidence = obj.get("confidence", 0)
                        obj_position = obj.get("position", "unknown")
                        
                        # If we find our target object with good confidence
                        if object_name.lower() in obj_name.lower() and confidence >= 0.6:
                            found_object = True
                            logger.info(f"Verified {object_name} at {obj_position} with {confidence*100:.1f}% confidence")
                            print(f"✅ Verified {object_name} at {obj_position} with {confidence*100:.1f}% confidence")
                            
                            # If object has moved from center, adjust direction
                            if "center" not in obj_position.lower():
                                # Adjust direction based on new position and maintain angle
                                new_position_details = self.extract_position_details(obj_position)
                                if new_position_details["horizontal"] == "left":
                                    # More significant left adjustment to maintain angle
                                    adjustment = -20  # Increased from -15
                                    logger.info(f"Object moved left, adjusting direction by {adjustment} degrees")
                                    print(f"🔄 Object moved left, adjusting direction...")
                                    self.turn(adjustment)
                                    # Set steering angle for forward movement to maintain trajectory
                                    self.px.set_dir_servo_angle(-10)  # Keep wheels turned left during forward movement
                                    # Store last known direction for use if object is lost
                                    self.memory.add("last_direction", "left")
                                elif new_position_details["horizontal"] == "right":
                                    # More significant right adjustment to maintain angle
                                    adjustment = 20  # Increased from 15
                                    logger.info(f"Object moved right, adjusting direction by {adjustment} degrees")
                                    print(f"🔄 Object moved right, adjusting direction...")
                                    self.turn(adjustment)
                                    # Set steering angle for forward movement to maintain trajectory
                                    self.px.set_dir_servo_angle(10)  # Keep wheels turned right during forward movement
                                    # Store last known direction for use if object is lost
                                    self.memory.add("last_direction", "right")
                                elif new_position_details["horizontal"] == "center":
                                    # Object is centered, reset steering angle
                                    logger.info("Object is centered, straightening wheels")
                                    print("🔄 Object is centered, straightening wheels...")
                                    self.px.set_dir_servo_angle(0)
                                    # Store last known direction for use if object is lost
                                    self.memory.add("last_direction", "center")
                                time.sleep(0.3)  # Longer wait for turn to complete
                            break
                    
                    if not found_object:
                        logger.warning(f"Object {object_name} no longer visible, continuing with last known direction")
                        print(f"⚠️ Object {object_name} no longer visible, continuing with last known direction")
                        
                        # Maintain steering angle based on last known direction
                        last_direction = self.memory.get("last_direction", "center")
                        if last_direction == "left":
                            # Continue turning slightly left to maintain trajectory
                            logger.info("Maintaining left steering angle since object was last seen on the left")
                            print("🔄 Maintaining left steering angle...")
                            self.px.set_dir_servo_angle(-10)
                        elif last_direction == "right":
                            # Continue turning slightly right to maintain trajectory
                            logger.info("Maintaining right steering angle since object was last seen on the right")
                            print("🔄 Maintaining right steering angle...")
                            self.px.set_dir_servo_angle(10)
            
            # Calculate approach speed and duration based on current distance and alignment
            is_centered = self.memory.get("last_direction", "center") == "center"
            
            if current_distance > 100 and is_centered:
                # Far away and well-aligned, take bigger steps
                approach_speed = 40
                approach_duration = min(0.8, current_distance / 150)  # Longer duration for faster approach
                logger.info(f"Object centered and far away, moving quickly for {approach_duration:.1f}s")
                print(f"🚗 Object centered and far away, moving quickly for {approach_duration:.1f}s...")
            elif current_distance > 50:
                # Still far away, move at moderate speed
                approach_speed = 30
                approach_duration = min(0.5, current_distance / 200)  # Adaptive duration
                logger.info(f"Moving forward toward object for {approach_duration:.1f}s")
                print(f"🚗 Moving forward toward object for {approach_duration:.1f}s...")
            elif current_distance > 25:
                # Getting close, slow down
                approach_speed = 20
                approach_duration = min(0.3, current_distance / 250)  # Shorter movements
                logger.info(f"Approaching object at medium speed for {approach_duration:.1f}s")
                print(f"🚘 Approaching object at medium speed for {approach_duration:.1f}s...")
            else:
                # Very close, move very slowly for final approach
                approach_speed = 15
                approach_duration = min(0.2, current_distance / 300)  # Very short movements
                logger.info(f"Final approach at slow speed for {approach_duration:.1f}s")
                print(f"🚙 Final approach at slow speed for {approach_duration:.1f}s...")
                
            # Add a small pause before moving to ensure stability
            time.sleep(0.2)
            
            # Move forward
            logger.info(f"Moving forward at speed {approach_speed} for {approach_duration}s")
            self.px.forward(approach_speed)
            time.sleep(approach_duration)
            self.px.stop()
            
            # Update distance tracking
            previous_distance = current_distance
            current_distance = self.check_distance()
            if current_distance < 0 or current_distance > 300:
                # Try one more time
                time.sleep(0.1)
                current_distance = self.check_distance()
                if current_distance < 0 or current_distance > 300:
                    # If still invalid, use an estimate based on previous distance
                    current_distance = previous_distance * 0.7  # Assume we moved about 30% closer
            
            logger.info(f"Getting closer, distance: {current_distance}cm (was {previous_distance}cm)")
            print(f"📏 New distance: {current_distance}cm (was {previous_distance}cm)")
        
        logger.info(f"Final distance to object: {current_distance}cm")
        print(f"🎉 Final distance to object: {current_distance}cm")
        return current_distance
    
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

# Simple memory implementation for the object search tool
class SearchMemory:
    """Simple memory class for storing search-related information"""
    
    def __init__(self):
        """Initialize the memory"""
        self._memory = {}
        self._lists = {}
    
    def set(self, key, value):
        """Set a value in memory"""
        self._memory[key] = value
    
    def get(self, key, default=None):
        """Get a value from memory"""
        return self._memory.get(key, default)
    
    def add(self, list_name, item):
        """Add an item to a list in memory"""
        if list_name not in self._lists:
            self._lists[list_name] = []
        self._lists[list_name].append(item)
    
    def get_list(self, list_name):
        """Get a list from memory"""
        return self._lists.get(list_name, [])
    
    def clear(self):
        """Clear the memory"""
        self._memory = {}
        self._lists = {}

