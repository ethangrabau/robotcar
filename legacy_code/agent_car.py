from openai_helper import OpenAiHelper
from keys import OPENAI_API_KEY, OPENAI_ASSISTANT_ID
from preset_actions import *
from utils import *

# Import the object search module
try:
    from object_search import ObjectSearcher
    object_search_available = True
except ImportError:
    print("Object search module not available")
    object_search_available = False

import readline # optimize keyboard input, only need to import

import speech_recognition as sr

from picarx import Picarx
from robot_hat import Music, Pin

import time
import threading
import random

import os
import sys
import subprocess

os.popen("pinctrl set 20 op dh") # enable robot_hat speaker switch
print("Speaker GPIO pin 20 enabled")
current_path = os.path.dirname(os.path.abspath(__file__))
os.chdir(current_path) # change working directory

input_mode = None
with_img = True
args = sys.argv[1:]
if '--keyboard' in args:
    input_mode = 'keyboard'
else:
    input_mode = 'voice'

if '--no-img' in args:
    with_img = False
else:
    with_img = True

# openai assistant init
# =================================================================
openai_helper = OpenAiHelper(OPENAI_API_KEY, OPENAI_ASSISTANT_ID, 'picarx')

# Set to True to enable continuous action mode (robot will keep executing actions until told to stop)
CONTINUOUS_ACTION_MODE = True
# Maximum number of times to repeat the last action sequence in continuous mode
MAX_ACTION_REPEATS = 5

# Set to True to enable advanced object search mode
ADVANCED_SEARCH_MODE = True
# Maximum search time in seconds
MAX_SEARCH_TIME = 120

LANGUAGE = []
# LANGUAGE = ['zh', 'en'] # config stt language code, https://en.wikipedia.org/wiki/List_of_ISO_639_language_codes

# VOLUME_DB = 5
VOLUME_DB = 3

# select tts voice role, counld be "alloy, echo, fable, onyx, nova, and shimmer"
# https://platform.openai.com/docs/guides/text-to-speech/supported-languages
TTS_VOICE = 'echo'

SOUND_EFFECT_ACTIONS = ["honking", "start engine"]

# car init - following the original gpt_car.py pattern EXACTLY
# =================================================================
try:
    print("Initializing PiCar-X hardware...")
    my_car = Picarx()
    time.sleep(1)
except Exception as e:
    print(f"Error initializing hardware: {e}")
    raise RuntimeError(e)

music = Music()
led = Pin('LED')
hardware_initialized = True

# Initialize the object searcher if hardware was initialized successfully
if hardware_initialized and object_search_available:
    try:
        print("Initializing object searcher...")
        object_searcher = ObjectSearcher(my_car, openai_helper)
        # Make sure preset_actions can access our objects
        import preset_actions
        preset_actions.my_car = my_car
        preset_actions.music = music
        preset_actions.object_searcher = object_searcher
        print("Object searcher initialized")
    except Exception as e:
        print(f"Error initializing object searcher: {e}")


DEFAULT_HEAD_TILT = 20

# Vilib start
# =================================================================
if with_img:
    from vilib import Vilib
    import cv2

    Vilib.camera_start(vflip=False,hflip=False)
    Vilib.show_fps()
    Vilib.display(local=False,web=True)

    while True:
        if Vilib.flask_start:
            break
        time.sleep(0.01)

    time.sleep(.5)
    print('\n')

# speech_recognition init
# =================================================================
'''
self.energy_threshold = 300  # minimum audio energy to consider for recording
self.dynamic_energy_threshold = True
self.dynamic_energy_adjustment_damping = 0.15
self.dynamic_energy_ratio = 1.5
self.pause_threshold = 0.8  # seconds of non-speaking audio before a phrase is considered complete
self.operation_timeout = None  # seconds after an internal operation (e.g., an API request) starts before it times out, or ``None`` for no timeout

self.phrase_threshold = 0.3  # minimum seconds of speaking audio before we consider the speaking audio a phrase - values below this are ignored (for filtering out clicks and pops)
self.non_speaking_duration = 0.5  # seconds of non-speaking audio to keep on both sides of the recording

'''
recognizer = sr.Recognizer()
recognizer.dynamic_energy_adjustment_damping = 0.16
recognizer.dynamic_energy_ratio = 1.6

# speak_hanlder
# =================================================================
speech_loaded = False
speech_lock = threading.Lock()
tts_file = None

# Simple espeak-based speech function as a fallback
def speak_with_espeak(text):
    try:
        print("Trying espeak with text:", text[:30], "...")
        subprocess.run(["espeak", text], check=True)
        return True
    except Exception as e:
        print(f"Espeak error: {e}")
        return False

