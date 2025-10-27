"""
Unit tests for the command handler.
"""
import pytest
from unittest.mock import MagicMock
from src.agent.command_handler import CommandHandler

class TestCommandHandler:
    """Test cases for CommandHandler."""
    
    @pytest.fixture
    def mock_robot(self):
        """Create a mock robot controller."""
        robot = MagicMock()
        robot.move_forward = MagicMock()
        robot.move_backward = MagicMock()
        robot.turn_left = MagicMock()
        robot.turn_right = MagicMock()
        robot.stop = MagicMock()
        robot.look_around = MagicMock()
        return robot
    
    @pytest.fixture
    def handler(self, mock_robot):
        """Create a CommandHandler with a mock robot."""
        return CommandHandler(mock_robot)
    
    def test_process_command_move_forward(self, handler, mock_robot):
        """Test processing a move forward command."""
        # Test with default speed
        success, response = handler.process_command("move forward")
        assert success is True
        mock_robot.move_forward.assert_called_once_with(50)  # Default speed
        
        # Test with custom speed
        mock_robot.move_forward.reset_mock()
        success, response = handler.process_command("move forward 75 percent")
        assert success is True
        mock_robot.move_forward.assert_called_once_with(75)
    
    def test_process_command_move_backward(self, handler, mock_robot):
        """Test processing a move backward command."""
        # Test with default speed
        success, response = handler.process_command("move backward")
        assert success is True
        mock_robot.move_backward.assert_called_once_with(30)  # Default speed
        
        # Test with custom speed
        mock_robot.move_backward.reset_mock()
        success, response = handler.process_command("move backward 40 percent")
        assert success is True
        mock_robot.move_backward.assert_called_once_with(40)
    
    def test_process_command_turn_left(self, handler, mock_robot):
        """Test processing a turn left command."""
        # Test with default angle
        success, response = handler.process_command("turn left")
        assert success is True
        mock_robot.turn_left.assert_called_once_with(30)  # Default angle
        
        # Test with custom angle
        mock_robot.turn_left.reset_mock()
        success, response = handler.process_command("turn left 45 degrees")
        assert success is True
        mock_robot.turn_left.assert_called_once_with(45)
    
    def test_process_command_turn_right(self, handler, mock_robot):
        """Test processing a turn right command."""
        # Test with default angle
        success, response = handler.process_command("turn right")
        assert success is True
        mock_robot.turn_right.assert_called_once_with(30)  # Default angle
        
        # Test with custom angle
        mock_robot.turn_right.reset_mock()
        success, response = handler.process_command("turn right 45 degrees")
        assert success is True
        mock_robot.turn_right.assert_called_once_with(45)
    
    def test_process_command_stop(self, handler, mock_robot):
        """Test processing a stop command."""
        success, response = handler.process_command("stop")
        assert success is True
        mock_robot.stop.assert_called_once()
    
    def test_process_command_look_around(self, handler, mock_robot):
        """Test processing a look around command."""
        success, response = handler.process_command("look around")
        assert success is True
        mock_robot.look_around.assert_called_once()
    
    def test_process_command_help(self, handler, mock_robot):
        """Test processing a help command."""
        success, response = handler.process_command("help")
        assert success is True
        assert "Here's what I can do" in response
    
    def test_process_command_unknown(self, handler, mock_robot):
        """Test processing an unknown command."""
        success, response = handler.process_command("do something crazy")
        assert success is False
        assert "I'm not sure how to do that" in response
