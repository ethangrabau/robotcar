"""
Integration tests for robot commands.
"""
import pytest
from unittest.mock import MagicMock, patch
from src.agent.command_handler import CommandHandler
from src.movement.navigation import RobotController

class TestRobotCommandsIntegration:
    """Integration tests for robot commands."""
    
    @pytest.fixture
    def robot_controller(self):
        """Create a real robot controller with a mock car."""
        with patch('picarx.Picarx') as mock_picarx:
            controller = RobotController()
            controller.car = mock_picarx()
            yield controller
    
    @pytest.fixture
    def command_handler(self, robot_controller):
        """Create a command handler with a real robot controller."""
        return CommandHandler(robot_controller)
    
    def test_move_forward_integration(self, command_handler, robot_controller):
        """Test the integration of move forward command with robot controller."""
        # Execute
        success, response = command_handler.process_command("move forward 50 percent")
        
        # Verify
        assert success is True
        robot_controller.car.forward.assert_called_once_with(50)
        assert "Moving forward at 50% speed" in response
    
    def test_turn_left_integration(self, command_handler, robot_controller):
        """Test the integration of turn left command with robot controller."""
        # Execute
        success, response = command_handler.process_command("turn left 45 degrees")
        
        # Verify
        assert success is True
        robot_controller.car.set_dir_servo_angle.assert_called_once_with(45)
        assert "Turning left 45 degrees" in response
    
    def test_stop_integration(self, command_handler, robot_controller):
        """Test the integration of stop command with robot controller."""
        # Execute
        success, response = command_handler.process_command("stop")
        
        # Verify
        assert success is True
        robot_controller.car.stop.assert_called_once()
        assert "Stopping all movement" in response
