"""
Text-to-speech module using Google's Text-to-Speech API.
"""
import os
import tempfile
from typing import Optional
import logging
from gtts import gTTS
import pygame
import time

from src.config import TTS_VOICE, VOLUME_DB

class TextToSpeech:
    """Handles text-to-speech conversion and playback."""
    
    def __init__(self, language: str = 'en', slow: bool = False):
        """Initialize the text-to-speech engine.
        
        Args:
            language: Language for speech synthesis (e.g., 'en')
            slow: Whether to speak slowly
        """
        self.language = language
        self.slow = slow
        self.temp_dir = tempfile.gettempdir()
        self.is_speaking = False
        
        # Initialize pygame mixer
        self._init_audio()
    
    def _init_audio(self):
        """Initialize the audio system."""
        try:
            pygame.mixer.init()
            # Set a reasonable buffer size to avoid audio lag
            pygame.mixer.pre_init(44100, -16, 2, 2048)
            pygame.mixer.init()
            return True
        except Exception as e:
            logging.error(f"Failed to initialize audio: {e}")
            return False
    
    def speak(self, text: str, block: bool = True) -> bool:
        """Convert text to speech and play it.
        
        Args:
            text: The text to speak
            block: If True, block until speech is finished
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not text.strip():
            return False
            
        try:
            # Create a temporary file for the speech
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as f:
                temp_file = f.name
            
            # Generate speech
            tts = gTTS(text=text, lang=self.language, slow=self.slow)
            tts.save(temp_file)
            
            # Play the speech
            return self._play_audio(temp_file, block)
            
        except Exception as e:
            logging.error(f"Error in text-to-speech: {e}")
            return False
        finally:
            # Clean up the temporary file
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
            except:
                pass
    
    def _play_audio(self, file_path: str, block: bool = True) -> bool:
        """Play an audio file.
        
        Args:
            file_path: Path to the audio file
            block: If True, block until playback is finished
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.is_speaking = True
            
            # Load and play the audio file
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.set_volume(1.0)  # Full volume
            pygame.mixer.music.play()
            
            # If blocking, wait for playback to finish
            if block:
                while pygame.mixer.music.get_busy():
                    time.sleep(0.1)
                
            return True
            
        except Exception as e:
            logging.error(f"Error playing audio: {e}")
            return False
        finally:
            self.is_speaking = False
    
    def stop(self):
        """Stop any ongoing speech."""
        try:
            if pygame.mixer.get_init() is not None:
                pygame.mixer.music.stop()
        except:
            pass
        self.is_speaking = False
    
    def is_busy(self) -> bool:
        """Check if the TTS engine is currently speaking.
        
        Returns:
            bool: True if speaking, False otherwise
        """
        try:
            return self.is_speaking or (pygame.mixer.get_init() is not None and pygame.mixer.music.get_busy())
        except:
            return False
    
    def __del__(self):
        """Clean up resources."""
        self.stop()
        try:
            pygame.mixer.quit()
        except:
            pass
