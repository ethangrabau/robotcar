#!/usr/bin/env python3
"""
Updated preset actions for PiCar-X robot with both original and new actions
"""
from time import sleep
import random
from math import sin, cos, pi
import os

# Original expression actions
# =================================================================
def wave_hands(car):
    car.reset()
    car.set_cam_tilt_angle(20)
    for _ in range(2):
        car.set_dir_servo_angle(-25)
        sleep(.1)
        car.set_dir_servo_angle(25)
        sleep(.1)
    car.set_dir_servo_angle(0)

def resist(car):
    car.reset()
    car.set_cam_tilt_angle(10)
    for _ in range(3):
        car.set_dir_servo_angle(-15)
        car.set_cam_pan_angle(15)
        sleep(.1)
        car.set_dir_servo_angle(15)
        car.set_cam_pan_angle(-15)
        sleep(.1)
    car.stop()
    car.set_dir_servo_angle(0)
    car.set_cam_pan_angle(0)

def act_cute(car):
    car.reset()
    car.set_cam_tilt_angle(-20)
    for i in range(15):
        car.forward(5)
        sleep(0.02)
        car.backward(5)
        sleep(0.02)
    car.set_cam_tilt_angle(0)
    car.stop()

def rub_hands(car):
    car.reset()
    for i in range(5):
        car.set_dir_servo_angle(-6)
        sleep(.5)
        car.set_dir_servo_angle(6)
        sleep(.5)
    car.reset()

def think(car):
    car.reset()
    for i in range(11):
        car.set_cam_pan_angle(i*3)
        car.set_cam_tilt_angle(-i*2)
        car.set_dir_servo_angle(i*2)
        sleep(.05)
    sleep(1)
    car.set_cam_pan_angle(15)
    car.set_cam_tilt_angle(-10)
    car.set_dir_servo_angle(10)
    sleep(.1)
    car.reset()

def keep_think(car):
    car.reset()
    for i in range(11):
        car.set_cam_pan_angle(i*3)
        car.set_cam_tilt_angle(-i*2)
        car.set_dir_servo_angle(i*2)
        sleep(.05)

def shake_head(car):
    car.stop()
    car.set_cam_pan_angle(0)
    car.set_cam_pan_angle(60)
    sleep(.2)
    car.set_cam_pan_angle(-50)
    sleep(.1)
    car.set_cam_pan_angle(40)
    sleep(.1)
    car.set_cam_pan_angle(-30)
    sleep(.1)
    car.set_cam_pan_angle(20)
    sleep(.1)
    car.set_cam_pan_angle(-10)
    sleep(.1)
    car.set_cam_pan_angle(10)
    sleep(.1)
    car.set_cam_pan_angle(-5)
    sleep(.1)
    car.set_cam_pan_angle(0)

def nod(car):
    car.reset()
    car.set_cam_tilt_angle(0)
    car.set_cam_tilt_angle(5)
    sleep(.1)
    car.set_cam_tilt_angle(-30)
    sleep(.1)
    car.set_cam_tilt_angle(5)
    sleep(.1)
    car.set_cam_tilt_angle(-30)
    sleep(.1)
    car.set_cam_tilt_angle(0)

def depressed(car):
    car.reset()
    car.set_cam_tilt_angle(0)
    car.set_cam_tilt_angle(20)
    sleep(.22)
    car.set_cam_tilt_angle(-22)
    sleep(.1)
    car.set_cam_tilt_angle(10)
    sleep(.1)
    car.set_cam_tilt_angle(-22)
    sleep(.1)
    car.set_cam_tilt_angle(0)
    sleep(.1)
    car.set_cam_tilt_angle(-22)
    sleep(.1)
    car.set_cam_tilt_angle(-10)
    sleep(.1)
    car.set_cam_tilt_angle(-22)
    sleep(.1)
    car.set_cam_tilt_angle(-15)
    sleep(.1)
    car.set_cam_tilt_angle(-22)
    sleep(.1)
    car.set_cam_tilt_angle(-19)
    sleep(.1)
    car.set_cam_tilt_angle(-22)
    sleep(.1)
    sleep(1.5)
    car.reset()

def twist_body(car):
    car.reset()
    for i in range(3):
        car.set_motor_speed(1, 20)
        car.set_motor_speed(2, 20)
        car.set_cam_pan_angle(-20)
        car.set_dir_servo_angle(-10)
        sleep(.1)
        car.set_motor_speed(1, 0)
        car.set_motor_speed(2, 0)
        car.set_cam_pan_angle(0)
        car.set_dir_servo_angle(0)
        sleep(.1)
        car.set_motor_speed(1, -20)
        car.set_motor_speed(2, -20)
        car.set_cam_pan_angle(20)
        car.set_dir_servo_angle(10)
        sleep(.1)
        car.set_motor_speed(1, 0)
        car.set_motor_speed(2, 0)
        car.set_cam_pan_angle(0)
        car.set_dir_servo_angle(0)
        sleep(.1)

