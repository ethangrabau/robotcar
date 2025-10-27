"""
PiCar-X Preset Actions Module
Contains predefined actions and sounds for the PiCar-X robot
"""

# Import standard modules
import time
from time import sleep
import random
import os

# Import hardware-specific modules with error handling
try:
    # Only import the classes, don't instantiate them
    from picarx import Picarx
    from robot_hat import Music
    hardware_available = True
except ImportError as e:
    print(f"Error importing hardware modules: {e}")
    hardware_available = False

# Import the object search module
try:
    from object_search import ObjectSearcher
    object_search_available = True
except ImportError:
    print("Object search module not available")
    object_search_available = False

# Global variables
# =================================================================
# These will be set by agent_car.py
my_car = None
music = None
object_searcher = None

# This file should not initialize any hardware
# Hardware will be initialized in agent_car.py
search_target = None

# Constants
DEFAULT_HEAD_PAN = 0
DEFAULT_HEAD_TILT = 0

# Original action functions
# =================================================================
def shake_head(car):
    """Shake head action"""
    print("Action: Shaking head")
    car.set_cam_pan_angle(30)
    sleep(.2)
    car.set_cam_pan_angle(-30)
    sleep(.2)
    car.set_cam_pan_angle(30)
    sleep(.2)
    car.set_cam_pan_angle(-30)
    sleep(.2)
    car.set_cam_pan_angle(0)
    sleep(.2)

def nod(car):
    """Nod action"""
    print("Action: Nodding")
    car.set_cam_tilt_angle(20)
    sleep(.2)
    car.set_cam_tilt_angle(-20)
    sleep(.2)
    car.set_cam_tilt_angle(20)
    sleep(.2)
    car.set_cam_tilt_angle(-20)
    sleep(.2)
    car.set_cam_tilt_angle(0)
    sleep(.2)

def wave_hands(car):
    """Wave hands action"""
    print("Action: Waving hands")
    car.set_dir_servo_angle(30)
    sleep(.2)
    car.set_dir_servo_angle(-30)
    sleep(.2)
    car.set_dir_servo_angle(30)
    sleep(.2)
    car.set_dir_servo_angle(-30)
    sleep(.2)
    car.set_dir_servo_angle(0)
    sleep(.2)

def resist(car):
    """Resist action"""
    print("Action: Resisting")
    car.forward(50)
    sleep(.1)
    car.forward(0)
    sleep(.1)
    car.backward(50)
    sleep(.1)
    car.forward(0)
    sleep(.1)
    car.forward(50)
    sleep(.1)
    car.forward(0)
    sleep(.1)
    car.backward(50)
    sleep(.1)
    car.forward(0)
    sleep(.1)

def act_cute(car):
    """Act cute action"""
    print("Action: Acting cute")
    car.set_cam_pan_angle(20)
    sleep(.2)
    car.set_cam_tilt_angle(20)
    sleep(.2)
    car.set_cam_pan_angle(-20)
    sleep(.2)
    car.set_cam_tilt_angle(-20)
    sleep(.2)
    car.set_cam_pan_angle(0)
    sleep(.2)
    car.set_cam_tilt_angle(0)
    sleep(.2)

def rub_hands(car):
    """Rub hands action"""
    print("Action: Rubbing hands")
    car.set_dir_servo_angle(20)
    sleep(.2)
    car.set_dir_servo_angle(30)
    sleep(.2)
    car.set_dir_servo_angle(20)
    sleep(.2)
    car.set_dir_servo_angle(30)
    sleep(.2)
    car.set_dir_servo_angle(0)
    sleep(.2)

def think(car):
    """Think action"""
    print("Action: Thinking")
    car.set_cam_pan_angle(30)
    sleep(.5)
    car.set_cam_tilt_angle(20)
    sleep(.5)
    car.set_cam_pan_angle(-30)
    sleep(.5)
    car.set_cam_tilt_angle(-20)
    sleep(.5)
    car.set_cam_pan_angle(0)
    sleep(.2)
    car.set_cam_tilt_angle(0)
    sleep(.2)

