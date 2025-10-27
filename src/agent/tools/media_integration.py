#!/usr/bin/env python3
"""
Media Integration for Robot Car Agent System
Registers the media control tool with the agent system and handles media-related commands
"""

import os
import sys
import logging
from pathlib import Path

# Add parent directory to path to import modules
parent_dir = str(Path(__file__).parent.parent.parent)
sys.path.insert(0, parent_dir)

from src.agent.tools.registry import tool_registry
from src.agent.tools.media_control_tool import MediaControlTool

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def register_media_control_tool():
    """Register the media control tool with the tool registry"""
    try:
        # Create a config path if it doesn't exist
        config_dir = os.path.join(parent_dir, "config")
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)
        
        config_file = os.path.join(config_dir, "media_control_config.json")
        
        # Register the tool class with the registry
        tool_registry.register_tool(MediaControlTool)
        
        logger.info("Media Control Tool registered successfully")
        return True
    except Exception as e:
        logger.error(f"Error registering Media Control Tool: {e}")
        return False

# Register the tool when this module is imported
register_media_control_tool()
