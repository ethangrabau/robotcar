"""
End-to-end tests for voice commands.
"""
import pytest
from unittest.mock import MagicMock, patch
from src.agent.robot_agent import RobotAgent

class TestVoiceCommandsE2E:
    """End-to-end tests for voice commands."""
    
    @pytest.fixture
    def robot_agent(self):
        """Create a robot agent with mocked components."""
        with patch('src.voice.speech_recognition.SpeechRecognizer') as mock_sr, \
             patch('src.voice.text_to_speech.TextToSpeech') as mock_tts, \
             patch('src.movement.navigation.RobotController') as mock_robot:
            
            # Create the robot agent
            agent = RobotAgent(use_voice=True)
            
            # Save references to the mocks
            agent.speech_recognizer = mock_sr
            agent.tts = mock_tts
            agent.robot = mock_robot
            
            # Configure the speech recognizer
            agent.speech_recognizer.listen.return_value = "robot move forward 50 percent"
            
            yield agent
    
    def test_voice_command_processing(self, robot_agent):
        """Test that voice commands are properly processed and executed."""
        # Mock the command handler's process_command method
        mock_process_command = MagicMock(return_value=(True, "Moving forward at 50% speed"))
        robot_agent.command_handler.process_command = mock_process_command
        
        # Mock the TTS speak method
        robot_agent.tts.speak.return_value = True
        
        # Run the interactive mode (will exit after one command due to our mock)
        robot_agent.running = False  # Ensure it only runs once
        robot_agent.run_interactive()
        
        # Verify the command was processed
        mock_process_command.assert_called_once_with("move forward 50 percent")
        
        # Verify the response was spoken
        robot_agent.tts.speak.assert_called_once_with("Moving forward at 50% speed")
    
    def test_wake_word_handling(self, robot_agent):
        """Test that the wake word is properly handled."""
        # Set up the test
        robot_agent.speech_recognizer.listen.return_value = "robot what time is it"
        mock_process_command = MagicMock(return_value=(True, "The time is 3:00 PM"))
        robot_agent.command_handler.process_command = mock_process_command
        robot_agent.tts.speak.return_value = True
        
        # Run the test
        robot_agent.running = False  # Ensure it only runs once
        robot_agent.run_interactive()
        
        # Verify the wake word was removed
        mock_process_command.assert_called_once_with("what time is it")
