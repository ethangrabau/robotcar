from openai_helper import OpenAiHelper
from keys import OPENAI_API_KEY, OPENAI_ASSISTANT_ID
import preset_actions # Added to make the module object available
import sys # For command-line arguments
from preset_actions import *
from utils import *

# Import the object search module
try:
    from object_search import ObjectSearcher
    object_search_available = True
    print("Object search module available")
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

os.popen("pinctrl set 20 op dh") # enable robot_hat speake switch
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

# car init 
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

# Initialize object searcher if available
object_searcher = None
if object_search_available and ADVANCED_SEARCH_MODE:
    try:
        print("Initializing object searcher...")
        object_searcher = ObjectSearcher(my_car, openai_helper)
        # Make it available in preset_actions
        preset_actions.object_searcher = object_searcher
        print("Object searcher initialized successfully")
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
            for _action in _actions:
                action_handled_directly = False
                try:
                    if _action == "forward":
                        my_car.forward(30) # Default speed 30
                        action_handled_directly = True
                        print(f"Executed direct: {_action}")
                    elif _action == "backward":
                        my_car.backward(30)
                        action_handled_directly = True
                        print(f"Executed direct: {_action}")
                    elif _action == "turn_left":
                        my_car.turn_left(30)
                        action_handled_directly = True
                        print(f"Executed direct: {_action}")
                    elif _action == "turn_right":
                        my_car.turn_right(30)
                        action_handled_directly = True
                        print(f"Executed direct: {_action}")
                    elif _action == "stop":
                        my_car.stop()
                        action_handled_directly = True
                        print(f"Executed direct: {_action}")
                    elif _action == "look_left":
                        my_car.set_cam_pan_angle(-30) # Absolute angle
                        action_handled_directly = True
                        print(f"Executed direct: {_action} (pan to -30)")
                    elif _action == "look_right":
                        my_car.set_cam_pan_angle(30) # Absolute angle
                        action_handled_directly = True
                        print(f"Executed direct: {_action} (pan to 30)")
                    elif _action == "look_center":
                        my_car.set_cam_pan_angle(0)
                        my_car.set_cam_tilt_angle(0) # Reset tilt too
                        action_handled_directly = True
                        print(f"Executed direct: {_action}")
                    elif _action == "look_up":
                        my_car.set_cam_tilt_angle(-20) # Absolute angle (camera down for up view)
                        action_handled_directly = True
                        print(f"Executed direct: {_action} (tilt to -20)")
                    elif _action == "look_down":
                        my_car.set_cam_tilt_angle(20) # Absolute angle (camera up for down view)
                        action_handled_directly = True
                        print(f"Executed direct: {_action} (tilt to 20)")
                    
                    if not action_handled_directly:
                        if _action in actions_dict: # actions_dict from preset_actions
                            if _action in SOUND_EFFECT_ACTIONS: # SOUND_EFFECT_ACTIONS is global list
                                actions_dict[_action](snd) # Assuming 'snd' is the global Music instance
                                print(f"Executed preset sound: {_action}")
                            else:
                                actions_dict[_action](my_car) # my_car is the global Picarx instance
                                print(f"Executed preset action: {_action}")
                        else:
                            print(f'Action "{_action}" not found in direct commands or preset_actions.actions_dict.')
                    
                except AttributeError as ae:
                    print(f'AttributeError executing action "{_action}": {ae}. Is hardware fully initialized or method name correct?')
                except Exception as e:
                    print(f'Error executing action "{_action}": {e}')
                
                time.sleep(0.5) # Delay after each action attempt

            with action_lock:
                action_status = 'actions_done'
            last_action_time = time.time()

        time.sleep(0.01)

action_thread = threading.Thread(target=action_handler)
action_thread.daemon = True


