#!/usr/bin/env python3
"""
Basic Google Cast Test Script
This script tests basic discovery and connection to Google Cast devices
"""

import time
import sys
import json
import logging
from pathlib import Path

# Add parent directory to path to import modules
parent_dir = str(Path(__file__).parent.parent)
sys.path.insert(0, parent_dir)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import pychromecast directly
import pychromecast
import zeroconf
import re
from urllib.parse import urlparse, parse_qs
from pychromecast.controllers.youtube import YouTubeController

def extract_youtube_video_id(url):
    """
    Extract the video ID from a YouTube URL
    
    Args:
        url: YouTube URL
        
    Returns:
        Video ID or None if not found
    """
    if not url:
        return None
        
    # Check for youtu.be format
    if 'youtu.be' in url:
        return url.split('/')[-1].split('?')[0]
    
    # Check for standard youtube.com format
    parsed_url = urlparse(url)
    if 'youtube.com' in parsed_url.netloc:
        query_params = parse_qs(parsed_url.query)
        return query_params.get('v', [None])[0]
    
    # If it's already just an ID (11-12 chars, alphanumeric with some special chars)
    if re.match(r'^[\w-]{10,12}$', url):
        return url
    
    return None

def main():
    """Main test function"""
    print("=== Basic Google Cast Test ===")
    print("This script will test basic discovery and connection to Google Cast devices")
    
    # Discover devices using pychromecast directly
    print("\nDiscovering Google Cast devices...")
    # Create a zeroconf instance
    zconf = zeroconf.Zeroconf()
    services, browser = pychromecast.discovery.discover_chromecasts(zeroconf_instance=zconf)
    
    if not services:
        print("No Google Cast devices found on your network.")
        print("Please make sure your Google TV or Chromecast is powered on and connected to the same network.")
        return
    
    print(f"\nFound {len(services)} Google Cast device(s):")
    for i, service in enumerate(services):
        print(f"{i+1}. {service.friendly_name} ({service.model_name})")
    
    # Select a device
    selected_idx = 0
    if len(services) > 1:
        try:
            selected_idx = int(input("\nSelect a device by number (or press Enter for first device): ")) - 1
            if selected_idx < 0 or selected_idx >= len(services):
                print("Invalid selection, using first device")
                selected_idx = 0
        except (ValueError, IndexError):
            print("Invalid input, using first device")
            selected_idx = 0
    
    service = services[selected_idx]
    print(f"\nSelected device: {service.friendly_name} ({service.model_name})")
    
    # Connect to the selected device
    print(f"\nConnecting to {service.friendly_name}...")
    
    try:
        # Get the chromecast instance
        chromecast = pychromecast.get_chromecast_from_cast_info(service, zconf)
        
        # Wait for the device to be ready
        chromecast.wait()
        print(f"Successfully connected to {service.friendly_name}")
        
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
        print("8. Play direct media URL")
        print("9. Exit")
        
        while True:
            choice = input("\nEnter option (1-9): ")
            
            if choice == "9" or choice.lower() in ["exit", "quit"]:
                break
                
            elif choice == "1":
                print("\nPlaying a sample video...")
                mc = chromecast.media_controller
                mc.play_media(
                    "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4",
                    "video/mp4",
                    title="Big Buck Bunny"
                )
                mc.block_until_active()
                print("Video should be playing now")
                
            elif choice == "2":
                video_url = input("Enter YouTube video URL or ID: ")
                video_id = extract_youtube_video_id(video_url)
                if video_id:
                    print(f"\nPlaying YouTube video {video_id}...")
                    try:
                        # Method 1: Using YouTubeController
                        print("Trying YouTube controller method...")
                        yt = YouTubeController()
                        chromecast.register_handler(yt)
                        yt.play_video(video_id)
                        print("YouTube video should be playing now")
                    except Exception as e:
                        print(f"YouTube controller error: {e}")
                        
                        # Method 2: Try playing the YouTube URL directly
                        try:
                            print("\nTrying direct URL method...")
                            mc = chromecast.media_controller
                            direct_url = f"https://www.youtube.com/watch?v={video_id}"
                            mc.play_media(direct_url, "video/mp4", title=f"YouTube Video {video_id}")
                            mc.block_until_active()
                            print("YouTube video should be playing now via direct URL")
                        except Exception as e2:
                            print(f"Direct URL method error: {e2}")
                            print("\nTrying with a web receiver...")
                            try:
                                # Method 3: Launch the YouTube app first
                                chromecast.quit_app()
                                time.sleep(1)
                                chromecast.start_app('233637DE')
                                time.sleep(2)
                                yt = YouTubeController()
                                chromecast.register_handler(yt)
                                yt.play_video(video_id)
                                print("YouTube video should be playing now via app launch")
                            except Exception as e3:
                                print(f"App launch method error: {e3}")
                else:
                    print("Invalid YouTube URL or video ID")
                    print("Example formats: https://www.youtube.com/watch?v=ys_fN3uy7bQ or ys_fN3uy7bQ")
                
            elif choice == "3":
                print("\nPausing playback...")
                chromecast.media_controller.pause()
                print("Playback paused")
                
            elif choice == "4":
                print("\nResuming playback...")
                chromecast.media_controller.play()
                print("Playback resumed")
                
            elif choice == "5":
                print("\nStopping playback...")
                chromecast.media_controller.stop()
                print("Playback stopped")
                
            elif choice == "6":
                try:
                    volume = float(input("Enter volume level (0.0-1.0): "))
                    if 0 <= volume <= 1:
                        print(f"\nSetting volume to {volume}...")
                        chromecast.set_volume(volume)
                        print(f"Volume set to {volume}")
                    else:
                        print("Volume must be between 0.0 and 1.0")
                except ValueError:
                    print("Invalid volume level")
                    
            elif choice == "7":
                print("\nGetting device status...")
                status = chromecast.status
                print(f"Device: {chromecast.device.friendly_name}")
                print(f"Model: {chromecast.device.model_name}")
                print(f"Manufacturer: {chromecast.device.manufacturer}")
                print(f"UUID: {chromecast.device.uuid}")
                print(f"Cast type: {chromecast.device.cast_type}")
                print(f"Volume: {status.volume_level}")
                print(f"Muted: {status.volume_muted}")
                
                media_status = chromecast.media_controller.status
                if media_status:
                    print("\nMedia Status:")
                    print(f"State: {media_status.player_state}")
                    if hasattr(media_status, 'title') and media_status.title:
                        print(f"Title: {media_status.title}")
                    if hasattr(media_status, 'content_id') and media_status.content_id:
                        print(f"Content: {media_status.content_id}")
                        
            elif choice == "8":
                media_url = input("Enter direct media URL to play: ")
                if media_url:
                    print(f"\nPlaying media from URL: {media_url}")
                    try:
                        # Try to guess content type based on URL
                        content_type = "video/mp4"
                        if media_url.endswith(".mp3"):
                            content_type = "audio/mp3"
                        elif media_url.endswith(".wav"):
                            content_type = "audio/wav"
                        elif media_url.endswith(".m3u8"):
                            content_type = "application/x-mpegURL"
                        
                        mc = chromecast.media_controller
                        mc.play_media(media_url, content_type)
                        mc.block_until_active()
                        print("Media should be playing now")
                    except Exception as e:
                        print(f"Error playing media: {e}")
                
            else:
                print(f"\nUnrecognized option: {choice}")
        
        # Clean up
        print("\nCleaning up...")
        chromecast.disconnect()
        print("Test complete!")
        
    except Exception as e:
        print(f"Error connecting to device: {e}")
    
    # Stop discovery
    browser.stop_discovery()

if __name__ == "__main__":
    main()
