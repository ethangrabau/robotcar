"""
Test script for basic robot movement functionality.
"""
import time
import unittest
from unittest.mock import MagicMock, patch

from src.movement.navigation import RobotController
from src.utils.gpio_utils import setup_gpio, safe_shutdown, is_raspberry_pi

class TestRobotMovement(unittest.TestCase):
    """Test cases for robot movement."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a mock for the Picarx class
        self.mock_car = MagicMock()
        
        # Patch the Picarx class to return our mock
        self.patcher = patch('picarx.Picarx', return_value=self.mock_car)
        self.mock_picarx = self.patcher.start()
        
        # Initialize the robot controller
        self.robot = RobotController()
        
    def tearDown(self):
        """Clean up after tests."""
        self.patcher.stop()
        
    def test_move_forward(self):
        """Test moving forward."""
        self.robot.move_forward(50)
        self.mock_car.forward.assert_called_once_with(50)
    
    def test_turn_left(self):
        """Test turning left."""
        self.robot.turn_left(30)
        self.mock_car.set_dir_servo_angle.assert_called_once_with(30)
    
    def test_stop(self):
        """Test stopping the robot."""
        self.robot.stop()
        self.mock_car.stop.assert_called_once()
        self.mock_car.set_dir_servo_angle.assert_called_once_with(0)
        self.mock_car.set_cam_pan_angle.assert_called_once_with(0)

class TestHardwareIntegration(unittest.TestCase):
    """Integration tests with actual hardware."""
    
    @classmethod
    def setUpClass(cls):
        """Set up the robot controller with actual hardware."""
        if not is_raspberry_pi():
            return
            
        try:
            # Set up GPIO before initializing hardware
            setup_gpio()
            
            # Initialize the robot controller
            cls.robot = RobotController()
            cls.hardware_available = True
            
            # Register cleanup for safe exit
            import atexit
            atexit.register(safe_shutdown)
            
        except Exception as e:
            print(f"Hardware initialization failed: {e}")
            cls.hardware_available = False
    
    def test_basic_movements(self):
        """Test basic movements if hardware is available."""
        if not self.hardware_available:
            self.skipTest("Hardware not available or initialization failed")
            
        try:
            # Test forward movement
            print("Testing forward movement...")
            self.robot.move_forward(30)
            time.sleep(1)
            self.robot.stop()
            
            # Test turning
            print("Testing turning...")
            self.robot.turn_left(30)
            time.sleep(1)
            self.robot.turn_right(30)
            time.sleep(1)
            self.robot.stop()
            
            # Test looking around
            print("Testing camera movement...")
            self.robot.look_around()
            
            print("All tests completed successfully!")
            
        except Exception as e:
            self.fail(f"Test failed with error: {e}")
        finally:
            self.robot.stop()

if __name__ == "__main__":
    unittest.main()