# main
# =================================================================
def main():
    global current_feeling, last_feeling
    global speech_loaded
    global action_status, actions_to_be_done
    global tts_file

    my_car.reset()
    my_car.set_cam_tilt_angle(DEFAULT_HEAD_TILT)

    speak_thread.start()
    action_thread.start()

    # Check for command-line argument to directly start a search
    if len(sys.argv) > 1 and object_search_available and object_searcher is not None:
        cli_search_target = " ".join(sys.argv[1:]) # Join all args after script name
        print(f"Command-line search initiated for: {cli_search_target}")
        
        # Stop any other potential startup actions / clear action queue
        with action_lock:
            actions_to_be_done = ['stop']
            action_status = 'standby'
        my_car.stop()
        time.sleep(0.2)

        object_searcher.start_search(cli_search_target)
        search_successful = False
        print(f"Search for '{cli_search_target}' is now active (CLI mode). Calling search_step loop...")
        
        while object_searcher.is_searching:
            found_in_step = object_searcher.search_step()
            if found_in_step:
                search_successful = True
                break
            time.sleep(0.1)

        if search_successful:
            print(f"CLI Search: Hooray! I found the {cli_search_target}!")
        else:
            print(f"CLI Search: I looked for the {cli_search_target}, but I could not find it.")
        
        my_car.stop()
        my_car.set_cam_pan_angle(0)
        my_car.set_cam_tilt_angle(DEFAULT_HEAD_TILT)
        print("CLI search finished. Exiting.")
        # Clean up before exiting after CLI search
        if with_img:
            Vilib.camera_close()
        my_car.reset()
        return # Exit after CLI search is done

    # If no CLI argument for search, proceed to normal interactive loop
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
                print("Calibrating for ambient noise (1 second)...")
                recognizer.adjust_for_ambient_noise(source, duration=1)
                print("Listening for command...")
                audio = recognizer.listen(source)

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
                # Check for object search commands
                search_command = False
                search_target = None

                # First, check the user's direct speech input for search intent
                if isinstance(_result, str) and object_search_available and object_searcher is not None:
                    lower_result = _result.lower()
                    search_keywords = ["find ", "search for ", "look for "]
                    for keyword in search_keywords:
                        if keyword in lower_result:
                            search_command = True
                            search_target = _result[lower_result.find(keyword) + len(keyword):].strip()
                            # Remove any trailing question marks or periods if they are part of the target
                            if search_target.endswith('?'):
                                search_target = search_target[:-1].strip()
                            if search_target.endswith('.'):
                                search_target = search_target[:-1].strip()
                            print(f"Search intent detected in user speech: '{keyword}{search_target}'")
                            break
                
                # If not found in user speech, check LLM's suggested actions as a fallback
                if not search_command and 'actions' in response:
                    actions = list(response['actions'])
                    for action in actions: # Iterate through LLM's suggested actions
                        action_lower = action.lower()
                        if action_lower.startswith('find ') or action_lower.startswith('search for ') or action_lower.startswith('look for '):
                            if object_search_available and object_searcher is not None:
                                search_command = True
                                if action_lower.startswith('find '):
                                    search_target = action[5:].strip()
                                elif action_lower.startswith('search for '):
                                    search_target = action[11:].strip()
                                elif action_lower.startswith('look for '):
                                    search_target = action[9:].strip()
                                print(f"Search intent detected in LLM action: '{action}'")
                                break
                
                # After all search intent detection, define the 'actions' list for the action_handler.
                # This uses the LLM's suggested actions if available, otherwise defaults.
                # The search_command variable will determine if object_searcher is called later.
                if 'actions' in response and isinstance(response.get('actions'), list):
                    actions = list(response['actions'])
                else:
                    actions = ['stop'] # Default if LLM provides no actions or malformed actions

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
                _tts_status = openai_helper.text_to_speech(answer, _tts_f, TTS_VOICE, response_format='wav') # alloy, echo, fable, onyx, nova, and shimmer
                if _tts_status:
                    tts_file = f"./tts/{_time}_{VOLUME_DB}dB.wav"
                    _tts_status = sox_volume(_tts_f, tts_file, VOLUME_DB)
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
                    
            # ---- Execute object search if requested ----
            if search_command and search_target and object_searcher is not None:
                print(f"Initiating search for: {search_target}")

                # Stop any ongoing actions from action_handler before search starts
                # This also helps if the LLM's response TTS was still queued or playing.
                with action_lock:
                    actions_to_be_done = ['stop'] # Clear previous actions from LLM
                    action_status = 'standby' 
                my_car.stop() # Ensure car is stopped before search
                # Potentially stop current speech too, if possible.
                # For now, assuming speech from LLM response will finish or be short.
                time.sleep(0.2) # Give action_handler a moment and ensure car stops

                object_searcher.start_search(search_target) # Correct method to start search
                search_successful = False
                
                print(f"Search for '{search_target}' is now active. Calling search_step loop...")
                # Loop while the searcher is active. The searcher handles its own timeout.
                while object_searcher.is_searching:
                    found_in_step = object_searcher.search_step() # This moves the car, scans, etc.
                    if found_in_step:
                        search_successful = True
                        # object_searcher.stop_search() is called internally if found_object is True
                        # and is_searching becomes False.
                        break 
                    time.sleep(0.1) # Yield CPU and allow other threads to run.

                if search_successful:
                    success_message = f"Hooray! I found the {search_target}!"
                    print(success_message)
                elif not object_searcher.is_searching and not search_successful: 
                    failure_message = f"I looked for the {search_target}, but I could not find it after searching."
                    print(failure_message)
                
                # Reset search_command and search_target to prevent re-triggering in the same main loop iteration
                search_command = False
                search_target = None
                # Ensure car is stopped and camera reset after the entire search attempt
                my_car.stop()
                my_car.set_cam_pan_angle(0)
                my_car.set_cam_tilt_angle(DEFAULT_HEAD_TILT)

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

