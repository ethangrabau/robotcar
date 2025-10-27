#!/usr/bin/env python3
"""
Google Cast Integration for Robot Car
This module provides functionality to control Google Cast devices, including Google TV
"""

import time
import logging
import pychromecast
from pychromecast.controllers.youtube import YouTubeController
from pychromecast.controllers.media import MediaController
from pychromecast.discovery import CastBrowser, SimpleCastListener
import asyncio
from typing import Dict, List, Optional, Tuple, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class GoogleCastControl:
    """
    Class to control Google Cast devices including Google TV
    """
    def __init__(self, friendly_name: Optional[str] = None, ip_address: Optional[str] = None):
        """
        Initialize the Google Cast controller
        
        Args:
            friendly_name: The friendly name of the Google Cast device to control
            ip_address: The IP address of the Google Cast device (alternative to friendly_name)
        """
        self.cast = None
        self.friendly_name = friendly_name
        self.ip_address = ip_address
        self.media_controller = None
        self.youtube_controller = None
        self.connected = False
        self.available_devices = []
        
    async def discover_devices(self) -> List[Dict[str, Any]]:
        """
        Discover available Google Cast devices on the network
        
        Returns:
            List of dictionaries containing device information
        """
        logger.info("Discovering Google Cast devices...")
        
        # Create a simple listener that just collects devices
        class DeviceCollector:
            def __init__(self):
                self.devices = {}
                
            def add_cast(self, uuid, service):
                self.devices[uuid] = service
                
            def update_cast(self, uuid, service):
                self.devices[uuid] = service
                
            def remove_cast(self, uuid, service, cast_info):
                if uuid in self.devices:
                    del self.devices[uuid]
        
        # Run discovery in a separate thread to avoid blocking
        loop = asyncio.get_event_loop()
        collector = DeviceCollector()
        zconf = await loop.run_in_executor(None, lambda: pychromecast.discovery.CastZeroconf())
        browser = await loop.run_in_executor(
            None, 
            lambda: pychromecast.discovery.CastBrowser(
                collector, zconf
            )
        )
        
        # Start discovery
        await loop.run_in_executor(None, browser.start_discovery)
        
        # Wait for devices to be discovered (5 seconds)
        await asyncio.sleep(5)
        
        # Stop discovery
        await loop.run_in_executor(None, browser.stop_discovery)
        
        # Convert to a more usable format
        self.available_devices = []
        for uuid, service in collector.devices.items():
            cast_info = browser.devices[uuid]
            self.available_devices.append({
                "friendly_name": cast_info.friendly_name,
                "model_name": cast_info.model_name,
                "manufacturer": cast_info.manufacturer,
                "uuid": str(uuid),
                "ip_address": cast_info.host,
                "port": cast_info.port,
                "cast_type": cast_info.cast_type
            })
        
        logger.info(f"Found {len(self.available_devices)} Google Cast devices")
        return self.available_devices
    
    async def connect(self, friendly_name: Optional[str] = None, ip_address: Optional[str] = None) -> bool:
        """
        Connect to a specific Google Cast device
        
        Args:
            friendly_name: The friendly name of the device to connect to
            ip_address: The IP address of the device to connect to
            
        Returns:
            True if connection successful, False otherwise
        """
        # Use provided parameters or fall back to instance variables
        target_name = friendly_name or self.friendly_name
        target_ip = ip_address or self.ip_address
        
        if not target_name and not target_ip:
            logger.error("No device specified. Provide either friendly_name or ip_address")
            return False
        
        try:
            logger.info(f"Connecting to Google Cast device: {target_name or target_ip}")
            
            # First, make sure we have discovered devices
            if not self.available_devices:
                await self.discover_devices()
            
            # Try to find the device in our discovered devices
            device_info = None
            if target_name:
                for device in self.available_devices:
                    if device['friendly_name'] == target_name:
                        device_info = device
                        target_ip = device['ip_address']
                        break
            
            if not device_info and not target_ip:
                logger.error(f"Device not found: {target_name}")
                return False
            
            # Connect using the get_listed_chromecasts method which is more reliable
            loop = asyncio.get_event_loop()
            chromecasts, browser = await loop.run_in_executor(
                None, 
                lambda: pychromecast.get_listed_chromecasts(
                    friendly_names=[target_name] if target_name else None,
                    known_hosts=[target_ip] if target_ip else None,
                    discovery_timeout=10
                )
            )
            
            if not chromecasts:
                logger.error(f"Could not connect to device: {target_name or target_ip}")
                return False
                
            # Get the first matching chromecast
            self.cast = chromecasts[0]
            
            # Wait for the device to be ready
            await loop.run_in_executor(None, self.cast.wait)
            
            # Initialize controllers
            self.media_controller = self.cast.media_controller
            self.youtube_controller = YouTubeController()
            self.cast.register_handler(self.youtube_controller)
            
            # Update instance variables
            self.friendly_name = self.cast.device.friendly_name
            self.ip_address = self.cast.host
            self.connected = True
            
            logger.info(f"Successfully connected to {self.friendly_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error connecting to Google Cast device: {e}")
            self.connected = False
            return False
    
    def disconnect(self) -> None:
        """
        Disconnect from the Google Cast device
        """
        if self.cast:
            logger.info(f"Disconnecting from {self.friendly_name}")
            self.cast.disconnect()
            self.connected = False
            self.cast = None
            self.media_controller = None
            self.youtube_controller = None
    
    async def play_media(self, url: str, content_type: str, title: Optional[str] = None) -> bool:
        """
        Play media from a URL
        
        Args:
            url: The URL of the media to play
            content_type: The MIME type of the media
            title: Optional title to display
            
        Returns:
            True if successful, False otherwise
        """
        if not self.connected or not self.cast:
            logger.error("Not connected to any Google Cast device")
            return False
        
        try:
            logger.info(f"Playing media: {title or url}")
            self.media_controller.play_media(url, content_type, title=title)
            self.media_controller.block_until_active()
            return True
        except Exception as e:
            logger.error(f"Error playing media: {e}")
            return False
    
    async def play_youtube(self, video_id: str) -> bool:
        """
        Play a YouTube video by its ID
        
        Args:
            video_id: The YouTube video ID
            
        Returns:
            True if successful, False otherwise
        """
        if not self.connected or not self.cast:
            logger.error("Not connected to any Google Cast device")
            return False
        
        try:
            logger.info(f"Playing YouTube video: {video_id}")
            self.youtube_controller.play_video(video_id)
            return True
        except Exception as e:
            logger.error(f"Error playing YouTube video: {e}")
            return False
    
    async def pause(self) -> bool:
        """Pause the currently playing media"""
        if not self.connected or not self.media_controller:
            return False
        
        try:
            self.media_controller.pause()
            return True
        except Exception as e:
            logger.error(f"Error pausing media: {e}")
            return False
    
    async def resume(self) -> bool:
        """Resume the currently paused media"""
        if not self.connected or not self.media_controller:
            return False
        
        try:
            self.media_controller.play()
            return True
        except Exception as e:
            logger.error(f"Error resuming media: {e}")
            return False
    
    async def stop(self) -> bool:
        """Stop the currently playing media"""
        if not self.connected or not self.media_controller:
            return False
        
        try:
            self.media_controller.stop()
            return True
        except Exception as e:
            logger.error(f"Error stopping media: {e}")
            return False
    
    async def set_volume(self, volume_level: float) -> bool:
        """
        Set the volume level
        
        Args:
            volume_level: Volume level between 0.0 and 1.0
            
        Returns:
            True if successful, False otherwise
        """
        if not self.connected or not self.cast:
            return False
        
        try:
            self.cast.set_volume(volume_level)
            return True
        except Exception as e:
            logger.error(f"Error setting volume: {e}")
            return False
    
    async def mute(self, mute_on: bool = True) -> bool:
        """
        Mute or unmute the device
        
        Args:
            mute_on: True to mute, False to unmute
            
        Returns:
            True if successful, False otherwise
        """
        if not self.connected or not self.cast:
            return False
        
        try:
            self.cast.set_volume_muted(mute_on)
            return True
        except Exception as e:
            logger.error(f"Error setting mute state: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the device
        
        Returns:
            Dictionary with status information
        """
        status = {
            "connected": self.connected,
            "device_name": self.friendly_name if self.connected else None,
            "ip_address": self.ip_address if self.connected else None,
        }
        
        if self.connected and self.cast:
            status.update({
                "is_idle": self.cast.is_idle,
                "app_id": self.cast.app_id,
                "app_display_name": self.cast.app_display_name,
                "volume_level": self.cast.status.volume_level,
                "is_muted": self.cast.status.volume_muted,
            })
            
            if self.media_controller and self.media_controller.status:
                status.update({
                    "media_title": self.media_controller.status.title,
                    "media_artist": self.media_controller.status.artist,
                    "media_album": self.media_controller.status.album_name,
                    "media_current_time": self.media_controller.status.current_time,
                    "media_duration": self.media_controller.status.duration,
                    "media_state": self.media_controller.status.player_state,
                })
                
        return status


# Simple test function
async def test_cast():
    cast = GoogleCastControl()
    devices = await cast.discover_devices()
    
    if not devices:
        print("No Google Cast devices found")
        return
    
    print("Available devices:")
    for i, device in enumerate(devices):
        print(f"{i+1}. {device['friendly_name']} ({device['model_name']})")
    
    device_idx = int(input("Select device number: ")) - 1
    if device_idx < 0 or device_idx >= len(devices):
        print("Invalid selection")
        return
    
    selected_device = devices[device_idx]
    await cast.connect(friendly_name=selected_device['friendly_name'])
    
    print("Connected! Testing playback...")
    # Example: Play a sample media file
    await cast.play_media(
        "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4",
        "video/mp4",
        "Big Buck Bunny"
    )
    
    print("Media should be playing now. Waiting 10 seconds...")
    await asyncio.sleep(10)
    
    print("Pausing...")
    await cast.pause()
    await asyncio.sleep(3)
    
    print("Resuming...")
    await cast.resume()
    await asyncio.sleep(5)
    
    print("Stopping...")
    await cast.stop()
    
    print("Test complete!")
    cast.disconnect()

if __name__ == "__main__":
    asyncio.run(test_cast())
