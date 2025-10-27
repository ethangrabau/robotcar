"""
Approach Object Tool for the Robot Agent

This tool enables the agent to approach an already detected object in the environment
using GPT-4 Vision for object tracking and PiCar-X for movement.
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
        logging.FileHandler('object_approach.log')
    ]
)
logger = logging.getLogger('approach_object_tool')

# Check for OpenAI availability
try:
    import openai
    OPENAI_AVAILABLE = True
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
except ImportError:
    OPENAI_AVAILABLE = False
    OPENAI_API_KEY = None
    logger.warning("OpenAI package not available, vision features will be limited")

# Check for camera and hardware availability
try:
    from vilib import Vilib
    CAMERA_AVAILABLE = True
except ImportError:
    CAMERA_AVAILABLE = False
    logger.warning("vilib not available, camera features will be limited")

# Import hardware dependencies (with fallbacks for testing)
try:
    import robot_hat
    from robot_hat import Pin, ADC, PWM, Servo, utils
    import picarx
    HARDWARE_AVAILABLE = True
except ImportError:
    HARDWARE_AVAILABLE = False
    logger.warning("Hardware libraries not available, will run in simulation mode")

# Simple memory class for storing approach-related information
class ApproachMemory:
    """Simple memory class for storing approach-related information"""
    
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


class ApproachObjectTool(BaseTool):
    """Tool for approaching objects in the environment.
    
    This tool enables the agent to approach an already detected object in the environment
    using GPT-4 Vision for object tracking and PiCar-X for movement.
    """
    
    name = "approach_object"
    description = "Approach an object in the environment. Returns when reached or approach is complete."
    parameters = {
        "object_name": {
            "type": str,
            "description": "Name or description of the object to approach",
            "required": True
        },
        "position": {
            "type": str,
            "description": "Initial position of the object (e.g., 'left', 'right center')",
            "required": True
        },
        "confidence": {
            "type": float,
            "description": "Confidence in the object detection (0.0-1.0)",
            "required": False,
            "default": 0.6
        },
        "max_approach_time": {
            "type": int,
            "description": "Maximum time to spend approaching in seconds",
            "required": False,
            "default": 30
        },
        "min_distance": {
            "type": int,
            "description": "Minimum distance to maintain from object in cm",
            "required": False,
            "default": 15
        }
    }
    
    def __init__(self, car=None, vision_system=None):
        """Initialize the approach object tool.
        
        Args:
            car: Optional car controller interface. If None, will initialize hardware directly.
            vision_system: Optional vision system interface. If None, will initialize camera directly.
        """
        # Store agent interfaces if provided
        self.car = car
        self.vision_system = vision_system
        self.memory = ApproachMemory()  # Memory for approach history
        
        # Initialize state variables
        self.px = None
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
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the approach object tool
        
        Args:
            object_name: Name of the object to approach
            position: Position of the object (e.g., 'left', 'right center')
            confidence: Confidence threshold for object detection
            max_approach_time: Maximum time to spend approaching in seconds
            min_distance: Minimum distance to maintain from object in cm
            
        Returns:
            Dict containing approach results
        """
        # Extract parameters
        object_name = kwargs.get('object_name', 'object')
        position = kwargs.get('position', 'center')
        confidence = kwargs.get('confidence', 0.6)
        max_approach_time = kwargs.get('max_approach_time', 30)
        min_distance = kwargs.get('min_distance', 15)
        
        logger.info(f"Executing ApproachObjectTool for {object_name} at position {position}")
        print(f"🚗 Approaching {object_name} at position {position}...")
        
        try:
            # Execute the approach algorithm
            result = self.approach_object(
                object_name=object_name,
                position=position,
                confidence=confidence,
                max_approach_time=max_approach_time,
                min_distance=min_distance
            )
            
            # Log the result
            if result["success"]:
                logger.info(f"Successfully approached {object_name}: {result['message']}")
            else:
                logger.warning(f"Failed to approach {object_name}: {result['message']}")
                
            return result
            
        except Exception as e:
            logger.error(f"Error during approach: {e}")
            print(f"❌ Error during approach: {e}")
            return {
                "success": False,
                "approach_time": 0,
                "message": f"Error during approach: {str(e)}"
            }
        finally:
            # Clean up resources
            try:
                # Stop the robot
                if self.initialized:
                    self.px.stop()
            except Exception as e:
                logger.error(f"Error during cleanup: {e}")
    
    def _init_hardware(self):
        """Initialize hardware components following working_gpt_car.py pattern"""
        if not HARDWARE_AVAILABLE:
            logger.warning("Hardware libraries not available, running in simulation mode")
            return
        
        try:
            # Initialize PiCar-X hardware
            self.px = picarx.Picarx()
            self.pin = Pin("D0")
            
            # Test basic movement to verify hardware
            self.px.forward(0)  # Stop any existing movement
            time.sleep(0.1)
            
            # Hardware initialization successful
            self.initialized = True
            logger.info("Hardware initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize hardware: {e}")
            self.initialized = False
    
    def move_forward(self, speed=50, duration=1.0):
        """Move forward at the specified speed for the specified duration"""
        if not self.initialized:
            logger.warning("Hardware not initialized, cannot move forward")
            return
        
        try:
            self.px.forward(speed)
            time.sleep(duration)
            self.px.forward(0)  # Stop
        except Exception as e:
            logger.error(f"Error moving forward: {e}")
    
    def turn(self, angle):
        """Turn by the specified angle"""
        if not self.initialized:
            logger.warning("Hardware not initialized, cannot turn")
            return
        
        try:
            # Convert angle to appropriate turn direction and magnitude
            if angle > 0:  # Turn right
                self.px.set_dir_servo_angle(angle)
                time.sleep(0.3)  # Give time for the servo to adjust
                self.px.forward(30)  # Move forward while turning
                time.sleep(0.5)
                self.px.forward(0)  # Stop
                self.px.set_dir_servo_angle(0)  # Reset steering
            elif angle < 0:  # Turn left
                self.px.set_dir_servo_angle(angle)
                time.sleep(0.3)  # Give time for the servo to adjust
                self.px.forward(30)  # Move forward while turning
                time.sleep(0.5)
                self.px.forward(0)  # Stop
                self.px.set_dir_servo_angle(0)  # Reset steering
        except Exception as e:
            logger.error(f"Error turning: {e}")
    
    def check_distance(self):
        """Check distance using ultrasonic sensor with improved reliability"""
        if not self.initialized:
            logger.warning("Hardware not initialized, cannot check distance")
            return 50  # Return a default value
        
        try:
            # Take multiple readings for reliability
            distances = []
            for _ in range(3):
                distance = self.px.ultrasonic.read()
                if 0 <= distance < 300:  # Valid reading range
                    distances.append(distance)
                time.sleep(0.05)  # Short delay between readings
            
            # Filter out invalid readings and average the rest
            valid_distances = [d for d in distances if 0 <= d < 300]
            if valid_distances:
                return sum(valid_distances) / len(valid_distances)
            else:
                logger.warning("No valid distance readings")
                return 50  # Default value
                
        except Exception as e:
            logger.error(f"Error checking distance: {e}")
            return 50  # Default value
    
    def capture_image(self, save_path="current_view.jpg"):
        """Capture an image from the camera using vilib"""
        if not self.camera_initialized:
            logger.warning("Camera not initialized, cannot capture image")
            return None
        
        try:
            # Use vilib to capture image
            Vilib.take_photo(save_path)
            logger.info(f"Image captured and saved to {save_path}")
            return save_path
        except Exception as e:
            logger.error(f"Error capturing image: {e}")
            return None
    
    def analyze_image_with_gpt4(self, image_path, object_name="object"):
        """Analyze an image using GPT-4 Vision to find and track objects"""
        if not self.openai_client:
            logger.warning("OpenAI client not available, cannot analyze image")
            return []
        
        try:
            # Read the image file
            with open(image_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode('utf-8')
            
            # Prepare the prompt for object detection with position information
            prompt = f"""Analyze this image and find the {object_name}. 
            If you see the {object_name}, provide the following information in JSON format:
            1. Is the {object_name} present? (true/false)
            2. Position of the {object_name} in the image (left/center/right, top/middle/bottom)
            3. Approximate distance (close, medium, far) if you can estimate it
            4. Your confidence level (0.0-1.0)
            5. A brief description of the {object_name}
            
            Format your response as a JSON object with the following structure:
            {{"objects": [{{"name": "{object_name}", "present": true/false, "position": "position description", "distance": "distance estimate", "confidence": confidence_value, "description": "brief description"}}]}}
            
            If multiple {object_name}s are visible, include all of them in the objects array.
            If no {object_name} is visible, return {{"objects": []}}
            """
            
            # Call the OpenAI API with the image
            response = self.openai_client.chat.completions.create(
                model="gpt-4-vision-preview",
                messages=[
                    {"role": "system", "content": "You are a computer vision system that detects objects and their positions in images."},
                    {"role": "user", "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]}
                ],
                max_tokens=1000
            )
            
            # Extract the response text
            response_text = response.choices[0].message.content
            logger.info(f"GPT-4 Vision response: {response_text}")
            
            # Parse the JSON response
            # Find JSON content between triple backticks if present
            import re
            json_match = re.search(r'```json\s*(.+?)\s*```', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try to find any JSON-like structure
                json_match = re.search(r'\{\s*"objects"\s*:.+?\}', response_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    json_str = response_text
            
            try:
                result = json.loads(json_str)
                objects = result.get("objects", [])
                return objects
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {e}")
                # Attempt to extract information manually
                if "not present" in response_text.lower() or "no object" in response_text.lower():
                    return []
                else:
                    # Create a basic object with available information
                    return [{
                        "name": object_name,
                        "present": "present" in response_text.lower(),
                        "position": "unknown",
                        "confidence": 0.5,
                        "description": "Object details could not be parsed"
                    }]
                
        except Exception as e:
            logger.error(f"Error analyzing image with GPT-4 Vision: {e}")
            return []
    
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
        distance_keywords = {"close": "close", "near": "close", "far": "far", "distant": "far", "medium": "medium"}
        for keyword, value in distance_keywords.items():
            if keyword in position_str:
                position["distance_estimate"] = value
                break
                
        return position
    
    def approach_object(self, object_name, position, confidence=0.6, max_approach_time=30, min_distance=15):
        """Approach an object using an iterative approach algorithm
        
        Args:
            object_name: Name of the object to approach
            position: Initial position of the object (e.g., 'left', 'right center')
            confidence: Confidence threshold for object detection
            max_approach_time: Maximum time to spend approaching in seconds
            min_distance: Minimum distance to maintain from object in cm
            
        Returns:
            Dict containing approach results
        """
        if not self.initialized or not self.camera_initialized:
            logger.warning("Hardware or camera not initialized, cannot approach object")
            return {
                "success": False,
                "approach_time": 0,
                "message": "Hardware or camera not initialized"
            }
        
        # Initialize approach variables
        start_time = time.time()
        approach_complete = False
        object_lost = False
        approach_steps = 0
        last_position = position
        last_confidence = confidence
        last_distance = self.check_distance()
        
        # Extract initial position details
        position_details = self.extract_position_details(position)
        logger.info(f"Initial position details: {position_details}")
        
        # Store initial state
        self.memory.set("initial_distance", last_distance)
        
        # Main approach loop
        while not approach_complete and time.time() - start_time < max_approach_time:
            approach_steps += 1
            logger.info(f"Approach step {approach_steps}")
            print(f"🚗 Approach step {approach_steps}...")
            
            # Check current distance
            current_distance = self.check_distance()
            logger.info(f"Current distance: {current_distance}cm")
            
            # If we're close enough to the object, we're done
            if current_distance <= min_distance + 5:  # Add small buffer
                logger.info(f"Reached target distance: {current_distance}cm")
                print(f"🎉 Reached target distance: {current_distance}cm!")
                approach_complete = True
                break
            
            # Capture image to verify object is still visible
            image_path = self.capture_image(f"approach_{approach_steps}.jpg")
            if not image_path:
                logger.warning("Failed to capture image")
                continue
            
            # Analyze image to find object
            objects = self.analyze_image_with_gpt4(image_path, object_name)
            
            # Check if object is still visible
            target_object = None
            for obj in objects:
                obj_name = obj.get("name", "").lower()
                obj_confidence = obj.get("confidence", 0)
                if object_name.lower() in obj_name and obj_confidence >= confidence:
                    target_object = obj
                    break
            
            if not target_object:
                logger.warning(f"Object {object_name} not found in image")
                print(f"⚠️ Object {object_name} not visible, trying to recover...")
                
                # If we've lost the object, try turning slightly to find it again
                if not object_lost:
                    object_lost = True
                    # Try turning in the direction we last saw the object
                    if position_details["horizontal"] == "left":
                        self.turn(-20)  # Turn left
                    elif position_details["horizontal"] == "right":
                        self.turn(20)  # Turn right
                    continue
                else:
                    # If we've already tried to recover once, give up
                    logger.warning("Object lost and recovery failed")
                    print(f"❌ Object {object_name} lost, approach failed")
                    return {
                        "success": False,
                        "approach_time": time.time() - start_time,
                        "approach_steps": approach_steps,
                        "final_distance": current_distance,
                        "message": f"Object {object_name} lost during approach"
                    }
            
            # Reset object_lost flag if we found the object again
            object_lost = False
            
            # Update position and confidence
            last_position = target_object.get("position", last_position)
            last_confidence = target_object.get("confidence", last_confidence)
            
            # Extract new position details
            position_details = self.extract_position_details(last_position)
            logger.info(f"Updated position details: {position_details}")
            
            # Determine approach strategy based on position and distance
            if position_details["horizontal"] != "center":
                # Need to turn toward the object first
                turn_angle = 30 if position_details["horizontal"] == "right" else -30
                logger.info(f"Turning {turn_angle} degrees toward object")
                print(f"🔄 Turning {'right' if turn_angle > 0 else 'left'} to center object...")
                self.turn(turn_angle)
                continue  # Skip forward movement this iteration
            
            # Object is centered, move forward
            # Calculate approach distance based on current distance and position
            approach_distance = min(current_distance - min_distance, 30)  # Cap at 30cm per step
            
            # Convert distance to movement time (rough approximation)
            # Assuming speed of 30 moves about 20cm per second
            move_time = approach_distance / 40.0  # seconds
            move_time = max(min(move_time, 1.0), 0.3)  # Between 0.3 and 1.0 seconds
            
            # Move forward
            logger.info(f"Moving forward for {move_time:.1f}s (approx {approach_distance:.1f}cm)")
            print(f"🚗 Moving forward for {move_time:.1f}s...")
            self.move_forward(speed=30, duration=move_time)
            
            # Short pause to stabilize
            time.sleep(0.3)
            
            # Update last distance
            last_distance = current_distance
        
        # Check if we timed out
        elapsed_time = time.time() - start_time
        if not approach_complete and elapsed_time >= max_approach_time:
            logger.warning(f"Approach timed out after {max_approach_time}s")
            print(f"⏰ Approach timed out after {max_approach_time}s")
            return {
                "success": False,
                "approach_time": elapsed_time,
                "approach_steps": approach_steps,
                "final_distance": self.check_distance(),
                "message": f"Approach timed out after {max_approach_time}s"
            }
        
        # Approach complete
        final_distance = self.check_distance()
        logger.info(f"Approach complete in {elapsed_time:.1f}s, final distance: {final_distance}cm")
        print(f"🎉 Approach complete in {elapsed_time:.1f}s, final distance: {final_distance}cm")
        
        # Celebrate by wiggling if we reached the target
        if final_distance <= min_distance + 10:  # Within 10cm of target
            self.turn(10)
            time.sleep(0.2)
            self.turn(-20)
            time.sleep(0.2)
            self.turn(10)
        
        return {
            "success": True,
            "approach_time": elapsed_time,
            "approach_steps": approach_steps,
            "final_distance": final_distance,
            "message": f"Successfully approached {object_name} to {final_distance}cm in {elapsed_time:.1f}s"
        }
    
    def cleanup(self):
        """Clean up resources"""
        logger.info("Cleaning up resources")
        
        # Clean up hardware
        if self.initialized:
            try:
                self.px.stop()
            except Exception as e:
                logger.error(f"Hardware cleanup error: {e}")
        
        # Clean up camera
        if self.camera_initialized:
            try:
                Vilib.camera_close()
                logger.info("Camera closed")
            except Exception as e:
                logger.error(f"Camera cleanup error: {e}")
