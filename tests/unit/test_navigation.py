"""
Unit tests for the navigation module.
"""
import pytest
from unittest.mock import MagicMock, patch
from src.movement.navigation import RobotController

class TestRobotController:
    """Test cases for RobotController."""
    
    def test_move_forward(self, mock_robot_controller):
        """Test moving forward with a given speed."""
        # Setup
        controller = RobotController()
        test_speed = 50
        
        # Execute
        controller.move_forward(test_speed)
        
        # Verify
        controller.car.forward.assert_called_once_with(test_speed)
    
    def test_move_backward(self, mock_robot_controller):
        """Test moving backward with a given speed."""
        # Setup
        controller = RobotController()
        test_speed = 30
        
        # Execute
        controller.move_backward(test_speed)
        
        # Verify
        controller.car.backward.assert_called_once_with(test_speed)
    
    def test_turn_left(self, mock_robot_controller):
        """Test turning left by a given angle."""
        # Setup
        controller = RobotController()
        test_angle = 45
        
        # Execute
        controller.turn_left(test_angle)
        
        # Verify
        controller.car.set_dir_servo_angle.assert_called_once_with(test_angle)
    
    def test_turn_right(self, mock_robot_controller):
        """Test turning right by a given angle."""
        # Setup
        controller = RobotController()
        test_angle = 45
        
        # Execute
        controller.turn_right(test_angle)
        
        # Verify
        controller.car.set_dir_servo_angle.assert_called_once_with(-test_angle)
    
    def test_stop(self, mock_robot_controller):
        """Test stopping all movement."""
        # Setup
        controller = RobotController()
        
        # Execute
        controller.stop()
        
        # Verify
        controller.car.stop.assert_called_once()
        controller.car.set_dir_servo_angle.assert_called_once_with(0)
        controller.car.set_cam_pan_angle.assert_called_once_with(0)