def keep_think(car):
    """Keep thinking action"""
    print("Action: Keep thinking")
    car.set_cam_pan_angle(30)
    sleep(.5)
    car.set_cam_tilt_angle(20)
    sleep(.5)
    car.set_cam_pan_angle(-30)
    sleep(.5)
    car.set_cam_tilt_angle(-20)
    sleep(.5)
    car.set_cam_pan_angle(0)
    sleep(.2)
    car.set_cam_tilt_angle(0)
    sleep(.2)

def twist_body(car):
    """Twist body action"""
    print("Action: Twisting body")
    car.set_dir_servo_angle(30)
    sleep(.2)
    car.set_dir_servo_angle(-30)
    sleep(.2)
    car.set_dir_servo_angle(30)
    sleep(.2)
    car.set_dir_servo_angle(-30)
    sleep(.2)
    car.set_dir_servo_angle(0)
    sleep(.2)

def celebrate(car):
    """Celebrate action"""
    print("Action: Celebrating")
    car.set_dir_servo_angle(30)
    sleep(.1)
    car.set_dir_servo_angle(-30)
    sleep(.1)
    car.set_dir_servo_angle(30)
    sleep(.1)
    car.set_dir_servo_angle(-30)
    sleep(.1)
    car.set_dir_servo_angle(0)
    sleep(.1)
    car.set_cam_pan_angle(30)
    sleep(.1)
    car.set_cam_pan_angle(-30)
    sleep(.1)
    car.set_cam_pan_angle(30)
    sleep(.1)
    car.set_cam_pan_angle(-30)
    sleep(.1)
    car.set_cam_pan_angle(0)
    sleep(.1)

def depressed(car):
    """Depressed action"""
    print("Action: Depressed")
    car.set_cam_tilt_angle(-30)
    sleep(.2)
    car.set_cam_pan_angle(0)
    sleep(.2)

# Search and exploration actions
# =================================================================
def search(car):
    """Basic search action that combines movement and looking around"""
    print("Action: Searching the area")
    # Look around in different directions
    car.set_cam_pan_angle(30)
    time.sleep(0.5)
    car.set_cam_pan_angle(-30)
    time.sleep(0.5)
    car.set_cam_pan_angle(0)
    
    # Move forward a bit
    car.forward(40)
    time.sleep(1.5)
    car.stop()
    
    # Look around again
    car.set_cam_tilt_angle(20)
    time.sleep(0.5)
    car.set_cam_tilt_angle(-20)
    time.sleep(0.5)
    car.set_cam_tilt_angle(0)
    
    # Turn slightly and continue
    car.set_dir_servo_angle(15)
    car.forward(40)
    time.sleep(1)
    car.stop()
    car.set_dir_servo_angle(0)
    
def find_object(car):
    """Start the advanced object search process"""
    global object_searcher, search_target
    
    if not object_search_available or object_searcher is None:
        print("Object search not available, using basic search instead")
        search(car)
        return
    
    # Use the global search_target if available
    object_name = search_target if search_target else "anything interesting"
        
    print(f"Action: Starting advanced search for {object_name}")
    object_searcher.start_search(object_name)
    
    # Do one search step immediately
    object_searcher.search_step()
    
def search_step(car):
    """Execute one step of the object search process"""
    global object_searcher
    
    if not object_search_available or object_searcher is None:
        print("Object search not available, using basic search instead")
        search(car)
        return
        
    # Execute one step of the search process
    found = object_searcher.search_step()
    if found:
        print("Object found!")
        
def stop_search(car):
    """Stop the current search process"""
    global object_searcher
    
    if not object_search_available or object_searcher is None:
        print("No active search to stop")
        car.stop()
        return
        
    print("Action: Stopping search")
    object_searcher.stop_search()

