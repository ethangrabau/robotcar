"""
Command handler for processing voice commands and executing robot actions.
"""
import re
import logging
from typing import Dict, Callable, Any, Optional, List, Tuple

class CommandHandler:
    """Handles voice commands and maps them to robot actions."""
    
    def __init__(self, robot_controller):
        """Initialize the command handler.
        
        Args:
            robot_controller: Instance of RobotController for movement control
        """
        self.robot = robot_controller
        self.commands = self._initialize_commands()
        
    def _initialize_commands(self) -> Dict[str, Dict[str, Any]]:
        """Initialize the command patterns and their handlers.
        
        Returns:
            Dict containing command patterns and their handlers
        """
        return {
            "move_forward": {
                "patterns": [
                    r"go forward(?: (\d+) (?:percent|%))?",
                    r"move forward(?: (\d+) (?:percent|%))?",
                    r"drive forward(?: (\d+) (?:percent|%))?",
                ],
                "handler": self._handle_move_forward,
                "help": "Move forward [speed in %]"
            },
            "move_backward": {
                "patterns": [
                    r"go backward(?: (\d+) (?:percent|%))?",
                    r"move backward(?: (\d+) (?:percent|%))?",
                    r"drive backward(?: (\d+) (?:percent|%))?",
                    r"reverse(?: (\d+) (?:percent|%))?",
                ],
                "handler": self._handle_move_backward,
                "help": "Move backward [speed in %]"
            },
            "turn_left": {
                "patterns": [
                    r"turn left(?: (\d+) degrees)?",
                    r"go left(?: (\d+) degrees)?",
                    r"steer left(?: (\d+) degrees)?",
                ],
                "handler": self._handle_turn_left,
                "help": "Turn left [angle in degrees]"
            },
            "turn_right": {
                "patterns": [
                    r"turn right(?: (\d+) degrees)?",
                    r"go right(?: (\d+) degrees)?",
                    r"steer right(?: (\d+) degrees)?",
                ],
                "handler": self._handle_turn_right,
                "help": "Turn right [angle in degrees]"
            },
            "stop": {
                "patterns": [
                    r"stop",
                    r"halt",
                    r"freeze",
                    r"emergency stop",
                ],
                "handler": self._handle_stop,
                "help": "Stop all movement"
            },
            "look_around": {
                "patterns": [
                    r"look around",
                    r"scan area",
                    r"survey the area",
                ],
                "handler": self._handle_look_around,
                "help": "Look around with the camera"
            },
            "help": {
                "patterns": [
                    r"help",
                    r"what can you do",
                    r"list commands",
                ],
                "handler": self._handle_help,
                "help": "Show available commands"
            },
        }
    
    def process_command(self, command: str) -> Tuple[bool, str]:
        """Process a voice command and execute the corresponding action.
        
        Args:
            command: The voice command string
            
        Returns:
            Tuple of (success, response_message)
        """
        if not command.strip():
            return False, "I didn't hear a command."
            
        command = command.lower().strip()
        logging.info(f"Processing command: {command}")
        
        # Check for matching command patterns
        for cmd_name, cmd_info in self.commands.items():
            for pattern in cmd_info["patterns"]:
                match = re.fullmatch(pattern, command)
                if match:
                    try:
                        response = cmd_info["handler"](*match.groups())
                        return True, response or f"Executed: {cmd_name}"
                    except Exception as e:
                        logging.error(f"Error executing command {cmd_name}: {e}")
                        return False, f"Sorry, I couldn't execute that command: {str(e)}"
        
        return False, "I'm not sure how to do that. Say 'help' for a list of commands."
    
    # Command handlers
    def _handle_move_forward(self, speed_str: str = None) -> str:
        """Handle move forward command."""
        speed = self._parse_speed(speed_str, default=50)
        self.robot.move_forward(speed)
        return f"Moving forward at {speed}% speed"
    
    def _handle_move_backward(self, speed_str: str = None) -> str:
        """Handle move backward command."""
        speed = self._parse_speed(speed_str, default=30)  # Safer default for reverse
        self.robot.move_backward(speed)
        return f"Moving backward at {speed}% speed"
    
    def _handle_turn_left(self, angle_str: str = None) -> str:
        """Handle turn left command."""
        angle = self._parse_angle(angle_str, default=30)
        self.robot.turn_left(angle)
        return f"Turning left {angle} degrees"
    
    def _handle_turn_right(self, angle_str: str = None) -> str:
        """Handle turn right command."""
        angle = self._parse_angle(angle_str, default=30)
        self.robot.turn_right(angle)
        return f"Turning right {angle} degrees"
    
    def _handle_stop(self) -> str:
        """Handle stop command."""
        self.robot.stop()
        return "Stopping all movement"
    
    def _handle_look_around(self) -> str:
        """Handle look around command."""
        self.robot.look_around()
        return "Looking around"
    
    def _handle_help(self) -> str:
        """Handle help command."""
        help_text = "Here's what I can do:\n"
        for cmd_info in self.commands.values():
            help_text += f"- {cmd_info['help']}\n"
        return help_text
    
    # Utility methods
    def _parse_speed(self, speed_str: Optional[str], default: int = 50) -> int:
        """Parse speed from string, ensuring it's within valid range."""
        if not speed_str:
            return default
            
        try:
            speed = int(speed_str)
            return max(0, min(100, speed))  # Clamp between 0 and 100
        except (ValueError, TypeError):
            return default
    
    def _parse_angle(self, angle_str: Optional[str], default: int = 30) -> int:
        """Parse angle from string, ensuring it's within valid range."""
        if not angle_str:
            return default
            
        try:
            angle = int(angle_str)
            return max(0, min(90, angle))  # Clamp between 0 and 90 degrees
        except (ValueError, TypeError):
            return default
