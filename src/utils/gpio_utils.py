"""
GPIO utilities for managing hardware resources and preventing conflicts.
"""
import RPi.GPIO as GPIO
import os
import time
from typing import Optional

def cleanup_gpio():
    """
    Clean up GPIO resources.
    This should be called before initializing hardware to prevent conflicts.
    """
    try:
        GPIO.cleanup()
        time.sleep(0.1)  # Give time for cleanup to complete
    except Exception as e:
        print(f"Warning during GPIO cleanup: {e}")

def is_raspberry_pi() -> bool:
    """
    Check if the code is running on a Raspberry Pi.
    
    Returns:
        bool: True if running on a Raspberry Pi, False otherwise
    """
    try:
        with open('/proc/device-tree/model', 'r') as f:
            return 'Raspberry Pi' in f.read()
    except:
        return False

def setup_gpio():
    """
    Set up GPIO with safe defaults.
    Should be called at the start of the program.
    """
    if not is_raspberry_pi():
        return
        
    try:
        # Clean up any existing GPIO state
        cleanup_gpio()
        
        # Set GPIO mode to BCM (Broadcom SOC channel numbering)
        GPIO.setmode(GPIO.BCM)
        
        # Disable GPIO warnings (they can be noisy)
        GPIO.setwarnings(False)
        
    except Exception as e:
        print(f"Warning: Failed to set up GPIO: {e}")

def safe_shutdown():
    """
    Safely shut down the GPIO and hardware components.
    Should be called when the program exits.
    """
    if not is_raspberry_pi():
        return
        
    try:
        # Clean up GPIO
        cleanup_gpio()
    except Exception as e:
        print(f"Warning during safe shutdown: {e}")
    finally:
        # Ensure we don't leave any processes hanging
        try:
            import psutil
            current_process = psutil.Process()
            for child in current_process.children(recursive=True):
                child.terminate()
            current_process.terminate()
        except:
            pass
