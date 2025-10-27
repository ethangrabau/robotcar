"""
Unit tests for the voice module.
"""
import pytest
import tempfile
from unittest.mock import MagicMock, patch
from src.voice.speech_recognition import SpeechRecognizer
from src.voice.text_to_speech import TextToSpeech

class TestSpeechRecognizer:
    """Test cases for SpeechRecognizer."""
    
    @pytest.fixture
    def recognizer(self):
        """Create a SpeechRecognizer instance for testing."""
        with patch('speech_recognition.Recognizer') as mock_recognizer:
            with patch('speech_recognition.Microphone'):
                yield SpeechRecognizer()
    
    def test_listen_success(self, recognizer):
        """Test successful speech recognition."""
        # Mock the recognizer to return test text
        recognizer.recognizer.recognize_google.return_value = "test command"
        
        # Call the method
        result = recognizer.listen()
        
        # Verify
        assert result == "test command"
        recognizer.recognizer.listen.assert_called_once()
    
    def test_listen_timeout(self, recognizer):
        """Test speech recognition timeout."""
        # Mock the recognizer to raise a timeout
        recognizer.recognizer.listen.side_effect = recognizer.recognizer.WaitTimeoutError()
        
        # Call the method
        result = recognizer.listen()
        
        # Verify
        assert result is None

class TestTextToSpeech:
    """Test cases for TextToSpeech."""
    
    @pytest.fixture
    def tts(self):
        """Create a TextToSpeech instance for testing."""
        with patch('pygame.mixer.init'), \
             patch('pygame.mixer.music'):
            yield TextToSpeech()
    
    def test_speak_success(self, tts):
        """Test successful text-to-speech conversion."""
        # Mock the gTTS and file operations
        with patch('gtts.gTTS') as mock_gtts, \
             patch('tempfile.NamedTemporaryFile') as mock_temp_file:
            # Setup mock file
            mock_file = MagicMock()
            mock_temp_file.return_value.__enter__.return_value = mock_file
            mock_file.name = "/tmp/test.mp3"
            
            # Call the method
            result = tts.speak("Hello, world!")
            
            # Verify
            assert result is True
            mock_gtts.assert_called_once_with(
                text="Hello, world!",
                lang='en',
                slow=False
            )
    
    def test_speak_empty_text(self, tts):
        """Test speaking empty text."""
        result = tts.speak("")
        assert result is False
    
    def test_stop(self, tts):
        """Test stopping speech."""
        tts.stop()
        tts.mixer.music.stop.assert_called_once()
