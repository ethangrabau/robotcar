"""
Speech recognition module using Google's Speech Recognition API.
"""
import speech_recognition as sr
import logging
from typing import Optional, Callable

from src.config import STT_LANGUAGE

class SpeechRecognizer:
    """Handles speech-to-text conversion."""
    
    def __init__(self, language: str = STT_LANGUAGE, energy_threshold: int = 300):
        """Initialize the speech recognizer.
        
        Args:
            language: Language for speech recognition (e.g., 'en-US')
            energy_threshold: Energy level for considering audio as speech
        """
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = energy_threshold
        self.language = language
        self.microphone = None
        
        # Adjust for ambient noise
        self._adjust_for_ambient_noise()
    
    def _adjust_for_ambient_noise(self, duration: float = 1.0):
        """Adjust the recognizer for ambient noise.
        
        Args:
            duration: Duration in seconds to listen for ambient noise
        """
        try:
            with sr.Microphone() as source:
                logging.info("Adjusting for ambient noise...")
                self.recognizer.adjust_for_ambient_noise(source, duration=duration)
        except Exception as e:
            logging.warning(f"Could not adjust for ambient noise: {e}")
    
    def listen(self, timeout: float = 5.0, phrase_time_limit: float = 5.0) -> Optional[str]:
        """Listen for audio input and convert to text.
        
        Args:
            timeout: Time in seconds to wait for speech before timing out
            phrase_time_limit: Maximum length of a phrase in seconds
            
        Returns:
            str: The recognized text, or None if no speech was detected
        """
        try:
            with sr.Microphone() as source:
                logging.info("Listening...")
                audio = self.recognizer.listen(
                    source, 
                    timeout=timeout,
                    phrase_time_limit=phrase_time_limit
                )
                
                logging.info("Processing speech...")
                text = self.recognizer.recognize_google(audio, language=self.language)
                logging.info(f"Recognized: {text}")
                return text.lower()
                
        except sr.WaitTimeoutError:
            logging.info("No speech detected")
            return None
        except sr.UnknownValueError:
            logging.info("Could not understand audio")
            return None
        except sr.RequestError as e:
            logging.error(f"Could not request results from Google Speech Recognition service; {e}")
            return None
        except Exception as e:
            logging.error(f"Error in speech recognition: {e}")
            return None
    
    def continuous_listen(self, 
                         callback: Callable[[str], None], 
                         wake_word: Optional[str] = None,
                         timeout: float = 5.0,
                         phrase_time_limit: float = 5.0):
        """Continuously listen for speech and call the callback with recognized text.
        
        Args:
            callback: Function to call with recognized text
            wake_word: Optional wake word to listen for before processing commands
            timeout: Time in seconds to wait for speech before timing out
            phrase_time_limit: Maximum length of a phrase in seconds
        """
        logging.info(f"Starting continuous listening{' for wake word: ' + wake_word if wake_word else ''}")
        
        while True:
            try:
                text = self.listen(timeout=timeout, phrase_time_limit=phrase_time_limit)
                if text:
                    if not wake_word or wake_word.lower() in text.lower():
                        # Remove wake word from the beginning of the text if present
                        if wake_word and text.lower().startswith(wake_word.lower()):
                            text = text[len(wake_word):].strip()
                        callback(text)
            except KeyboardInterrupt:
                logging.info("Stopping continuous listening")
                break
            except Exception as e:
                logging.error(f"Error in continuous listening: {e}")
                continue
