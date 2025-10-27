#!/usr/bin/env python3
"""
Hardware integration for PiCar-X agent system
Connects the agent tools with the actual hardware using the proven initialization pattern
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
        logging.FileHandler('hardware_integration.log')
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
except ImportError as e:
    logger.warning(f"Hardware modules not available, using mock implementations: {e}")

# Try to import vision components
VISION_AVAILABLE = False
try:
    import vilib
    from picamera2 import Picamera2
    VISION_AVAILABLE = True
    logger.info("Vision modules available")
except ImportError as e:
    logger.warning(f"Vision modules not available, using mock implementations: {e}")

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
            # Convert distance to time based on speed
            # This is an approximation and may need calibration
            await asyncio.sleep(abs(distance) / max(speed, 1) * 10)
            self.px.stop()
        except Exception as e:
            logger.error(f"Movement error: {e}")
            self.px.stop()  # Safety stop
    
    async def move_backward(self, distance: float, speed: float = 50) -> None:
        """Move backward a specific distance"""
        if not self.initialized:
            logger.warning("Hardware not initialized, simulating movement")
            await asyncio.sleep(abs(distance) / max(speed, 1) * 0.1)
            return
            
        try:
            logger.info(f"Moving backward {distance}m at speed {speed}")
            self.px.backward(speed)
            await asyncio.sleep(abs(distance) / max(speed, 1) * 10)
            self.px.stop()
        except Exception as e:
            logger.error(f"Movement error: {e}")
            self.px.stop()  # Safety stop
    
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
            # Limit the angle to what the hardware can handle
            clamped_angle = max(min(degrees, 35), -35)
            
            if clamped_angle != degrees:
                logger.warning(f"Angle {degrees} clamped to {clamped_angle}")
            
            # Set the steering angle
            self.px.set_dir_servo_angle(clamped_angle)
            
            # If we need to turn more than the hardware allows, we'll need to move forward a bit
            if abs(degrees) > 35:
                # Move forward while turning to achieve a larger turn
                self.px.forward(30)
                await asyncio.sleep(abs(degrees) / 35 * 0.5)
                self.px.stop()
            else:
                # Just wait a moment for the turn to complete
                await asyncio.sleep(abs(degrees) / 90)
            
            # Reset steering to straight
            self.px.set_dir_servo_angle(0)
        except Exception as e:
            logger.error(f"Turn error: {e}")
            self.px.set_dir_servo_angle(0)  # Reset steering
    
    async def scan_surroundings(self, angles: List[float] = [-30, 0, 30]):
        """Scan surroundings by turning to different angles"""
        if not self.initialized:
            logger.warning("Hardware not initialized, simulating scan")
            for angle in angles:
                logger.info(f"Mock: Scanning at angle {angle}")
                await asyncio.sleep(0.5)
            return
        
        try:
            logger.info("Scanning surroundings")
            for angle in angles:
                self.px.set_dir_servo_angle(angle)
                await asyncio.sleep(1)  # Give time to scan at this angle
            
            # Reset to center
            self.px.set_dir_servo_angle(0)
        except Exception as e:
            logger.error(f"Scan error: {e}")
            self.px.set_dir_servo_angle(0)  # Reset steering
    
    async def check_obstacles(self) -> Optional[float]:
        """Check for obstacles using ultrasonic sensor"""
        if not self.initialized:
            logger.warning("Hardware not initialized, simulating obstacle check")
            return None
            
        try:
            # Get distance from ultrasonic sensor
            distance = self.px.ultrasonic.read()
            logger.info(f"Obstacle distance: {distance}cm")
            return distance
        except Exception as e:
            logger.error(f"Obstacle check error: {e}")
            return None
    
    def get_position(self) -> Tuple[float, float, float]:
        """Get the current position and heading"""
        return self.position
    
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
    Integrates with the camera and GPT-4 Vision API
    """
    
    def __init__(self):
        self.camera_initialized = False
        self.camera = None
        
        # Try to initialize camera
        if VISION_AVAILABLE:
            try:
                # Initialize camera using vilib
                vilib.init_camera()
                vilib.camera_start()
                self.camera_initialized = True
                logger.info("Camera initialized successfully using vilib")
            except Exception as e:
                logger.error(f"Failed to initialize camera with vilib: {e}")
                try:
                    # Fallback to picamera2
                    self.camera = Picamera2()
                    self.camera.start()
                    self.camera_initialized = True
                    logger.info("Camera initialized successfully using picamera2")
                except Exception as e2:
                    logger.error(f"Failed to initialize camera with picamera2: {e2}")
        else:
            logger.warning("Vision modules not available, vision will be simulated")
    
    async def capture_image(self, save_path: str = "current_view.jpg"):
        """Capture an image from the camera"""
        if not self.camera_initialized:
            logger.warning("Camera not initialized, simulating capture")
            return None
            
        try:
            if self.camera:
                # Using picamera2
                self.camera.capture_file(save_path)
            else:
                # Using vilib
                import cv2
                frame = vilib.get_frame()
                if frame is not None:
                    cv2.imwrite(save_path, frame)
                else:
                    logger.warning("Failed to get frame from camera")
                    return None
                    
            logger.info(f"Image captured and saved to {save_path}")
            return save_path
        except Exception as e:
            logger.error(f"Image capture error: {e}")
            return None
    
    async def detect_objects(self, image_path: Optional[str] = None):
        """
        Detect objects in an image
        In a real implementation, this would use GPT-4 Vision or another model
        """
        # If we have a real image, capture it
        if self.camera_initialized and image_path is None:
            image_path = await self.capture_image()
        
        if image_path and os.path.exists(image_path):
            # TODO: Replace with actual GPT-4 Vision API call
            logger.info(f"Simulating object detection on {image_path}")
            await asyncio.sleep(1)
            
            # Return mock detection results
            return [
                {"name": "ball", "confidence": 0.85, "position": (2, 1, 0)},
                {"name": "chair", "confidence": 0.75, "position": (3, 2, 0)}
            ]
        else:
            logger.warning("No image available for object detection")
            return []
    
    def cleanup(self):
        """Clean up vision resources"""
        if self.camera_initialized:
            try:
                if self.camera:
                    self.camera.stop()
                else:
                    vilib.camera_release()
                logger.info("Camera resources released")
            except Exception as e:
                logger.error(f"Camera cleanup error: {e}")

