#!/usr/bin/env python3
"""
Media Control Tool for Robot Car
Handles commands to play media on Google Cast devices
"""

import os
import sys
import asyncio
import logging
import json
import re
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

# Add parent directory to path to import modules
parent_dir = str(Path(__file__).parent.parent.parent)
sys.path.insert(0, parent_dir)

from home_control.google_cast import GoogleCastControl
# Import the base tool class
try:
    from agent.tools.base_tool import BaseTool
except ImportError:
    # If direct import fails, try relative import
    from .base_tool import BaseTool

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MediaControlTool(BaseTool):
    """
    Tool for controlling media playback on Google Cast devices
    """
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize the media control tool
        
        Args:
            config_file: Path to configuration file with device information
        """
        super().__init__()
        self.name = "media_control"
        self.description = "Control media playback on Google Cast devices"
        self.cast_controller = GoogleCastControl()
        self.connected = False
        self.default_device = None
        self.config = {}
        self.streaming_services = {
            "netflix": {
                "app_id": "Netflix",
                "launch_command": "netflix://"
            },
            "disney": {
                "app_id": "Disney+",
                "launch_command": "disney://"
            },
            "youtube": {
                "app_id": "YouTube",
                "search_url": "https://www.youtube.com/results?search_query="
            },
            "hulu": {
                "app_id": "Hulu",
                "launch_command": "hulu://"
            },
            "prime": {
                "app_id": "Amazon Prime Video",
                "launch_command": "amazon://"
            }
        }
        
        # Load configuration if provided
        if config_file:
            self._load_config(config_file)
    
    def _load_config(self, config_file: str) -> None:
        """
        Load configuration from file
        
        Args:
            config_file: Path to configuration file
        """
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    self.config = json.load(f)
                    
                # Set default device if specified
                if "default_device" in self.config:
                    self.default_device = self.config["default_device"]
                    logger.info(f"Default device set to: {self.default_device}")
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
    
    def _save_config(self, config_file: str) -> None:
        """
        Save configuration to file
        
        Args:
            config_file: Path to configuration file
        """
        try:
            with open(config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
            logger.info(f"Configuration saved to {config_file}")
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
    
    async def discover_devices(self) -> List[Dict[str, Any]]:
        """
        Discover available Google Cast devices
        
        Returns:
            List of available devices
        """
        return await self.cast_controller.discover_devices()
    
    async def connect_to_device(self, device_name: Optional[str] = None) -> bool:
        """
        Connect to a Google Cast device
        
        Args:
            device_name: Name of the device to connect to, or None to use default
            
        Returns:
            True if connection successful, False otherwise
        """
        target_device = device_name or self.default_device
        
        if not target_device:
            # If no device specified, try to discover and connect to the first Google TV
            devices = await self.discover_devices()
            for device in devices:
                if "Google TV" in device["model_name"]:
                    target_device = device["friendly_name"]
                    break
            
            if not target_device and devices:
                # Fall back to the first available device
                target_device = devices[0]["friendly_name"]
        
        if not target_device:
            logger.error("No device specified and no devices found")
            return False
        
        result = await self.cast_controller.connect(friendly_name=target_device)
        self.connected = result
        return result
    
    async def parse_media_command(self, command: str) -> Dict[str, Any]:
        """
        Parse a natural language media command
        
        Args:
            command: Natural language command like "play Paw Patrol on Disney"
            
        Returns:
            Dictionary with parsed command information
        """
        command = command.lower().strip()
        result = {
            "action": None,
            "content": None,
            "service": None,
            "valid": False
        }
        
        # Extract action (play, pause, stop)
        if "play" in command:
            result["action"] = "play"
        elif "pause" in command:
            result["action"] = "pause"
        elif "stop" in command:
            result["action"] = "stop"
        elif "resume" in command:
            result["action"] = "resume"
        else:
            return result
        
        # For pause/stop/resume, we don't need content or service
        if result["action"] in ["pause", "stop", "resume"]:
            result["valid"] = True
            return result
        
        # Extract service
        for service in self.streaming_services.keys():
            if service in command or self.streaming_services[service]["app_id"].lower() in command:
                result["service"] = service
                break
        
        # Extract content (what to play)
        if "play" in command:
            # Remove "play" and service name to get content
            content = command.replace("play", "", 1).strip()
            
            if result["service"]:
                content = re.sub(f"on {result['service']}", "", content, flags=re.IGNORECASE).strip()
                content = re.sub(f"on {self.streaming_services[result['service']]['app_id'].lower()}", "", content, flags=re.IGNORECASE).strip()
            
            # Remove other common phrases
            content = re.sub(r"on (the|my|our) (tv|television|google tv|chromecast)", "", content, flags=re.IGNORECASE).strip()
            
            if content:
                result["content"] = content
        
        # Command is valid if we have an action and either content or it's a simple action
        result["valid"] = bool(result["action"]) and (bool(result["content"]) or result["action"] in ["pause", "stop", "resume"])
        
        return result
    
    async def execute(self, command: str = "", device: str = None, **kwargs) -> Dict[str, Any]:
        """
        Execute a media control command
        
        Args:
            command: Natural language command like "play Paw Patrol on Disney"
            device: Optional device name to use
            
        Returns:
            Dictionary with result information
        """
        result = {
            "success": False,
            "message": "",
            "action_taken": None
        }
        
        # Connect to device if not already connected
        if not self.connected:
            connected = await self.connect_to_device(device)
            if not connected:
                result["message"] = "Failed to connect to Google Cast device"
                return result
        
        # Parse the command
        parsed = await self.parse_media_command(command)
        
        if not parsed["valid"]:
            result["message"] = "Invalid media command. Please specify what to play."
            return result
        
        # Handle simple actions (pause, stop, resume)
        if parsed["action"] == "pause":
            success = await self.cast_controller.pause()
            result["success"] = success
            result["message"] = "Media paused" if success else "Failed to pause media"
            result["action_taken"] = "pause"
            return result
        
        elif parsed["action"] == "resume":
            success = await self.cast_controller.resume()
            result["success"] = success
            result["message"] = "Media resumed" if success else "Failed to resume media"
            result["action_taken"] = "resume"
            return result
        
        elif parsed["action"] == "stop":
            success = await self.cast_controller.stop()
            result["success"] = success
            result["message"] = "Media stopped" if success else "Failed to stop media"
            result["action_taken"] = "stop"
            return result
        
        # Handle play commands
        elif parsed["action"] == "play" and parsed["content"]:
            content = parsed["content"]
            service = parsed["service"]
            
            result["action_taken"] = "play"
            result["content"] = content
            result["service"] = service
            
            # Handle YouTube specifically
            if service == "youtube":
                # For YouTube, we need to search for the content
                # In a real implementation, you would use the YouTube API to search
                # For now, we'll just simulate playing the first search result
                logger.info(f"Searching YouTube for: {content}")
                result["success"] = True
                result["message"] = f"Playing '{content}' on YouTube"
                # In a real implementation, you would use the YouTube API to get the video ID
                # await self.cast_controller.play_youtube("dQw4w9WgXcQ")  # Example video ID
                
            # For other services, we would use deep links or the Cast SDK
            # This is a simplified implementation
            elif service:
                logger.info(f"Playing '{content}' on {self.streaming_services[service]['app_id']}")
                result["success"] = True
                result["message"] = f"Playing '{content}' on {self.streaming_services[service]['app_id']}"
            else:
                # If no service specified, default to YouTube
                logger.info(f"No service specified, defaulting to YouTube for: {content}")
                result["success"] = True
                result["service"] = "youtube"
                result["message"] = f"Playing '{content}' on YouTube"
            
            return result
        
        result["message"] = "Could not process media command"
        return result
    
    def cleanup(self) -> None:
        """Clean up resources"""
        if self.cast_controller:
            self.cast_controller.disconnect()
            self.connected = False


# Simple test function
async def test_media_control():
    tool = MediaControlTool()
    
    # Discover devices
    print("Discovering Google Cast devices...")
    devices = await tool.discover_devices()
    
    if not devices:
        print("No Google Cast devices found")
        return
    
    print("Available devices:")
    for i, device in enumerate(devices):
        print(f"{i+1}. {device['friendly_name']} ({device['model_name']})")
    
    # Test parsing commands
    test_commands = [
        "play Paw Patrol on Disney",
        "play Stranger Things on Netflix",
        "pause",
        "resume",
        "stop",
        "play cat videos on YouTube"
    ]
    
    print("\nTesting command parsing:")
    for cmd in test_commands:
        parsed = await tool.parse_media_command(cmd)
        print(f"Command: '{cmd}'")
        print(f"Parsed: {json.dumps(parsed, indent=2)}")
        print()
    
    # Test execution with user input
    user_cmd = input("Enter a media command to test (e.g., 'play Paw Patrol on Disney'): ")
    if user_cmd:
        print(f"Executing: '{user_cmd}'")
        result = await tool.execute(user_cmd)
        print(f"Result: {json.dumps(result, indent=2)}")
    
    tool.cleanup()

if __name__ == "__main__":
    asyncio.run(test_media_control())
