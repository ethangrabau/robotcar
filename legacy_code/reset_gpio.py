#!/usr/bin/env python3
"""
GPIO Reset Utility for PiCar-X
This script attempts to clean up and release any GPIO pins that might be in use
"""

import time
import os
import sys

def reset_gpio():
    """Attempt to reset and release all GPIO pins"""
    print("Attempting to reset GPIO pins...")
    
    try:
        # Try to use gpiozero's cleanup functions
        from gpiozero import Device
        from gpiozero.pins.rpigpio import RPiGPIOFactory
        Device.pin_factory = RPiGPIOFactory()
        Device.pin_factory.close()
        print("GPIO pins reset via gpiozero")
        return True
    except Exception as e:
        print(f"Error resetting via gpiozero: {e}")
    
    try:
        # Alternative method using RPi.GPIO
        import RPi.GPIO as GPIO
        # Check if mode is already set
        try:
            mode = GPIO.getmode()
            if mode is None:
                GPIO.setmode(GPIO.BCM)
        except:
            # If getmode() isn't available, just set it
            GPIO.setmode(GPIO.BCM)
        
        # Clean up all pins
        GPIO.cleanup()
        print("GPIO pins reset via RPi.GPIO")
        return True
    except Exception as e:
        print(f"Error resetting via RPi.GPIO: {e}")
    
    # Last resort - try to use system commands
    try:
        os.system("sudo killall pigpiod")
        time.sleep(1)
        os.system("sudo pigpiod")
        time.sleep(1)
        print("GPIO pins reset via system commands")
        return True
    except Exception as e:
        print(f"Error resetting via system commands: {e}")
    
    return False

if __name__ == "__main__":
    success = reset_gpio()
    sys.exit(0 if success else 1)
