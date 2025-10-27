#!/usr/bin/env python3
"""
Hardware bridge for PiCar-X agent system
Connects the agent tools with the hardware using the proven initialization pattern
"""

import os
import sys
import time
import asyncio
import logging
from typing import Dict, Any, Optional, List, Tuple

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('hardware_bridge.log')
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

class PiCarXHardware:
    """
    Hardware controller for PiCar-X
    Follows the exact initialization pattern from working_gpt_car.py
    """
    
    def __init__(self):
        self.px = None
        self.music = None
        self.pin = None
        self.initialized = False
        self.position = (0, 0, 0)  # x, y, heading in degrees
        
    def initialize(self):
        """Initialize hardware components in the correct order"""
        if not HARDWARE_AVAILABLE:
            logger.warning("Hardware not available, running in simulation mode")
            return False
            
        try:
            # Follow the exact initialization pattern from working_gpt_car.py
            logger.info("Initializing PiCar-X hardware...")
            
            # Enable robot_hat speaker switch (from working_gpt_car.py)
            os.popen("pinctrl set 20 op dh")
            
            # Initialize hardware in the correct order
            self.px = Picarx()
            self.music = Music()
            self.pin = Pin('LED_R')
            
            self.initialized = True
            logger.info("Hardware initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize hardware: {e}")
            self.initialized = False
            return False
    
    async def move_forward(self, distance: float, speed: float = 50) -> None:
        """Move forward a specific distance"""
        if not self.initialized:
            logger.warning("Hardware not initialized, simulating movement")
            await asyncio.sleep(abs(distance) / max(speed, 1) * 0.1)
            # Update simulated position
            self.position = (
                self.position[0] + distance * 0.1,  # Simple forward movement
                self.position[1],
                self.position[2]
            )
            return
            
        try:
            logger.info(f"Moving forward {distance}m at speed {speed}")
            self.px.forward(speed)
            await asyncio.sleep(abs(distance) / max(speed, 1) * 10)  # Rough estimate
            self.px.stop()
        except Exception as e:
            logger.error(f"Movement error: {e}")
    
    async def turn(self, degrees: float, speed: float = 50) -> None:
        """Turn in place by the specified degrees"""
        if not self.initialized:
            logger.warning("Hardware not initialized, simulating turn")
            await asyncio.sleep(abs(degrees) / 90 * 0.5)
            # Update simulated heading
            self.position = (
                self.position[0],
                self.position[1],
                (self.position[2] + degrees) % 360
            )
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
    
    def get_position(self) -> Tuple[float, float, float]:
        """Get the current position and heading"""
        return self.position
    
    async def distance_sensor(self) -> float:
        """Get distance from ultrasonic sensor with improved reliability"""
        if not self.initialized:
            logger.warning("Hardware not initialized, simulating distance check")
            return 100.0  # Simulate no obstacles
        
        try:
            # Take multiple readings to improve reliability
            readings = []
            for _ in range(3):
                distance = self.px.ultrasonic.read()
                # Filter out invalid readings (negative or very large values)
                if 0 <= distance < 300:  # Valid range: 0-300cm
                    readings.append(distance)
                await asyncio.sleep(0.05)  # Short delay between readings
            
            # Calculate average of valid readings
            if readings:
                avg_distance = sum(readings) / len(readings)
                logger.info(f"Distance: {avg_distance:.2f}cm")
                return avg_distance
            else:
                logger.warning("No valid distance readings")
                return 100.0  # Default safe distance
        except Exception as e:
            logger.error(f"Distance sensor error: {e}")
            return 100.0  # Default to no obstacles on error
    
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

# Singleton instance
_hardware = None

def get_hardware():
    """Get or create the hardware singleton"""
    global _hardware
    if _hardware is None:
        _hardware = PiCarXHardware()
        _hardware.initialize()
    return _hardware
