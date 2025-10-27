#!/usr/bin/env python3
"""
Media Command Handler for Robot Car
Processes voice commands related to media playback and controls Google TV
"""

import os
import sys
import asyncio
import logging
import re
from typing import Dict, Any, Optional
from pathlib import Path

# Add parent directory to path to import modules
parent_dir = str(Path(__file__).parent.parent)
sys.path.insert(0, parent_dir)

from src.agent.tools.registry import tool_registry
from src.agent.tools.media_control_tool import MediaControlTool

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MediaCommandHandler:
    """
    Handler for media-related voice commands
    Integrates with the agent system to process commands like "play Paw Patrol on Disney"
    """
    
    def __init__(self):
        """Initialize the media command handler"""
        self.media_tool = None
        self._initialize_tool()
    
    def _initialize_tool(self):
        """Initialize the media control tool"""
        try:
            # Try to get the tool from the registry first
            self.media_tool = tool_registry.create_tool("media_control")
            
            # If not registered, create it directly
            if not self.media_tool:
                config_file = os.path.join(parent_dir, "config", "media_control_config.json")
                self.media_tool = MediaControlTool(config_file=config_file)
                
            logger.info("Media Command Handler initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing Media Command Handler: {e}")
    
    async def is_media_command(self, command: str) -> bool:
        """
        Check if a command is related to media playback
        
        Args:
            command: The voice command to check
            
        Returns:
            True if the command is a media command, False otherwise
        """
        command = command.lower().strip()
        
        # Check for media-related keywords
        media_keywords = [
            "play", "pause", "stop", "resume", "watch", "stream",
            "netflix", "disney", "youtube", "hulu", "prime", "video",
            "movie", "show", "episode", "tv", "television"
        ]
        
        # Check if any media keyword is in the command
        for keyword in media_keywords:
            if keyword in command:
                return True
        
        return False
    
    async def process_command(self, command: str) -> Dict[str, Any]:
        """
        Process a media-related voice command
        
        Args:
            command: The voice command to process
            
        Returns:
            Dictionary with the result of the command execution
        """
        if not self.media_tool:
            self._initialize_tool()
            if not self.media_tool:
                return {
                    "success": False,
                    "message": "Media control tool not available",
                    "response": "I'm sorry, but I can't control your TV right now. The media control system is not available."
                }
        
        # Check if this is a media command
        if not await self.is_media_command(command):
            return {
                "success": False,
                "message": "Not a media command",
                "response": None  # Let other handlers process this command
            }
        
        try:
            # Connect to the device if not already connected
            if not self.media_tool.connected:
                logger.info("Connecting to Google Cast device...")
                connected = await self.media_tool.connect_to_device()
                
                if not connected:
                    return {
                        "success": False,
                        "message": "Failed to connect to Google Cast device",
                        "response": "I'm sorry, but I couldn't connect to your TV. Make sure it's turned on and connected to the same network."
                    }
            
            # Execute the command
            result = await self.media_tool.execute(command)
            
            # Generate a user-friendly response
            response = self._generate_response(command, result)
            
            result["response"] = response
            return result
            
        except Exception as e:
            logger.error(f"Error processing media command: {e}")
            return {
                "success": False,
                "message": f"Error: {str(e)}",
                "response": "I'm sorry, but I encountered an error while trying to control your TV."
            }
    
    def _generate_response(self, command: str, result: Dict[str, Any]) -> str:
        """
        Generate a user-friendly response based on the command and result
        
        Args:
            command: The original command
            result: The result of the command execution
            
        Returns:
            A user-friendly response
        """
        if not result["success"]:
            return f"I'm sorry, but I couldn't {result.get('action_taken', 'process your request')}. {result['message']}"
        
        if result.get("action_taken") == "play":
            content = result.get("content", "the content")
            service = result.get("service", "")
            
            if service:
                service_name = {
                    "netflix": "Netflix",
                    "disney": "Disney+",
                    "youtube": "YouTube",
                    "hulu": "Hulu",
                    "prime": "Amazon Prime Video"
                }.get(service, service)
                
                return f"Playing {content} on {service_name} for you now."
            else:
                return f"Playing {content} for you now."
        
        elif result.get("action_taken") == "pause":
            return "I've paused the playback for you."
        
        elif result.get("action_taken") == "resume":
            return "I've resumed the playback for you."
        
        elif result.get("action_taken") == "stop":
            return "I've stopped the playback for you."
        
        return "I've processed your request for the TV."
    
    def cleanup(self):
        """Clean up resources"""
        if self.media_tool:
            self.media_tool.cleanup()


# Simple test function
async def test_media_command_handler():
    handler = MediaCommandHandler()
    
    test_commands = [
        "play Paw Patrol on Disney",
        "pause the TV",
        "resume playback",
        "stop the movie",
        "play cat videos on YouTube",
        "what's the weather like today"  # Non-media command
    ]
    
    for cmd in test_commands:
        print(f"\nTesting command: '{cmd}'")
        is_media = await handler.is_media_command(cmd)
        print(f"Is media command: {is_media}")
        
        if is_media:
            result = await handler.process_command(cmd)
            print(f"Success: {result['success']}")
            print(f"Response: {result['response']}")
    
    handler.cleanup()

if __name__ == "__main__":
    asyncio.run(test_media_command_handler())
