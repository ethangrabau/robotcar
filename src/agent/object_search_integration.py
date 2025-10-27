#!/usr/bin/env python3
"""
Object Search Integration for Agent Architecture
This module integrates the object search functionality with the agent system
"""

import os
import sys
import time
import asyncio
import logging
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('agent_search.log')
    ]
)
logger = logging.getLogger(__name__)

# Import our modules
from .tools.object_search_tool import ObjectSearchTool
from .hardware_bridge import get_hardware
from ..vision.gpt_vision import get_gpt_vision

class ObjectSearchManager:
    """
    Manager class for object search functionality in the agent system
    """
    
    def __init__(self):
        """Initialize the object search manager"""
        self.car = None
        self.vision = None
        self.search_tool = None
        self.initialized = False
        self.current_search = None
    
    async def initialize(self):
        """Initialize hardware and vision system"""
        if self.initialized:
            return True
            
        try:
            logger.info("Initializing object search manager")
            
            # Initialize hardware
            self.car = get_hardware()
            
            # Initialize vision system
            self.vision = get_gpt_vision()
            
            # Create the object search tool
            self.search_tool = ObjectSearchTool(car=self.car, vision_system=self.vision)
            
            self.initialized = True
            logger.info("Object search manager initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize object search manager: {e}")
            return False
    
    async def search_for_object(self, object_name: str, search_area: Optional[str] = None, 
                               timeout: int = 60, confidence_threshold: float = 0.5) -> Dict[str, Any]:
        """
        Search for an object using the object search tool
        
        Args:
            object_name: Name of the object to search for
            search_area: Optional area to search in
            timeout: Search timeout in seconds
            confidence_threshold: Confidence threshold (0.0-1.0)
            
        Returns:
            Dictionary with search results
        """
        if not self.initialized:
            success = await self.initialize()
            if not success:
                return {
                    "status": "error",
                    "message": "Failed to initialize object search manager",
                    "object_found": False
                }
        
        try:
            logger.info(f"Starting search for {object_name}")
            
            # Execute the search
            self.current_search = asyncio.create_task(
                self.search_tool.execute(
                    object_name=object_name,
                    search_area=search_area,
                    timeout=timeout,
                    confidence_threshold=confidence_threshold
                )
            )
            
            # Wait for the search to complete
            result = await self.current_search
            self.current_search = None
            
            return result
            
        except asyncio.CancelledError:
            logger.info("Search cancelled")
            return {
                "status": "cancelled",
                "message": "Search was cancelled",
                "object_found": False
            }
        except Exception as e:
            logger.error(f"Error during search: {e}")
            return {
                "status": "error",
                "message": f"Error during search: {str(e)}",
                "object_found": False
            }
    
    async def cancel_search(self):
        """Cancel the current search if one is in progress"""
        if self.current_search and not self.current_search.done():
            logger.info("Cancelling current search")
            self.search_tool.stop_search()
            self.current_search.cancel()
            return True
        return False
    
    def cleanup(self):
        """Clean up resources"""
        logger.info("Cleaning up object search manager resources")
        
        # Cancel any ongoing search
        if self.current_search and not self.current_search.done():
            self.search_tool.stop_search()
            self.current_search.cancel()
        
        # Clean up hardware and vision resources
        if self.car:
            self.car.cleanup()
        
        if self.vision:
            self.vision.cleanup()
        
        self.initialized = False

# Singleton instance
_object_search_manager = None

def get_object_search_manager():
    """Get or create the object search manager singleton"""
    global _object_search_manager
    if _object_search_manager is None:
        _object_search_manager = ObjectSearchManager()
    return _object_search_manager

# Example usage in agent system
async def agent_search_command(object_name: str, **kwargs):
    """Example of how an agent would use the object search functionality"""
    manager = get_object_search_manager()
    result = await manager.search_for_object(object_name, **kwargs)
    
    # Format the result for the agent
    if result["object_found"]:
        return {
            "success": True,
            "message": result["message"],
            "position": result.get("position", {}).get("position", "unknown"),
            "confidence": result.get("confidence", 0.0),
            "search_time": result.get("search_time", 0.0)
        }
    else:
        return {
            "success": False,
            "message": result["message"],
            "search_time": result.get("search_time", 0.0)
        }

# Main function for testing
async def main():
    """Main function for testing the object search integration"""
    try:
        # Initialize the manager
        manager = get_object_search_manager()
        await manager.initialize()
        
        # Search for a tennis ball
        result = await manager.search_for_object("tennis ball", timeout=60, confidence_threshold=0.6)
        
        # Display the result
        if result["object_found"]:
            print(f"✅ {result['message']}")
            print(f"📍 Position: {result.get('position', {}).get('position', 'unknown')}")
            print(f"🕒 Search time: {result['search_time']:.1f}s")
        else:
            print(f"❌ {result['message']}")
            print(f"🕒 Search time: {result.get('search_time', 0.0):.1f}s")
        
    except KeyboardInterrupt:
        print("\n🛑 Search interrupted by user")
    except Exception as e:
        logger.error(f"Error: {e}")
        print(f"❌ Error: {e}")
    finally:
        # Clean up resources
        if 'manager' in locals():
            manager.cleanup()
        print("🧹 Cleaned up resources")

if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
