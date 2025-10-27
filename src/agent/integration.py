#!/usr/bin/env python3
"""
Integration module for PiCar-X agent system
Bridges the working hardware code with the new agent framework
"""

import os
import sys
import time
import asyncio
import logging
from typing import Dict, Any, Optional, List

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('agent_integration.log')
    ]
)
logger = logging.getLogger(__name__)

# Hardware availability flag
HARDWARE_AVAILABLE = False

# Try to import hardware components
try:
    from picarx import Picarx
    from robot_hat import Music, Pin
    HARDWARE_AVAILABLE = True
    logger.info("Hardware modules available")
except ImportError:
    logger.warning("Hardware modules not available, using mock implementations")

# Import agent components
try:
    from src.agent.tools import ObjectSearchTool, tool_registry
    from src.agent.memory import SearchMemory
    logger.info("Agent modules loaded successfully")
except ImportError as e:
    logger.error(f"Failed to import agent modules: {e}")
    logger.error("Make sure the agent code is properly deployed")

class PiCarXController:
    """
    Controller for PiCar-X hardware
    Follows the initialization pattern from working_gpt_car.py
    """
    
    def __init__(self):
        self.px = None
        self.music = None
        self.pin = None
        self.initialized = False
        
    def initialize(self):
        """Initialize hardware components in the correct order"""
        if not HARDWARE_AVAILABLE:
            logger.warning("Hardware not available, running in simulation mode")
            return False
            
        try:
            # Follow the exact initialization pattern from working_gpt_car.py
            logger.info("Initializing PiCar-X hardware...")
            self.px = Picarx()
            self.music = Music()
            self.pin = Pin('LED_R')
            
            # Enable robot_hat speaker switch (from working_gpt_car.py)
            os.popen("pinctrl set 20 op dh")
            
            self.initialized = True
            logger.info("Hardware initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize hardware: {e}")
            self.initialized = False
            return False
    
    async def move_forward(self, distance: float, speed: float = 50):
        """Move forward a specific distance"""
        if not self.initialized:
            logger.warning("Hardware not initialized, simulating movement")
            await asyncio.sleep(abs(distance) / max(speed, 1) * 0.1)
            return
            
        try:
            logger.info(f"Moving forward {distance}m at speed {speed}")
            self.px.forward(speed)
            await asyncio.sleep(abs(distance) / max(speed, 1) * 10)  # Rough estimate
            self.px.stop()
        except Exception as e:
            logger.error(f"Movement error: {e}")
    
    async def turn(self, degrees: float, speed: float = 50):
        """Turn in place by the specified degrees"""
        if not self.initialized:
            logger.warning("Hardware not initialized, simulating turn")
            await asyncio.sleep(abs(degrees) / 90 * 0.5)
            return
            
        try:
            logger.info(f"Turning {degrees} degrees")
            if degrees > 0:
                self.px.set_dir_servo_angle(degrees)
            else:
                self.px.set_dir_servo_angle(degrees)
            await asyncio.sleep(abs(degrees) / 90)  # Rough estimate
            self.px.set_dir_servo_angle(0)
        except Exception as e:
            logger.error(f"Turn error: {e}")
    
    def cleanup(self):
        """Clean up hardware resources"""
        if self.initialized:
            try:
                logger.info("Cleaning up hardware resources")
                self.px.stop()
                if self.music:
                    self.music.music_stop()
            except Exception as e:
                logger.error(f"Cleanup error: {e}")

class VisionSystem:
    """
    Vision system for object detection
    Integrates with the camera and GPT-4 Vision
    """
    
    def __init__(self):
        self.camera_initialized = False
        
        # Try to initialize camera
        try:
            import vilib
            vilib.init_camera()
            vilib.camera_start()
            self.camera_initialized = True
            logger.info("Camera initialized successfully")
        except ImportError:
            logger.warning("vilib not available, vision will be simulated")
        except Exception as e:
            logger.error(f"Failed to initialize camera: {e}")
    
    async def capture_image(self, save_path: str = "current_view.jpg"):
        """Capture an image from the camera"""
        if not self.camera_initialized:
            logger.warning("Camera not initialized, simulating capture")
            return None
            
        try:
            import vilib
            import cv2
            import numpy as np
            
            # Get frame from vilib
            frame = vilib.get_frame()
            if frame is not None:
                cv2.imwrite(save_path, frame)
                logger.info(f"Image captured and saved to {save_path}")
                return save_path
            else:
                logger.warning("Failed to get frame from camera")
                return None
        except Exception as e:
            logger.error(f"Image capture error: {e}")
            return None
    
    async def detect_objects(self, image_path: Optional[str] = None):
        """
        Detect objects in an image
        In a real implementation, this would use GPT-4 Vision or another model
        """
        # Simulate object detection
        logger.info("Simulating object detection")
        await asyncio.sleep(0.5)
        
        # Return mock detection results
        return [
            {"name": "ball", "confidence": 0.85, "position": (2, 1, 0)},
            {"name": "chair", "confidence": 0.75, "position": (3, 2, 0)}
        ]
    
    def cleanup(self):
        """Clean up vision resources"""
        if self.camera_initialized:
            try:
                import vilib
                vilib.camera_release()
                logger.info("Camera resources released")
            except Exception as e:
                logger.error(f"Camera cleanup error: {e}")

class AgentSystem:
    """
    Main agent system for PiCar-X
    Integrates hardware control, vision, and agent tools
    """
    
    def __init__(self):
        self.car = PiCarXController()
        self.vision = VisionSystem()
        self.memory = SearchMemory()
        self.tools = {}
        self.initialized = False
    
    def initialize(self):
        """Initialize the agent system"""
        # Initialize hardware first
        hardware_ok = self.car.initialize()
        
        # Register tools
        try:
            self.tools['search'] = ObjectSearchTool(
                car=self.car,
                vision_system=self.vision
            )
            self.initialized = True
            logger.info("Agent system initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize agent system: {e}")
            self.initialized = False
            return False
    
    async def search_for_object(self, object_name: str, timeout: int = 60):
        """Search for an object using the search tool"""
        if not self.initialized:
            logger.warning("Agent system not initialized")
            return {"status": "error", "message": "Agent system not initialized"}
            
        if 'search' not in self.tools:
            logger.warning("Search tool not available")
            return {"status": "error", "message": "Search tool not available"}
            
        try:
            logger.info(f"Starting search for {object_name}")
            result = await self.tools['search'].execute(
                object_name=object_name,
                timeout=timeout
            )
            return result
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return {"status": "error", "message": str(e)}
    
    def cleanup(self):
        """Clean up all resources"""
        logger.info("Cleaning up agent system")
        self.car.cleanup()
        self.vision.cleanup()

# Singleton instance
_agent_system = None

def get_agent_system():
    """Get or create the agent system singleton"""
    global _agent_system
    if _agent_system is None:
        _agent_system = AgentSystem()
    return _agent_system

async def run_search(object_name: str, timeout: int = 60):
    """Helper function to run a search"""
    agent = get_agent_system()
    agent.initialize()
    try:
        return await agent.search_for_object(object_name, timeout)
    finally:
        agent.cleanup()