def speak_hanlder():
    global speech_loaded, tts_file
    while True:
        with speech_lock:
            _isloaded = speech_loaded
        if _isloaded:
            # gray_print('speak start')
            speak_block(music, tts_file)
            # gray_print('speak done')
            with speech_lock:
                speech_loaded = False
        time.sleep(0.05)

speak_thread = threading.Thread(target=speak_hanlder)
speak_thread.daemon = True


# actions thread
# =================================================================
action_status = 'standby' # 'standby', 'think', 'actions', 'actions_done'
led_status = 'standby' # 'standby', 'think' or 'actions', 'actions_done'
last_action_status = 'standby'
last_led_status = 'standby'

LED_DOUBLE_BLINK_INTERVAL = 0.8 # seconds
LED_BLINK_INTERVAL = 0.1 # seconds

actions_to_be_done = []
action_lock = threading.Lock()

def action_handler():
    global action_status, actions_to_be_done, led_status, last_action_status, last_led_status

    # standby_actions = ['waiting', 'feet_left_right']
    # standby_weights = [1, 0.3]

    action_interval = 5 # seconds
    last_action_time = time.time()
    last_led_time = time.time()
    
    # For continuous action mode
    current_action_sequence = []
    action_repeat_count = 0

    while True:
        with action_lock:
            _state = action_status

        # led
        # ------------------------------
        led_status = _state

        if led_status != last_led_status:
            last_led_time = 0
            last_led_status = led_status

        if led_status == 'standby':
            if time.time() - last_led_time > LED_DOUBLE_BLINK_INTERVAL:
                led.off()
                led.on()
                sleep(.1)
                led.off()
                sleep(.1)
                led.on()
                sleep(.1)
                led.off()
                last_led_time = time.time()
        elif led_status == 'think':
            if time.time() - last_led_time > LED_BLINK_INTERVAL:
                led.off()
                sleep(LED_BLINK_INTERVAL)
                led.on()
                sleep(LED_BLINK_INTERVAL)
                last_led_time = time.time()
        elif led_status == 'actions':
                led.on() 

        # actions
        # ------------------------------
        if _state == 'standby':
            last_action_status = 'standby'
            if time.time() - last_action_time > action_interval:
                # TODO: standby actions
                last_action_time = time.time()
                action_interval = random.randint(2, 6)
        elif _state == 'think':
            if last_action_status != 'think':
                last_action_status = 'think'
                # think(my_car)
                keep_think(my_car)
        elif _state == 'actions':
            last_action_status = 'actions'
            with action_lock:
                _actions = actions_to_be_done
                
            # Save the current action sequence for potential repeating in continuous mode
            if CONTINUOUS_ACTION_MODE and len(_actions) > 0:
                current_action_sequence = _actions.copy()
                action_repeat_count = 0
                
            for _action in _actions:
                try:
                    actions_dict[_action](my_car)
                except Exception as e:
                    print(f'action error: {e}')
                time.sleep(0.5)

            with action_lock:
                # In continuous mode, check if we should repeat actions
                if CONTINUOUS_ACTION_MODE and action_repeat_count < MAX_ACTION_REPEATS:
                    # Check if any search-related actions are in the sequence
                    action_string = ' '.join(current_action_sequence)
                    search_terms = ['search', 'find', 'look_for', 'explore']
                    is_search_action = any(term in action_string for term in search_terms)
                    
                    if is_search_action:
                        print(f"Continuing search sequence (repeat {action_repeat_count + 1}/{MAX_ACTION_REPEATS})")
                        
                        # For advanced search, use search_step instead of repeating the whole sequence
                        if object_search_available and ADVANCED_SEARCH_MODE and 'find' in action_string:
                            # Just add a search_step action
                            actions_to_be_done = ['search_step']
                        else:
                            # Add some variation to the search pattern
                            if 'search' in current_action_sequence:
                                # Keep the search action
                                pass
                            else:
                                # Add search action if not already present
                                current_action_sequence.append('search')
                                
                            actions_to_be_done = current_action_sequence.copy()
                            
                        action_repeat_count += 1
                        # Stay in 'actions' state to repeat the sequence
                        action_status = 'actions'
                    else:
                        action_status = 'actions_done'
                else:
                    action_status = 'actions_done'
            last_action_time = time.time()

        time.sleep(0.01)

action_thread = threading.Thread(target=action_handler)
action_thread.daemon = True