def celebrate(car):
    car.reset()
    car.set_cam_tilt_angle(20)
    car.set_dir_servo_angle(30)
    car.set_cam_pan_angle(60)
    sleep(.3)
    car.set_dir_servo_angle(10)
    car.set_cam_pan_angle(30)
    sleep(.1)
    car.set_dir_servo_angle(30)
    car.set_cam_pan_angle(60)
    sleep(.3)
    car.set_dir_servo_angle(0)
    car.set_cam_pan_angle(0)
    sleep(.2)
    car.set_dir_servo_angle(-30)
    car.set_cam_pan_angle(-60)
    sleep(.3)
    car.set_dir_servo_angle(-10)
    car.set_cam_pan_angle(-30)
    sleep(.1)
    car.set_dir_servo_angle(-30)
    car.set_cam_pan_angle(-60)
    sleep(.3)
    car.set_dir_servo_angle(0)
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
    print("Action: Moving forward")
    car.forward(50)
    sleep(1)
    car.stop()

def backward(car):
    print("Action: Moving backward")
    car.backward(50)
    sleep(1)
    car.stop()

def turn_left(car):
    print("Action: Turning left")
    car.set_dir_servo_angle(30)  # Set steering to left
    car.forward(50)  # Move forward with left steering
    sleep(0.5)
    car.stop()

def turn_right(car):
    print("Action: Turning right")
    car.set_dir_servo_angle(-30)  # Set steering to right
    car.forward(50)  # Move forward with right steering
    sleep(0.5)
    car.stop()

def stop(car):
    print("Action: Stopping")
    car.stop()

# New head movement actions
# =================================================================
def look_up(car):
    print("Action: Looking up")
    # Since get_cam_tilt_angle isn't available, we'll use a relative movement
    car.set_cam_tilt_angle(20)  # Positive angle for looking up

def look_down(car):
    print("Action: Looking down")
    # Since get_cam_tilt_angle isn't available, we'll use a relative movement
    car.set_cam_tilt_angle(-20)  # Negative angle for looking down

def look_left(car):
    print("Action: Looking left")
    # Since get_cam_pan_angle isn't available, we'll use a relative movement
    car.set_cam_pan_angle(30)  # Positive angle for looking left

def look_right(car):
    print("Action: Looking right")
    # Since get_cam_pan_angle isn't available, we'll use a relative movement
    car.set_cam_pan_angle(-30)  # Negative angle for looking right

def look_center(car):
    print("Action: Looking center")
    car.set_cam_pan_angle(0)
    car.set_cam_tilt_angle(0)

# Sound effects
# =================================================================
def honking(music):
    print("Sound: Honking")
    try:
        music.sound_play_threading("../sounds/car-double-horn.wav", 100)
    except Exception as e:
        print(f"Sound effect error: {e}")

def start_engine(music):
    print("Sound: Starting engine")
    try:
        music.sound_play_threading("../sounds/car-start-engine.wav", 50)
    except Exception as e:
        print(f"Sound effect error: {e}")

# Global variables
# =================================================================
# These will be initialized after the functions are defined
my_car = None
music = None
object_searcher = None
search_target = None

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
    # Original sound actions
    "honking": honking,
    "start engine": start_engine,
    
    # New sound actions with underscores

if __name__ == "__main__":
    if hardware_available:
        my_car = Picarx()
        music = Music()

    os.popen("pinctrl set 20 op dh") # enable robot_hat speaker switch
    current_path = os.path.dirname(os.path.abspath(__file__))
    os.chdir(current_path) # change working directory

    if hardware_available:
        my_car.reset()
    my_car.reset()

    music = Music()

    sleep(.5)

    print("Available actions:")
    _actions_num = len(actions_dict)
    actions = list(actions_dict.keys())
    for i, key in enumerate(actions):
        print(f'{i} {key}')
    
    print("\nAvailable sounds:")
    _sounds_num = len(sounds_dict)
    sounds = list(sounds_dict.keys())
    for i, key in enumerate(sounds_dict):
        print(f'{i} {key}')

    last_key = None

    try:
        while True:
            key = input("Enter action number or name (or press Enter to repeat last action): ")

            if key == '':
                if last_key > _actions_num - 1:
                    print(sounds[last_key-_actions_num])
                    sounds_dict[sounds[last_key-_actions_num]](music)
                else:
                    print(actions[last_key])
                    actions_dict[actions[last_key]](my_car)
            else:
                try:
                    # Try to parse as a number
                    key_num = int(key)
                    if key_num > (_actions_num + _sounds_num - 1):
                        print("Invalid key number")
                    elif key_num > (_actions_num - 1):
                        last_key = key_num
                        print(sounds[last_key-_actions_num])
                        sounds_dict[sounds[last_key-_actions_num]](music)
                    else:
                        last_key = key_num
                        print(actions[key_num])
                        actions_dict[actions[key_num]](my_car)
                except ValueError:
                    # Try as a string key
                    if key in actions_dict:
                        print(f"Executing action: {key}")
                        actions_dict[key](my_car)
                    elif key in sounds_dict:
                        print(f"Playing sound: {key}")
                        sounds_dict[key](music)
                    else:
                        print(f"Unknown action or sound: {key}")

    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f'Error:\n {e}')
    finally:
        my_car.reset()
        sleep(.1)
