#!/usr/bin/env python3
"""
Simple Google Cast Test Script
Tests basic discovery and control of Google Cast devices
"""

import time
import sys
import json
import asyncio
import logging
import pychromecast
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Main test function"""
    print("=== Simple Google Cast Test ===")
    print("This script will test basic Google Cast functionality")
    
    # Discover devices
    print("\nDiscovering Google Cast devices...")
    # Use the timeout parameter to give more time for discovery
    chromecasts, browser = pychromecast.get_chromecasts(timeout=10)
    
    if not chromecasts:
        print("No Google Cast devices found on your network.")
        print("Please make sure your Google TV or Chromecast is powered on and connected to the same network.")
        return
    
    print(f"\nFound {len(chromecasts)} Google Cast device(s):")
    for i, cast in enumerate(chromecasts):
        print(f"{i+1}. {cast.device.friendly_name} ({cast.device.model_name})")
    
    # Select a device
    selected_idx = 0
    if len(chromecasts) > 1:
        try:
            selected_idx = int(input("\nSelect a device by number (or press Enter for first device): ")) - 1
            if selected_idx < 0 or selected_idx >= len(chromecasts):
                print("Invalid selection, using first device")
                selected_idx = 0
        except (ValueError, IndexError):
            print("Invalid input, using first device")
            selected_idx = 0
    
    cast = chromecasts[selected_idx]
    print(f"\nSelected device: {cast.device.friendly_name} ({cast.device.model_name})")
    
    # Connect to the selected device
    print(f"\nConnecting to {cast.device.friendly_name}...")
    cast.wait()
    print(f"Successfully connected to {cast.device.friendly_name}")
    
    # Interactive testing
    print("\n=== Interactive Test ===")
    print("Enter a command to test:")
    print("1. Play a sample video")
    print("2. Play a YouTube video")
    print("3. Pause playback")
    print("4. Resume playback")
    print("5. Stop playback")
    print("6. Set volume")
    print("7. Get device status")
    print("8. Exit")
    
    while True:
        choice = input("\nEnter option (1-8): ")
        
        if choice == "8" or choice.lower() in ["exit", "quit"]:
            break
            
        elif choice == "1":
            print("\nPlaying a sample video...")
            mc = cast.media_controller
            mc.play_media(
                "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4",
                "video/mp4",
                title="Big Buck Bunny"
            )
            mc.block_until_active()
            print("Video should be playing now")
            
        elif choice == "2":
            from pychromecast.controllers.youtube import YouTubeController
            video_id = input("Enter YouTube video ID (e.g., dQw4w9WgXcQ): ")
            if video_id:
                print(f"\nPlaying YouTube video {video_id}...")
                yt = YouTubeController()
                cast.register_handler(yt)
                yt.play_video(video_id)
                print("YouTube video should be playing now")
            
        elif choice == "3":
            print("\nPausing playback...")
            cast.media_controller.pause()
            print("Playback paused")
            
        elif choice == "4":
            print("\nResuming playback...")
            cast.media_controller.play()
            print("Playback resumed")
            
        elif choice == "5":
            print("\nStopping playback...")
            cast.media_controller.stop()
            print("Playback stopped")
            
        elif choice == "6":
            try:
                volume = float(input("Enter volume level (0.0-1.0): "))
                if 0 <= volume <= 1:
                    print(f"\nSetting volume to {volume}...")
                    cast.set_volume(volume)
                    print(f"Volume set to {volume}")
                else:
                    print("Volume must be between 0.0 and 1.0")
            except ValueError:
                print("Invalid volume level")
                
        elif choice == "7":
            print("\nGetting device status...")
            status = cast.status
            print(f"Device: {cast.device.friendly_name}")
            print(f"Model: {cast.device.model_name}")
            print(f"Manufacturer: {cast.device.manufacturer}")
            print(f"UUID: {cast.device.uuid}")
            print(f"Cast type: {cast.device.cast_type}")
            print(f"Volume: {status.volume_level}")
            print(f"Muted: {status.volume_muted}")
            
            media_status = cast.media_controller.status
            if media_status:
                print("\nMedia Status:")
                print(f"State: {media_status.player_state}")
                if media_status.title:
                    print(f"Title: {media_status.title}")
                if media_status.content_id:
                    print(f"Content: {media_status.content_id}")
            
        else:
            print(f"\nUnrecognized option: {choice}")
    
    # Clean up
    print("\nCleaning up...")
    cast.disconnect()
    pychromecast.discovery.stop_discovery(browser)
    print("Test complete!")

if __name__ == "__main__":
    asyncio.run(main())