class ObstacleAvoidance:
    """
    Obstacle avoidance system for PiCar-X
    """
    
    def __init__(self, car):
        self.car = car
        self.safe_distance = 30  # cm
        logger.info("Obstacle avoidance system initialized")
    
    async def check_path(self) -> bool:
        """Check if the path ahead is clear"""
        if not self.car.initialized:
            return True
            
        distance = await self.car.check_obstacles()
        if distance is None:
            logger.warning("Could not get obstacle distance, assuming path is clear")
            return True
            
        is_clear = distance > self.safe_distance
        if not is_clear:
            logger.warning(f"Obstacle detected at {distance}cm")
        
        return is_clear
    
    async def avoid_obstacle(self) -> bool:
        """Try to avoid an obstacle"""
        logger.info("Attempting to avoid obstacle")
        
        # Scan surroundings to find the best path
        await self.car.scan_surroundings([-30, -15, 0, 15, 30])
        
        # Check left and right
        await self.car.turn(-30)
        left_distance = await self.car.check_obstacles()
        
        await self.car.turn(60)  # Turn from -30 to +30
        right_distance = await self.car.check_obstacles()
        
        # Reset direction
        await self.car.turn(-30)  # Back to center
        
        # Choose the direction with more space
        if left_distance is None and right_distance is None:
            logger.warning("Could not determine obstacle distances, backing up")
            await self.car.move_backward(0.3)
            return False
            
        if (left_distance or 0) > (right_distance or 0):
            logger.info(f"Turning left to avoid obstacle (distance: {left_distance}cm)")
            await self.car.turn(-45)
            await self.car.move_forward(0.5)
        else:
            logger.info(f"Turning right to avoid obstacle (distance: {right_distance}cm)")
            await self.car.turn(45)
            await self.car.move_forward(0.5)
        
        # Check if we're clear now
        return await self.check_path()

# Singleton instances
_hardware = None
_vision = None
_obstacle_avoidance = None

def get_hardware():
    """Get or create the hardware singleton"""
    global _hardware
    if _hardware is None:
        _hardware = PiCarXHardware()
        _hardware.initialize()
    return _hardware

def get_vision_system():
    """Get or create the vision system singleton"""
    global _vision
    if _vision is None:
        _vision = VisionSystem()
    return _vision

def get_obstacle_avoidance():
    """Get or create the obstacle avoidance singleton"""
    global _obstacle_avoidance, _hardware
    if _obstacle_avoidance is None:
        _obstacle_avoidance = ObstacleAvoidance(get_hardware())
    return _obstacle_avoidance

def cleanup_all():
    """Clean up all hardware resources"""
    global _hardware, _vision
    
    if _vision:
        _vision.cleanup()
    
    if _hardware:
        _hardware.cleanup()