# New movement actions
# =================================================================
def forward(car):
    """Move forward"""
    print("Action: Moving forward")
    car.set_dir_servo_angle(0)
    car.forward(50)
    time.sleep(1)
    car.stop()

def backward(car):
    """Move backward"""
    print("Action: Moving backward")
    car.set_dir_servo_angle(0)
    car.backward(50)
    time.sleep(1)
    car.stop()

def turn_left(car):
    """Turn left"""
    print("Action: Turning left")
    car.set_dir_servo_angle(-30)
    car.forward(50)
    time.sleep(1)
    car.stop()
    car.set_dir_servo_angle(0)

def turn_right(car):
    """Turn right"""
    print("Action: Turning right")
    car.set_dir_servo_angle(30)
    car.forward(50)
    time.sleep(1)
    car.stop()
    car.set_dir_servo_angle(0)

def stop(car):
    """Stop movement"""
    print("Action: Stopping")
    car.stop()

# Head movement actions
# =================================================================
def look_up(car):
    """Look up"""
    print("Action: Looking up")
    car.set_cam_tilt_angle(30)
    time.sleep(0.5)

def look_down(car):
    """Look down"""
    print("Action: Looking down")
    car.set_cam_tilt_angle(-30)
    time.sleep(0.5)

def look_left(car):
    """Look left"""
    print("Action: Looking left")
    car.set_cam_pan_angle(30)
    time.sleep(0.5)

def look_right(car):
    """Look right"""
    print("Action: Looking right")
    car.set_cam_pan_angle(-30)
    time.sleep(0.5)

def look_center(car):
    """Look center"""
    print("Action: Looking center")
    car.set_cam_pan_angle(0)
    car.set_cam_tilt_angle(0)
    time.sleep(0.5)

# Sound effects
# =================================================================
def start_engine(car):
    """Play start engine sound"""
    print("Sound: Start engine")
    try:
        global music
        if music:
            music.sound_effect_threading(music.sound_effect_path + "start_engine.wav")
    except Exception as e:
        print(f"Sound effect error: {e}")

# Action and sound dictionaries
# =================================================================
actions_dict = {
    # Original actions with spaces
    "shake head": shake_head, 
    "nod": nod,
    "wave hands": wave_hands,
    "resist": resist,
    "act cute": act_cute,
    "rub hands": rub_hands,
    "think": think,
    "twist body": twist_body,
    "celebrate": celebrate,
    "depressed": depressed,
    
    # New actions with underscores
    "shake_head": shake_head, 
    "nod": nod,
    "wave_hands": wave_hands,
    "resist": resist,
    "act_cute": act_cute,
    "rub_hands": rub_hands,
    "think": think,
    "twist_body": twist_body,
    "celebrate": celebrate,
    "depressed": depressed,
    
    # Movement actions
    "forward": forward,
    "backward": backward,
    "turn_left": turn_left,
    "turn_right": turn_right,
    "stop": stop,
    
    # Head movement actions
    "look_up": look_up,
    "look_down": look_down,
    "look_left": look_left,
    "look_right": look_right,
    "look_center": look_center,
    
    # Search and exploration actions
    "search": search,
    "search_area": search,
    "explore": search,
    "find": find_object,
    "find_object": find_object,
    "look_for": find_object,
    "search_step": search_step,
    "stop_search": stop_search,
}

sounds_dict = {
    # Original sound actions with spaces
    "start engine": start_engine,
    
    # New sound actions with underscores
    "start_engine": start_engine,
}


# Test code when run directly
# =================================================================
if __name__ == "__main__":
    if hardware_available:
        test_car = Picarx()
        test_car.reset()
        
        print("Testing basic actions...")
        shake_head(test_car)
        nod(test_car)
        
        print("Testing search actions...")
        search(test_car)
    else:
        print("Hardware not available, can't run test actions")