# main
# =================================================================
def main():
    global action_status, actions_to_be_done, speak_queue, led_status

    # init
    # =================================================================
    # Following the original pattern exactly - initialize hardware here
    my_car.reset()
    my_car.set_cam_tilt_angle(DEFAULT_HEAD_TILT)

    speak_thread.start()
    action_thread.start()

    while True:
        if input_mode == 'voice':
            my_car.set_cam_tilt_angle(DEFAULT_HEAD_TILT)

            # listen
            # ----------------------------------------------------------------
            gray_print("listening ...")

            with action_lock:
                action_status = 'standby'

            _stderr_back = redirect_error_2_null() # ignore error print to ignore ALSA errors
            # If the chunk_size is set too small (default_size=1024), it may cause the program to freeze
            with sr.Microphone(chunk_size=8192) as source:
                cancel_redirect_error(_stderr_back) # restore error print
                print("Adjusting for ambient noise...")
                recognizer.adjust_for_ambient_noise(source, duration=1.5)
                print("Listening for speech... (speak clearly and wait for processing)")
                # Increase phrase_time_limit to give more time to finish speaking
                # Default timeout is 8 seconds if nothing is heard, and up to 15 seconds for the full phrase
                audio = recognizer.listen(source, timeout=8, phrase_time_limit=15)

            # stt
            # ----------------------------------------------------------------
            st = time.time()
            _result = openai_helper.stt(audio, language=LANGUAGE)
            gray_print(f"stt takes: {time.time() - st:.3f} s")

            if _result == False or _result == "":
                print() # new line
                continue

        elif input_mode == 'keyboard':
            my_car.set_cam_tilt_angle(DEFAULT_HEAD_TILT)

            with action_lock:
                action_status = 'standby'

            _result = input(f'\033[1;30m{"intput: "}\033[0m').encode(sys.stdin.encoding).decode('utf-8')

            if _result == False or _result == "":
                print() # new line
                continue

        else:
            raise ValueError("Invalid input mode")

        # chat-gpt
        # ---------------------------------------------------------------- 
        response = {}
        st = time.time()

        with action_lock:
            action_status = 'think'

        if with_img:
            img_path = './img_imput.jpg'
            cv2.imwrite(img_path, Vilib.img)
            response = openai_helper.dialogue_with_img(_result, img_path)
        else:
            response = openai_helper.dialogue(_result)

        gray_print(f'chat takes: {time.time() - st:.3f} s')

        # actions & TTS
        # ----------------------------------------------------------------
        _sound_actions = [] 
        try:
            if isinstance(response, dict):
                if 'actions' in response:
                    actions = list(response['actions'])
                else:
                    actions = ['stop']

                if 'answer' in response:
                    answer = response['answer']
                else:
                    answer = ''

                if len(answer) > 0:
                    _actions = list.copy(actions)
                    for _action in _actions:
                        if _action in SOUND_EFFECT_ACTIONS:
                            _sound_actions.append(_action)
                            actions.remove(_action)

            else:
                response = str(response)
                if len(response) > 0:
                    actions = []
                    answer = response

        except:
            actions = []
            answer = ''
    
        try:
            # ---- tts ----
            _tts_status = False
            if answer != '':
                st = time.time()
                _time = time.strftime("%y-%m-%d_%H-%M-%S", time.localtime())
                _tts_f = f"./tts/{_time}_raw.wav"
                
                # Try OpenAI TTS first
                print("Attempting OpenAI TTS...")
                _tts_status = openai_helper.text_to_speech(answer, _tts_f, TTS_VOICE, response_format='wav') # alloy, echo, fable, onyx, nova, and shimmer
                if _tts_status:
                    tts_file = f"./tts/{_time}_{VOLUME_DB}dB.wav"
                    _tts_status = sox_volume(_tts_f, tts_file, VOLUME_DB)
                    print("OpenAI TTS generated successfully")
                else:
                    print("OpenAI TTS failed, trying espeak fallback")
                    # Try espeak as fallback
                    espeak_success = speak_with_espeak(answer)
                    if espeak_success:
                        print("Espeak TTS successful")
                    else:
                        print("Both TTS methods failed")
                
                gray_print(f'tts takes: {time.time() - st:.3f} s')

            # ---- actions ----
            with action_lock:
                actions_to_be_done = actions
                gray_print(f'actions: {actions_to_be_done}')
                action_status = 'actions'

            # --- sound effects and voice ---
            for _sound in _sound_actions:
                try:
                    sounds_dict[_sound](music)
                except Exception as e:
                    print(f'action error: {e}')

            if _tts_status:
                with speech_lock:
                    speech_loaded = True

            # ---- wait speak done ----
            if _tts_status:
                while True:
                    with speech_lock:
                        if not speech_loaded:
                            break
                    time.sleep(.01)

            # ---- wait actions done ----
            while True:
                with action_lock:
                    if action_status != 'actions':
                        break
                time.sleep(.01)

            ##
            print() # new line

        except Exception as e:
            print(f'actions or TTS error: {e}')


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"\033[31mERROR: {e}\033[m")
    finally:
        if with_img:
            Vilib.camera_close()
        my_car.reset()