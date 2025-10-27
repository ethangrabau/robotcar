"""
Navigation and movement control for the robot.
"""
import time
from typing import Optional, Tuple
from picarx import Picarx
from robot_hat import Pin

from src.config import (
    DEFAULT_HEAD_TILT,
    DEFAULT_POWER,
    SAFE_DISTANCE,
    DANGER_DISTANCE
)

class RobotController:
    """Handles all robot movement and servo control."""
    
    def __init__(self):
        """Initialize the robot controller."""
        try:
            self.car = Picarx()
            time.sleep(1)  # Allow time for hardware to initialize
            self.led = Pin('LED')
            self.reset()
            print("Robot hardware initialized successfully")
        except Exception as e:
            print(f"Error initializing robot hardware: {e}")
            raise
    
    def reset(self) -> None:
        """Reset all servos and stop all motors."""
        self.car.stop()
        self.car.set_dir_servo_angle(0)
        self.car.set_cam_pan_angle(0)
        self.car.set_cam_tilt_angle(DEFAULT_HEAD_TILT)
    
    def move_forward(self, power: int = DEFAULT_POWER) -> None:
        """Move the robot forward.
        
        Args:
            power: Motor power (0-100)
        """
        self.car.forward(power)
    
    def move_backward(self, power: int = DEFAULT_POWER) -> None:
        """Move the robot backward.
        
        Args:
            power: Motor power (0-100)
        """
        self.car.backward(power)
    
    def turn_left(self, angle: int = 30) -> None:
        """Turn the robot left.
        
        Args:
            angle: Steering angle (degrees)
        """
        self.car.set_dir_servo_angle(angle)
    
    def turn_right(self, angle: int = 30) -> None:
        """Turn the robot right.
        
        Args:
            angle: Steering angle (degrees)
        """
        self.car.set_dir_servo_angle(-angle)
    
    def stop(self) -> None:
        """Stop all movement and center servos."""
        self.reset()
    
    def look_around(self) -> None:
        """Perform a simple look-around pattern."""
        for angle in [30, 0, -30, 0]:
            self.car.set_cam_pan_angle(angle)
            time.sleep(0.5)
        self.car.set_cam_pan_angle(0)
    
    def get_distance(self) -> float:
        """Get the distance to the nearest obstacle in cm.
        
        Returns:
            Distance in centimeters
        """
        return self.car.get_distance()
    
    def is_safe_to_move(self) -> bool:
        """Check if it's safe to move forward.
        
        Returns:
            True if path is clear, False if obstacle is too close
        """
        distance = self.get_distance()
        return distance > SAFE_DISTANCE if distance > 0 else True
    
    def __del__(self):
        """Clean up resources."""
        try:
            self.reset()
            self.car.stop()
        except:
            pass
