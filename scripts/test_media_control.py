#!/usr/bin/env python3
"""
Test script for the Media Control Tool
This script tests the Google Cast integration for controlling media playback on Google TV
"""

import os
import sys
import asyncio
import logging
import json
from pathlib import Path

# Add parent directory to path to import modules
parent_dir = str(Path(__file__).parent.parent)
sys.path.insert(0, parent_dir)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Import the GoogleCastControl directly
sys.path.append(parent_dir)

# Adjust import path based on directory structure
try:
    from src.home_control.google_cast import GoogleCastControl
except ImportError:
    # Try direct import if module structure is different
    sys.path.append(os.path.join(parent_dir, 'src'))
    from home_control.google_cast import GoogleCastControl

async def main():
    """Main test function"""
    print("=== Google Cast Control Test ===")
    print("This script will test the Google Cast integration for controlling media playback")
    
    # Create the Google Cast controller
    cast_controller = GoogleCastControl()
    
    # Discover devices
    print("\nDiscovering Google Cast devices...")
    devices = await cast_controller.discover_devices()
    
    if not devices:
        print("No Google Cast devices found on your network.")
        print("Please make sure your Google TV or Chromecast is powered on and connected to the same network.")
        return
    
    print(f"\nFound {len(devices)} Google Cast device(s):")
    for i, device in enumerate(devices):
        print(f"{i+1}. {device['friendly_name']} ({device['model_name']})")
    
    # Select a device
    selected_idx = 0
    if len(devices) > 1:
        try:
            selected_idx = int(input("\nSelect a device by number (or press Enter for first device): ")) - 1
            if selected_idx < 0 or selected_idx >= len(devices):
                print("Invalid selection, using first device")
                selected_idx = 0
        except (ValueError, IndexError):
            print("Invalid input, using first device")
            selected_idx = 0
    
    selected_device = devices[selected_idx]
    print(f"\nSelected device: {selected_device['friendly_name']} ({selected_device['model_name']})")
    
    # Connect to the selected device
    print(f"\nConnecting to {selected_device['friendly_name']}...")
    connected = await cast_controller.connect(friendly_name=selected_device['friendly_name'])
    
    if not connected:
        print("Failed to connect to the device.")
        return
    
    print(f"Successfully connected to {selected_device['friendly_name']}")
    
    # Save the selected device as default in config
    config_dir = os.path.join(parent_dir, "config")
    if not os.path.exists(config_dir):
        os.makedirs(config_dir)
        
    config_file = os.path.join(config_dir, "media_control_config.json")
    try:
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                config = json.load(f)
        else:
            config = {"devices": [], "streaming_services": {}}
        
        config['default_device'] = selected_device['friendly_name']
        
        # Add device to known devices if not already there
        device_exists = False
        for device in config.get("devices", []):
            if device.get("friendly_name") == selected_device['friendly_name']:
                device_exists = True
                break
                
        if not device_exists:
            if "devices" not in config:
                config["devices"] = []
            config["devices"].append(selected_device)
        
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"Saved {selected_device['friendly_name']} as the default device")
    except Exception as e:
        print(f"Error saving configuration: {e}")
    
    # Interactive testing
    print("\n=== Interactive Test ===")
    print("Enter a command to test or select an option:")
    print("1. Play a sample video")
    print("2. Play a YouTube video")
    print("3. Pause playback")
    print("4. Resume playback")
    print("5. Stop playback")
    print("6. Set volume")
    print("7. Get device status")
    print("8. Exit")
    
    while True:
        choice = input("\nEnter option (1-8) or command: ")
        
        if choice == "8" or choice.lower() in ["exit", "quit"]:
            break
            
        elif choice == "1":
            print("\nPlaying a sample video...")
            await cast_controller.play_media(
                "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4",
                "video/mp4",
                "Big Buck Bunny"
            )
            
        elif choice == "2":
            video_id = input("Enter YouTube video ID (e.g., dQw4w9WgXcQ): ")
            if video_id:
                print(f"\nPlaying YouTube video {video_id}...")
                await cast_controller.play_youtube(video_id)
            
        elif choice == "3":
            print("\nPausing playback...")
            await cast_controller.pause()
            
        elif choice == "4":
            print("\nResuming playback...")
            await cast_controller.resume()
            
        elif choice == "5":
            print("\nStopping playback...")
            await cast_controller.stop()
            
        elif choice == "6":
            try:
                volume = float(input("Enter volume level (0.0-1.0): "))
                if 0 <= volume <= 1:
                    print(f"\nSetting volume to {volume}...")
                    await cast_controller.set_volume(volume)
                else:
                    print("Volume must be between 0.0 and 1.0")
            except ValueError:
                print("Invalid volume level")
                
        elif choice == "7":
            print("\nGetting device status...")
            status = cast_controller.get_status()
            print(json.dumps(status, indent=2))
            
        else:
            print(f"\nUnrecognized option: {choice}")
    
    # Clean up
    print("\nCleaning up...")
    cast_controller.disconnect()
    print("Test complete!")

if __name__ == "__main__":
    asyncio.run(main())
