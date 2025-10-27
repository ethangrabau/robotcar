#!/usr/bin/env python3
"""
Simple test script to verify speaker functionality on Raspberry Pi with PicarX
"""
import os
import subprocess
import time

def main():
    print("Testing speaker functionality...")
    
    # Enable the speaker GPIO pin
    print("Enabling speaker GPIO pin 20...")
    os.popen("pinctrl set 20 op dh")
    time.sleep(1)
    
    # Test with espeak
    print("Testing with espeak...")
    try:
        subprocess.run(["espeak", "Hello, this is a test of the speaker system"], check=True)
        print("Espeak test completed. Did you hear anything?")
    except Exception as e:
        print(f"Espeak error: {e}")
    
    # Test with aplay if we have a WAV file
    print("\nTesting with aplay and a test sound...")
    try:
        # Create a simple test sound using sox if available
        try:
            subprocess.run(["sox", "-n", "/tmp/test_sound.wav", "synth", "3", "sine", "1000"], check=True)
            print("Created test sound with sox")
            test_sound = "/tmp/test_sound.wav"
        except:
            print("Sox not available, using system sounds if available")
            test_sound = "/usr/share/sounds/alsa/Front_Center.wav"
        
        # Try to play the sound
        subprocess.run(["aplay", test_sound], check=True)
        print("Aplay test completed. Did you hear anything?")
    except Exception as e:
        print(f"Aplay error: {e}")
    
    print("\nSpeaker test complete.")
    print("If you didn't hear anything, check:")
    print("1. Is the speaker properly connected to GPIO pin 20?")
    print("2. Is the volume set correctly?")
    print("3. Are audio packages installed? (espeak, alsa-utils)")
    print("4. Try running with sudo: 'sudo python3 test_speaker.py'")

if __name__ == "__main__":
    main()
