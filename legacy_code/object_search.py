"""
Object search module for PiCar-X
Combines movement, obstacle avoidance, and scene analysis to find objects
"""

import time
import random
from picarx import Picarx
import os
from time import strftime, localtime
from vilib import Vilib

# Constants for obstacle avoidance
POWER = 40  # Slightly reduced from 50 to be more careful
SAFE_DISTANCE = 40  # > 40 safe
DANGER_DISTANCE = 20  # > 20 && < 40 turn around, < 20 backward

# Search patterns
SEARCH_PATTERNS = [
    # Each pattern is a list of (direction, duration) tuples
    # direction: angle of the steering servo
    # duration: time to drive in that direction
    [(0, 2), (15, 1.5), (0, 2), (-15, 1.5)],  # Square-ish pattern
    [(0, 3), (20, 1), (-20, 1), (0, 2)],      # Zigzag pattern
    [(0, 2), (30, 0.8), (-30, 0.8), (0, 2)],  # Wide scan
]

class ObjectSearcher:
    """
    Handles searching for objects by combining movement and scene analysis
    """
    def __init__(self, car, openai_helper=None):
        """
        Initialize the object searcher
        
        Args:
            car: Picarx instance
            openai_helper: OpenAI helper for scene analysis
        """
        self.car = car
        self.openai_helper = openai_helper
        self.target_object = None
        self.is_searching = False
        self.found_object = False
        self.search_start_time = 0
        self.last_scan_time = 0
        self.scan_interval = 5  # seconds between scene scans
        self.max_search_time = 120  # maximum search time in seconds
        self.current_pattern_index = 0
        self.current_step_index = 0
        
        self.IMAGE_CAPTURE_DIR = "image_captures"
        os.makedirs(self.IMAGE_CAPTURE_DIR, exist_ok=True)
        
    def start_search(self, target_object):
        """
        Start searching for a specific object
        
        Args:
            target_object: String description of the object to find
        """
        print(f"Starting search for: {target_object}")
        self.target_object = target_object.lower()
        self.is_searching = True
        self.found_object = False
        self.search_start_time = time.time()
        self.last_scan_time = 0
        self.current_pattern_index = 0
        self.current_step_index = 0
        
    def stop_search(self):
        """Stop the current search"""
        if self.is_searching:
            print("Stopping search")
            self.is_searching = False
            self.car.stop()
            
    def search_step(self):
        """
        Execute one step of the search process
        Returns:
            bool: True if object was found, False otherwise
        """
        if not self.is_searching:
            return False
            
        # Check if we've been searching too long
        if time.time() - self.search_start_time > self.max_search_time:
            print(f"Search timeout after {self.max_search_time} seconds")
            self.stop_search()
            return False
            
        # Check for obstacles
        distance = self.get_distance()
        print(f"Distance to obstacle: {distance} cm")
        
        # Handle obstacles first
        if distance < DANGER_DISTANCE:
            print("Obstacle too close, backing up")
            self.car.set_dir_servo_angle(-30)
            self.car.backward(POWER)
            time.sleep(0.8)
            self.car.stop()
            # Choose a random new direction
            turn_angle = random.choice([-45, -30, 30, 45])
            self.car.set_dir_servo_angle(turn_angle)
            self.car.forward(POWER)
            time.sleep(0.5)
            self.car.stop()
            return False
        elif distance < SAFE_DISTANCE:
            print("Obstacle detected, turning")
            # Turn away from obstacle
            turn_angle = random.choice([-30, 30])
            self.car.set_dir_servo_angle(turn_angle)
            self.car.forward(POWER)
            time.sleep(0.8)
            self.car.stop()
            return False
            
        # Time to scan the environment?
        if time.time() - self.last_scan_time > self.scan_interval:
            return self.scan_for_object()
            
        # Otherwise, follow the search pattern
        pattern = SEARCH_PATTERNS[self.current_pattern_index]
        direction, duration = pattern[self.current_step_index]
        
        print(f"Search pattern: direction={direction}, duration={duration}")
        self.car.set_dir_servo_angle(direction)
        self.car.forward(POWER)
        time.sleep(duration)
        self.car.stop()
        
        # Move to next step in pattern
        self.current_step_index = (self.current_step_index + 1) % len(pattern)
        if self.current_step_index == 0:
            # Completed a pattern, switch to a different one
            self.current_pattern_index = (self.current_pattern_index + 1) % len(SEARCH_PATTERNS)
            
        return False
        
    def scan_for_object(self):
        """
        Scan the environment and check if the target object is visible
        
        Returns:
            bool: True if object was found, False otherwise
        """
        print(f"Scanning for {self.target_object}...")
        self.last_scan_time = time.time()
        
        # Look around in different directions
        scan_directions = [(0, 0), (30, 0), (-30, 0), (0, 20), (0, -20)]
        
        for pan, tilt in scan_directions:
            # Move camera
            self.car.set_cam_pan_angle(pan)
            self.car.set_cam_tilt_angle(tilt)
            time.sleep(0.5)  # Give camera time to move
            
            # Ask GPT to analyze the scene
            if self.openai_helper:
                prompt = f"Can you see a {self.target_object} in the current view? If yes, describe where it is."
                # Capture image
                img_name = f"scan_{strftime('%Y%m%d_%H%M%S', localtime())}"
                response = None # Initialize response
                img_path = None # Initialize img_path
                try:
                    # Vilib should be imported at the top of the file
                    # self.IMAGE_CAPTURE_DIR should be initialized in __init__
                    Vilib.take_photo(img_name, self.IMAGE_CAPTURE_DIR)
                    # Vilib.take_photo saves as path/name.jpg, so img_name should not have .jpg yet
                    img_path = os.path.join(self.IMAGE_CAPTURE_DIR, img_name + ".jpg") 
                    
                    if os.path.exists(img_path):
                        print(f"Captured image: {img_path}")
                        if hasattr(self.openai_helper, 'dialogue_with_img'):
                            response = self.openai_helper.dialogue_with_img(prompt, img_path)
                        else:
                            print("Error: openai_helper does not have dialogue_with_img. Falling back to text-only.")
                            if hasattr(self.openai_helper, 'dialogue'): # Check if dialogue method exists
                                response = self.openai_helper.dialogue(prompt) # Fallback
                            else:
                                print("Error: openai_helper also does not have dialogue method.")
                    else:
                        print(f"Error: Image file not found after Vilib.take_photo: {img_path}")
                
                except NameError as e: 
                    print(f"Error: Vilib or os/time functions not available. Imports correct? Details: {e}")
                except AttributeError as e: 
                    print(f"Error: Attribute missing, likely on self.openai_helper. Details: {e}")
                    # Fallback if dialogue_with_img is somehow not there despite checks
                    if hasattr(self.openai_helper, 'dialogue'):
                         response = self.openai_helper.dialogue(prompt)
                except Exception as e:
                    print(f"Error during image capture or OpenAI call: {e}")
                finally:
                    # Clean up the image if it was created
                    if img_path and os.path.exists(img_path):
                        try:
                            os.remove(img_path)
                            print(f"Deleted image: {img_path}")
                        except OSError as e_del:
                            print(f"Error deleting image {img_path}: {e_del}")
                
                # Check if response indicates the object was found
                if isinstance(response, dict) and "answer" in response:
                    answer_text = response["answer"].lower()
                    print(f"Scene analysis: {answer_text}")
                    
                    # Check if the answer indicates the object was found
                    positive_indicators = ["yes", "i can see", "i see", "found", "visible", "there is", "there's"]
                    if self.target_object in answer_text and any(indicator in answer_text for indicator in positive_indicators):
                        print(f"Found {self.target_object}!")
                        self.found_object = True
                        self.is_searching = False
                        return True
        
        # Reset camera position
        self.car.set_cam_pan_angle(0)
        self.car.set_cam_tilt_angle(0)
        return False
    
    def get_distance(self):
        """Get distance from ultrasonic sensor, with error handling"""
        try:
            return round(self.car.ultrasonic.read(), 2)
        except Exception as e:
            print(f"Error reading ultrasonic sensor: {e}")
            return 100  # Return a safe value if sensor fails
