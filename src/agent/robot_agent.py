"""
Main agent class for the family robot assistant.
"""
import os
import time
import logging
from typing import Optional, Callable

from src.movement.navigation import RobotController
from src.voice import SpeechRecognizer, TextToSpeech
from .command_handler import CommandHandler
from src.config import (
    LOG_LEVEL, LOG_FORMAT, LOG_FILE,
    STT_LANGUAGE, TTS_LANGUAGE, TTS_VOICE, VOLUME_DB,
    WAKE_WORD
)

# Configure logging
logging.basicConfig(
    level=LOG_LEVEL,
    format=LOG_FORMAT,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_FILE)
    ]
)
logger = logging.getLogger(__name__)

class RobotAgent:
    """Main agent class that ties together all robot components."""
    
    def __init__(self, use_voice: bool = True, wake_word: Optional[str] = WAKE_WORD):
        """Initialize the robot agent.
        
        Args:
            use_voice: Whether to enable voice input/output
            wake_word: Optional wake word to listen for
        """
        self.use_voice = use_voice
        self.wake_word = wake_word.lower() if wake_word else None
        self.is_running = False
        
        # Initialize components
        self._init_components()
        
    def _init_components(self):
        """Initialize all robot components."""
        logger.info("Initializing robot components...")
        
        try:
            # Initialize robot controller
            self.robot = RobotController()
            logger.info("Robot controller initialized")
            
            # Initialize voice components if enabled
            if self.use_voice:
                self.speech_recognizer = SpeechRecognizer(language=STT_LANGUAGE)
                self.tts = TextToSpeech(language=TTS_LANGUAGE)
                logger.info("Voice components initialized")
            
            # Initialize command handler
            self.command_handler = CommandHandler(self.robot)
            logger.info("Command handler initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize components: {e}")
            self.cleanup()
            raise
    
    def speak(self, text: str, block: bool = True) -> bool:
        """Speak the given text if voice is enabled.
        
        Args:
            text: The text to speak
            block: Whether to block until speech is complete
            
        Returns:
            bool: True if speech was initiated successfully
        """
        if not self.use_voice or not hasattr(self, 'tts'):
            print(f"[ROBOT] {text}")
            return False
            
        return self.tts.speak(text, block=block)
    
    def listen(self, timeout: float = 5.0) -> Optional[str]:
        """Listen for voice input if voice is enabled.
        
        Args:
            timeout: Time in seconds to wait for input
            
        Returns:
            str: The recognized text, or None if no speech was detected
        """
        if not self.use_voice or not hasattr(self, 'speech_recognizer'):
            return input("Enter command: ")
            
        return self.speech_recognizer.listen(timeout=timeout)
    
    def process_command(self, command: str) -> bool:
        """Process a command and execute the corresponding action.
        
        Args:
            command: The command to process
            
        Returns:
            bool: True if the command was processed successfully
        """
        if not command:
            return False
            
        # Check for wake word if one is set
        if self.wake_word and self.wake_word in command.lower():
            # Remove wake word from command
            command = command.lower().replace(self.wake_word, '').strip()
            if not command:  # If only wake word was said
                self.speak("Yes? How can I help you?")
                return True
        
        # Process the command
        success, response = self.command_handler.process_command(command)
        
        # Speak or print the response
        if response:
            self.speak(response)
            
        return success
    
    def run_interactive(self):
        """Run the robot in interactive mode, listening for commands."""
        self.is_running = True
        
        try:
            # Greet the user
            greeting = f"Hello! I'm your family robot assistant."
            if self.wake_word:
                greeting += f" Say '{self.wake_word}' followed by a command."
            self.speak(greeting)
            
            # Main loop
            while self.is_running:
                try:
                    # Listen for a command
                    command = self.listen()
                    
                    # Process the command
                    if command and command.lower() in ['exit', 'quit', 'goodbye']:
                        self.speak("Goodbye!")
                        break
                        
                    if command:
                        self.process_command(command)
                        
                except KeyboardInterrupt:
                    logger.info("Keyboard interrupt received, shutting down...")
                    break
                except Exception as e:
                    logger.error(f"Error in main loop: {e}")
                    self.speak("Sorry, I encountered an error. Please try again.")
                    
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources."""
        logger.info("Cleaning up...")
        self.is_running = False
        
        # Stop the robot
        if hasattr(self, 'robot'):
            try:
                self.robot.stop()
            except Exception as e:
                logger.error(f"Error stopping robot: {e}")
        
        # Clean up voice components
        if hasattr(self, 'tts'):
            try:
                self.tts.stop()
            except Exception as e:
                logger.error(f"Error cleaning up TTS: {e}")
        
        logger.info("Cleanup complete")
    
    def __del__(self):
        """Ensure resources are cleaned up when the object is destroyed."""
        self.cleanup()

def main():
    """Main entry point for the robot agent."""
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Family Robot Assistant')
    parser.add_argument('--no-voice', action='store_true', help='Disable voice input/output')
    parser.add_argument('--wake-word', type=str, default=WAKE_WORD, 
                       help=f'Wake word to listen for (default: {WAKE_WORD})')
    args = parser.parse_args()
    
    # Create and run the robot agent
    try:
        robot = RobotAgent(use_voice=not args.no_voice, wake_word=args.wake_word)
        robot.run_interactive()
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        print(f"\nA fatal error occurred: {e}")
        print("Check the logs for more details.")
    finally:
        if 'robot' in locals():
            robot.cleanup()

if __name__ == "__main__":
    main()
