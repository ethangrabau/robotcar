#!/usr/bin/env python3
"""
Preset actions for PiCar-X robot
"""
import time
from robot_hat import Music

# Movement actions
# =================================================================
def forward(car):
    print("Action: Moving forward")
    car.forward(50)
    time.sleep(1)
    car.stop()

def backward(car):
    print("Action: Moving backward")
    car.backward(50)
    time.sleep(1)
    car.stop()

def turn_left(car):
    print("Action: Turning left")
    car.turn_left(50)
    time.sleep(0.5)
    car.stop()

def turn_right(car):
    print("Action: Turning right")
    car.turn_right(50)
    time.sleep(0.5)
    car.stop()

def stop(car):
    print("Action: Stopping")
    car.stop()

# Head movement actions
# =================================================================
def look_up(car):
    print("Action: Looking up")
    current_angle = car.get_cam_tilt_angle()
    car.set_cam_tilt_angle(current_angle + 10)

def look_down(car):
    print("Action: Looking down")
    current_angle = car.get_cam_tilt_angle()
    car.set_cam_tilt_angle(current_angle - 10)

def look_left(car):
    print("Action: Looking left")
    current_angle = car.get_cam_pan_angle()
    car.set_cam_pan_angle(current_angle + 10)

def look_right(car):
    print("Action: Looking right")
    current_angle = car.get_cam_pan_angle()
    car.set_cam_pan_angle(current_angle - 10)

def look_center(car):
    print("Action: Looking center")
    car.set_cam_pan_angle(0)
    car.set_cam_tilt_angle(0)

# Expression actions
# =================================================================
def shake_head(car):
    print("Action: Shaking head")
    car.set_cam_pan_angle(20)
    time.sleep(0.2)
    car.set_cam_pan_angle(-20)
    time.sleep(0.2)
    car.set_cam_pan_angle(20)
    time.sleep(0.2)
    car.set_cam_pan_angle(0)

def nod(car):
    print("Action: Nodding")
    car.set_cam_tilt_angle(20)
    time.sleep(0.2)
    car.set_cam_tilt_angle(-20)
    time.sleep(0.2)
    car.set_cam_tilt_angle(20)
    time.sleep(0.2)
    car.set_cam_tilt_angle(0)

def wave_hands(car):
    print("Action: Waving hands (simulated with head movement)")
    for _ in range(3):
        car.set_cam_pan_angle(15)
        time.sleep(0.2)
        car.set_cam_pan_angle(-15)
        time.sleep(0.2)
    car.set_cam_pan_angle(0)

def resist(car):
    print("Action: Resisting")
    car.backward(30)
    time.sleep(0.3)
    car.forward(30)
    time.sleep(0.3)
    car.stop()

def act_cute(car):
    print("Action: Acting cute")
    car.set_cam_tilt_angle(15)
    car.set_cam_pan_angle(15)
    time.sleep(0.5)
    car.set_cam_tilt_angle(-15)
    car.set_cam_pan_angle(-15)
    time.sleep(0.5)
    car.set_cam_tilt_angle(0)
    car.set_cam_pan_angle(0)

def rub_hands(car):
    print("Action: Rubbing hands (simulated with movement)")
    car.forward(20)
    time.sleep(0.2)
    car.backward(20)
    time.sleep(0.2)
    car.forward(20)
    time.sleep(0.2)
    car.backward(20)
    time.sleep(0.2)
    car.stop()

def think(car):
    print("Action: Thinking")
    car.set_cam_tilt_angle(20)
    time.sleep(1)
    car.set_cam_tilt_angle(0)

def twist_body(car):
    print("Action: Twisting body")
    car.turn_left(30)
    time.sleep(0.3)
    car.turn_right(30)
    time.sleep(0.3)
    car.turn_left(30)
    time.sleep(0.3)
    car.stop()

def celebrate(car):
    print("Action: Celebrating")
    for _ in range(2):
        car.forward(40)
        time.sleep(0.3)
        car.backward(40)
        time.sleep(0.3)
    car.stop()
    for _ in range(2):
        car.set_cam_tilt_angle(20)
        time.sleep(0.2)
        car.set_cam_tilt_angle(-20)
        time.sleep(0.2)
    car.set_cam_tilt_angle(0)

def depressed(car):
    print("Action: Depressed")
    car.set_cam_tilt_angle(-20)
    time.sleep(1.5)
    car.set_cam_tilt_angle(0)

# Keep thinking action for continuous movement
# =================================================================
def keep_think(car):
    print("Action: Keep thinking")
    car.set_cam_tilt_angle(10)
    time.sleep(0.5)
    car.set_cam_tilt_angle(-10)
    time.sleep(0.5)

# Sound effects
# =================================================================
def start_engine(music):
    print("Sound: Starting engine")
    try:
        music.sound_effect('start_engine.wav')
    except Exception as e:
        print(f"Sound effect error: {e}")

def honking(music):
    print("Sound: Honking")
    try:
        music.sound_effect('honking.wav')
    except Exception as e:
        print(f"Sound effect error: {e}")

# Action and sound dictionaries
# =================================================================
actions_dict = {
    'forward': forward,
    'backward': backward,
    'turn_left': turn_left,
    'turn_right': turn_right,
    'stop': stop,
    'look_up': look_up,
    'look_down': look_down,
    'look_left': look_left,
    'look_right': look_right,
    'look_center': look_center,
    'shake_head': shake_head,
    'nod': nod,
    'wave_hands': wave_hands,
    'resist': resist,
    'act_cute': act_cute,
    'rub_hands': rub_hands,
    'think': think,
    'twist_body': twist_body,
    'celebrate': celebrate,
    'depressed': depressed,
}

sounds_dict = {
    'start_engine': start_engine,
    'honking': honking,
}
